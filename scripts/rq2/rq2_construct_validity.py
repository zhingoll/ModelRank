#!/usr/bin/env python3
"""
RQ2 Construct Validity Experiments
===================================
Addresses reviewer concerns about whether ModelRank truly measures
reuse centrality vs popularity-augmented influence.

Three experiments:
  A. Pure-Structure baseline (remove quality/popularity from teleport)
  B. Convergent validity (MR vs reuse-oriented structural proxies)
  C. Discriminant validity (within similar-downloads bands, does MR
     still distinguish reuse structure?)

Reads:
  output_v2/modelrank_scores.csv
  data_new/monthly/deriv_edges.csv
  data_new/monthly/deriv_models.csv

Output:
  output_v2/rq2_construct_pure_structure.csv
  output_v2/rq2_construct_convergent.csv
  output_v2/rq2_construct_discriminant.csv
"""
import os, sys, time
import pandas as pd
import numpy as np
from scipy import stats, sparse
from collections import defaultdict

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")

MONTHS = [
    "2024-07","2024-08","2024-09","2024-10","2024-11","2024-12",
    "2025-01","2025-02","2025-03","2025-04","2025-05","2025-06",
    "2025-07","2025-08","2025-09","2025-10","2025-11","2025-12",
    "2026-01","2026-02",
]
LAST = "2026-02"

t0 = time.time()

# ── Load data ──
print("Loading data ...")
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
edges_all = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
edges_all["child_month"] = edges_all["child_created"].str[:7]

print(f"  Scores: {len(scores):,} rows")
print(f"  Edges: {len(edges_all):,} rows")

# Last month data
df = scores[scores["month"] == LAST].copy()
print(f"  Last month ({LAST}): {len(df):,} models")


# ============================================================
# Compute structural reuse proxies for all models
# ============================================================
print("\nComputing structural reuse proxies ...")

# Build full DAG from all edges (not just window)
# For each parent, compute:
#   - descendant_count: total number of descendants (direct + transitive)
#   - descendant_depth: max depth of descendant tree
#   - descendant_breadth: number of direct children (all-time)
#   - active_months: number of months in which model received >= 1 derivative
#   - deriv_type_diversity: number of distinct derivation types among children

# Direct children per parent (all-time)
direct_children = defaultdict(set)
child_types = defaultdict(set)
for _, row in edges_all.iterrows():
    pid = row["parent_id"]
    cid = row["child_id"]
    direct_children[pid].add(cid)
    if pd.notna(row.get("relation")):
        child_types[pid].add(row["relation"])

# Active months per parent
active_months = defaultdict(set)
for _, row in edges_all.iterrows():
    pid = row["parent_id"]
    cm = row["child_month"]
    if pd.notna(cm):
        active_months[pid].add(cm)

# Build adjacency for BFS (parent -> children)
parent_to_children = defaultdict(set)
for _, row in edges_all.iterrows():
    parent_to_children[row["parent_id"]].add(row["child_id"])

# Compute descendant depth and count via BFS (for models in last month)
print("  Computing descendant depth/count via BFS ...")
model_ids = set(df["model_id"].values)

desc_count = {}
desc_depth = {}

# BFS from each model that has children
models_with_children = set(parent_to_children.keys()) & model_ids
print(f"  {len(models_with_children):,} models have children")

batch_size = 10000
processed = 0
for mid in models_with_children:
    # BFS
    visited = set()
    queue = [(mid, 0)]
    max_depth = 0
    while queue:
        node, depth = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if depth > max_depth:
            max_depth = depth
        for child in parent_to_children.get(node, []):
            if child not in visited:
                queue.append((child, depth + 1))
    desc_count[mid] = len(visited) - 1  # exclude self
    desc_depth[mid] = max_depth
    processed += 1
    if processed % batch_size == 0:
        print(f"    {processed:,}/{len(models_with_children):,} ...")

# For models without children
for mid in model_ids - models_with_children:
    desc_count[mid] = 0
    desc_depth[mid] = 0

print(f"  BFS complete. {processed:,} models processed.")

# Add proxies to dataframe
df["desc_count"] = df["model_id"].map(desc_count).fillna(0).astype(int)
df["desc_depth"] = df["model_id"].map(desc_depth).fillna(0).astype(int)
df["desc_breadth"] = df["model_id"].map(lambda m: len(direct_children.get(m, set()))).astype(int)
df["active_months"] = df["model_id"].map(lambda m: len(active_months.get(m, set()))).astype(int)
df["type_diversity"] = df["model_id"].map(lambda m: len(child_types.get(m, set()))).astype(int)

print(f"\nProxy statistics:")
for col in ["desc_count", "desc_depth", "desc_breadth", "active_months", "type_diversity"]:
    nz = (df[col] > 0).sum()
    print(f"  {col}: mean={df[col].mean():.2f}, median={df[col].median():.0f}, "
          f"max={df[col].max()}, >0: {nz:,} ({nz/len(df)*100:.1f}%)")


# ============================================================
# Experiment A: Pure-Structure Baseline
# ============================================================
print("\n" + "="*60)
print("EXPERIMENT A: Pure-Structure Baseline")
print("="*60)
print("Computing MR variant with q(v,t) = constant (no popularity)")
print("This tests whether Hidden Roots persist without downloads/likes")

# Pure-structure score: use event_value only (no quality in teleport)
# event_value already captures type weights, child quality, size mitigation
# But child quality itself uses downloads/likes...
# The cleanest approach: rank by event_value alone (= Simplified-MR without q)
# This is: sum of type-weighted, quality-weighted derivatives with size mitigation
# For a truly pure-structure version, we also remove quality weighting from event value
# Pure-structure = sum of (type_weight / n_parents) * ln(1+params)^kappa per derivative

# We'll compute two variants:
# A1: event_value only (still has quality weighting of children)
# A2: pure_structure (type_weight * size_mitigation only, no quality at all)

# A2: Pure structure score
print("\n  Computing pure-structure scores ...")
# For each parent in last month, sum type_weight * size_mitigation / n_parents
# across all derivatives received in the last month

TYPE_WEIGHTS = {"finetune": 1.0, "adapter": 0.8, "merge": 0.5, "quantized": 0.3}
DEFAULT_TW = 0.5
KAPPA = 0.5

# Load model metadata for params
models_meta = pd.read_csv(os.path.join(DATA_DIR, "deriv_models.csv"),
                          usecols=["id", "params"])
params_map = dict(zip(models_meta["id"], models_meta["params"]))
p10 = np.nanpercentile([v for v in params_map.values() if v and v > 0], 10)

last_edges = edges_all[edges_all["child_month"] == LAST]

# Pre-compute parent count per child in last month
child_parent_count = last_edges.groupby("child_id")["parent_id"].count().to_dict()

pure_struct = defaultdict(float)
for _, row in last_edges.iterrows():
    pid = row["parent_id"]
    cid = row["child_id"]
    rel = row.get("relation", "")
    tw = TYPE_WEIGHTS.get(rel, DEFAULT_TW)
    p_val = params_map.get(pid)
    if p_val is None or p_val <= 0 or (isinstance(p_val, float) and np.isnan(p_val)):
        p_val = p10
    size_factor = np.log1p(p_val) ** KAPPA
    n_parents = child_parent_count.get(cid, 1)
    pure_struct[pid] += tw * size_factor / n_parents

df["pure_struct_score"] = df["model_id"].map(pure_struct).fillna(0.0)

# Also compute cumulative pure-structure (all-time descendant-based)
# = desc_breadth weighted by type
cum_struct = defaultdict(float)
for _, row in edges_all.iterrows():
    pid = row["parent_id"]
    rel = row.get("relation", "")
    tw = TYPE_WEIGHTS.get(rel, DEFAULT_TW)
    cum_struct[pid] += tw

df["cum_struct_score"] = df["model_id"].map(cum_struct).fillna(0.0)

# Assign roles using pure-structure score
dl_p90 = df["downloads"].quantile(0.9)
mr_p90 = df["score_normalized"].quantile(0.9)
ps_p90 = df["pure_struct_score"].quantile(0.9)
cs_p90 = df["cum_struct_score"].quantile(0.9)

def assign_role(dl, metric, thresh):
    hi_dl = dl >= dl_p90
    hi_m = metric >= thresh
    if hi_dl and hi_m: return "PR"
    if hi_dl and not hi_m: return "PL"
    if not hi_dl and hi_m: return "HR"
    return "LT"

df["role_mr"] = df.apply(lambda r: assign_role(r["downloads"], r["score_normalized"], mr_p90), axis=1)
df["role_ps"] = df.apply(lambda r: assign_role(r["downloads"], r["pure_struct_score"], ps_p90), axis=1)
df["role_cs"] = df.apply(lambda r: assign_role(r["downloads"], r["cum_struct_score"], cs_p90), axis=1)

print("\n  Role distribution comparison:")
for label, col in [("ModelRank", "role_mr"), ("PureStruct(monthly)", "role_ps"),
                    ("CumStruct(all-time)", "role_cs")]:
    counts = df[col].value_counts()
    total = len(df)
    print(f"\n  {label}:")
    for role in ["PR", "PL", "HR", "LT"]:
        c = counts.get(role, 0)
        print(f"    {role}: {c:>7,} ({c/total*100:.1f}%)")

# Overlap of Hidden Roots between MR and pure-structure
hr_mr = set(df[df["role_mr"] == "HR"]["model_id"])
hr_ps = set(df[df["role_ps"] == "HR"]["model_id"])
hr_cs = set(df[df["role_cs"] == "HR"]["model_id"])
overlap_ps = len(hr_mr & hr_ps) / len(hr_mr | hr_ps) if (hr_mr | hr_ps) else 0
overlap_cs = len(hr_mr & hr_cs) / len(hr_mr | hr_cs) if (hr_mr | hr_cs) else 0
print(f"\n  HR overlap (Jaccard):")
print(f"    MR vs PureStruct(monthly): {overlap_ps:.3f} ({len(hr_mr & hr_ps):,} shared)")
print(f"    MR vs CumStruct(all-time): {overlap_cs:.3f} ({len(hr_mr & hr_cs):,} shared)")

# Correlation between MR and pure-structure scores
rho_ps, _ = stats.spearmanr(df["score_normalized"], df["pure_struct_score"])
rho_cs, _ = stats.spearmanr(df["score_normalized"], df["cum_struct_score"])
rho_dl_ps, _ = stats.spearmanr(df["downloads"], df["pure_struct_score"])
rho_dl_cs, _ = stats.spearmanr(df["downloads"], df["cum_struct_score"])
print(f"\n  Spearman correlations:")
print(f"    MR vs PureStruct(monthly): {rho_ps:.3f}")
print(f"    MR vs CumStruct(all-time): {rho_cs:.3f}")
print(f"    Downloads vs PureStruct(monthly): {rho_dl_ps:.3f}")
print(f"    Downloads vs CumStruct(all-time): {rho_dl_cs:.3f}")

# Save
ps_results = {
    "metric": ["MR_vs_PureStruct_rho", "MR_vs_CumStruct_rho",
                "DL_vs_PureStruct_rho", "DL_vs_CumStruct_rho",
                "HR_overlap_MR_PureStruct", "HR_overlap_MR_CumStruct",
                "HR_count_MR", "HR_count_PureStruct", "HR_count_CumStruct"],
    "value": [rho_ps, rho_cs, rho_dl_ps, rho_dl_cs,
              overlap_ps, overlap_cs,
              len(hr_mr), len(hr_ps), len(hr_cs)]
}
pd.DataFrame(ps_results).to_csv(
    os.path.join(OUT_DIR, "rq2_construct_pure_structure.csv"), index=False)


# ============================================================
# Experiment B: Convergent Validity
# ============================================================
print("\n" + "="*60)
print("EXPERIMENT B: Convergent Validity")
print("="*60)
print("Does MR correlate more with reuse proxies than Downloads does?")

proxies = ["desc_count", "desc_depth", "desc_breadth", "active_months", "type_diversity"]
methods = {
    "ModelRank": "score_normalized",
    "Downloads": "downloads",
    "Likes": "likes",
    "DerivCount": "n_derivatives",
    "PureStruct": "pure_struct_score",
    "CumStruct": "cum_struct_score",
}

conv_rows = []
print(f"\n  Spearman correlations with reuse proxies (n={len(df):,}):")
print(f"  {'Method':<15} " + " ".join(f"{p:>15}" for p in proxies))
for mname, mcol in methods.items():
    row = {"method": mname}
    vals = []
    for proxy in proxies:
        rho, _ = stats.spearmanr(df[mcol], df[proxy])
        row[f"rho_{proxy}"] = round(rho, 3)
        vals.append(f"{rho:>15.3f}")
    conv_rows.append(row)
    print(f"  {mname:<15} " + " ".join(vals))

conv_df = pd.DataFrame(conv_rows)
conv_df.to_csv(os.path.join(OUT_DIR, "rq2_construct_convergent.csv"), index=False)

# Key comparison: MR vs Downloads on each proxy
print(f"\n  MR advantage over Downloads (rho_MR - rho_DL):")
mr_row = conv_df[conv_df["method"] == "ModelRank"].iloc[0]
dl_row = conv_df[conv_df["method"] == "Downloads"].iloc[0]
for proxy in proxies:
    diff = mr_row[f"rho_{proxy}"] - dl_row[f"rho_{proxy}"]
    print(f"    {proxy}: {diff:+.3f} ({'MR better' if diff > 0 else 'DL better'})")


# ============================================================
# Experiment C: Discriminant Validity
# ============================================================
print("\n" + "="*60)
print("EXPERIMENT C: Discriminant Validity")
print("="*60)
print("Within similar-downloads bands, does MR distinguish reuse structure?")

# Bin models by downloads into deciles, then within each bin
# compare MR-high vs MR-low on structural proxies
df_with_dl = df[df["downloads"] > 0].copy()
df_with_dl["dl_decile"] = pd.qcut(df_with_dl["downloads"], 10, labels=False, duplicates="drop")

disc_rows = []
print(f"\n  Within-decile analysis (models with downloads > 0, n={len(df_with_dl):,}):")
print(f"  {'Decile':<8} {'n':>6} {'MR-hi desc_ct':>14} {'MR-lo desc_ct':>14} "
      f"{'U-test p':>10} {'effect r':>10}")

for dec in sorted(df_with_dl["dl_decile"].unique()):
    band = df_with_dl[df_with_dl["dl_decile"] == dec]
    if len(band) < 20:
        continue
    mr_median = band["score_normalized"].median()
    hi = band[band["score_normalized"] >= mr_median]
    lo = band[band["score_normalized"] < mr_median]
    if len(hi) < 5 or len(lo) < 5:
        continue

    # Compare on desc_count
    u, p = stats.mannwhitneyu(hi["desc_count"], lo["desc_count"], alternative="two-sided")
    r = 1 - 2*u/(len(hi)*len(lo))

    row = {
        "decile": int(dec),
        "n": len(band),
        "dl_range": f"{band['downloads'].min():.0f}-{band['downloads'].max():.0f}",
        "mr_hi_desc_count_mean": hi["desc_count"].mean(),
        "mr_lo_desc_count_mean": lo["desc_count"].mean(),
        "mr_hi_desc_depth_mean": hi["desc_depth"].mean(),
        "mr_lo_desc_depth_mean": lo["desc_depth"].mean(),
        "mr_hi_active_months_mean": hi["active_months"].mean(),
        "mr_lo_active_months_mean": lo["active_months"].mean(),
        "u_stat": u,
        "p_value": p,
        "effect_r": r,
    }
    disc_rows.append(row)
    print(f"  {dec:<8} {len(band):>6} {hi['desc_count'].mean():>14.2f} "
          f"{lo['desc_count'].mean():>14.2f} {p:>10.2e} {r:>10.3f}")

disc_df = pd.DataFrame(disc_rows)
disc_df.to_csv(os.path.join(OUT_DIR, "rq2_construct_discriminant.csv"), index=False)

# Summary: how many deciles show significant discrimination?
sig_deciles = disc_df[disc_df["p_value"] < 0.05]
print(f"\n  Significant discrimination (p<0.05): {len(sig_deciles)}/{len(disc_df)} deciles")
print(f"  Mean effect size r: {disc_df['effect_r'].mean():.3f}")


# ============================================================
# Experiment D: RQ3 External Variable Comparison
# ============================================================
print("\n" + "="*60)
print("EXPERIMENT D: RQ3 External Variable Comparison")
print("="*60)
print("Compare roles on NON-definitional variables")

# Roles already assigned as role_mr
role_order = ["PR", "PL", "HR", "LT"]
ext_vars = ["desc_count", "desc_depth", "desc_breadth", "active_months", "type_diversity"]

print(f"\n  Role characteristics on external variables (median):")
print(f"  {'Variable':<18} {'PR':>10} {'PL':>10} {'HR':>10} {'LT':>10}")
ext_rows = []
for var in ext_vars:
    vals = {}
    for role in role_order:
        sub = df[df["role_mr"] == role]
        vals[role] = sub[var].median()
    ext_rows.append({"variable": var, **vals})
    print(f"  {var:<18} {vals['PR']:>10.1f} {vals['PL']:>10.1f} "
          f"{vals['HR']:>10.1f} {vals['LT']:>10.1f}")

# Statistical tests: HR vs PL on external variables
print(f"\n  Mann-Whitney U: Hidden Roots vs Popular Leaves (external vars):")
hr_data = df[df["role_mr"] == "HR"]
pl_data = df[df["role_mr"] == "PL"]
test_rows = []
for var in ext_vars:
    u, p = stats.mannwhitneyu(hr_data[var], pl_data[var], alternative="two-sided")
    r = 1 - 2*u/(len(hr_data)*len(pl_data))
    test_rows.append({
        "variable": var,
        "HR_median": hr_data[var].median(),
        "PL_median": pl_data[var].median(),
        "U": u, "p": p, "r": r
    })
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"    {var:<18}: HR_med={hr_data[var].median():>6.1f}, "
          f"PL_med={pl_data[var].median():>6.1f}, "
          f"U={u:,.0f}, p={p:.2e}, r={r:.3f} {sig}")

# PR vs HR
print(f"\n  Mann-Whitney U: Popular Roots vs Hidden Roots (external vars):")
pr_data = df[df["role_mr"] == "PR"]
for var in ext_vars:
    u, p = stats.mannwhitneyu(pr_data[var], hr_data[var], alternative="two-sided")
    r = 1 - 2*u/(len(pr_data)*len(hr_data))
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"    {var:<18}: PR_med={pr_data[var].median():>6.1f}, "
          f"HR_med={hr_data[var].median():>6.1f}, "
          f"U={u:,.0f}, p={p:.2e}, r={r:.3f} {sig}")

# Save external comparison
ext_df = pd.DataFrame(ext_rows)
ext_df.to_csv(os.path.join(OUT_DIR, "rq3_external_variables.csv"), index=False)
test_df = pd.DataFrame(test_rows)
test_df.to_csv(os.path.join(OUT_DIR, "rq3_hr_vs_pl_external.csv"), index=False)

# ============================================================
# Experiment E: HR Matched Control Group
# ============================================================
print("\n" + "="*60)
print("EXPERIMENT E: HR Matched Control Group")
print("="*60)
print("For each HR, find download-matched non-HR model, compare structure")

# Match each HR to a non-HR model with similar downloads
hr_models = df[df["role_mr"] == "HR"].copy()
non_hr = df[df["role_mr"] != "HR"].copy()

# For efficiency, bin by downloads and match within bins
hr_models["dl_bin"] = pd.qcut(hr_models["downloads"].clip(lower=0), 20,
                               labels=False, duplicates="drop")
non_hr["dl_bin"] = pd.qcut(non_hr["downloads"].clip(lower=0), 20,
                            labels=False, duplicates="drop")

matched_hr = []
matched_ctrl = []
np.random.seed(42)

for dl_bin in hr_models["dl_bin"].unique():
    hr_bin = hr_models[hr_models["dl_bin"] == dl_bin]
    ctrl_pool = non_hr[non_hr["dl_bin"] == dl_bin]
    if len(ctrl_pool) == 0:
        continue
    # Sample with replacement if needed
    n_need = len(hr_bin)
    ctrl_sample = ctrl_pool.sample(n=min(n_need, len(ctrl_pool)),
                                    replace=len(ctrl_pool) < n_need,
                                    random_state=42)
    matched_hr.append(hr_bin.head(len(ctrl_sample)))
    matched_ctrl.append(ctrl_sample)

if matched_hr:
    hr_matched = pd.concat(matched_hr)
    ctrl_matched = pd.concat(matched_ctrl)
    print(f"  Matched pairs: {len(hr_matched):,} HR vs {len(ctrl_matched):,} controls")
    print(f"  HR downloads: median={hr_matched['downloads'].median():.0f}, "
          f"mean={hr_matched['downloads'].mean():.0f}")
    print(f"  Ctrl downloads: median={ctrl_matched['downloads'].median():.0f}, "
          f"mean={ctrl_matched['downloads'].mean():.0f}")

    print(f"\n  Matched comparison (HR vs download-matched controls):")
    match_rows = []
    for var in ext_vars:
        u, p = stats.mannwhitneyu(hr_matched[var], ctrl_matched[var],
                                   alternative="two-sided")
        r = 1 - 2*u/(len(hr_matched)*len(ctrl_matched))
        match_rows.append({
            "variable": var,
            "HR_median": hr_matched[var].median(),
            "ctrl_median": ctrl_matched[var].median(),
            "U": u, "p": p, "r": r
        })
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"    {var:<18}: HR={hr_matched[var].median():>6.1f}, "
              f"ctrl={ctrl_matched[var].median():>6.1f}, "
              f"r={r:.3f} {sig}")

    pd.DataFrame(match_rows).to_csv(
        os.path.join(OUT_DIR, "rq3_hr_matched_control.csv"), index=False)

elapsed = time.time() - t0
print(f"\n{'='*60}")
print(f"All experiments complete in {elapsed:.1f}s")
print(f"Output files in {OUT_DIR}/:")
for f in ["rq2_construct_pure_structure.csv", "rq2_construct_convergent.csv",
          "rq2_construct_discriminant.csv", "rq3_external_variables.csv",
          "rq3_hr_vs_pl_external.csv", "rq3_hr_matched_control.csv"]:
    print(f"  {f}")
print(f"{'='*60}")
