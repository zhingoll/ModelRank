#!/usr/bin/env python3
"""
RQ2: Validity of ModelRank
==========================
Baseline correlation, ranking stability, component ablation, parameter sensitivity.

Reads:
  output_v2/modelrank_scores.csv
  data_new/monthly/deriv_models.csv
  data_new/monthly/deriv_edges.csv
  data_new/monthly/{month}_metrics.csv

Output:
  output_v2/rq2_correlation.csv
  output_v2/rq2_stability.csv
  output_v2/rq2_correlation_trend.csv
"""
import os, sys, time
import pandas as pd
import numpy as np
from scipy import stats
from collections import defaultdict
import calendar

DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")

MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]

print("Loading ModelRank scores ...")
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
print(f"  {len(scores):,} rows, {scores['month'].nunique()} months")

print("Loading edges ...")
edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
edges["child_month"] = edges["child_created"].str[:7]

# ── Compute baselines for each month ──
print("\nComputing baselines ...")

def compute_baselines(month_scores, month_edges):
    """Add baseline columns to month_scores DataFrame."""
    df = month_scores.copy()

    # DerivCount: number of new derivatives received this month
    deriv_counts = month_edges.groupby("parent_id").size()
    df["deriv_count"] = df["model_id"].map(deriv_counts).fillna(0).astype(int)

    # Downloads and Likes are already in scores
    # Vanilla-PR-Event: since we proved it degenerates to DerivCount (rho=1.00),
    # we use DerivCount as proxy

    return df


# ── 1. Cross-method correlation (last month) ──
print("\n=== 1. Baseline Correlation (last month) ===")
last_month = MONTHS[-1]
lm_scores = scores[scores["month"] == last_month].copy()
lm_edges = edges[edges["child_month"] == last_month]
lm_scores = compute_baselines(lm_scores, lm_edges)

methods = {
    "ModelRank": "score_normalized",
    "Downloads": "downloads",
    "Likes": "likes",
    "DerivCount": "deriv_count",
}

# Correlation matrix
print(f"\nSpearman correlation matrix ({last_month}, n={len(lm_scores):,}):")
corr_data = {}
for name, col in methods.items():
    corr_data[name] = lm_scores[col].values

corr_rows = []
names = list(methods.keys())
for i, n1 in enumerate(names):
    row = {"method": n1}
    for j, n2 in enumerate(names):
        rho, _ = stats.spearmanr(corr_data[n1], corr_data[n2])
        row[n2] = round(rho, 3)
    corr_rows.append(row)

corr_df = pd.DataFrame(corr_rows).set_index("method")
corr_df.to_csv(os.path.join(OUT_DIR, "rq2_correlation.csv"))
print(corr_df.to_string())

# ── 2. Correlation trend across months ──
print("\n=== 2. Correlation Trend ===")
trend_rows = []
for ym in MONTHS:
    ms = scores[scores["month"] == ym].copy()
    me = edges[edges["child_month"] == ym]
    ms = compute_baselines(ms, me)
    if len(ms) < 100:
        continue

    row = {"month": ym, "n": len(ms)}
    mr = ms["score_normalized"].values
    for bname, bcol in [("Downloads", "downloads"), ("Likes", "likes"), ("DerivCount", "deriv_count")]:
        rho, _ = stats.spearmanr(mr, ms[bcol].values)
        row[f"rho_{bname}"] = round(rho, 3)
    trend_rows.append(row)

trend_df = pd.DataFrame(trend_rows)
trend_df.to_csv(os.path.join(OUT_DIR, "rq2_correlation_trend.csv"), index=False)
print(trend_df.to_string(index=False))

# ── 3. Ranking Stability ──
print("\n=== 3. Ranking Stability (Jaccard) ===")

def jaccard(set1, set2):
    if not set1 and not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

stability_rows = []
for i in range(1, len(MONTHS)):
    ym_prev = MONTHS[i-1]
    ym_curr = MONTHS[i]

    prev_scores = scores[scores["month"] == ym_prev]
    curr_scores = scores[scores["month"] == ym_curr]

    if len(prev_scores) < 100 or len(curr_scores) < 100:
        continue

    row = {"month_pair": f"{ym_prev}->{ym_curr}"}

    for method_name, sort_col in [("ModelRank", "score_normalized"),
                                   ("Downloads", "downloads"),
                                   ("Likes", "likes")]:
        prev_sorted = prev_scores.nlargest(500, sort_col)["model_id"]
        curr_sorted = curr_scores.nlargest(500, sort_col)["model_id"]

        for K in [10, 50, 100, 500]:
            prev_topk = set(prev_sorted.head(K))
            curr_topk = set(curr_sorted.head(K))
            j = jaccard(prev_topk, curr_topk)
            row[f"{method_name}_top{K}"] = round(j, 3)

    stability_rows.append(row)

stab_df = pd.DataFrame(stability_rows)
stab_df.to_csv(os.path.join(OUT_DIR, "rq2_stability.csv"), index=False)

# Average stability
print(f"\nAverage Jaccard stability:")
for method in ["ModelRank", "Downloads", "Likes"]:
    vals = {K: stab_df[f"{method}_top{K}"].mean() for K in [10, 50, 100, 500]}
    print(f"  {method:>10}: " + "  ".join(f"top-{K}={v:.3f}" for K, v in vals.items()))

print(f"\nDone. Results saved to {OUT_DIR}/")
