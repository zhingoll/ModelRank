#!/usr/bin/env python3
"""
Comprehensive RQ2 indicator suite.

Builds the full four-layer validation table described in
docs/rq2_indicator_framework.md.

Outputs:
  - output_v3/rq2_indicator_suite_monthly.csv
  - output_v3/rq2_indicator_suite_summary.csv
"""
import math
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v3")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")

MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]


def owner_of(model_id: str) -> str:
    return model_id.split("/", 1)[0] if "/" in model_id else model_id


def auc_binary(y_true: np.ndarray, scores: np.ndarray) -> float:
    y_true = np.asarray(y_true).astype(int)
    scores = np.asarray(scores).astype(float)
    pos = y_true == 1
    neg = y_true == 0
    n_pos = int(pos.sum())
    n_neg = int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = stats.rankdata(scores)
    rank_sum_pos = ranks[pos].sum()
    u = rank_sum_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    rho, _ = stats.spearmanr(x, y)
    return float(rho)


def top_decile_indices(scores: np.ndarray) -> np.ndarray:
    n = len(scores)
    top_n = max(1, math.ceil(0.10 * n))
    order = np.argsort(-scores, kind="mergesort")
    return order[:top_n]


def summarize_metric(
    month: str,
    method: str,
    layer: str,
    metric: str,
    values: np.ndarray,
    top_idx: np.ndarray,
    signal: np.ndarray,
    is_binary: bool = False,
):
    top = float(values[top_idx].mean())
    base = float(values.mean())
    row = {
        "month": month,
        "method": method,
        "layer": layer,
        "metric": metric,
        "top_value": top,
        "base_value": base,
        "lift": float(top / max(base, 1e-9)),
        "spearman": safe_spearman(signal, values),
        "auc": float("nan"),
    }
    if is_binary:
        row["auc"] = auc_binary(values, signal)
    return row


def main() -> None:
    scores = pd.read_csv(
        os.path.join(OUT_DIR, "modelrank_scores.csv"),
        usecols=[
            "month", "model_id", "score_normalized", "q_base",
            "event_value", "downloads", "n_derivatives",
        ],
    )
    edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
    edges["child_month"] = edges["child_created"].astype(str).str[:7]
    edges = edges[edges["child_month"].isin(MONTHS)].copy()
    month_to_idx = {m: i for i, m in enumerate(MONTHS)}

    # Child quality at creation month
    child_quality = {}
    for ym in MONTHS:
        path = os.path.join(DATA_DIR, f"{ym}_metrics.csv")
        df = pd.read_csv(path, usecols=["id", "downloads", "likes"])
        child_quality[ym] = dict(
            zip(
                df["id"],
                zip(
                    df["downloads"].fillna(0.0).astype(float),
                    df["likes"].fillna(0.0).astype(float),
                ),
            )
        )

    # Parent -> children rows by child creation month
    child_rows_by_month = defaultdict(list)
    added_children_by_month = defaultdict(lambda: defaultdict(int))
    unique_child_rows = edges[["child_id", "child_month"]].drop_duplicates()
    for _, row in edges.iterrows():
        ym = row["child_month"]
        pid = row["parent_id"]
        cid = row["child_id"]
        child_rows_by_month[ym].append((pid, cid))
        added_children_by_month[ym][pid] += 1

    # Cumulative direct-child counts by month
    cumulative_children = {}
    running = defaultdict(int)
    for ym in MONTHS:
        for pid, cnt in added_children_by_month.get(ym, {}).items():
            running[pid] += cnt
        cumulative_children[ym] = dict(running)

    # Child future growth after its own creation
    child_future_count = {}
    child_becomes_parent = {}
    child_second_order = {}
    for _, row in unique_child_rows.iterrows():
        cid = row["child_id"]
        c_month = row["child_month"]
        start = month_to_idx[c_month]
        fut_months = MONTHS[start + 1:start + 4]
        cnt = sum(added_children_by_month.get(fm, {}).get(cid, 0) for fm in fut_months)
        child_future_count[(cid, c_month)] = cnt
        child_becomes_parent[(cid, c_month)] = 1 if cnt > 0 else 0
        child_second_order[(cid, c_month)] = 1 if cnt >= 2 else 0

    scores_by_month = {ym: g.copy() for ym, g in scores.groupby("month", sort=False)}
    methods = ["Downloads", "CurrentDerivCount", "AllTimeDerivCount", "EventValue", "Simplified-MR", "ModelRank"]
    monthly_rows = []

    for i in range(len(MONTHS) - 3):
        ym = MONTHS[i]
        future_months = MONTHS[i + 1:i + 4]
        cur = scores_by_month.get(ym)
        if cur is None or cur.empty:
            continue
        cur = cur.copy()
        cur["Downloads"] = cur["downloads"].astype(float)
        cur["CurrentDerivCount"] = cur["n_derivatives"].astype(float)
        cur["AllTimeDerivCount"] = cur["model_id"].map(cumulative_children.get(ym, {})).fillna(0).astype(float)
        cur["EventValue"] = cur["event_value"].astype(float)
        cur["Simplified-MR"] = cur["q_base"].astype(float) + 0.8 * cur["event_value"].astype(float)
        cur["ModelRank"] = cur["score_normalized"].astype(float)
        cur["parent_owner"] = cur["model_id"].map(owner_of)

        dl_p90 = cur["downloads"].quantile(0.90)
        low = cur[cur["downloads"] < dl_p90].copy()
        if len(low) < 100:
            continue

        # Build future child pools and global top-10% sets for this evaluation window
        future_child_records = []
        for fym in future_months:
            qual_map = child_quality.get(fym, {})
            for pid, cid in child_rows_by_month.get(fym, []):
                dls, likes = qual_map.get(cid, (0.0, 0.0))
                future_child_records.append({
                    "parent_id": pid,
                    "child_id": cid,
                    "child_month": fym,
                    "child_owner": owner_of(cid),
                    "child_downloads": float(dls),
                    "child_likes": float(likes),
                    "child_download_q": float(math.log1p(dls)),
                    "child_like_q": float(math.log1p(likes)),
                    "child_becomes_parent": child_becomes_parent.get((cid, fym), 0),
                    "child_future_child_count": child_future_count.get((cid, fym), 0),
                    "child_second_order": child_second_order.get((cid, fym), 0),
                })

        future_df = pd.DataFrame(future_child_records)
        if future_df.empty:
            continue

        n_top = max(1, math.ceil(0.10 * len(future_df)))
        top_download_ids = set(
            future_df.sort_values("child_downloads", ascending=False, kind="mergesort")
            .head(n_top)["child_id"].tolist()
        )
        top_like_ids = set(
            future_df.sort_values("child_likes", ascending=False, kind="mergesort")
            .head(n_top)["child_id"].tolist()
        )

        agg = defaultdict(lambda: {
            "future_direct_children_3m": 0,
            "future_active_parent_months_3m": 0,
            "future_active_parent_binary_3m": 0,
            "future_child_download_quality_sum_3m": 0.0,
            "future_child_like_quality_sum_3m": 0.0,
            "future_high_download_child_count_3m": 0,
            "future_high_like_child_count_3m": 0,
            "future_nonzero_like_child_count_3m": 0,
            "future_nonzero_download_child_count_3m": 0,
            "future_child_download_values_3m": [],
            "future_child_like_values_3m": [],
            "future_child_becomes_parent_values_3m": [],
            "future_child_future_child_count_values_3m": [],
            "future_child_second_order_values_3m": [],
            "future_child_owner_set_3m": set(),
            "future_high_download_child_owner_set_3m": set(),
            "future_high_like_child_owner_set_3m": set(),
            "future_cross_owner_count_3m": 0,
            "active_months_set": set(),
        })

        parent_owner_map = dict(zip(low["model_id"], low["parent_owner"]))

        for row in future_child_records:
            pid = row["parent_id"]
            if pid not in parent_owner_map:
                continue
            rec = agg[pid]
            rec["future_direct_children_3m"] += 1
            rec["active_months_set"].add(row["child_month"])
            rec["future_child_download_quality_sum_3m"] += row["child_download_q"]
            rec["future_child_like_quality_sum_3m"] += row["child_like_q"]
            rec["future_child_download_values_3m"].append(row["child_download_q"])
            rec["future_child_like_values_3m"].append(row["child_like_q"])
            rec["future_child_becomes_parent_values_3m"].append(row["child_becomes_parent"])
            rec["future_child_future_child_count_values_3m"].append(row["child_future_child_count"])
            rec["future_child_second_order_values_3m"].append(row["child_second_order"])
            rec["future_child_owner_set_3m"].add(row["child_owner"])
            if row["child_id"] in top_download_ids:
                rec["future_high_download_child_count_3m"] += 1
                rec["future_high_download_child_owner_set_3m"].add(row["child_owner"])
            if row["child_id"] in top_like_ids:
                rec["future_high_like_child_count_3m"] += 1
                rec["future_high_like_child_owner_set_3m"].add(row["child_owner"])
            if row["child_likes"] > 0:
                rec["future_nonzero_like_child_count_3m"] += 1
            if row["child_downloads"] > 0:
                rec["future_nonzero_download_child_count_3m"] += 1
            if row["child_owner"] != parent_owner_map[pid]:
                rec["future_cross_owner_count_3m"] += 1

        for pid, rec in agg.items():
            n_child = rec["future_direct_children_3m"]
            rec["future_active_parent_months_3m"] = len(rec["active_months_set"])
            rec["future_active_parent_binary_3m"] = 1 if n_child > 0 else 0
            rec["future_nonzero_like_child_share_3m"] = rec["future_nonzero_like_child_count_3m"] / max(n_child, 1)
            rec["future_nonzero_download_child_share_3m"] = rec["future_nonzero_download_child_count_3m"] / max(n_child, 1)
            rec["future_child_download_quality_mean_3m"] = float(np.mean(rec["future_child_download_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_download_quality_median_3m"] = float(np.median(rec["future_child_download_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_like_quality_mean_3m"] = float(np.mean(rec["future_child_like_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_like_quality_median_3m"] = float(np.median(rec["future_child_like_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_becomes_parent_share_3m"] = float(np.mean(rec["future_child_becomes_parent_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_future_child_count_mean_3m"] = float(np.mean(rec["future_child_future_child_count_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_future_child_count_median_3m"] = float(np.median(rec["future_child_future_child_count_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_second_order_diffusion_share_3m"] = float(np.mean(rec["future_child_second_order_values_3m"])) if n_child > 0 else 0.0
            rec["future_child_owner_breadth_3m"] = len(rec["future_child_owner_set_3m"])
            rec["future_high_download_child_owner_breadth_3m"] = len(rec["future_high_download_child_owner_set_3m"])
            rec["future_high_like_child_owner_breadth_3m"] = len(rec["future_high_like_child_owner_set_3m"])
            rec["future_cross_owner_reuse_share_3m"] = rec["future_cross_owner_count_3m"] / max(n_child, 1)

        # attach all 21 metrics to low-download parent rows
        metric_names = [
            # quantity
            "future_direct_children_3m",
            "future_active_parent_months_3m",
            "future_active_parent_binary_3m",
            # descendant quality
            "future_child_download_quality_sum_3m",
            "future_child_like_quality_sum_3m",
            "future_high_download_child_count_3m",
            "future_high_like_child_count_3m",
            "future_nonzero_like_child_share_3m",
            "future_nonzero_download_child_share_3m",
            "future_child_download_quality_mean_3m",
            "future_child_download_quality_median_3m",
            "future_child_like_quality_mean_3m",
            "future_child_like_quality_median_3m",
            # re-propagation
            "future_child_becomes_parent_share_3m",
            "future_child_future_child_count_mean_3m",
            "future_child_future_child_count_median_3m",
            "future_child_second_order_diffusion_share_3m",
            # adoption breadth
            "future_child_owner_breadth_3m",
            "future_high_download_child_owner_breadth_3m",
            "future_high_like_child_owner_breadth_3m",
            "future_cross_owner_reuse_share_3m",
        ]
        for name in metric_names:
            low[name] = low["model_id"].map(lambda m: agg.get(m, {}).get(name, 0.0)).astype(float)

        metric_layer = {
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

        # Re-propagation metrics require that even children born in t+3 have a
        # full 3-month follow-up window. This only holds for parent months up to
        # LAST-6 months in the panel.
        reprop_fully_observed = (i <= len(MONTHS) - 7)

        for method in methods:
            signal = low[method].to_numpy(dtype=float)
            top_idx = top_decile_indices(signal)
            for metric in metric_names:
                if metric_layer[metric] == "repropagation" and not reprop_fully_observed:
                    continue
                monthly_rows.append(
                    summarize_metric(
                        month=ym,
                        method=method,
                        layer=metric_layer[metric],
                        metric=metric,
                        values=low[metric].to_numpy(dtype=float),
                        top_idx=top_idx,
                        signal=signal,
                        is_binary=(metric == "future_active_parent_binary_3m"),
                    )
                )

    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(os.path.join(OUT_DIR, "rq2_indicator_suite_monthly.csv"), index=False)

    summary = (
        monthly.groupby(["layer", "metric", "method"], as_index=False)
        .agg(
            n_months=("month", "count"),
            mean_top_value=("top_value", "mean"),
            mean_base_value=("base_value", "mean"),
            mean_lift=("lift", "mean"),
            mean_spearman=("spearman", "mean"),
            mean_auc=("auc", "mean"),
        )
    )
    summary.to_csv(os.path.join(OUT_DIR, "rq2_indicator_suite_summary.csv"), index=False)
    print("Monthly rows:", len(monthly))
    print("Summary rows:", len(summary))


if __name__ == "__main__":
    main()
