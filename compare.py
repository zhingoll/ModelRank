"""Recompute paired inference from frozen monthly metric observations."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
import numpy as np
import pandas as pd
from scipy import stats

def holm_adjust(p_values: Iterable[float]) -> np.ndarray:
    raw = np.asarray(list(p_values), dtype=float)
    if not np.isfinite(raw).all() or ((raw < 0) | (raw > 1)).any():
        raise ValueError("Holm p-values must be finite and within [0,1]")
    order = np.argsort(raw, kind="mergesort")
    adjusted_sorted = np.maximum.accumulate((len(raw) - np.arange(len(raw))) * raw[order])
    adjusted = np.empty_like(raw)
    adjusted[order] = np.minimum(1.0, adjusted_sorted)
    return adjusted


def metric_registry(protocol: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [
        (metric, family)
        for family, metrics in protocol["metric_families"].items()
        for metric in metrics
    ]


def _threshold(statistic: str, protocol: Mapping[str, Any]) -> float:
    thresholds = protocol["inference"]["material_thresholds"]
    return float(
        thresholds["roc_auc_difference"]
        if statistic == "auc"
        else thresholds["top_decile_lift_difference"]
    )


def _seed(*parts: str) -> int:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).digest()
    return (int.from_bytes(digest[:8], "big") ^ 20260811) % (2**32)


def _paired_summary(values: np.ndarray, seed_parts: Iterable[str]) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("paired inference requires at least two finite origin months")
    mean = float(values.mean())
    sd = float(values.std(ddof=1))
    if sd == 0.0:
        ci_low = ci_high = mean
        p_raw = 1.0 if mean == 0.0 else 0.0
    else:
        half = float(stats.t.ppf(0.975, len(values) - 1) * sd / np.sqrt(len(values)))
        ci_low, ci_high = mean - half, mean + half
        p_raw = float(stats.ttest_1samp(values, 0.0).pvalue)
    rng = np.random.default_rng(_seed(*[str(item) for item in seed_parts]))
    indices = rng.integers(0, len(values), size=(10_000, len(values)))
    boot = values[indices].mean(axis=1)
    boot_low, boot_high = (float(item) for item in np.quantile(boot, [0.025, 0.975]))
    direction = "positive" if boot_low > 0 else "negative" if boot_high < 0 else "mixed"
    return {
        "n_months": len(values),
        "mean_difference": mean,
        "sd_difference": sd,
        "ci_low": ci_low,
        "ci_high": ci_high,
        "p_raw": p_raw,
        "bootstrap_ci_low": boot_low,
        "bootstrap_ci_high": boot_high,
        "bootstrap_direction": direction,
    }


def validate_monthly_grid(
    monthly: pd.DataFrame,
    methods: Iterable[str],
    protocol: Mapping[str, Any],
) -> None:
    methods = [str(method) for method in methods]
    counts = monthly.groupby(["method", "metric", "month"], dropna=False).size()
    problems = []
    for method in methods:
        for family, metrics in protocol["metric_families"].items():
            months = protocol["origins"]["repropagation" if family == "repropagation" else "three_month"]
            for metric in metrics:
                for month in months:
                    if counts.get((method, metric, month), 0) != 1:
                        problems.append((method, metric, month, int(counts.get((method, metric, month), 0))))
    if problems:
        raise ValueError(f"monthly grid is incomplete: {problems[:5]} (total={len(problems)})")


def compare_ordered_contrast(
    monthly: pd.DataFrame,
    candidate: str,
    baseline: str,
    protocol: Mapping[str, Any],
) -> pd.DataFrame:
    validate_monthly_grid(monthly, [candidate, baseline], protocol)
    rows = []
    for metric, family in metric_registry(protocol):
        selected = monthly.loc[
            (monthly["metric"].astype(str) == metric)
            & monthly["method"].astype(str).isin([candidate, baseline])
        ]
        wide = selected.pivot(index="month", columns="method", values="value")
        difference = wide[candidate].to_numpy(float) - wide[baseline].to_numpy(float)
        statistic_values = selected["statistic"].drop_duplicates().astype(str).tolist()
        if len(statistic_values) != 1:
            raise ValueError(f"statistic mismatch: {metric}")
        statistic = statistic_values[0]
        rows.append(
            {
                "candidate": candidate,
                "baseline": baseline,
                "family": family,
                "metric": metric,
                "statistic": statistic,
                "material_threshold": _threshold(statistic, protocol),
                **_paired_summary(difference, [candidate, baseline, metric]),
            }
        )
    result = pd.DataFrame(rows)
    result["holm_p"] = holm_adjust(result["p_raw"].to_numpy(float))
    result["holm_family_size"] = 21
    positive = (result["mean_difference"] > 0) & (result["ci_low"] > 0) & (result["holm_p"] <= 0.05)
    negative = (result["mean_difference"] < 0) & (result["ci_high"] < 0) & (result["holm_p"] <= 0.05)
    result["decision"] = np.where(positive, "win", np.where(negative, "loss", "tie"))
    result["robust_material_win"] = (
        positive
        & (result["mean_difference"] >= result["material_threshold"])
        & (result["bootstrap_direction"] != "negative")
    )
    result["material_loss"] = result["mean_difference"] <= -result["material_threshold"]
    return result


def summarize_families(
    monthly: pd.DataFrame,
    comparison: pd.DataFrame,
    candidate: str,
    baseline: str,
    protocol: Mapping[str, Any],
) -> pd.DataFrame:
    rows = []
    for family, metrics in protocol["metric_families"].items():
        month_series = []
        months = protocol["origins"]["repropagation" if family == "repropagation" else "three_month"]
        for month in months:
            scaled = []
            for metric in metrics:
                selected = monthly.loc[
                    (monthly["month"].astype(str) == month)
                    & (monthly["metric"].astype(str) == metric)
                    & monthly["method"].astype(str).isin([candidate, baseline])
                ]
                wide = selected.pivot(index="month", columns="method", values="value")
                statistic = selected["statistic"].iloc[0]
                scaled.append(float(wide[candidate].iloc[0] - wide[baseline].iloc[0]) / _threshold(statistic, protocol))
            month_series.append(float(np.mean(scaled)))
        summary = _paired_summary(np.asarray(month_series), [candidate, baseline, family, "family"])
        metric_rows = comparison.loc[comparison["family"] == family]
        robust_count = int(metric_rows["robust_material_win"].sum())
        rows.append(
            {
                "candidate": candidate,
                "baseline": baseline,
                "family": family,
                "metric_count": len(metrics),
                "family_material_index": summary.pop("mean_difference"),
                "family_ci_low": summary.pop("ci_low"),
                "family_ci_high": summary.pop("ci_high"),
                "holm_robust_material_metric_count": robust_count,
                "family_positive_gate": False,
                **summary,
            }
        )
        rows[-1]["family_positive_gate"] = bool(
            rows[-1]["family_material_index"] >= 1.0
            and rows[-1]["family_ci_low"] > 0
            and robust_count >= 1
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--grid', action='store_true', help='Also rebuild parameter-grid comparisons')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('Use a new output directory')
    output.mkdir(parents=True)
    protocol = json.loads((root / 'data/comparison_protocol.json').read_text())
    monthly = pd.read_csv(root / 'results/rq2/monthly_all.csv', float_precision='round_trip')
    names = ['primary_comparisons_21.csv', 'mtpr_ablation_comparisons.csv']
    if args.grid:
        names.append('grid_comparisons.csv')
    for name in names:
        reference = pd.read_csv(root / 'results/rq2' / name, float_precision='round_trip')
        parts = []
        for candidate, baseline in reference[['candidate','baseline']].drop_duplicates().itertuples(index=False,name=None):
            parts.append(compare_ordered_contrast(monthly, candidate, baseline, protocol))
        result = pd.concat(parts, ignore_index=True)
        columns = list(reference.columns)
        if not set(columns).issubset(result.columns):
            raise ValueError('Reference schema contains unsupported fields')
        result = result[columns]
        key = ['candidate','baseline','metric']
        pd.testing.assert_frame_equal(result.sort_values(key).reset_index(drop=True),
            reference.sort_values(key).reset_index(drop=True), check_dtype=False, atol=1e-12, rtol=1e-10)
        result.to_csv(output / name, index=False)
        print(name, len(result), 'reference matched', flush=True)


if __name__ == '__main__':
    main()
