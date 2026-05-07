"""Compute baseline stability summaries used in the appendix."""
import os
from pathlib import Path
import pandas as pd, numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SCORES = ROOT / "results" / "shared" / "modelrank_scores.csv"
OUT = ROOT / "results" / "rq2"
DATA = Path(os.environ.get("MODELRANK_DATA_DIR", ROOT / "data" / "processed"))
MONTHS = ["2024-07","2024-08","2024-09","2024-10","2024-11","2024-12",
          "2025-01","2025-02","2025-03","2025-04","2025-05","2025-06",
          "2025-07","2025-08","2025-09","2025-10","2025-11","2025-12",
          "2026-01","2026-02"]
LAST = "2026-02"

scores = pd.read_csv(SCORES)
edges = pd.read_csv(DATA / "deriv_edges.csv")
edges["child_month"] = edges["child_created"].str[:7]

df = scores[scores["month"] == LAST].copy()
last_e = edges[edges["child_month"] == LAST]
dc_map = last_e.groupby("parent_id").size().to_dict()
df["deriv_count"] = df["model_id"].map(dc_map).fillna(0)
df["simplified_mr"] = df["q_base"] + 0.8 * df["event_value"]

print("=== MI1: Baseline Comparison (last month) ===")
n_dang = (df["deriv_count"] == 0).sum()
print(f"Dangling ratio: {n_dang}/{len(df)} = {n_dang/len(df)*100:.1f}%")

# Correlations
for name, col in [("Simplified-MR", "simplified_mr"), ("DerivCount", "deriv_count")]:
    rho, _ = stats.spearmanr(df["score_normalized"], df[col])
    print(f"MR vs {name}: rho={rho:.4f}")

# Top-K Jaccard
print("\nTop-K Jaccard (MR vs baseline):")
print(f"{'K':>6} {'vs SMR':>8} {'vs DC':>8}")
for K in [10, 50, 100, 500]:
    mr_top = set(df.nlargest(K, "score_normalized")["model_id"])
    smr_top = set(df.nlargest(K, "simplified_mr")["model_id"])
    dc_top = set(df.nlargest(K, "deriv_count")["model_id"])
    j_smr = len(mr_top & smr_top) / len(mr_top | smr_top)
    j_dc = len(mr_top & dc_top) / len(mr_top | dc_top)
    print(f"{K:>6} {j_smr:>8.3f} {j_dc:>8.3f}")

print("\n=== MI2: Month-to-Month Stability (Top-100 Jaccard) ===")
stab = {"MR": [], "DC": [], "SMR": []}
for i in range(1, len(MONTHS)):
    prev_s = scores[scores["month"] == MONTHS[i-1]]
    curr_s = scores[scores["month"] == MONTHS[i]]
    prev_e = edges[edges["child_month"] == MONTHS[i-1]]
    curr_e = edges[edges["child_month"] == MONTHS[i]]

    K = 100
    # MR
    mr_p = set(prev_s.nlargest(K, "score_normalized")["model_id"])
    mr_c = set(curr_s.nlargest(K, "score_normalized")["model_id"])
    j_mr = len(mr_p & mr_c) / len(mr_p | mr_c) if (mr_p | mr_c) else 0

    # DC
    prev_dc = prev_e.groupby("parent_id").size()
    curr_dc = curr_e.groupby("parent_id").size()
    dc_p = set(prev_dc.nlargest(K).index) if len(prev_dc) >= K else set(prev_dc.index)
    dc_c = set(curr_dc.nlargest(K).index) if len(curr_dc) >= K else set(curr_dc.index)
    j_dc = len(dc_p & dc_c) / len(dc_p | dc_c) if (dc_p | dc_c) else 0

    # SMR
    prev_s2 = prev_s.copy()
    prev_s2["smr"] = prev_s2["q_base"] + 0.8 * prev_s2["event_value"]
    curr_s2 = curr_s.copy()
    curr_s2["smr"] = curr_s2["q_base"] + 0.8 * curr_s2["event_value"]
    smr_p = set(prev_s2.nlargest(K, "smr")["model_id"])
    smr_c = set(curr_s2.nlargest(K, "smr")["model_id"])
    j_smr = len(smr_p & smr_c) / len(smr_p | smr_c) if (smr_p | smr_c) else 0

    stab["MR"].append(j_mr)
    stab["DC"].append(j_dc)
    stab["SMR"].append(j_smr)

print(f"Average Top-100 Jaccard stability:")
for m in ["MR", "DC", "SMR"]:
    print(f"  {m:>3}: {np.mean(stab[m]):.3f}")
print(f"  MR/DC ratio: {np.mean(stab['MR'])/np.mean(stab['DC']):.2f}x")
print(f"  MR/SMR ratio: {np.mean(stab['MR'])/np.mean(stab['SMR']):.2f}x")

# Save for paper
pd.DataFrame({
    "month_pair": [f"{MONTHS[i]}->{MONTHS[i+1]}" for i in range(len(MONTHS)-1)],
    "MR_top100": stab["MR"],
    "DC_top100": stab["DC"],
    "SMR_top100": stab["SMR"],
}).to_csv(OUT / "rq2_baseline_stability.csv", index=False)

print("\nDone.")
