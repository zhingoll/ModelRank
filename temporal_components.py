"""Recompute temporal MTPR and seven matched component removals."""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd
from scipy import sparse
from graph_inputs import GraphInputs
from primary import primary_score
from scoring import ScoreConfig, score_month
from reuse import evaluate_candidate_month
from compare import compare_ordered_contrast, validate_monthly_grid
from future_reuse import METHODS, MONTHS

FULL = "MTPR_time_safe_typed"
NAMES = ["No child quality", "No type weight", "No parent size",
         "No quality teleport", "No PageRank propagation",
         "No temporal inheritance", "No event injection"]
VARIANT_SPECS = {
    "Full ModelRank": {},
    "No child quality": {"child_quality": False},
    "No type weight": {"type_weight": False},
    "No parent size": {"parent_size": False},
    "No quality teleport": {"quality_teleport": False},
    "No PageRank propagation": {"pagerank_propagation": False},
    "No temporal inheritance": {"beta": 0.0},
    "No event injection": {"lambda_e": 0.0},
}
FULL_CONFIG = ScoreConfig("Full ModelRank recomputation", 1., .8,
                         direct_blend=.10, beta=.15, mix_mode="raw")

def compute_modelrank_variants(
    model_ids: Iterable[str],
    edges: Iterable[tuple[str, str, str]],
    q_base: dict[str, float],
    params: dict[str, float | None],
    previous: dict[str, object] | None,
) -> dict[str, dict[str, float]]:
    """Compute one-component removals on an identical monthly node/event graph."""
    ordered = list(dict.fromkeys(str(model_id) for model_id in model_ids))
    if not ordered:
        return {name: {} for name in VARIANT_SPECS}
    id_to_index = {model_id: index for index, model_id in enumerate(ordered)}
    size = len(ordered)
    q_values = np.array([float(q_base.get(model_id, 0.0)) for model_id in ordered])
    if not np.isfinite(q_values).all():
        raise ValueError("q_base contains nonfinite values")
    q_values = np.maximum(0.0, q_values)
    q_max = max(1.0, float(q_values.max()))
    parents_by_child: dict[int, list[tuple[int, str]]] = {}
    for child, parent, relation in sorted(set(edges)):
        if child not in id_to_index or parent not in id_to_index:
            continue
        parents_by_child.setdefault(id_to_index[child], []).append(
            (id_to_index[parent], str(relation).lower())
        )
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    for child_index, parents in parents_by_child.items():
        share = 1.0 / len(parents)
        for parent_index, _relation in parents:
            rows.append(child_index)
            columns.append(parent_index)
            values.append(share)
    transition = sparse.csr_matrix((values, (rows, columns)), shape=(size, size))
    dangling = np.asarray(transition.sum(axis=1)).ravel() == 0
    type_weights = {"finetune": 1.0, "adapter": 0.8, "merge": 0.5, "quantized": 0.3}

    previous = previous or {}
    nested_previous = bool(previous) and isinstance(next(iter(previous.values())), dict)
    results: dict[str, dict[str, float]] = {}
    for variant, overrides in VARIANT_SPECS.items():
        signal_mode = str(overrides.get("signal_mode", "full"))
        use_child_quality = bool(overrides.get("child_quality", True))
        use_type_weight = bool(overrides.get("type_weight", True))
        use_parent_size = bool(overrides.get("parent_size", True))
        use_quality_teleport = bool(overrides.get("quality_teleport", True))
        use_propagation = bool(overrides.get("pagerank_propagation", True))
        lambda_e = float(overrides.get("lambda_e", 0.8))
        lambda_q = float(overrides.get("lambda_q", 0.10))
        beta = float(overrides.get("beta", 0.15))
        event_value = np.zeros(size, dtype=float)
        for child_index, parents in parents_by_child.items():
            share = 1.0 / len(parents)
            quality_factor = (
                0.3 + 0.7 * (q_values[child_index] / q_max)
                if use_child_quality else 1.0
            )
            for parent_index, relation in parents:
                relation_weight = type_weights.get(relation, 0.5) if use_type_weight else 1.0
                parent_id = ordered[parent_index]
                parameter_value = params.get(parent_id)
                if parameter_value is None or not np.isfinite(float(parameter_value)) or float(parameter_value) <= 0:
                    parameter_value = 66_955_779.0
                size_factor = np.log1p(float(parameter_value)) ** 0.5 if use_parent_size else 1.0
                event_value[parent_index] += (
                    share * relation_weight * quality_factor * size_factor
                )
        if signal_mode == "quality_only":
            tau = q_values.copy()
            if float(tau.sum()) <= 0:
                tau.fill(1.0)
        elif signal_mode == "structural_event":
            tau = event_value.copy()
            if float(tau.sum()) <= 0:
                tau.fill(1.0)
        elif use_quality_teleport:
            tau = q_values + lambda_e * event_value
            if float(tau.sum()) <= 0:
                tau.fill(1.0)
        else:
            # Remove only the direct q_base teleport contribution.  Event
            # injection remains active (and may still carry child-quality
            # weighting), so this ablation is not a full quality removal.
            tau = lambda_e * event_value
            if float(tau.sum()) <= 0:
                tau.fill(1.0)
        tau /= float(tau.sum())
        if signal_mode == "quality_only":
            page_rank = tau.copy()
        elif use_propagation:
            page_rank = tau.copy()
            for _ in range(200):
                updated = 0.85 * (transition.T @ page_rank)
                updated += 0.85 * float(page_rank[dangling].sum()) * tau
                updated += 0.15 * tau
                updated /= float(updated.sum())
                difference = float(np.abs(updated - page_rank).sum())
                page_rank = updated
                if difference < 1e-8:
                    break
            else:
                raise ValueError("MTPR variant did not converge within the iteration limit: " + variant)
        else:
            page_rank = tau.copy()
        raw = (
            tau.copy() if signal_mode == "quality_only"
            else (1.0 - lambda_q) * page_rank + lambda_q * tau
        )
        previous_scores = previous.get(variant, {}) if nested_previous else previous
        if beta > 0 and isinstance(previous_scores, dict) and previous_scores:
            inherited = np.array([
                float(previous_scores.get(model_id, 0.0)) for model_id in ordered
            ])
            if not np.isfinite(inherited).all():
                raise ValueError("previous_scores contains nonfinite values")
            inherited = np.maximum(0.0, inherited)
            if float(inherited.sum()) > 0:
                inherited /= float(inherited.sum())
                final = (1.0 - beta) * raw + beta * inherited
            else:
                final = raw
        else:
            final = raw
        final /= float(final.sum())
        results[variant] = {
            model_id: float(final[index]) for index, model_id in enumerate(ordered)
        }
    return results


def temporal_step(frame, events, params, variant_previous, full_previous):
    ids = frame.model_id.tolist()
    if not ids or frame.model_id.isna().any() or not frame.model_id.is_unique:
        raise ValueError("Invalid node population")
    observations = frame[["Downloads", "Likes"]].to_numpy(float)
    if not np.isfinite(observations).all() or (observations < 0).any():
        raise ValueError("Invalid observations")
    universe = set(ids)
    if any(c not in universe or p not in universe for c, p, _ in events):
        raise ValueError("Unknown event endpoint")
    q = dict(zip(ids, .5*np.log1p(frame.Downloads) + .5*np.log1p(frame.Likes)))
    variants = compute_modelrank_variants(ids, events, q, params, variant_previous)
    primary = score_month(ids, events, events, q, params, full_previous, FULL_CONFIG)
    raw = frame[["model_id", "Downloads", "Likes"]].copy()
    raw[FULL] = [variants["Full ModelRank"][i] * len(ids) for i in ids]
    for name in NAMES:
        raw[name] = [variants[name][i] * len(ids) for i in ids]
    aligned = raw.copy()
    aligned[FULL] = [primary.score_normalized[i] for i in ids]
    np.testing.assert_allclose(raw[FULL], aligned[FULL], rtol=1e-10, atol=1e-8)
    for scores in (raw, aligned):
        values = scores[[FULL, *NAMES]].to_numpy(float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError("Invalid temporal scores")
        np.testing.assert_allclose(values.sum(axis=0), len(ids), rtol=1e-12)
    return raw, aligned, variants, dict(primary.scores), primary


def primary_panel(frame, edges, current, full):
    ids = frame.model_id.tolist()
    q = dict(zip(ids, .5*np.log1p(frame.Downloads) + .5*np.log1p(frame.Likes)))
    panel = frame[["model_id", "Downloads", "Likes"]].copy()
    panel["S_C3_Q10"], _ = primary_score(ids, frame.Downloads, frame.Likes, current, edges)
    panel["Vanilla PageRank"], _ = primary_score(ids, frame.Downloads, frame.Likes, current, edges, vanilla=True)
    panel["AllTime DerivCount"] = frame.model_id.map(edges.parent_id.value_counts()).fillna(0).astype(int)
    panel["Current DerivCount"] = frame.model_id.map(current.parent_id.value_counts()).fillna(0).astype(int)
    events = [(c, p, "pair") for c, p in current[["child_id", "parent_id"]].itertuples(index=False, name=None)]
    no = score_month(ids, [], events, q, {}, {}, ScoreConfig("matched no propagation", .1, .9,
        child_quality=False, type_weight=False, parent_size=False, damping=0, beta=0))
    panel["No-Propagation ModelRank"] = [no.score_normalized[i] for i in ids]
    panel[FULL] = [full.score_normalized[i] for i in ids]
    panel["EventValue_time_safe_typed"] = [full.trace.event_value[i] for i in ids]
    panel["Simplified_MTPR_time_safe_typed"] = [q[i] + .8*full.trace.event_value[i] for i in ids]
    return panel


def evaluate(panel, outcomes, month, methods, protocol):
    low = panel.loc[panel.Downloads.lt(panel.Downloads.quantile(.9))].reset_index(drop=True)
    if low.model_id.tolist() != outcomes.model_id.tolist():
        raise ValueError("Score and outcome populations differ")
    applicable = {f: names for f, names in protocol["metric_families"].items()
                  if f != "repropagation" or month in protocol["origins"]["repropagation"]}
    metrics = [m for names in applicable.values() for m in names]
    if set(outcomes.columns) != {"model_id", *metrics}:
        raise ValueError("Outcome columns differ from the origin protocol")
    low = pd.concat([low, outcomes[metrics]], axis=1)
    result = evaluate_candidate_month(low, month, methods, {**protocol, "metric_families": applicable})
    result["scheme"] = "primary"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--outcomes", type=Path, required=True)
    args = parser.parse_args()
    root, output = Path(__file__).resolve().parent, args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if output == root or root in output.parents:
        raise ValueError("Keep generated results outside the replication package")
    bindings = {}

    def bind(path):
        path = Path(path).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if str(path) in bindings and bindings[str(path)] != digest:
            raise ValueError("Input changed during computation")
        bindings[str(path)] = digest
        return path

    for name in ("temporal_components.py", "primary.py", "scoring.py", "graph_inputs.py",
                 "graph_clock.py", "reuse.py", "compare.py", "future_reuse.py"):
        bind(root / name)
    protocol = json.loads(bind(root / "data/comparison_protocol.json").read_text(encoding="utf-8"))
    if protocol["origins"]["three_month"] != MONTHS[11:17]:
        raise ValueError("Expected the fixed six evaluation origins")
    graph = GraphInputs(pd.read_parquet(bind(root / "assets/core/first_observed_edges.parquet")),
                        bind(root / "data/derivation_evidence/relations.csv"))
    metadata = pd.read_parquet(bind(root / "assets/core/models.parquet"), columns=["id", "params"])
    metadata = metadata.drop_duplicates("id", keep="last")
    parameter_values = pd.to_numeric(metadata.params, errors="coerce")
    params = dict(zip(metadata.id.astype(str), [None if pd.isna(v) else float(v) for v in parameter_values]))
    del metadata, parameter_values
    output.mkdir(parents=True, exist_ok=False)
    state, primary_state, trace, primary_rows, component_rows = {}, {}, [], [], []
    for month in MONTHS[:17]:
        frame = pd.read_parquet(bind(root / "assets/core/panel" / (month + ".parquet")),
                                columns=["model_id", "Downloads", "Likes"]).sort_values("model_id").reset_index(drop=True)
        edges, current, typed = graph.month(frame.model_id, month, first_empty=(month == MONTHS[0]))
        tuples = list(typed[["child_id", "parent_id", "relation"]].itertuples(index=False, name=None))
        raw, aligned, state, primary_state, full = temporal_step(frame, tuples, params, state, primary_state)
        trace.append(dict(month=month, nodes=len(frame), active_pairs=len(edges), pair_events=len(current),
                          typed_events=len(typed), primary_iterations=full.trace.iterations,
                          raw_full_max_difference=float(abs(raw[FULL]-aligned[FULL]).max())))
        if month in protocol["origins"]["three_month"]:
            panel = primary_panel(frame, edges, current, full)
            raw.to_parquet(output / (month + "_raw_components.parquet"), index=False)
            aligned.to_parquet(output / (month + "_components.parquet"), index=False)
            panel.to_parquet(output / (month + ".parquet"), index=False)
            outcomes = pd.read_parquet(bind(args.outcomes / (month + "_outcomes.parquet")))
            primary_rows.append(evaluate(panel, outcomes, month, METHODS, protocol))
            component_rows.append(evaluate(aligned, outcomes, month, [FULL, *NAMES], protocol))
            del panel, outcomes
        print("TEMPORAL_COMPONENTS", month, len(frame), flush=True)
        del raw, aligned, full, frame, edges, current, typed, tuples
        gc.collect()
    primary_rows, component_rows = pd.concat(primary_rows, ignore_index=True), pd.concat(component_rows, ignore_index=True)
    validate_monthly_grid(primary_rows, METHODS, protocol)
    validate_monthly_grid(component_rows, [FULL, *NAMES], protocol)
    primary_comparisons = pd.concat([compare_ordered_contrast(primary_rows, METHODS[0], m, protocol)
                                    for m in METHODS[1:]], ignore_index=True)
    component_comparisons = pd.concat([compare_ordered_contrast(component_rows, FULL, m, protocol)
                                      for m in NAMES], ignore_index=True)
    for name, table in [("primary_monthly", primary_rows), ("component_monthly", component_rows),
                        ("primary_comparisons", primary_comparisons), ("component_comparisons", component_comparisons),
                        ("score_trace", pd.DataFrame(trace))]:
        table.to_csv(output / (name + ".csv"), index=False)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in bindings.items()):
        raise ValueError("Input changed during computation")
    report = dict(inputs_sha256=bindings, warmup_and_evaluation_months=len(trace),
        primary_monthly_rows=len(primary_rows), component_monthly_rows=len(component_rows),
        primary_comparisons=len(primary_comparisons), component_comparisons=len(component_comparisons),
        component_solver="Frozen 200-iteration, 1e-8 legacy solver; no per-variant convergence trace",
        state_chains="Independent primary and legacy-variant probability states; evaluation alignment leaves states unchanged")
    (output / "verification.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()

