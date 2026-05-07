#!/usr/bin/env python3
"""
RQ4: Temporal Dynamics of Ecosystem Roles (optimized)
"""
import os
import pandas as pd
import numpy as np
from collections import Counter

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v2")
MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]

print("Loading scores ...")
scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"),
                     usecols=["month", "model_id", "score_normalized", "downloads", "rank", "n_derivatives"])
month_vals = scores["month"].to_numpy()
download_vals = scores["downloads"].to_numpy()
mr_vals_all = scores["score_normalized"].to_numpy()

# Assign roles per month using P90
print("Assigning roles ...")
role_col = np.full(len(scores), "LT", dtype=object)
for ym in MONTHS:
    mask = month_vals == ym
    idx = np.flatnonzero(mask)
    if len(idx) == 0:
        continue
    dl_vals = download_vals[idx]
    mr_vals = mr_vals_all[idx]
    dl_t = np.percentile(dl_vals, 90)
    mr_t = np.percentile(mr_vals, 90)
    high_dl = dl_vals >= dl_t
    high_mr = mr_vals >= mr_t
    role_col[idx[high_dl & high_mr]] = "PR"
    role_col[idx[high_dl & ~high_mr]] = "PL"
    role_col[idx[~high_dl & high_mr]] = "HR"

scores["role"] = role_col
print(f"  Done: {len(scores):,} rows")

# ── 1. Role stability ──
print("\n=== 1. Role Stability ===")
# Pivot: model_id x month -> role
pivot = scores.pivot_table(index="model_id", columns="month", values="role", aggfunc="first")
# Count months present
n_months = pivot.notna().sum(axis=1)
# Filter to models present >= 10 months
stable_ids = n_months[n_months >= 10].index
print(f"Models present >= 10 months: {len(stable_ids):,}")

stab_rows = []
for mid in stable_ids:
    roles = pivot.loc[mid].dropna().values
    role_counts = Counter(roles)
    dominant = role_counts.most_common(1)[0]
    stab_rows.append({
        "model_id": mid,
        "n_months": len(roles),
        "dominant_role": dominant[0],
        "consistency": round(dominant[1] / len(roles), 3),
    })

stab_df = pd.DataFrame(stab_rows)
print(f"\nConsistency by dominant role:")
for role in ["PR", "PL", "HR", "LT"]:
    sub = stab_df[stab_df["dominant_role"] == role]
    if len(sub) > 0:
        print(f"  {role}: mean={sub['consistency'].mean():.3f}, n={len(sub):,}")

stab_df.to_csv(os.path.join(OUT_DIR, "rq4_role_stability.csv"), index=False)

# ── 2. Role transitions ──
print("\n=== 2. Role Transitions ===")
trans_counts = Counter()
for mid in stable_ids:
    roles = pivot.loc[mid].dropna().values
    for i in range(1, len(roles)):
        if roles[i] != roles[i-1]:
            trans_counts[(roles[i-1], roles[i])] += 1

print("Top 15 transitions:")
trans_rows = []
for (fr, to), cnt in trans_counts.most_common(15):
    print(f"  {fr} -> {to}: {cnt:,}")
    trans_rows.append({"from": fr, "to": to, "count": cnt})
pd.DataFrame(trans_rows).to_csv(os.path.join(OUT_DIR, "rq4_transitions.csv"), index=False)

# ── 3. Trajectories ──
print("\n=== 3. Trajectories ===")
interesting = [
    "Qwen/Qwen2.5-7B-Instruct",
    "lerobot/smolvla_base",
    "meta-llama/Llama-3.1-8B-Instruct",
    "black-forest-labs/FLUX.1-dev",
]
traj_rows = []
for mid in interesting:
    mr = scores[scores["model_id"] == mid].sort_values("month")
    if len(mr) == 0:
        continue
    print(f"\n  {mid}:")
    for _, r in mr.iterrows():
        traj_rows.append({
            "model_id": mid, "month": r["month"],
            "rank": int(r["rank"]), "score": round(r["score_normalized"], 2),
            "downloads": int(r["downloads"]), "derivs": int(r["n_derivatives"]),
            "role": r["role"],
        })
        print(f"    {r['month']}: rank={int(r['rank']):>6} dl={int(r['downloads']):>10,} "
              f"derivs={int(r['n_derivatives']):>4} role={r['role']}")

pd.DataFrame(traj_rows).to_csv(os.path.join(OUT_DIR, "rq4_trajectories.csv"), index=False)
print("\nDone.")
