#!/usr/bin/env python3
"""
RQ2: Component Ablation and Parameter Sensitivity
===================================================
Runs ModelRank variants (ablation + sensitivity) and compares with default.

Ablation variants:
  1. No event value (lambda_E=0)
  2. No quality weighting (alpha=1)
  3. No size mitigation (kappa=0)
  4. No temporal inheritance (beta=0)
  5. No type weights (all types=1.0)

Sensitivity variants:
  alpha:    [0, 0.1, 0.3*, 0.5, 0.7, 1.0]
  kappa:    [0, 0.25, 0.5*, 0.75, 1.0]
  lambda_E: [0, 0.2, 0.4, 0.8*, 1.2, 1.6]
  beta:     [0, 0.05, 0.15*, 0.3, 0.5]
  d:        [0.7, 0.8, 0.85*, 0.9, 0.95]

Output:
  output_v2/rq2_ablation.csv
  output_v2/rq2_sensitivity.csv
"""
import os, sys, time, csv
import numpy as np
import pandas as pd
from scipy import sparse, stats
from collections import defaultdict

DATA_DIR = "data_new/monthly"
OUT_DIR = "output_v2"
LAST_MONTH = "2026-02"

# Default parameters
DEFAULTS = {
    "alpha": 0.3, "kappa": 0.5, "lambda_E": 0.8,
    "damping": 0.85, "lambda_q": 0.10, "beta": 0.15,
}
TYPE_WEIGHTS_DEFAULT = {"finetune": 1.0, "adapter": 0.8, "merge": 0.5, "quantized": 0.3}
DEFAULT_TYPE_WEIGHT = 0.5
PR_TOL = 1e-8
PR_MAX_ITER = 200

MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]

# ── Data loading (same as derivative_influence_v2.py) ──

def load_data():
    print("Loading data ...")
    models = {}
    with open(os.path.join(DATA_DIR, "deriv_models.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mid = row["id"]
            p = row.get("params")
            models[mid] = {
                "createdAt": row["createdAt"][:7],
                "params": float(p) if p and p != "" else None,
            }
    all_ids = sorted(models.keys())
    id_to_idx = {mid: i for i, mid in enumerate(all_ids)}
    idx_to_id = {i: mid for mid, i in id_to_idx.items()}
    n = len(all_ids)
    for mid in models:
        models[mid]["idx"] = id_to_idx[mid]

    edges = []
    with open(os.path.join(DATA_DIR, "deriv_edges.csv"), "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            edges.append((row["child_id"], row["parent_id"], row["relation"], row["child_created"][:7]))

    param_vals = [m["params"] for m in models.values() if m["params"] and m["params"] > 0]
    p10 = float(np.percentile(param_vals, 10)) if param_vals else 6.7e7

    # Pre-load all monthly metrics
    all_metrics = {}
    for ym in MONTHS:
        path = os.path.join(DATA_DIR, f"{ym}_metrics.csv")
        dl = np.zeros(n); lk = np.zeros(n)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row["id"] in id_to_idx:
                        idx = id_to_idx[row["id"]]
                        dl[idx] = float(row.get("downloads") or 0)
                        lk[idx] = float(row.get("likes") or 0)
        all_metrics[ym] = (dl, lk)

    print(f"  {n:,} models, {len(edges):,} edges")
    return models, edges, id_to_idx, idx_to_id, n, p10, all_metrics

def run_variant(models, edges, id_to_idx, idx_to_id, n, p10, all_metrics,
                alpha, kappa, lambda_E, damping, lambda_q, beta, type_weights):
    """Run full 20-month ModelRank with given parameters. Return last-month scores."""
    prev_y = None
    last_scores = None

    for ym in MONTHS:
        # V_t
        vt_mask = np.zeros(n, dtype=bool)
        for mid, meta in models.items():
            if meta["createdAt"] <= ym:
                vt_mask[meta["idx"]] = True
        n_vt = int(vt_mask.sum())
        if n_vt == 0:
            continue

        # E_t
        child_parent_rels = defaultdict(list)
        for cid, pid, rel, cc in edges:
            if cc != ym: continue
            if cid not in id_to_idx or pid not in id_to_idx: continue
            ci, pi = id_to_idx[cid], id_to_idx[pid]
            if vt_mask[ci] and vt_mask[pi]:
                child_parent_rels[ci].append((pi, rel))

        # Quality
        dl, lk = all_metrics.get(ym, (np.zeros(n), np.zeros(n)))
        q = 0.5 * np.log1p(dl) + 0.5 * np.log1p(lk)
        q[~vt_mask] = 0.0
        q_max = q.max() or 1.0

        # Transition matrix
        if child_parent_rels:
            ri, ci_arr, va = [], [], []
            for ci, parents in child_parent_rels.items():
                s = 1.0 / len(parents)
                for pi, _ in parents:
                    ri.append(ci); ci_arr.append(pi); va.append(s)
            P = sparse.csr_matrix((va, (ri, ci_arr)), shape=(n, n))
        else:
            P = sparse.csr_matrix((n, n))

        # Event value
        E_t = np.zeros(n)
        for ci, parents in child_parent_rels.items():
            s = 1.0 / len(parents)
            q_hat = q[ci] / q_max
            qf = alpha + (1.0 - alpha) * q_hat
            for pi, rel in parents:
                wt = type_weights.get(rel, DEFAULT_TYPE_WEIGHT)
                pv = models[idx_to_id[pi]].get("params") or p10
                if pv <= 0: pv = p10
                E_t[pi] += s * wt * qf * np.log1p(pv) ** kappa

        # Teleport
        tau = q.copy()
        tau += lambda_E * E_t
        tau[~vt_mask] = 0.0
        ts = tau.sum()
        if ts > 0: tau /= ts
        else: tau[vt_mask] = 1.0 / n_vt

        # PageRank
        out_deg = np.array(P.sum(axis=1)).flatten()
        dangling = (out_deg == 0) & vt_mask
        x = tau.copy()
        for _ in range(PR_MAX_ITER):
            xn = damping * (P.T @ x)
            xn += damping * x[dangling].sum() * tau
            xn += (1.0 - damping) * tau
            xn[~vt_mask] = 0.0
            s = xn.sum()
            if s > 0: xn /= s
            if np.abs(xn - x).sum() < PR_TOL: break
            x = xn

        # Fuse + inherit
        x_raw = (1.0 - lambda_q) * x + lambda_q * tau
        if prev_y is not None:
            y = (1.0 - beta) * x_raw + beta * prev_y
        else:
            y = x_raw.copy()
        prev_y = y.copy()

        if ym == LAST_MONTH:
            last_scores = y * n_vt

    return last_scores

def kendall_tau_topk(scores1, scores2, k=1000):
    """Kendall's tau on top-K models (by scores1)."""
    top_idx = np.argsort(-scores1)[:k]
    result = stats.kendalltau(scores1[top_idx], scores2[top_idx])
    return result.correlation if hasattr(result, 'correlation') else result[0]


if __name__ == "__main__":
    models, edges, id_to_idx, idx_to_id, n, p10, all_metrics = load_data()

    # Run default
    print("\n[Default] Running ...")
    t0 = time.time()
    default_scores = run_variant(models, edges, id_to_idx, idx_to_id, n, p10, all_metrics,
                                  **DEFAULTS, type_weights=TYPE_WEIGHTS_DEFAULT)
    print(f"  Done in {time.time()-t0:.0f}s")

    # ── Ablation ──
    print("\n=== Ablation ===")
    ablation_variants = [
        ("No event value", {**DEFAULTS, "lambda_E": 0}, TYPE_WEIGHTS_DEFAULT),
        ("No quality weighting", {**DEFAULTS, "alpha": 1.0}, TYPE_WEIGHTS_DEFAULT),
        ("No size mitigation", {**DEFAULTS, "kappa": 0}, TYPE_WEIGHTS_DEFAULT),
        ("No temporal inherit", {**DEFAULTS, "beta": 0}, TYPE_WEIGHTS_DEFAULT),
        ("No type weights", DEFAULTS, {k: 1.0 for k in TYPE_WEIGHTS_DEFAULT}),
    ]

    ablation_rows = [{"variant": "Full ModelRank", "change": "(reference)",
                      "tau_1k": 1.0, "tau_5k": 1.0, "rho_1k": 1.0}]

    for name, params, tw in ablation_variants:
        print(f"  [{name}] Running ...", end=" ", flush=True)
        t0 = time.time()
        variant_scores = run_variant(models, edges, id_to_idx, idx_to_id, n, p10,
                                      all_metrics, **params, type_weights=tw)
        elapsed = time.time() - t0

        tau_1k = kendall_tau_topk(default_scores, variant_scores, 1000)
        tau_5k = kendall_tau_topk(default_scores, variant_scores, 5000)
        top1k_idx = np.argsort(-default_scores)[:1000]
        rho_result = stats.spearmanr(default_scores[top1k_idx], variant_scores[top1k_idx])
        rho_1k = rho_result.correlation if hasattr(rho_result, 'correlation') else rho_result[0]

        print(f"tau@1k={tau_1k:.3f}, tau@5k={tau_5k:.3f}, rho@1k={rho_1k:.3f} ({elapsed:.0f}s)")
        ablation_rows.append({"variant": name, "change": "",
                              "tau_1k": round(tau_1k, 3), "tau_5k": round(tau_5k, 3),
                              "rho_1k": round(rho_1k, 3)})

    abl_df = pd.DataFrame(ablation_rows)
    abl_df.to_csv(os.path.join(OUT_DIR, "rq2_ablation.csv"), index=False)
    print(f"\n{abl_df.to_string(index=False)}")

    # ── Sensitivity ──
    print("\n=== Parameter Sensitivity ===")
    sensitivity_configs = {
        "alpha":    [0, 0.1, 0.3, 0.5, 0.7, 1.0],
        "kappa":    [0, 0.25, 0.5, 0.75, 1.0],
        "lambda_E": [0, 0.2, 0.4, 0.8, 1.2, 1.6],
        "beta":     [0, 0.05, 0.15, 0.3, 0.5],
        "damping":  [0.7, 0.8, 0.85, 0.9, 0.95],
    }

    sens_rows = []
    for param_name, values in sensitivity_configs.items():
        print(f"\n  Param: {param_name}")
        for val in values:
            params = {**DEFAULTS, param_name: val}
            is_default = (val == DEFAULTS[param_name])
            print(f"    {param_name}={val}" + (" (default)" if is_default else ""), end=" ... ", flush=True)
            t0 = time.time()
            variant_scores = run_variant(models, edges, id_to_idx, idx_to_id, n, p10,
                                          all_metrics, **params, type_weights=TYPE_WEIGHTS_DEFAULT)
            elapsed = time.time() - t0

            if is_default:
                tau_1k = 1.0
            else:
                tau_1k = kendall_tau_topk(default_scores, variant_scores, 1000)

            print(f"tau@1k={tau_1k:.3f} ({elapsed:.0f}s)")
            sens_rows.append({"param": param_name, "value": val,
                              "is_default": is_default, "tau_1k": round(tau_1k, 3)})

    sens_df = pd.DataFrame(sens_rows)
    sens_df.to_csv(os.path.join(OUT_DIR, "rq2_sensitivity.csv"), index=False)
    print(f"\n{sens_df.to_string(index=False)}")
    print(f"\nDone. Results saved to {OUT_DIR}/")
