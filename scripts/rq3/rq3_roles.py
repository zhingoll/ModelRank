#!/usr/bin/env python3
"""
RQ3: Structural Divergence and Ecosystem Roles
===============================================
Core RQ: identify four ecosystem roles based on usage x reuse dimensions.

Reads: output_v2/modelrank_scores.csv
Output:
  output_v2/rq3_role_distribution.csv
  output_v2/rq3_role_characteristics.csv
  output_v2/rq3_top_hidden_roots.csv
  output_v2/rq3_case_studies.csv
"""
import os
import pandas as pd
import numpy as np
from scipy import stats

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")

print("Loading scores ...")
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))

# Use last month for main analysis
LAST_MONTH = "2026-02"
df = scores[scores["month"] == LAST_MONTH].copy()
print(f"Last month ({LAST_MONTH}): {len(df):,} models")

# Two dimensions:
# - Usage popularity: downloads (near 30-day)
# - Derivative reuse: score_normalized (ModelRank)

# Use median as threshold for role classification
dl_median = df["downloads"].median()
mr_median = df["score_normalized"].median()
print(f"Downloads median: {dl_median:,.0f}")
print(f"ModelRank median: {mr_median:.4f}")

# Assign roles
def assign_role(row, dl_thresh, mr_thresh):
    high_dl = row["downloads"] >= dl_thresh
    high_mr = row["score_normalized"] >= mr_thresh
    if high_dl and high_mr:
        return "Popular Roots"
    elif high_dl and not high_mr:
        return "Popular Leaves"
    elif not high_dl and high_mr:
        return "Hidden Roots"
    else:
        return "Long Tail"

# Use top-500 by ModelRank for focused analysis (consistent with paper approach)
# Within top-500, use median downloads as threshold
top500 = df.nsmallest(500, "rank").copy()
dl_thresh = top500["downloads"].median()
mr_thresh = top500["score_normalized"].median()
print(f"\nTop-500 analysis:")
print(f"  Downloads median (threshold): {dl_thresh:,.0f}")
print(f"  MR score median (threshold): {mr_thresh:.2f}")

# Also try: use overall P90 as "high usage" threshold
dl_p90 = df["downloads"].quantile(0.90)
mr_p90 = df["score_normalized"].quantile(0.90)
print(f"\nP90 thresholds: downloads >= {dl_p90:,.0f}, MR >= {mr_p90:.2f}")

# Use P90 for role assignment (top 10% = high)
df["role"] = df.apply(lambda r: assign_role(r, dl_p90, mr_p90), axis=1)

# Role distribution
print(f"\n=== Role Distribution ===")
role_counts = df["role"].value_counts()
for role, cnt in role_counts.items():
    print(f"  {role:<20}: {cnt:>7,} ({cnt/len(df)*100:.1f}%)")

# ── Role characteristics ──
print(f"\n=== Role Characteristics ===")
char_rows = []
for role in ["Popular Roots", "Popular Leaves", "Hidden Roots", "Long Tail"]:
    sub = df[df["role"] == role]
    if len(sub) == 0:
        continue
    char_rows.append({
        "role": role,
        "count": len(sub),
        "median_downloads": sub["downloads"].median(),
        "median_likes": sub["likes"].median(),
        "median_mr_score": sub["score_normalized"].median(),
        "median_derivs": sub["n_derivatives"].median(),
        "mean_derivs": sub["n_derivatives"].mean(),
        "median_q_base": sub["q_base"].median(),
    })

char_df = pd.DataFrame(char_rows)
char_df.to_csv(os.path.join(OUT_DIR, "rq3_role_characteristics.csv"), index=False)
print(char_df.to_string(index=False))

# ── Statistical tests: Popular Roots vs Popular Leaves, Hidden Roots vs Long Tail ──
print(f"\n=== Statistical Tests ===")

def mann_whitney_test(group1, group2, label):
    u, p = stats.mannwhitneyu(group1, group2, alternative="two-sided")
    n1, n2 = len(group1), len(group2)
    r = 1 - (2 * u) / (n1 * n2)  # rank-biserial correlation
    print(f"  {label}: U={u:,.0f}, p={p:.2e}, r={r:.3f}, n1={n1}, n2={n2}")
    return u, p, r

pr = df[df["role"] == "Popular Roots"]
pl = df[df["role"] == "Popular Leaves"]
hr = df[df["role"] == "Hidden Roots"]

print("Popular Roots vs Popular Leaves:")
mann_whitney_test(pr["downloads"], pl["downloads"], "downloads")
mann_whitney_test(pr["score_normalized"], pl["score_normalized"], "MR score")
mann_whitney_test(pr["n_derivatives"], pl["n_derivatives"], "derivs")

print("\nHidden Roots vs Popular Leaves:")
mann_whitney_test(hr["downloads"], pl["downloads"], "downloads")
mann_whitney_test(hr["score_normalized"], pl["score_normalized"], "MR score")
mann_whitney_test(hr["n_derivatives"], pl["n_derivatives"], "derivs")

print("\nHidden Roots vs Popular Roots:")
mann_whitney_test(hr["downloads"], pr["downloads"], "downloads")
mann_whitney_test(hr["score_normalized"], pr["score_normalized"], "MR score")

# ── Top Hidden Roots ──
print(f"\n=== Top 20 Hidden Roots ===")
hr_top = hr.nlargest(20, "score_normalized")
top_hr_rows = []
for _, r in hr_top.iterrows():
    top_hr_rows.append({
        "model_id": r["model_id"],
        "mr_rank": int(r["rank"]),
        "mr_score": round(r["score_normalized"], 2),
        "downloads": int(r["downloads"]),
        "likes": int(r["likes"]),
        "n_derivatives": int(r["n_derivatives"]),
    })

top_hr_df = pd.DataFrame(top_hr_rows)
top_hr_df.to_csv(os.path.join(OUT_DIR, "rq3_top_hidden_roots.csv"), index=False)
for _, r in top_hr_df.iterrows():
    print(f"  Rank {r['mr_rank']:>4}: {r['model_id'][:55]:<55} "
          f"dl={r['downloads']:>10,} derivs={r['n_derivatives']:>4}")

# ── Case studies: representative models from each role ──
print(f"\n=== Case Studies ===")
case_rows = []
for role in ["Popular Roots", "Popular Leaves", "Hidden Roots", "Long Tail"]:
    sub = df[df["role"] == role]
    if len(sub) == 0:
        continue
    # Top 3 by MR score for Roots, by downloads for Leaves/LongTail
    if "Roots" in role:
        top3 = sub.nlargest(3, "score_normalized")
    else:
        top3 = sub.nlargest(3, "downloads")
    for _, r in top3.iterrows():
        case_rows.append({
            "role": role,
            "model_id": r["model_id"],
            "mr_rank": int(r["rank"]),
            "mr_score": round(r["score_normalized"], 2),
            "downloads": int(r["downloads"]),
            "likes": int(r["likes"]),
            "n_derivatives": int(r["n_derivatives"]),
        })

case_df = pd.DataFrame(case_rows)
case_df.to_csv(os.path.join(OUT_DIR, "rq3_case_studies.csv"), index=False)
print(case_df.to_string(index=False))

# ── Role distribution over time ──
print(f"\n=== Role Distribution Over Time ===")
role_time_rows = []
for ym in scores["month"].unique():
    ms = scores[scores["month"] == ym].copy()
    dl_t = ms["downloads"].quantile(0.90)
    mr_t = ms["score_normalized"].quantile(0.90)
    ms["role"] = ms.apply(lambda r: assign_role(r, dl_t, mr_t), axis=1)
    counts = ms["role"].value_counts()
    total = len(ms)
    role_time_rows.append({
        "month": ym,
        "Popular_Roots": counts.get("Popular Roots", 0),
        "Popular_Leaves": counts.get("Popular Leaves", 0),
        "Hidden_Roots": counts.get("Hidden Roots", 0),
        "Long_Tail": counts.get("Long Tail", 0),
        "PR_pct": counts.get("Popular Roots", 0) / total * 100,
        "PL_pct": counts.get("Popular Leaves", 0) / total * 100,
        "HR_pct": counts.get("Hidden Roots", 0) / total * 100,
        "LT_pct": counts.get("Long Tail", 0) / total * 100,
    })

role_time_df = pd.DataFrame(role_time_rows)
role_time_df.to_csv(os.path.join(OUT_DIR, "rq3_role_distribution.csv"), index=False)
print(role_time_df[["month", "PR_pct", "PL_pct", "HR_pct", "LT_pct"]].to_string(index=False, float_format="%.1f"))

print(f"\nDone.")
