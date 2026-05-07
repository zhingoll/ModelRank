#!/usr/bin/env python3
"""
RQ2 Pure-Structure ModelRank Pipeline
======================================
Runs the full ModelRank pipeline with q(v,t) = 1.0 for ALL models
(i.e., removes the popularity signal entirely).

Key change vs derivative_influence_v2.py:
  - quality_factor = 1.0 always (equivalent to alpha=1.0)
  - teleport base = uniform 1.0 for all V_t models (no downloads/likes)
  - Everything else identical: type weights, size mitigation, PageRank,
    temporal inheritance

Question answered: "Do Hidden Roots still exist without popularity?"
"""
import os, sys, time, logging
from collections import defaultdict
from typing import Optional, Tuple
import numpy as np
from scipy import sparse
import csv

# ── Parameters (same as derivative_influence_v2.py) ──
KAPPA = 0.5
LAMBDA_E = 0.8
DAMPING = 0.85
LAMBDA_Q = 0.10
BETA = 0.15
PR_TOL = 1e-8
PR_MAX_ITER = 200

TYPE_WEIGHTS = {"finetune": 1.0, "adapter": 0.8, "merge": 0.5, "quantized": 0.3}
DEFAULT_TYPE_WEIGHT = 0.5

DATA_DIR = "data_new/monthly"
OUT_DIR = "output_v2"

MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


# ── Data Loading ──

def load_static_data():
    """Load static model metadata and derivation edges."""
    log.info("Loading deriv_models.csv ...")
    models = {}
    with open(os.path.join(DATA_DIR, "deriv_models.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = row["id"]
            params = row.get("params")
            models[mid] = {
                "createdAt": row["createdAt"][:7],
                "params": float(params) if params and params != "" else None,
                "pipeline_tag": row.get("pipeline_tag", ""),
            }
    log.info(f"  Loaded {len(models):,} models")

    all_ids = sorted(models.keys())
    id_to_idx = {mid: i for i, mid in enumerate(all_ids)}
    idx_to_id = {i: mid for mid, i in id_to_idx.items()}
    n = len(all_ids)

    for mid in models:
        models[mid]["idx"] = id_to_idx[mid]

    log.info("Loading deriv_edges.csv ...")
    edges = []
    with open(os.path.join(DATA_DIR, "deriv_edges.csv"), "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            edges.append((row["child_id"], row["parent_id"],
                          row["relation"], row["child_created"][:7]))
    log.info(f"  Loaded {len(edges):,} edges")

    param_vals = [m["params"] for m in models.values()
                  if m["params"] is not None and m["params"] > 0]
    p10 = float(np.percentile(param_vals, 10)) if param_vals else 6.7e7
    log.info(f"  P10 param backfill: {p10:.2e}")

    return models, edges, id_to_idx, idx_to_id, n, p10


def pagerank(P: sparse.csr_matrix, tau: np.ndarray,
             vt_mask: np.ndarray) -> np.ndarray:
    """Power-iteration PageRank with teleport and dangling redirect."""
    n = P.shape[0]
    out_degree = np.array(P.sum(axis=1)).flatten()
    dangling = (out_degree == 0) & vt_mask

    x = tau.copy()
    for it in range(PR_MAX_ITER):
        x_new = DAMPING * (P.T @ x)
        dang_mass = x[dangling].sum()
        x_new += DAMPING * dang_mass * tau
        x_new += (1.0 - DAMPING) * tau
        x_new[~vt_mask] = 0.0
        s = x_new.sum()
        if s > 0:
            x_new /= s
        diff = np.abs(x_new - x).sum()
        x = x_new
        if diff < PR_TOL:
            log.info(f"    PR converged in {it+1} iters (diff={diff:.2e})")
            break
    else:
        log.info(f"    PR max iters ({PR_MAX_ITER}), diff={diff:.2e}")
    return x


def compute_month(ym, models, edges, id_to_idx, idx_to_id, n, p10, prev_y):
    """Compute pure-structure ModelRank for one month.

    Key difference: quality_factor = 1.0 always, teleport base = uniform.
    """
    log.info(f"  Building V_t and E_t ...")

    # V_t: models created on or before this month
    vt_mask = np.zeros(n, dtype=bool)
    for mid, meta in models.items():
        if meta["createdAt"] <= ym:
            vt_mask[meta["idx"]] = True
    n_vt = int(vt_mask.sum())
    if n_vt == 0:
        return None, []

    # E_t: edges where child created in this month
    child_parent_rels = defaultdict(list)
    for cid, pid, rel, cc_month in edges:
        if cc_month != ym:
            continue
        if cid not in id_to_idx or pid not in id_to_idx:
            continue
        ci = id_to_idx[cid]
        pi = id_to_idx[pid]
        if vt_mask[ci] and vt_mask[pi]:
            child_parent_rels[ci].append((pi, rel))

    n_et = sum(len(v) for v in child_parent_rels.values())
    log.info(f"  |V_t|={n_vt:,}, |E_t|={n_et:,}")

    # Stage 2: Transition matrix (uniform edge weights) — same as original
    if child_parent_rels:
        rows_idx, cols_idx, vals = [], [], []
        for ci, parents in child_parent_rels.items():
            share = 1.0 / len(parents)
            for pi, rel in parents:
                rows_idx.append(ci)
                cols_idx.append(pi)
                vals.append(share)
        P = sparse.csr_matrix((vals, (rows_idx, cols_idx)), shape=(n, n))
    else:
        P = sparse.csr_matrix((n, n))

    # Stage 3: Event value injection — PURE STRUCTURE variant
    # quality_factor = 1.0 always (no downloads/likes)
    E_t = np.zeros(n, dtype=np.float64)
    for ci, parents in child_parent_rels.items():
        share = 1.0 / len(parents)
        quality_factor = 1.0  # ← THE KEY CHANGE
        for pi, rel in parents:
            w_type = TYPE_WEIGHTS.get(rel, DEFAULT_TYPE_WEIGHT)
            p_val = models[idx_to_id[pi]].get("params")
            if p_val is None or p_val <= 0:
                p_val = p10
            E_t[pi] += share * w_type * quality_factor * np.log1p(p_val) ** KAPPA

    # Teleport: uniform base (1.0 for all V_t) + event value
    tau = np.zeros(n, dtype=np.float64)
    tau[vt_mask] = 1.0  # uniform base instead of q_base
    tau += LAMBDA_E * E_t
    tau[~vt_mask] = 0.0
    tau_sum = tau.sum()
    if tau_sum > 0:
        tau /= tau_sum
    else:
        tau[vt_mask] = 1.0 / n_vt

    # Stage 4: PageRank
    pr = pagerank(P, tau, vt_mask)

    # Stage 5: Fuse + inherit — same as original
    x_raw = (1.0 - LAMBDA_Q) * pr + LAMBDA_Q * tau
    if prev_y is not None:
        y = (1.0 - BETA) * x_raw + BETA * prev_y
    else:
        y = x_raw.copy()

    y_norm = y * n_vt

    # Build results
    scores_vt = [(idx, y[idx]) for idx in range(n) if vt_mask[idx]]
    scores_vt.sort(key=lambda x: x[1], reverse=True)
    rank_map = {idx: rank for rank, (idx, _) in enumerate(scores_vt, 1)}

    deriv_counts = defaultdict(int)
    for ci, parents in child_parent_rels.items():
        for pi, _ in parents:
            deriv_counts[pi] += 1

    results = []
    for idx in range(n):
        if vt_mask[idx] and y[idx] > 0:
            mid = idx_to_id[idx]
            results.append({
                "month": ym,
                "model_id": mid,
                "score": float(y[idx]),
                "score_normalized": float(y_norm[idx]),
                "rank": rank_map.get(idx, n_vt),
                "event_value": float(E_t[idx]),
                "n_derivatives": deriv_counts.get(idx, 0),
                "n_vt": n_vt,
            })
    return y, results


# ── Analysis ──

def analyze_results(ps_scores_path, orig_scores_path):
    """Compare pure-structure scores with original MR scores."""
    import pandas as pd
    from scipy import stats

    print("\n" + "=" * 70)
    print("ANALYSIS: Pure-Structure ModelRank vs Original ModelRank")
    print("=" * 70)

    ps = pd.read_csv(ps_scores_path)
    orig = pd.read_csv(orig_scores_path)

    LAST = "2026-02"
    ps_last = ps[ps["month"] == LAST].copy()
    orig_last = orig[orig["month"] == LAST].copy()

    print(f"\nLast month ({LAST}):")
    print(f"  Pure-structure models: {len(ps_last):,}")
    print(f"  Original MR models:   {len(orig_last):,}")

    # Merge on model_id
    merged = ps_last.merge(orig_last, on="model_id", suffixes=("_ps", "_orig"))
    print(f"  Merged (common):      {len(merged):,}")

    # ── Role assignment ──
    # Use P90 on ORIGINAL downloads for the popularity axis
    # Use P90 on each score for the influence axis
    dl_p90 = merged["downloads"].quantile(0.9)
    mr_p90 = merged["score_normalized_orig"].quantile(0.9)
    ps_p90 = merged["score_normalized_ps"].quantile(0.9)

    print(f"\n  Thresholds:")
    print(f"    Downloads P90:       {dl_p90:,.0f}")
    print(f"    Original MR P90:     {mr_p90:.4f}")
    print(f"    Pure-struct MR P90:  {ps_p90:.4f}")

    def assign_role(dl, metric, thresh):
        hi_dl = dl >= dl_p90
        hi_m = metric >= thresh
        if hi_dl and hi_m:
            return "PR"
        if hi_dl and not hi_m:
            return "PL"
        if not hi_dl and hi_m:
            return "HR"
        return "LT"

    merged["role_orig"] = merged.apply(
        lambda r: assign_role(r["downloads"], r["score_normalized_orig"], mr_p90), axis=1)
    merged["role_ps"] = merged.apply(
        lambda r: assign_role(r["downloads"], r["score_normalized_ps"], ps_p90), axis=1)

    # ── Role distribution ──
    print(f"\n  Role distribution:")
    print(f"  {'Role':<6} {'Original MR':>14} {'Pure-Struct MR':>16}")
    print(f"  {'-'*38}")
    total = len(merged)
    for role in ["PR", "PL", "HR", "LT"]:
        c_orig = (merged["role_orig"] == role).sum()
        c_ps = (merged["role_ps"] == role).sum()
        print(f"  {role:<6} {c_orig:>8,} ({c_orig/total*100:4.1f}%) "
              f"{c_ps:>8,} ({c_ps/total*100:4.1f}%)")

    # ── Hidden Roots overlap ──
    hr_orig = set(merged[merged["role_orig"] == "HR"]["model_id"])
    hr_ps = set(merged[merged["role_ps"] == "HR"]["model_id"])
    union = hr_orig | hr_ps
    inter = hr_orig & hr_ps
    jaccard = len(inter) / len(union) if union else 0.0

    print(f"\n  Hidden Roots analysis:")
    print(f"    HR in Original MR:     {len(hr_orig):,}")
    print(f"    HR in Pure-Struct MR:  {len(hr_ps):,}")
    print(f"    Intersection:          {len(inter):,}")
    print(f"    Union:                 {len(union):,}")
    print(f"    Jaccard overlap:       {jaccard:.4f}")
    if hr_orig:
        recall = len(inter) / len(hr_orig)
        print(f"    Recall (orig HR in PS): {recall:.4f}")
    if hr_ps:
        precision = len(inter) / len(hr_ps)
        print(f"    Precision (PS HR in orig): {precision:.4f}")

    # ── Correlation ──
    rho_scores, p_scores = stats.spearmanr(
        merged["score_normalized_orig"], merged["score_normalized_ps"])
    rho_ranks, p_ranks = stats.spearmanr(
        merged["rank_orig"], merged["rank_ps"])

    print(f"\n  Spearman correlations:")
    print(f"    Scores (orig vs PS):  rho={rho_scores:.4f}, p={p_scores:.2e}")
    print(f"    Ranks  (orig vs PS):  rho={rho_ranks:.4f}, p={p_ranks:.2e}")

    # Downloads vs pure-structure score
    rho_dl_ps, _ = stats.spearmanr(merged["downloads"], merged["score_normalized_ps"])
    rho_dl_orig, _ = stats.spearmanr(merged["downloads"], merged["score_normalized_orig"])
    print(f"    Downloads vs PS score:   rho={rho_dl_ps:.4f}")
    print(f"    Downloads vs Orig score: rho={rho_dl_orig:.4f}")

    # ── Cross-tabulation ──
    print(f"\n  Role transition matrix (Original → Pure-Structure):")
    header_label = "Orig \\ PS"
    print(f"  {header_label:<8} {'PR':>8} {'PL':>8} {'HR':>8} {'LT':>8} {'Total':>8}")
    print(f"  {'-'*48}")
    for r_orig in ["PR", "PL", "HR", "LT"]:
        sub = merged[merged["role_orig"] == r_orig]
        counts = sub["role_ps"].value_counts()
        row_total = len(sub)
        print(f"  {r_orig:<8}", end="")
        for r_ps in ["PR", "PL", "HR", "LT"]:
            c = counts.get(r_ps, 0)
            print(f" {c:>8,}", end="")
        print(f" {row_total:>8,}")

    # ── Top-20 Hidden Roots in pure-structure ──
    ps_hr = merged[merged["role_ps"] == "HR"].sort_values(
        "score_normalized_ps", ascending=False)
    print(f"\n  Top-20 Hidden Roots (pure-structure):")
    print(f"  {'Rank':>5} {'Model':<50} {'PS Score':>10} {'DL':>10} {'Orig Role':>10}")
    for i, (_, row) in enumerate(ps_hr.head(20).iterrows()):
        mid = row["model_id"]
        if len(mid) > 48:
            mid = mid[:45] + "..."
        print(f"  {i+1:>5} {mid:<50} {row['score_normalized_ps']:>10.2f} "
              f"{row['downloads']:>10.0f} {row['role_orig']:>10}")

    # ── Answer the research question ──
    print(f"\n{'=' * 70}")
    print("CONCLUSION")
    print(f"{'=' * 70}")
    hr_exist = len(hr_ps) > 0
    hr_pct = len(hr_ps) / total * 100 if total > 0 else 0
    print(f"  Hidden Roots in pure-structure MR: {len(hr_ps):,} ({hr_pct:.1f}%)")
    if hr_exist:
        print(f"  YES — Hidden Roots persist even without popularity signals.")
        print(f"  Jaccard overlap with original HR: {jaccard:.4f}")
        print(f"  This confirms HR is a structural phenomenon, not a popularity artifact.")
    else:
        print(f"  NO — Hidden Roots disappear without popularity signals.")
        print(f"  This would suggest HR depends on the popularity component.")

    return merged


# ── Main ──

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t_start = time.time()

    models, edges, id_to_idx, idx_to_id, n, p10 = load_static_data()
    log.info(f"Network: {n:,} models, {len(edges):,} edges\n")

    out_path = os.path.join(OUT_DIR, "rq2_pure_structure_scores.csv")
    # Remove old output if exists
    if os.path.exists(out_path):
        os.remove(out_path)

    header_written = False
    total_rows = 0
    prev_y = None

    for i, ym in enumerate(MONTHS):
        log.info(f"[{i+1:2d}/20] Month {ym}")
        t0 = time.time()

        y, results = compute_month(ym, models, edges, id_to_idx, idx_to_id,
                                   n, p10, prev_y)
        if y is not None:
            prev_y = y.copy()

        if results:
            with open(out_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                if not header_written:
                    writer.writeheader()
                    header_written = True
                writer.writerows(results)
            total_rows += len(results)

        elapsed = time.time() - t0
        log.info(f"  {len(results):,} scored models, {elapsed:.1f}s\n")

    total_time = time.time() - t_start
    log.info(f"Pipeline done. {total_rows:,} total rows in {total_time:.0f}s")
    log.info(f"Output: {out_path}")

    # ── Run analysis ──
    orig_path = os.path.join(OUT_DIR, "modelrank_scores.csv")
    if os.path.exists(orig_path):
        analyze_results(out_path, orig_path)
    else:
        log.warning(f"Original scores not found at {orig_path}, skipping analysis.")

    print(f"\nTotal wall time: {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
