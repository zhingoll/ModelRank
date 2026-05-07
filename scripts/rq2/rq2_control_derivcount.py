#!/usr/bin/env python3
"""
RQ2 controlled comparisons using all-time raw derivative counts.

Outputs:
  - output_v3/rq2_control_derivcount.csv
  - output_v3/rq2_control_downloads_derivcount.csv
"""
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from scipy import stats

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v3")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
LAST = "2026-02"

DOWNLOAD_BANDS = [
    ("1-2", 1, 2),
    ("3", 3, 3),
    ("4", 4, 4),
    ("5-7", 5, 7),
    ("8-16", 8, 16),
    ("17-43", 17, 43),
    ("44-140", 44, 140),
    ("141+", 141, float("inf")),
]

DERIV_BANDS = [
    ("1", 1, 1),
    ("2", 2, 2),
    ("3-4", 3, 4),
    ("5-8", 5, 8),
    ("9+", 9, float("inf")),
]

OUTCOME_VARS = ["desc_count", "desc_depth", "active_months", "type_diversity"]


def effect_r_from_u(u_stat: float, n_hi: int, n_lo: int) -> float:
    return abs(1 - 2 * u_stat / (n_hi * n_lo))


def compare_hi_lo(sub: pd.DataFrame) -> dict | None:
    if len(sub) < 100:
        return None
    median_score = sub["score_normalized"].median()
    hi = sub[sub["score_normalized"] >= median_score].copy()
    lo = sub[sub["score_normalized"] < median_score].copy()
    if len(hi) < 30 or len(lo) < 30:
        return None

    row = {
        "n": int(len(sub)),
        "n_hi": int(len(hi)),
        "n_lo": int(len(lo)),
        "median_score": float(median_score),
    }
    favorable = 0
    for var in OUTCOME_VARS:
        u_stat, p_val = stats.mannwhitneyu(
            hi[var].values, lo[var].values, alternative="greater"
        )
        eff = effect_r_from_u(u_stat, len(hi), len(lo))
        if hi[var].mean() > lo[var].mean():
            favorable += 1
        row[f"mr_hi_{var}_mean"] = float(hi[var].mean())
        row[f"mr_lo_{var}_mean"] = float(lo[var].mean())
        row[f"mr_hi_{var}_median"] = float(hi[var].median())
        row[f"mr_lo_{var}_median"] = float(lo[var].median())
        row[f"{var}_u_stat"] = float(u_stat)
        row[f"{var}_p_value"] = float(p_val)
        row[f"{var}_effect_r"] = float(eff)
    row["favorable_metrics"] = favorable
    return row


def load_last_month() -> pd.DataFrame:
    scores = pd.read_csv(os.path.join(OUT_DIR, "modelrank_scores.csv"))
    df = scores[scores["month"] == LAST].copy()
    edges = pd.read_csv(
        os.path.join(DATA_DIR, "deriv_edges.csv"),
        usecols=["parent_id", "child_id", "relation", "child_created"],
    )
    edges["child_month"] = edges["child_created"].str[:7]

    direct_counts = edges.groupby("parent_id").size().rename("alltime_deriv_count")
    df = df.merge(direct_counts, left_on="model_id", right_index=True, how="left")
    df["alltime_deriv_count"] = df["alltime_deriv_count"].fillna(0).astype(int)

    children_of = defaultdict(list)
    active_months = defaultdict(set)
    child_types = defaultdict(set)
    for row in edges.itertuples(index=False):
        children_of[row.parent_id].append(row.child_id)
        if row.child_month:
            active_months[row.parent_id].add(row.child_month)
        if isinstance(row.relation, str) and row.relation:
            child_types[row.parent_id].add(row.relation)

    target_ids = set(df.loc[df["alltime_deriv_count"] > 0, "model_id"])
    desc_count = {}
    desc_depth = {}
    for i, model_id in enumerate(target_ids, start=1):
        seen = set()
        queue = deque([(model_id, 0)])
        max_depth = 0
        while queue:
            node, depth = queue.popleft()
            for child in children_of.get(node, []):
                if child not in seen:
                    seen.add(child)
                    next_depth = depth + 1
                    if next_depth > max_depth:
                        max_depth = next_depth
                    queue.append((child, next_depth))
        desc_count[model_id] = len(seen)
        desc_depth[model_id] = max_depth
        if i % 10000 == 0:
            print(f"processed descendants for {i:,}/{len(target_ids):,} parent models")

    df["desc_count"] = df["model_id"].map(desc_count).fillna(0).astype(int)
    df["desc_depth"] = df["model_id"].map(desc_depth).fillna(0).astype(int)
    df["active_months"] = (
        df["model_id"].map(lambda mid: len(active_months.get(mid, set()))).astype(int)
    )
    df["type_diversity"] = (
        df["model_id"].map(lambda mid: len(child_types.get(mid, set()))).astype(int)
    )
    return df


def run_control_derivcount(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, lo, hi in DERIV_BANDS:
        band = df[
            (df["alltime_deriv_count"] >= lo) & (df["alltime_deriv_count"] <= hi)
        ].copy()
        result = compare_hi_lo(band)
        if result is None:
            continue
        result["deriv_band"] = label
        rows.append(result)
    cols = ["deriv_band"] + [c for c in rows[0].keys() if c != "deriv_band"]
    return pd.DataFrame(rows)[cols]


def run_joint_control(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dl_label, dl_lo, dl_hi in DOWNLOAD_BANDS:
        dl_band = df[(df["downloads"] >= dl_lo) & (df["downloads"] <= dl_hi)].copy()
        for deriv_label, deriv_lo, deriv_hi in DERIV_BANDS:
            sub = dl_band[
                (dl_band["alltime_deriv_count"] >= deriv_lo)
                & (dl_band["alltime_deriv_count"] <= deriv_hi)
            ].copy()
            result = compare_hi_lo(sub)
            if result is None:
                continue
            result["download_band"] = dl_label
            result["deriv_band"] = deriv_label
            rows.append(result)
    cols = (
        ["download_band", "deriv_band"]
        + [c for c in rows[0].keys() if c not in {"download_band", "deriv_band"}]
    )
    return pd.DataFrame(rows)[cols]


def main() -> None:
    print("loading last-month scores and all-time derivation graph ...")
    df = load_last_month()
    print(f"last-month models: {len(df):,}")
    print(f"models with all-time derivatives: {(df['alltime_deriv_count'] > 0).sum():,}")

    controlled = run_control_derivcount(df[df["alltime_deriv_count"] > 0].copy())
    joint = run_joint_control(
        df[(df["downloads"] > 0) & (df["alltime_deriv_count"] > 0)].copy()
    )

    controlled.to_csv(
        os.path.join(OUT_DIR, "rq2_control_derivcount.csv"), index=False
    )
    joint.to_csv(
        os.path.join(OUT_DIR, "rq2_control_downloads_derivcount.csv"), index=False
    )

    print("\nSaved:")
    print(f"  {OUT_DIR}/rq2_control_derivcount.csv ({len(controlled):,} rows)")
    print(
        f"  {OUT_DIR}/rq2_control_downloads_derivcount.csv ({len(joint):,} rows)"
    )


if __name__ == "__main__":
    main()
