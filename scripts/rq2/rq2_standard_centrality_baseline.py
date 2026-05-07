#!/usr/bin/env python3
"""
RQ2 standard centrality sanity baseline.

Compute a vanilla PageRank score on monthly event graphs with:
  - child -> parent edges
  - uniform teleport within V_t
  - no event value
  - no temporal inheritance

Output:
  - output_v3/rq2_standard_centrality_baseline.csv
"""
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from scipy import sparse, stats

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v3")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
LAST = "2026-02"
MONTHS = [
    "2024-07", "2024-08", "2024-09", "2024-10", "2024-11", "2024-12",
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]
DAMPING = 0.85
PR_TOL = 1e-8
PR_MAX_ITER = 200
EXT_VARS = ["desc_count", "desc_depth", "desc_breadth", "active_months", "type_diversity"]


def pagerank(P: sparse.csr_matrix, tau: np.ndarray, vt_mask: np.ndarray) -> np.ndarray:
    out_degree = np.array(P.sum(axis=1)).flatten()
    dangling = (out_degree == 0) & vt_mask
    x = tau.copy()
    for _ in range(PR_MAX_ITER):
        x_new = DAMPING * (P.T @ x)
        x_new += DAMPING * x[dangling].sum() * tau
        x_new += (1.0 - DAMPING) * tau
        x_new[~vt_mask] = 0.0
        s = x_new.sum()
        if s > 0:
            x_new /= s
        if np.abs(x_new - x).sum() < PR_TOL:
            return x_new
        x = x_new
    return x


def assign_roles(df: pd.DataFrame, score_col: str) -> pd.DataFrame:
    df = df.copy()
    dl_p90 = df["downloads"].quantile(0.90)
    sc_p90 = df[score_col].quantile(0.90)
    high_dl = df["downloads"] >= dl_p90
    if sc_p90 == 0:
        high_sc = df[score_col] > 0
    else:
        high_sc = df[score_col] >= sc_p90
    df["role"] = np.where(
        high_dl & high_sc, "PR",
        np.where(high_dl & ~high_sc, "PL", np.where(~high_dl & high_sc, "HR", "LT"))
    )
    return df


def build_structural_vars(df_last: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    direct_children = defaultdict(set)
    child_types = defaultdict(set)
    child_months = defaultdict(set)
    children_of = defaultdict(list)
    for row in edges.itertuples(index=False):
        direct_children[row.parent_id].add(row.child_id)
        children_of[row.parent_id].append(row.child_id)
        if isinstance(row.relation, str) and row.relation:
            child_types[row.parent_id].add(row.relation)
        cm = row.child_created[:7]
        if cm:
            child_months[row.parent_id].add(cm)

    desc_count = {}
    desc_depth = {}
    for i, parent in enumerate(children_of.keys(), start=1):
        seen = set()
        q = deque([(parent, 0)])
        max_depth = 0
        while q:
            node, depth = q.popleft()
            for child in children_of.get(node, []):
                if child not in seen:
                    seen.add(child)
                    nd = depth + 1
                    if nd > max_depth:
                        max_depth = nd
                    q.append((child, nd))
        desc_count[parent] = len(seen)
        desc_depth[parent] = max_depth
        if i % 10000 == 0:
            print(f"struct vars processed {i:,}/{len(children_of):,}")

    out = df_last.copy()
    out["desc_count"] = out["model_id"].map(desc_count).fillna(0).astype(int)
    out["desc_depth"] = out["model_id"].map(desc_depth).fillna(0).astype(int)
    out["desc_breadth"] = out["model_id"].map(lambda m: len(direct_children.get(m, set()))).astype(int)
    out["active_months"] = out["model_id"].map(lambda m: len(child_months.get(m, set()))).astype(int)
    out["type_diversity"] = out["model_id"].map(lambda m: len(child_types.get(m, set()))).astype(int)
    return out


def matched_control_eval(df_last: pd.DataFrame, score_col: str) -> tuple[dict, list[dict]]:
    role_df = assign_roles(df_last, score_col)
    hr_models = role_df[role_df["role"] == "HR"].copy()
    non_hr = role_df[role_df["role"] != "HR"].copy()
    hr_models["dl_bin"] = pd.qcut(hr_models["downloads"].clip(lower=0), 20, labels=False, duplicates="drop")
    non_hr["dl_bin"] = pd.qcut(non_hr["downloads"].clip(lower=0), 20, labels=False, duplicates="drop")

    matched_hr = []
    matched_ctrl = []
    for dl_bin in hr_models["dl_bin"].dropna().unique():
        hr_bin = hr_models[hr_models["dl_bin"] == dl_bin]
        ctrl_pool = non_hr[non_hr["dl_bin"] == dl_bin]
        if len(ctrl_pool) == 0:
            continue
        n_need = len(hr_bin)
        ctrl_sample = ctrl_pool.sample(
            n=min(n_need, len(ctrl_pool)),
            replace=len(ctrl_pool) < n_need,
            random_state=42,
        )
        matched_hr.append(hr_bin.head(len(ctrl_sample)))
        matched_ctrl.append(ctrl_sample)
    if not matched_hr:
        return {}, []

    hr_matched = pd.concat(matched_hr)
    ctrl_matched = pd.concat(matched_ctrl)
    details = []
    effect_vals = []
    for var in EXT_VARS:
        u_stat, p_val = stats.mannwhitneyu(
            hr_matched[var], ctrl_matched[var], alternative="two-sided"
        )
        eff = abs(1 - 2 * u_stat / (len(hr_matched) * len(ctrl_matched)))
        details.append({"variable": var, "abs_effect_r": eff, "p_value": float(p_val)})
        effect_vals.append(eff)
    summary = {
        "method": "Vanilla-PR",
        "hr_count_last_month": int((role_df["role"] == "HR").sum()),
        "matched_pairs": int(len(hr_matched)),
        "matched_mean_abs_r": float(np.mean(effect_vals)),
        "matched_min_abs_r": float(np.min(effect_vals)),
        "matched_max_abs_r": float(np.max(effect_vals)),
    }
    return summary, details


def persistence_eval(monthly_scores: pd.DataFrame, edges: pd.DataFrame) -> dict:
    edges = edges.copy()
    edges["child_month"] = edges["child_created"].str[:7]
    active_parents = defaultdict(set)
    for cm, pid in zip(edges["child_month"], edges["parent_id"]):
        if pd.notna(cm):
            active_parents[cm].add(pid)

    hr_sets = {}
    lt_sets = {}
    pr_sets = {}
    dl_by_month = {}
    for ym in MONTHS:
        ms = monthly_scores[monthly_scores["month"] == ym].copy()
        ms = assign_roles(ms, "score_normalized")
        hr_sets[ym] = set(ms.loc[ms["role"] == "HR", "model_id"])
        lt_sets[ym] = set(ms.loc[ms["role"] == "LT", "model_id"])
        pr_sets[ym] = set(ms.loc[ms["role"] == "PR", "model_id"])
        dl_by_month[ym] = dict(zip(ms["model_id"], ms["downloads"]))

    rows = []
    for i in range(len(MONTHS) - 3):
        ym = MONTHS[i]
        future = MONTHS[i + 1:i + 4]
        hr_ids = hr_sets[ym]
        lt_ids = lt_sets[ym]
        if len(hr_ids) < 10 or len(lt_ids) < 10:
            continue
        hr_dls = [dl_by_month[ym].get(m, 0) for m in hr_ids]
        q10, q90 = np.percentile(hr_dls, [10, 90])
        lt_similar = [m for m in lt_ids if q10 <= dl_by_month[ym].get(m, 0) <= q90]
        if len(lt_similar) < 100:
            lt_similar = list(lt_ids)
        if not lt_similar:
            continue
        rng = np.random.RandomState(42 + i)
        n_sample = min(len(hr_ids), len(lt_similar))
        ctrl_ids = set(rng.choice(lt_similar, size=n_sample, replace=False))
        hr_active = sum(1 for m in hr_ids if any(m in active_parents.get(fm, set()) for fm in future))
        ctrl_active = sum(1 for m in ctrl_ids if any(m in active_parents.get(fm, set()) for fm in future))
        hr_pr = sum(1 for m in hr_ids if any(m in pr_sets.get(fm, set()) for fm in future))
        ctrl_pr = sum(1 for m in ctrl_ids if any(m in pr_sets.get(fm, set()) for fm in future))
        rows.append({
            "hr_active_rate": hr_active / len(hr_ids),
            "ctrl_active_rate": ctrl_active / len(ctrl_ids),
            "hr_to_pr_rate": hr_pr / len(hr_ids),
            "ctrl_to_pr_rate": ctrl_pr / len(ctrl_ids),
            "hr_active_count": hr_active,
            "hr_to_pr_count": hr_pr,
        })
    rdf = pd.DataFrame(rows)
    if rdf.empty:
        return {
            "mean_hr_active_rate": np.nan,
            "mean_ctrl_active_rate": np.nan,
            "active_ratio": np.nan,
            "mean_hr_active_count": np.nan,
            "mean_hr_to_pr_rate": np.nan,
            "mean_ctrl_to_pr_rate": np.nan,
            "transition_ratio": np.nan,
            "mean_hr_to_pr_count": np.nan,
        }
    return {
        "mean_hr_active_rate": float(rdf["hr_active_rate"].mean()),
        "mean_ctrl_active_rate": float(rdf["ctrl_active_rate"].mean()),
        "active_ratio": float(rdf["hr_active_rate"].mean() / rdf["ctrl_active_rate"].mean()),
        "mean_hr_active_count": float(rdf["hr_active_count"].mean()),
        "mean_hr_to_pr_rate": float(rdf["hr_to_pr_rate"].mean()),
        "mean_ctrl_to_pr_rate": float(rdf["ctrl_to_pr_rate"].mean()),
        "transition_ratio": float(rdf["hr_to_pr_rate"].mean() / rdf["ctrl_to_pr_rate"].mean()),
        "mean_hr_to_pr_count": float(rdf["hr_to_pr_count"].mean()),
    }


def top100_stability(monthly_scores: pd.DataFrame) -> float:
    overlaps = []
    for i in range(1, len(MONTHS)):
        prev_df = monthly_scores[monthly_scores["month"] == MONTHS[i - 1]]
        curr_df = monthly_scores[monthly_scores["month"] == MONTHS[i]]
        prev_top = set(prev_df.nlargest(100, "score_normalized")["model_id"])
        curr_top = set(curr_df.nlargest(100, "score_normalized")["model_id"])
        denom = len(prev_top | curr_top)
        overlaps.append(len(prev_top & curr_top) / denom if denom else 0.0)
    return float(np.mean(overlaps))


def build_monthly_scores() -> pd.DataFrame:
    scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"), usecols=["month", "model_id", "downloads"])
    models = pd.read_csv(os.path.join(DATA_DIR, "deriv_models.csv"), usecols=["id", "createdAt"])
    models["created_month"] = models["createdAt"].str[:7]
    all_ids = sorted(models["id"].tolist())
    id_to_idx = {mid: i for i, mid in enumerate(all_ids)}
    idx_to_id = {i: mid for mid, i in id_to_idx.items()}
    created_month = dict(zip(models["id"], models["created_month"]))
    n = len(all_ids)

    edges = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"), usecols=["child_id", "parent_id", "child_created"])
    edges["child_month"] = edges["child_created"].str[:7]

    rows = []
    for ym in MONTHS:
        vt_mask = np.zeros(n, dtype=bool)
        for mid, cm in created_month.items():
            if cm <= ym:
                vt_mask[id_to_idx[mid]] = True
        n_vt = int(vt_mask.sum())
        month_edges = edges[edges["child_month"] == ym]
        child_parent_rels = defaultdict(list)
        for row in month_edges.itertuples(index=False):
            if row.child_id not in id_to_idx or row.parent_id not in id_to_idx:
                continue
            ci = id_to_idx[row.child_id]
            pi = id_to_idx[row.parent_id]
            if vt_mask[ci] and vt_mask[pi]:
                child_parent_rels[ci].append(pi)
        if child_parent_rels:
            ri, ci_arr, va = [], [], []
            for ci, parents in child_parent_rels.items():
                share = 1.0 / len(parents)
                for pi in parents:
                    ri.append(ci)
                    ci_arr.append(pi)
                    va.append(share)
            P = sparse.csr_matrix((va, (ri, ci_arr)), shape=(n, n))
        else:
            P = sparse.csr_matrix((n, n))
        tau = np.zeros(n, dtype=np.float64)
        tau[vt_mask] = 1.0 / n_vt
        pr = pagerank(P, tau, vt_mask)
        pr_norm = pr * n_vt
        month_downloads = scores[scores["month"] == ym][["model_id", "downloads"]]
        dl_map = dict(zip(month_downloads["model_id"], month_downloads["downloads"]))
        for idx in np.where(vt_mask)[0]:
            mid = idx_to_id[idx]
            rows.append({
                "month": ym,
                "model_id": mid,
                "score_normalized": float(pr_norm[idx]),
                "downloads": float(dl_map.get(mid, 0.0)),
            })
    return pd.DataFrame(rows)


def main() -> None:
    print("building monthly Vanilla-PR scores ...")
    monthly_scores = build_monthly_scores()
    print(f"monthly score rows: {len(monthly_scores):,}")

    edges_full = pd.read_csv(os.path.join(DATA_DIR, "deriv_edges.csv"))
    last_df = monthly_scores[monthly_scores["month"] == LAST].copy()
    last_df = build_structural_vars(last_df, edges_full)

    summary, _details = matched_control_eval(last_df, "score_normalized")
    persist = persistence_eval(monthly_scores, edges_full)
    summary.update(persist)
    summary["mean_top100_overlap"] = top100_stability(monthly_scores)

    out = pd.DataFrame([summary])
    out.to_csv(os.path.join(OUT_DIR, "rq2_standard_centrality_baseline.csv"), index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
