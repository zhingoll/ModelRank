#!/usr/bin/env python3
"""
RQ1: Structural Characteristics of the Derivation Network
==========================================================
Analyzes: network scale & growth, derivation type distribution & evolution,
head concentration (Gini, top-K shares), DAG structure properties.

Reads:
  data_new/monthly/deriv_models.csv
  data_new/monthly/deriv_edges.csv
  data_new/monthly/deriv_summary.csv

Output:
  output_v2/rq1_growth.csv           - monthly V_t, E_t, new models
  output_v2/rq1_type_evolution.csv   - monthly derivation type distribution
  output_v2/rq1_concentration.csv    - monthly top-K shares and Gini
  output_v2/rq1_structure_stats.csv  - DAG structure statistics
"""
import os, sys
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import calendar

DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")
os.makedirs(OUT_DIR, exist_ok=True)

MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]

print("Loading data ...")
models = pd.read_csv(os.path.join(DATA_DIR, "deriv_models.csv"))
edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
summary = pd.read_csv(os.path.join(DATA_DIR, "deriv_summary.csv"))

# Add month column to edges based on child_created
edges["child_month"] = edges["child_created"].str[:7]

print(f"Models: {len(models):,}, Edges: {len(edges):,}")

# ── 1. Growth statistics ──
print("\n=== 1. Network Growth ===")
growth_rows = []
for ym in MONTHS:
    y, m = int(ym[:4]), int(ym[5:7])
    last_day = calendar.monthrange(y, m)[1]
    month_end = f"{y:04d}-{m:02d}-{last_day:02d}"
    month_start = f"{y:04d}-{m:02d}-01"

    vt = models[models["createdAt"] <= month_end]
    et = edges[edges["child_month"] == ym]
    new_models = models[(models["createdAt"] >= month_start) &
                        (models["createdAt"] <= month_end)]
    # Active base models: unique parents receiving new derivatives this month
    active_bases = et["parent_id"].nunique()

    growth_rows.append({
        "month": ym,
        "vt_size": len(vt),
        "new_models": len(new_models),
        "et_edges": len(et),
        "active_bases": active_bases,
    })

growth_df = pd.DataFrame(growth_rows)
growth_df.to_csv(os.path.join(OUT_DIR, "rq1_growth.csv"), index=False)
print(growth_df.to_string(index=False))

total_growth = (growth_df["vt_size"].iloc[-1] - growth_df["vt_size"].iloc[0]) / growth_df["vt_size"].iloc[0] * 100
print(f"\nNetwork growth: {growth_df['vt_size'].iloc[0]:,} -> {growth_df['vt_size'].iloc[-1]:,} ({total_growth:.1f}%)")
print(f"Avg monthly new edges: {growth_df['et_edges'].mean():,.0f}")
print(f"Avg active bases/month: {growth_df['active_bases'].mean():,.0f}")

# ── 2. Derivation type evolution ──
print("\n=== 2. Derivation Type Evolution ===")
type_rows = []
for ym in MONTHS:
    et = edges[edges["child_month"] == ym]
    total = len(et)
    if total == 0:
        continue
    counts = et["relation"].value_counts()
    row = {"month": ym, "total": total}
    for rtype in ["finetune", "adapter", "quantized", "merge", "unknown"]:
        cnt = counts.get(rtype, 0)
        row[rtype] = cnt
        row[f"{rtype}_pct"] = cnt / total * 100
    type_rows.append(row)

type_df = pd.DataFrame(type_rows)
type_df.to_csv(os.path.join(OUT_DIR, "rq1_type_evolution.csv"), index=False)
print(type_df[["month", "total", "finetune_pct", "adapter_pct", "quantized_pct", "merge_pct"]].to_string(index=False, float_format="%.1f"))

# All-time type distribution
print(f"\nAll-time type distribution:")
for rtype, cnt in edges["relation"].value_counts().items():
    print(f"  {rtype}: {cnt:,} ({cnt/len(edges)*100:.1f}%)")

# ── 3. Head concentration ──
print("\n=== 3. Head Concentration ===")

def gini(values):
    """Compute Gini coefficient."""
    v = np.sort(np.array(values, dtype=float))
    n = len(v)
    if n == 0 or v.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return (2 * np.sum(idx * v) - (n + 1) * v.sum()) / (n * v.sum())

conc_rows = []
for ym in MONTHS:
    et = edges[edges["child_month"] == ym]
    if len(et) == 0:
        continue
    parent_counts = et["parent_id"].value_counts()
    total_edges = len(et)
    n_bases = len(parent_counts)

    top1 = parent_counts.iloc[0] if len(parent_counts) >= 1 else 0
    top10 = parent_counts.iloc[:10].sum() if len(parent_counts) >= 10 else parent_counts.sum()
    top50 = parent_counts.iloc[:50].sum() if len(parent_counts) >= 50 else parent_counts.sum()

    g = gini(parent_counts.values)

    conc_rows.append({
        "month": ym,
        "n_active_bases": n_bases,
        "top1_share": top1 / total_edges * 100,
        "top10_share": top10 / total_edges * 100,
        "top50_share": top50 / total_edges * 100,
        "gini": round(g, 3),
        "median_derivs": parent_counts.median(),
        "mean_derivs": round(parent_counts.mean(), 1),
        "top1_model": parent_counts.index[0] if len(parent_counts) > 0 else "",
        "top1_count": int(top1),
    })

conc_df = pd.DataFrame(conc_rows)
conc_df.to_csv(os.path.join(OUT_DIR, "rq1_concentration.csv"), index=False)
print(conc_df[["month", "n_active_bases", "top1_share", "top10_share", "top50_share", "gini"]].to_string(index=False, float_format="%.1f"))

# All-time Gini
all_parent_counts = edges["parent_id"].value_counts()
all_gini = gini(all_parent_counts.values)
print(f"\nAll-time Gini: {all_gini:.3f}")
print(f"All-time median derivs per base: {all_parent_counts.median()}")
print(f"All-time mean derivs per base: {all_parent_counts.mean():.1f}")
print(f"Top base model: {all_parent_counts.index[0]} ({all_parent_counts.iloc[0]:,} derivs)")

# ── 4. DAG structure statistics ──
print("\n=== 4. DAG Structure ===")

# Parent count distribution (how many parents per child)
child_parent_counts = edges.groupby("child_id")["parent_id"].nunique()
single_parent = (child_parent_counts == 1).sum()
multi_parent = (child_parent_counts > 1).sum()
total_children = len(child_parent_counts)

print(f"Total child models: {total_children:,}")
print(f"Single parent: {single_parent:,} ({single_parent/total_children*100:.1f}%)")
print(f"Multi parent:  {multi_parent:,} ({multi_parent/total_children*100:.1f}%)")
print(f"Max parents:   {child_parent_counts.max()}")

# Dangling node ratio (per month, in event graph)
# Dangling = in V_t but has no outgoing edge in E_t
# In our event graph, "outgoing edge" means the model is a child that points to a parent
# So dangling = models in V_t that are NOT children in E_t
print(f"\nDangling node ratio per month (models in V_t not acting as children in E_t):")
dang_rows = []
for ym in MONTHS:
    y, m = int(ym[:4]), int(ym[5:7])
    last_day = calendar.monthrange(y, m)[1]
    month_end = f"{y:04d}-{m:02d}-{last_day:02d}"

    vt_ids = set(models[models["createdAt"] <= month_end]["id"])
    et_children = set(edges[edges["child_month"] == ym]["child_id"])
    n_vt = len(vt_ids)
    n_active = len(et_children & vt_ids)
    n_dangling = n_vt - n_active
    dang_pct = n_dangling / n_vt * 100 if n_vt > 0 else 0

    dang_rows.append({"month": ym, "n_vt": n_vt, "n_dangling": n_dangling, "dangling_pct": round(dang_pct, 1)})

dang_df = pd.DataFrame(dang_rows)
print(dang_df.to_string(index=False))
print(f"\nAvg dangling ratio: {dang_df['dangling_pct'].mean():.1f}%")

# Save structure stats
stats = {
    "total_models_in_network": len(models),
    "total_edges": len(edges),
    "unique_parents": edges["parent_id"].nunique(),
    "unique_children": edges["child_id"].nunique(),
    "single_parent_pct": round(single_parent / total_children * 100, 1),
    "multi_parent_pct": round(multi_parent / total_children * 100, 1),
    "max_parents": int(child_parent_counts.max()),
    "alltime_gini": round(all_gini, 3),
    "avg_dangling_pct": round(dang_df["dangling_pct"].mean(), 1),
}
pd.DataFrame([stats]).to_csv(os.path.join(OUT_DIR, "rq1_structure_stats.csv"), index=False)
print(f"\nStructure stats saved.")
print(f"Done.")
