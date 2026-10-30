"""Frozen future-reuse aggregation and monthly evaluation arithmetic."""
from __future__ import annotations
import math
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence
import numpy as np
import pandas as pd
from scipy import stats
from compare import metric_registry

METRIC_FAMILIES = {
    "future_direct_children_3m": "quantity",
    "future_active_parent_months_3m": "quantity",
    "future_active_parent_binary_3m": "quantity",
    "future_child_download_quality_sum_3m": "descendant_quality",
    "future_child_like_quality_sum_3m": "descendant_quality",
    "future_high_download_child_count_3m": "descendant_quality",
    "future_high_like_child_count_3m": "descendant_quality",
    "future_nonzero_like_child_share_3m": "descendant_quality",
    "future_nonzero_download_child_share_3m": "descendant_quality",
    "future_child_download_quality_mean_3m": "descendant_quality",
    "future_child_download_quality_median_3m": "descendant_quality",
    "future_child_like_quality_mean_3m": "descendant_quality",
    "future_child_like_quality_median_3m": "descendant_quality",
    "future_child_becomes_parent_share_3m": "repropagation",
    "future_child_future_child_count_mean_3m": "repropagation",
    "future_child_future_child_count_median_3m": "repropagation",
    "future_child_second_order_diffusion_share_3m": "repropagation",
    "future_child_owner_breadth_3m": "adoption_breadth",
    "future_high_download_child_owner_breadth_3m": "adoption_breadth",
    "future_high_like_child_owner_breadth_3m": "adoption_breadth",
    "future_cross_owner_reuse_share_3m": "adoption_breadth",
}

def auc_binary(y_true: Iterable[float], scores: Iterable[float]) -> float:
    y = np.asarray(list(y_true), dtype=float)
    signal = np.asarray(list(scores), dtype=float)
    if y.ndim != 1 or y.shape != signal.shape:
        raise ValueError("outcome and score must be equal-length one-dimensional arrays")
    if not np.isfinite(y).all() or not np.isin(y, [0, 1]).all():
        raise ValueError("outcome labels must be binary")
    y = y.astype(int)
    positive = y == 1
    negative = y == 0
    n_pos, n_neg = int(positive.sum()), int(negative.sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = stats.rankdata(signal)
    u = float(ranks[positive].sum()) - n_pos * (n_pos + 1) / 2.0
    return u / (n_pos * n_neg)

def stable_top_decile_indices(scores: Iterable[float]) -> np.ndarray:
    signal = np.asarray(list(scores), dtype=float)
    count = max(1, math.ceil(0.10 * len(signal)))
    return np.argsort(-signal, kind="mergesort")[:count]

def owner(model_id: str) -> str:
    return str(model_id).split("/", 1)[0]

def build_reuse_inputs(
    ledger: pd.DataFrame,
    panel_months: Sequence[str],
) -> tuple[dict[str, list[tuple[str, str]]], dict[tuple[str, str], int]]:
    required = {"child_id", "parent_id", "relation", "entry_month"}
    missing = sorted(required.difference(ledger.columns))
    if missing:
        raise ValueError(f"edge ledger missing columns: {missing}")
    if ledger[list(required)].astype(str).duplicated().any():
        raise ValueError("edge ledger contains duplicate exact edge entry")
    months = [str(item) for item in panel_months]
    month_index = {month: index for index, month in enumerate(months)}
    by_month: dict[str, list[tuple[str, str]]] = defaultdict(list)
    additions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for child, parent, month in ledger[["child_id", "parent_id", "entry_month"]].itertuples(
        index=False, name=None
    ):
        month = str(month)
        if month not in month_index:
            continue
        by_month[month].append((str(parent), str(child)))
        additions[month][str(parent)] += 1
    unique_child_months = ledger[["child_id", "entry_month"]].astype(str).drop_duplicates()
    future_count: dict[tuple[str, str], int] = {}
    for child, entry_month in unique_child_months.itertuples(index=False, name=None):
        if entry_month not in month_index:
            continue
        start = month_index[entry_month]
        future_count[(child, entry_month)] = sum(
            additions[month].get(child, 0) for month in months[start + 1:start + 4]
        )
    return dict(by_month), future_count

def build_reuse_outcomes(
    low: pd.DataFrame,
    origin: str,
    quality: Mapping[str, Mapping[str, tuple[float, float]]],
    by_month: Mapping[str, list[tuple[str, str]]],
    future_count: Mapping[tuple[str, str], int],
    panel_months: Sequence[str],
) -> pd.DataFrame:
    months = [str(item) for item in panel_months]
    if str(origin) not in months:
        raise ValueError(f"origin outside panel: {origin}")
    start = months.index(str(origin))
    future_months = months[start + 1:start + 4]
    if len(future_months) != 3:
        raise ValueError(f"origin lacks three future months: {origin}")
    records: list[dict[str, object]] = []
    for month in future_months:
        for parent_id, child_id in by_month.get(month, []):
            downloads, likes = quality.get(month, {}).get(child_id, (0.0, 0.0))
            count = int(future_count.get((child_id, month), 0))
            records.append({
                "parent_id": parent_id, "child_id": child_id, "month": month,
                "child_owner": owner(child_id), "downloads": float(downloads),
                "likes": float(likes), "download_q": math.log1p(float(downloads)),
                "like_q": math.log1p(float(likes)), "becomes_parent": int(count > 0),
                "future_count": count, "second_order": int(count >= 2),
            })
    if not records:
        raise ValueError(f"no future first-observed edges for {origin}")
    future = pd.DataFrame(records)
    n_top = max(1, math.ceil(0.10 * len(future)))
    top_download = set(future.sort_values(
        ["downloads", "child_id"], ascending=[False, True], kind="mergesort"
    ).head(n_top)["child_id"])
    top_like = set(future.sort_values(
        ["likes", "child_id"], ascending=[False, True], kind="mergesort"
    ).head(n_top)["child_id"])
    parent_owners = dict(zip(low["model_id"].astype(str), low["model_id"].astype(str).map(owner)))
    agg: dict[str, dict[str, object]] = defaultdict(lambda: {
        "months": set(), "download_values": [], "like_values": [], "becomes": [],
        "future_counts": [], "second": [], "owners": set(),
        "high_download_owners": set(), "high_like_owners": set(), "n": 0,
        "download_sum": 0.0, "like_sum": 0.0, "high_download": 0,
        "high_like": 0, "nonzero_like": 0, "nonzero_download": 0, "cross_owner": 0,
    })
    for row in records:
        parent_id = str(row["parent_id"])
        if parent_id not in parent_owners:
            continue
        rec = agg[parent_id]
        rec["n"] += 1
        rec["months"].add(row["month"])
        rec["download_sum"] += row["download_q"]
        rec["like_sum"] += row["like_q"]
        rec["download_values"].append(row["download_q"])
        rec["like_values"].append(row["like_q"])
        rec["becomes"].append(row["becomes_parent"])
        rec["future_counts"].append(row["future_count"])
        rec["second"].append(row["second_order"])
        rec["owners"].add(row["child_owner"])
        if row["child_id"] in top_download:
            rec["high_download"] += 1
            rec["high_download_owners"].add(row["child_owner"])
        if row["child_id"] in top_like:
            rec["high_like"] += 1
            rec["high_like_owners"].add(row["child_owner"])
        rec["nonzero_like"] += int(row["likes"] > 0)
        rec["nonzero_download"] += int(row["downloads"] > 0)
        rec["cross_owner"] += int(row["child_owner"] != parent_owners[parent_id])

    def values(parent_id: str) -> dict[str, float]:
        rec = agg.get(parent_id)
        if not rec:
            return {metric: 0.0 for metric in METRIC_FAMILIES}
        n = int(rec["n"])
        mean = lambda key: float(np.mean(rec[key])) if n else 0.0
        median = lambda key: float(np.median(rec[key])) if n else 0.0
        return {
            "future_direct_children_3m": float(n),
            "future_active_parent_months_3m": float(len(rec["months"])),
            "future_active_parent_binary_3m": float(n > 0),
            "future_child_download_quality_sum_3m": float(rec["download_sum"]),
            "future_child_like_quality_sum_3m": float(rec["like_sum"]),
            "future_high_download_child_count_3m": float(rec["high_download"]),
            "future_high_like_child_count_3m": float(rec["high_like"]),
            "future_nonzero_like_child_share_3m": float(rec["nonzero_like"]) / max(n, 1),
            "future_nonzero_download_child_share_3m": float(rec["nonzero_download"]) / max(n, 1),
            "future_child_download_quality_mean_3m": mean("download_values"),
            "future_child_download_quality_median_3m": median("download_values"),
            "future_child_like_quality_mean_3m": mean("like_values"),
            "future_child_like_quality_median_3m": median("like_values"),
            "future_child_becomes_parent_share_3m": mean("becomes"),
            "future_child_future_child_count_mean_3m": mean("future_counts"),
            "future_child_future_child_count_median_3m": median("future_counts"),
            "future_child_second_order_diffusion_share_3m": mean("second"),
            "future_child_owner_breadth_3m": float(len(rec["owners"])),
            "future_high_download_child_owner_breadth_3m": float(len(rec["high_download_owners"])),
            "future_high_like_child_owner_breadth_3m": float(len(rec["high_like_owners"])),
            "future_cross_owner_reuse_share_3m": float(rec["cross_owner"]) / max(n, 1),
        }
    rows = [values(model_id) for model_id in low["model_id"].astype(str)]
    return pd.concat([low.reset_index(drop=True), pd.DataFrame(rows)], axis=1)

def evaluate_candidate_month(
    panel: pd.DataFrame,
    month: str,
    methods: Iterable[str],
    protocol: Mapping[str, Any],
) -> pd.DataFrame:
    methods = [str(method) for method in methods]
    required = {"model_id", *methods, *[metric for metric, _ in metric_registry(protocol)]}
    missing = sorted(required.difference(panel.columns))
    if missing:
        raise ValueError(f"candidate evaluation panel missing columns: {missing}")
    ordered = panel.copy()
    ordered["model_id"] = ordered["model_id"].astype(str)
    if ordered["model_id"].duplicated().any():
        raise ValueError("candidate evaluation panel has duplicate model IDs")
    ordered = ordered.sort_values("model_id", kind="mergesort").reset_index(drop=True)
    signals: dict[str, np.ndarray] = {}
    top_indices: dict[str, np.ndarray] = {}
    for method in methods:
        signal = pd.to_numeric(ordered[method], errors="raise").to_numpy(float)
        if not np.isfinite(signal).all():
            raise ValueError(f"nonfinite candidate score: {month}/{method}")
        signals[method] = signal
        top_indices[method] = stable_top_decile_indices(signal)
    rows = []
    for metric, family in metric_registry(protocol):
        outcome = pd.to_numeric(ordered[metric], errors="raise").to_numpy(float)
        if not np.isfinite(outcome).all():
            raise ValueError(f"nonfinite outcome: {month}/{metric}")
        statistic = "auc" if metric == "future_active_parent_binary_3m" else "lift"
        for method in methods:
            if statistic == "auc":
                value = auc_binary(outcome, signals[method])
            else:
                value = float(outcome[top_indices[method]].mean()) / max(float(outcome.mean()), 1e-9)
            rows.append(
                {
                    "scheme": "exposed_development",
                    "month": str(month),
                    "metric": metric,
                    "family": family,
                    "statistic": statistic,
                    "method": method,
                    "value": float(value),
                    "candidate_n": len(ordered),
                    "base_value": float(outcome.mean()),
                }
            )
    return pd.DataFrame(rows)

