#!/usr/bin/env python3
"""
Out-of-time validation for reuse-oriented signals.

Goal:
    Among low-download models at month t, compare whether alternative signals
    better surface models that continue to function as technical starting
    points over the next 3 months.

Signals compared:
    - Downloads
    - Current-month DerivCount
    - All-time DerivCount
    - EventValue
    - Simplified-MR
    - ModelRank

Future outcomes (months t+1 to t+3):
    - whether the model becomes an active parent
    - how many direct children it gains
    - in how many future months it remains active as a parent

Outputs:
    - output_v3/rq2_out_of_time_validation.csv
    - output_v3/rq2_out_of_time_validation_monthly.csv
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


def auc_binary(y_true: np.ndarray, scores: np.ndarray) -> float:
    """AUC via Mann-Whitney U; return nan if only one class is present."""
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


def top_decile_metrics(scores: np.ndarray, active: np.ndarray, future_children: np.ndarray):
    n = len(scores)
    if n == 0:
        return {
            "top_active_rate": float("nan"),
            "base_active_rate": float("nan"),
            "active_lift": float("nan"),
            "top_future_children": float("nan"),
            "base_future_children": float("nan"),
            "children_lift": float("nan"),
        }

    top_n = max(1, math.ceil(0.10 * n))
    order = np.argsort(-scores, kind="mergesort")
    top_idx = order[:top_n]

    top_active = float(active[top_idx].mean())
    base_active = float(active.mean())
    top_children = float(future_children[top_idx].mean())
    base_children = float(future_children.mean())

    return {
        "top_active_rate": top_active,
        "base_active_rate": base_active,
        "active_lift": float(top_active / max(base_active, 1e-9)),
        "top_future_children": top_children,
        "base_future_children": base_children,
        "children_lift": float(top_children / max(base_children, 1e-9)),
    }


def main() -> None:
    scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
    edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
    edges["child_month"] = edges["child_created"].astype(str).str[:7]

    # Month-indexed direct-child additions
    added_children_by_month = defaultdict(lambda: defaultdict(int))
    active_parent_by_month = defaultdict(set)
    for _, row in edges.iterrows():
        ym = row["child_month"]
        pid = row["parent_id"]
        added_children_by_month[ym][pid] += 1
        active_parent_by_month[ym].add(pid)

    # Cumulative direct-child counts up to and including month t
    cumulative_children = {}
    running = defaultdict(int)
    for ym in MONTHS:
        for pid, cnt in added_children_by_month.get(ym, {}).items():
            running[pid] += cnt
        cumulative_children[ym] = dict(running)

    monthly_rows = []
    methods = ["Downloads", "CurrentDerivCount", "AllTimeDerivCount", "EventValue", "Simplified-MR", "ModelRank"]

    for i in range(len(MONTHS) - 3):
        ym = MONTHS[i]
        future_months = MONTHS[i + 1:i + 4]

        cur = scores[scores["month"] == ym].copy()
        if cur.empty:
            continue

        cur["Downloads"] = cur["downloads"].astype(float)
        cur["CurrentDerivCount"] = cur["n_derivatives"].astype(float)
        cur["AllTimeDerivCount"] = cur["model_id"].map(cumulative_children.get(ym, {})).fillna(0).astype(float)
        cur["EventValue"] = cur["event_value"].astype(float)
        cur["Simplified-MR"] = cur["q_base"].astype(float) + 0.8 * cur["event_value"].astype(float)
        cur["ModelRank"] = cur["score_normalized"].astype(float)

        dl_p90 = cur["downloads"].quantile(0.90)
        low = cur[cur["downloads"] < dl_p90].copy()
        if len(low) < 100:
            continue

        future_children = defaultdict(int)
        future_active_months = defaultdict(int)
        for fym in future_months:
            for pid, cnt in added_children_by_month.get(fym, {}).items():
                future_children[pid] += cnt
            for pid in active_parent_by_month.get(fym, set()):
                future_active_months[pid] += 1

        low["future_direct_children_3m"] = low["model_id"].map(future_children).fillna(0).astype(int)
        low["future_active_months_3m"] = low["model_id"].map(future_active_months).fillna(0).astype(int)
        low["future_active_parent_3m"] = (low["future_direct_children_3m"] > 0).astype(int)

        for method in methods:
            signal = low[method].to_numpy(dtype=float)
            active = low["future_active_parent_3m"].to_numpy(dtype=int)
            future_children_arr = low["future_direct_children_3m"].to_numpy(dtype=float)
            future_active_months_arr = low["future_active_months_3m"].to_numpy(dtype=float)

            row = {
                "month": ym,
                "method": method,
                "n_low_download": int(len(low)),
                "future_active_rate": float(active.mean()),
                "auc_future_active_parent": auc_binary(active, signal),
                "spearman_future_direct_children": safe_spearman(signal, future_children_arr),
                "spearman_future_active_months": safe_spearman(signal, future_active_months_arr),
            }
            row.update(top_decile_metrics(signal, active, future_children_arr))
            monthly_rows.append(row)

    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(os.path.join(OUT_DIR, "rq2_out_of_time_validation_monthly.csv"), index=False)

    summary_rows = []
    for method, g in monthly.groupby("method"):
        summary_rows.append({
            "method": method,
            "n_months": int(len(g)),
            "mean_future_active_rate": float(g["future_active_rate"].mean()),
            "mean_auc_future_active_parent": float(g["auc_future_active_parent"].mean()),
            "mean_spearman_future_direct_children": float(g["spearman_future_direct_children"].mean()),
            "mean_spearman_future_active_months": float(g["spearman_future_active_months"].mean()),
            "mean_top_active_rate": float(g["top_active_rate"].mean()),
            "mean_base_active_rate": float(g["base_active_rate"].mean()),
            "mean_active_lift": float(g["active_lift"].mean()),
            "mean_top_future_children": float(g["top_future_children"].mean()),
            "mean_base_future_children": float(g["base_future_children"].mean()),
            "mean_children_lift": float(g["children_lift"].mean()),
        })

    summary = pd.DataFrame(summary_rows)
    order = {
        "Downloads": 1,
        "CurrentDerivCount": 2,
        "AllTimeDerivCount": 3,
        "EventValue": 4,
        "Simplified-MR": 5,
        "ModelRank": 6,
    }
    summary["order"] = summary["method"].map(order)
    summary = summary.sort_values("order").drop(columns="order")
    summary.to_csv(os.path.join(OUT_DIR, "rq2_out_of_time_validation.csv"), index=False)

    print("Monthly rows:", len(monthly))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
