"""Combine independently reconstructed RQ2 runs and regenerate their summaries."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import pandas as pd
from compare import compare_ordered_contrast, validate_monthly_grid
from future_reuse import METHODS
from temporal_components import FULL, NAMES
from rq2_summaries import reproduce, GRID_BASELINES


def merge_monthly(parts, expected_methods):
    keys = ["month", "method", "metric"]
    columns = list(parts[0].columns)
    combined = parts[0].iloc[:0].copy()
    for part in parts:
        if set(part.columns) != set(columns) or part[keys].isna().any().any() or part.duplicated(keys).any():
            raise ValueError("Invalid monthly source schema or duplicated result keys")
        part = part[columns]
        left, right = combined.set_index(keys), part.set_index(keys)
        common = left.index.intersection(right.index)
        if len(common):
            pd.testing.assert_frame_equal(left.loc[common], right.loc[common], check_dtype=False, check_exact=True)
        combined = pd.concat([combined, right.loc[~right.index.isin(left.index)].reset_index()[columns]], ignore_index=True)
    if set(combined.method) != set(expected_methods):
        raise ValueError("Reconstructed methods differ from the required grid")
    return combined.sort_values(keys).reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporal", type=Path, required=True, help="Output directory of temporal_components.py")
    parser.add_argument("--parameters", type=Path, required=True, help="Output directory of parameter_grid.py")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root, output = Path(__file__).resolve().parent, args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if output == root or root in output.parents:
        raise ValueError("Keep generated results outside the replication package")
    bound = {}

    def bind(path):
        path = Path(path).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if str(path) in bound and bound[str(path)] != digest:
            raise ValueError("Input changed during computation")
        bound[str(path)] = digest
        return path

    for name in ("rq2_reconstruction.py", "rq2_summaries.py", "compare.py",
                 "future_reuse.py", "temporal_components.py"):
        bind(root / name)
    protocol = json.loads(bind(root / "data/comparison_protocol.json").read_text(encoding="utf-8"))
    specs = pd.read_csv(bind(root / "results/table_sources/parameter_specs.csv"), float_precision="round_trip")
    expected = set(METHODS) | set(NAMES) | set(specs.specification_id)
    if len(specs) != 29 or len(expected) != 45:
        raise ValueError("Expected 29 configurations and 45 distinct methods")
    paths = [args.temporal / "primary_monthly.csv", args.temporal / "component_monthly.csv",
             args.parameters / "monthly.csv"]
    parts = [pd.read_csv(bind(p), float_precision="round_trip") for p in paths]
    monthly = merge_monthly(parts, expected)
    validate_monthly_grid(monthly, expected, protocol)
    if len(monthly) != 5130:
        raise ValueError("Incomplete monthly evaluation grid")
    contrasts = {
        "primary_comparisons_21.csv": [(METHODS[0], b) for b in METHODS[1:]],
        "mtpr_ablation_comparisons.csv": [(FULL, b) for b in NAMES],
        "grid_comparisons.csv": [(c, b) for c in specs.specification_id for b in GRID_BASELINES],
    }
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "summary_inputs"
    for rel in ("data/comparison_protocol.json", "results/table_sources/parameter_specs.csv",
                "data/top_decile/populations.csv", "compare.py", "rq2_summaries.py"):
        target = inputs / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bind(root / rel), target)
    results = inputs / "results/rq2"
    results.mkdir(parents=True, exist_ok=False)
    monthly.to_csv(results / "monthly_all.csv", index=False)
    comparison_counts = {}
    for name, pairs in contrasts.items():
        table = pd.concat([compare_ordered_contrast(monthly, a, b, protocol) for a, b in pairs], ignore_index=True)
        table.to_csv(results / name, index=False)
        comparison_counts[name] = len(table)
    tables, _, summary_bindings = reproduce(inputs)
    for rel, table in tables.items():
        target = output / "summaries" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(target, index=False)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in bound.items()):
        raise ValueError("Input changed during computation")
    report = dict(inputs_sha256=bound, monthly_rows=len(monthly), unique_methods=len(expected),
        comparison_rows=comparison_counts, summaries={n: len(t) for n, t in tables.items()},
        summary_inputs_sha256=summary_bindings, overlap_policy="Exact equality before deduplication",
        scope="Monthly evaluations from reconstructed primary, component and parameter runs")
    (output / "verification.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print("RQ2_RECONSTRUCTION", len(monthly), sum(comparison_counts.values()), flush=True)


if __name__ == "__main__":
    main()

