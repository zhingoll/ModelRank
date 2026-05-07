#!/usr/bin/env python3
"""
RQ3 supplement: HR persistence analysis (vectorized)
=====================================================
Output: output_v2/rq3_hr_persistence.csv
"""
import os, time
import pandas as pd
import numpy as np
from scipy import stats
from collections import defaultdict

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
MONTHS = [
    "2024-07","2024-08","2024-09","2024-10","2024-11","2024-12",
    "2025-01","2025-02","2025-03","2025-04","2025-05","2025-06",
    "2025-07","2025-08","2025-09","2025-10","2025-11","2025-12",
    "2026-01","2026-02",
]

t0 = time.time()
print("Loading data ...")
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
edges["child_month"] = edges["child_created"].str[:7]

# Active parents per month
active_parents = defaultdict(set)
for cm, pid in zip(edges["child_month"], edges["parent_id"]):
    if pd.notna(cm):
        active_parents[cm].add(pid)

# Vectorized role assignment per month
print("Computing roles per month (vectorized) ...")
hr_sets = {}
lt_sets = {}
pr_sets = {}
dl_by_month = {}  # month -> {model_id: downloads}

for ym in MONTHS:
    ms = scores[scores["month"] == ym].copy()
    dl_p90 = ms["downloads"].quantile(0.9)
    mr_p90 = ms["score_normalized"].quantile(0.9)

    hi_dl = ms["downloads"] >= dl_p90
    hi_mr = ms["score_normalized"] >= mr_p90

    hr_mask = (~hi_dl) & hi_mr
    lt_mask = (~hi_dl) & (~hi_mr)
    pr_mask = hi_dl & hi_mr

    hr_sets[ym] = set(ms.loc[hr_mask, "model_id"])
    lt_sets[ym] = set(ms.loc[lt_mask, "model_id"])
    pr_sets[ym] = set(ms.loc[pr_mask, "model_id"])
    dl_by_month[ym] = dict(zip(ms["model_id"], ms["downloads"]))

print(f"  Done in {time.time()-t0:.1f}s")

# Persistence analysis
print("\nComputing HR persistence ...")
results = []
np.random.seed(42)

for i in range(len(MONTHS) - 3):
    ym = MONTHS[i]
    future = MONTHS[i+1:i+4]

    hr_ids = hr_sets[ym]
    lt_ids = lt_sets[ym]
    if len(hr_ids) < 10:
        continue

    # Match LT controls by downloads
    hr_dls = [dl_by_month[ym].get(m, 0) for m in hr_ids]
    q10, q90 = np.percentile(hr_dls, [10, 90])
    lt_similar = [m for m in lt_ids if q10 <= dl_by_month[ym].get(m, 0) <= q90]
    if len(lt_similar) < 100:
        lt_similar = list(lt_ids)

    rng = np.random.RandomState(42 + i)
    n_sample = min(len(hr_ids), len(lt_similar))
    ctrl_ids = set(rng.choice(lt_similar, size=n_sample, replace=False))

    # Active-parent rate
    hr_active = sum(1 for m in hr_ids if any(m in active_parents.get(fm, set()) for fm in future))
    ctrl_active = sum(1 for m in ctrl_ids if any(m in active_parents.get(fm, set()) for fm in future))

    hr_rate = hr_active / len(hr_ids)
    ctrl_rate = ctrl_active / len(ctrl_ids) if ctrl_ids else 0

    # PR transition rate
    hr_ever_pr = sum(1 for m in hr_ids if any(m in pr_sets.get(fm, set()) for fm in future))
    ctrl_ever_pr = sum(1 for m in ctrl_ids if any(m in pr_sets.get(fm, set()) for fm in future))

    hr_pr_rate = hr_ever_pr / len(hr_ids)
    ctrl_pr_rate = ctrl_ever_pr / len(ctrl_ids) if ctrl_ids else 0

    results.append({
        "month": ym, "n_hr": len(hr_ids), "n_ctrl": len(ctrl_ids),
        "hr_active_rate": round(hr_rate, 4),
        "ctrl_active_rate": round(ctrl_rate, 4),
        "hr_to_pr_rate": round(hr_pr_rate, 4),
        "ctrl_to_pr_rate": round(ctrl_pr_rate, 4),
    })
    print(f"  {ym}: HR active={hr_rate:.1%} ctrl={ctrl_rate:.1%} | "
          f"HR→PR={hr_pr_rate:.1%} ctrl→PR={ctrl_pr_rate:.1%}")

res_df = pd.DataFrame(results)
res_df.to_csv(os.path.join(OUT_DIR, "rq3_hr_persistence.csv"), index=False)

print(f"\n=== Summary ({len(res_df)} months) ===")
print(f"Mean HR active-parent rate:   {res_df['hr_active_rate'].mean():.1%}")
print(f"Mean ctrl active-parent rate: {res_df['ctrl_active_rate'].mean():.1%}")
ratio = res_df['hr_active_rate'].mean() / max(res_df['ctrl_active_rate'].mean(), 1e-9)
print(f"Ratio: {ratio:.1f}x")
print(f"Mean HR→PR rate:   {res_df['hr_to_pr_rate'].mean():.1%}")
print(f"Mean ctrl→PR rate: {res_df['ctrl_to_pr_rate'].mean():.1%}")

if len(res_df) >= 5:
    t1, p1 = stats.wilcoxon(res_df["hr_active_rate"], res_df["ctrl_active_rate"])
    print(f"Wilcoxon (active): T={t1:.1f}, p={p1:.4f}")
    t2, p2 = stats.wilcoxon(res_df["hr_to_pr_rate"], res_df["ctrl_to_pr_rate"])
    print(f"Wilcoxon (→PR):    T={t2:.1f}, p={p2:.4f}")

print(f"\nDone in {time.time()-t0:.1f}s")
