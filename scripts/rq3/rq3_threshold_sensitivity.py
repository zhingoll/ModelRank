#!/usr/bin/env python3
"""
RQ3: Threshold sensitivity analysis for role classification.
=============================================================
Tests P50, P70, P80, P85, P90, P95 thresholds to show that
core findings (HR existence, HR-PL separation, HR persistence)
are robust to threshold choice.

Output: output_v2/rq3_threshold_sensitivity.csv
"""
import os, time
import pandas as pd
import numpy as np
from scipy import stats
from collections import defaultdict

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
LAST = "2026-02"

t0 = time.time()
print("Loading data ...")
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))

df = scores[scores["month"] == LAST].copy()
print(f"  {len(df):,} models in {LAST}")

# Pre-compute structural proxies (descendant breadth)
direct_children = defaultdict(int)
for pid in edges["parent_id"]:
    direct_children[pid] += 1
df["desc_breadth"] = df["model_id"].map(direct_children).fillna(0).astype(int)

# Active months
edges["child_month"] = edges["child_created"].str[:7]
active_months = edges.groupby("parent_id")["child_month"].nunique().to_dict()
df["active_months"] = df["model_id"].map(active_months).fillna(0).astype(int)

THRESHOLDS = [50, 70, 80, 85, 90, 95]

results = []
print(f"\n{'Pctl':>5} {'PR%':>7} {'PL%':>7} {'HR%':>7} {'LT%':>7} "
      f"{'n_HR':>8} {'HR-PL breadth r':>16} {'HR-PL active_m r':>18}")
print("-" * 90)

for pctl in THRESHOLDS:
    q = pctl / 100.0
    dl_thresh = df["downloads"].quantile(q)
    mr_thresh = df["score_normalized"].quantile(q)

    hi_dl = df["downloads"] >= dl_thresh
    hi_mr = df["score_normalized"] >= mr_thresh

    df["role"] = "LT"
    df.loc[hi_dl & hi_mr, "role"] = "PR"
    df.loc[hi_dl & ~hi_mr, "role"] = "PL"
    df.loc[~hi_dl & hi_mr, "role"] = "HR"

    total = len(df)
    pr_n = (df["role"] == "PR").sum()
    pl_n = (df["role"] == "PL").sum()
    hr_n = (df["role"] == "HR").sum()
    lt_n = (df["role"] == "LT").sum()

    # HR vs PL on external variables
    hr_data = df[df["role"] == "HR"]
    pl_data = df[df["role"] == "PL"]

    if len(hr_data) > 5 and len(pl_data) > 5:
        u_b, p_b = stats.mannwhitneyu(hr_data["desc_breadth"], pl_data["desc_breadth"],
                                       alternative="two-sided")
        r_b = 1 - 2 * u_b / (len(hr_data) * len(pl_data))

        u_a, p_a = stats.mannwhitneyu(hr_data["active_months"], pl_data["active_months"],
                                       alternative="two-sided")
        r_a = 1 - 2 * u_a / (len(hr_data) * len(pl_data))
    else:
        r_b, r_a = 0, 0

    results.append({
        "percentile": pctl,
        "dl_threshold": dl_thresh,
        "mr_threshold": mr_thresh,
        "PR_pct": pr_n / total * 100,
        "PL_pct": pl_n / total * 100,
        "HR_pct": hr_n / total * 100,
        "LT_pct": lt_n / total * 100,
        "n_HR": hr_n,
        "n_PL": pl_n,
        "hr_pl_breadth_r": round(r_b, 3),
        "hr_pl_active_m_r": round(r_a, 3),
    })

    print(f"P{pctl:>3} {pr_n/total*100:>6.1f}% {pl_n/total*100:>6.1f}% "
          f"{hr_n/total*100:>6.1f}% {lt_n/total*100:>6.1f}% "
          f"{hr_n:>8,} {r_b:>16.3f} {r_a:>18.3f}")

res_df = pd.DataFrame(results)
res_df.to_csv(os.path.join(OUT_DIR, "rq3_threshold_sensitivity.csv"), index=False)

# Also check HR overlap across thresholds (Jaccard between P90 and others)
print(f"\n=== HR Overlap with P90 baseline ===")
p90_hr = set(df.loc[
    (df["downloads"] < df["downloads"].quantile(0.9)) &
    (df["score_normalized"] >= df["score_normalized"].quantile(0.9)),
    "model_id"])

for pctl in THRESHOLDS:
    q = pctl / 100.0
    dl_t = df["downloads"].quantile(q)
    mr_t = df["score_normalized"].quantile(q)
    hr_set = set(df.loc[
        (df["downloads"] < dl_t) & (df["score_normalized"] >= mr_t),
        "model_id"])
    if hr_set | p90_hr:
        j = len(hr_set & p90_hr) / len(hr_set | p90_hr)
    else:
        j = 0
    print(f"  P{pctl} vs P90: Jaccard={j:.3f}, |HR|={len(hr_set):,}")

print(f"\nDone in {time.time()-t0:.1f}s")
