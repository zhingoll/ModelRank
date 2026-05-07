#!/usr/bin/env python3
"""
Future descendant quality and adopter-breadth validation for RQ2.

Goal:
    Among low-download models at month t, compare whether alternative signals
    surface parents whose future direct children are not only more numerous,
    but also higher-quality and adopted by a broader set of owners.

Signals compared:
    - Downloads
    - CurrentDerivCount
    - AllTimeDerivCount
    - EventValue
    - Simplified-MR
    - ModelRank

Future outcomes (months t+1 to t+3):
    - sum of log(1 + child downloads-at-creation-month)
    - sum of log(1 + child likes-at-creation-month)
    - count of children with nonzero likes
    - number of unique child owners / namespaces

Outputs:
    - output_v3/rq2_future_descendant_quality.csv
    - output_v3/rq2_future_descendant_quality_monthly.csv
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


def safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.all(x == x[0]) or np.all(y == y[0]):
        return float("nan")
    rho, _ = stats.spearmanr(x, y)
    return float(rho)


def top_decile_ratio(scores: np.ndarray, outcome: np.ndarray):
    n = len(scores)
    top_n = max(1, math.ceil(0.10 * n))
    order = np.argsort(-scores, kind="mergesort")
    top_idx = order[:top_n]
    top_mean = float(outcome[top_idx].mean())
    base_mean = float(outcome.mean())
    return top_mean, base_mean, float(top_mean / max(base_mean, 1e-9))


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

    # Cumulative direct-child counts
    added_children_by_month = defaultdict(lambda: defaultdict(int))
    child_rows_by_month = defaultdict(list)
    for _, row in edges.iterrows():
        ym = row["child_month"]
        pid = row["parent_id"]
        cid = row["child_id"]
        added_children_by_month[ym][pid] += 1
        child_rows_by_month[ym].append((pid, cid))

    cumulative_children = {}
    running = defaultdict(int)
    for ym in MONTHS:
        for pid, cnt in added_children_by_month.get(ym, {}).items():
            running[pid] += cnt
        cumulative_children[ym] = dict(running)

    monthly_rows = []
    methods = ["Downloads", "CurrentDerivCount", "AllTimeDerivCount", "EventValue", "Simplified-MR", "ModelRank"]
    scores_by_month = {ym: g.copy() for ym, g in scores.groupby("month", sort=False)}

    for i in range(len(MONTHS) - 3):
        ym = MONTHS[i]
        future_months = MONTHS[i + 1:i + 4]

        cur = scores_by_month.get(ym)
        if cur.empty:
            continue
        cur = cur.copy()

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

        future_download_quality = defaultdict(float)
        future_like_quality = defaultdict(float)
        future_nonzero_liked_children = defaultdict(int)
        future_owner_breadth_sets = defaultdict(set)

        for fym in future_months:
            qual_map = child_quality.get(fym, {})
            for pid, cid in child_rows_by_month.get(fym, []):
                dls, likes = qual_map.get(cid, (0.0, 0.0))
                future_download_quality[pid] += math.log1p(dls)
                future_like_quality[pid] += math.log1p(likes)
                if likes > 0:
                    future_nonzero_liked_children[pid] += 1
                future_owner_breadth_sets[pid].add(owner_of(cid))

        low["future_child_download_quality_3m"] = low["model_id"].map(future_download_quality).fillna(0.0)
        low["future_child_like_quality_3m"] = low["model_id"].map(future_like_quality).fillna(0.0)
        low["future_nonzero_liked_children_3m"] = low["model_id"].map(future_nonzero_liked_children).fillna(0).astype(int)
        low["future_owner_breadth_3m"] = low["model_id"].map(lambda m: len(future_owner_breadth_sets.get(m, set()))).astype(int)

        for method in methods:
            signal = low[method].to_numpy(dtype=float)

            dl_quality = low["future_child_download_quality_3m"].to_numpy(dtype=float)
            like_quality = low["future_child_like_quality_3m"].to_numpy(dtype=float)
            liked_children = low["future_nonzero_liked_children_3m"].to_numpy(dtype=float)
            owner_breadth = low["future_owner_breadth_3m"].to_numpy(dtype=float)

            top_dl, base_dl, lift_dl = top_decile_ratio(signal, dl_quality)
            top_like, base_like, lift_like = top_decile_ratio(signal, like_quality)
            top_owner, base_owner, lift_owner = top_decile_ratio(signal, owner_breadth)

            monthly_rows.append({
                "month": ym,
                "method": method,
                "n_low_download": int(len(low)),
                "spearman_future_child_download_quality": safe_spearman(signal, dl_quality),
                "spearman_future_child_like_quality": safe_spearman(signal, like_quality),
                "spearman_future_nonzero_liked_children": safe_spearman(signal, liked_children),
                "spearman_future_owner_breadth": safe_spearman(signal, owner_breadth),
                "top_future_child_download_quality": top_dl,
                "base_future_child_download_quality": base_dl,
                "download_quality_lift": lift_dl,
                "top_future_child_like_quality": top_like,
                "base_future_child_like_quality": base_like,
                "like_quality_lift": lift_like,
                "top_future_owner_breadth": top_owner,
                "base_future_owner_breadth": base_owner,
                "owner_breadth_lift": lift_owner,
            })

    monthly = pd.DataFrame(monthly_rows)
    monthly.to_csv(os.path.join(OUT_DIR, "rq2_future_descendant_quality_monthly.csv"), index=False)

    summary_rows = []
    for method, g in monthly.groupby("method"):
        summary_rows.append({
            "method": method,
            "n_months": int(len(g)),
            "mean_spearman_future_child_download_quality": float(g["spearman_future_child_download_quality"].mean()),
            "mean_spearman_future_child_like_quality": float(g["spearman_future_child_like_quality"].mean()),
            "mean_spearman_future_nonzero_liked_children": float(g["spearman_future_nonzero_liked_children"].mean()),
            "mean_spearman_future_owner_breadth": float(g["spearman_future_owner_breadth"].mean()),
            "mean_top_future_child_download_quality": float(g["top_future_child_download_quality"].mean()),
            "mean_base_future_child_download_quality": float(g["base_future_child_download_quality"].mean()),
            "mean_download_quality_lift": float(g["download_quality_lift"].mean()),
            "mean_top_future_child_like_quality": float(g["top_future_child_like_quality"].mean()),
            "mean_base_future_child_like_quality": float(g["base_future_child_like_quality"].mean()),
            "mean_like_quality_lift": float(g["like_quality_lift"].mean()),
            "mean_top_future_owner_breadth": float(g["top_future_owner_breadth"].mean()),
            "mean_base_future_owner_breadth": float(g["base_future_owner_breadth"].mean()),
            "mean_owner_breadth_lift": float(g["owner_breadth_lift"].mean()),
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
    summary.to_csv(os.path.join(OUT_DIR, "rq2_future_descendant_quality.csv"), index=False)

    print("Monthly rows:", len(monthly))
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
