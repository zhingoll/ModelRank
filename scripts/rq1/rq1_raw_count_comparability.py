#!/usr/bin/env python3
"""
RQ1 raw derivative-count comparability audit.

Question:
    Do similar raw derivative counts correspond to similar downstream
    structural outcomes? If not, raw counts are not directly comparable.

Output:
    output_v3/rq1_raw_count_comparability.csv
"""
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v3")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
LAST = "2026-02"

BANDS = [
    ("1", 1, 1),
    ("2", 2, 2),
    ("3-4", 3, 4),
    ("5-8", 5, 8),
    ("9+", 9, float("inf")),
]


def load_last_month_with_structure() -> pd.DataFrame:
    scores = pd.read_csv(
        os.path.join(OUT_DIR, "modelrank_scores.csv"),
        usecols=["month", "model_id", "downloads", "n_derivatives"],
    )
    df = scores[scores["month"] == LAST].copy()

    edges = pd.read_csv(
        os.path.join(DATA_DIR, "deriv_edges.csv"),
        usecols=["parent_id", "child_id", "relation", "child_created"],
    )

    alltime_counts = edges.groupby("parent_id").size().rename("alltime_deriv_count")
    df = df.merge(alltime_counts, left_on="model_id", right_index=True, how="left")
    df["alltime_deriv_count"] = df["alltime_deriv_count"].fillna(0).astype(int)

    children_of = defaultdict(list)
    active_months = defaultdict(set)
    child_types = defaultdict(set)
    for row in edges.itertuples(index=False):
        children_of[row.parent_id].append(row.child_id)
        if isinstance(row.relation, str) and row.relation:
            child_types[row.parent_id].add(row.relation)
        cm = row.child_created[:7]
        if cm:
            active_months[row.parent_id].add(cm)

    targets = set(df.loc[df["alltime_deriv_count"] > 0, "model_id"])
    desc_count = {}
    desc_depth = {}
    for i, model_id in enumerate(targets, start=1):
        seen = set()
        queue = deque([(model_id, 0)])
        max_depth = 0
        while queue:
            node, depth = queue.popleft()
            for child in children_of.get(node, []):
                if child not in seen:
                    seen.add(child)
                    nd = depth + 1
                    if nd > max_depth:
                        max_depth = nd
                    queue.append((child, nd))
        desc_count[model_id] = len(seen)
        desc_depth[model_id] = max_depth
        if i % 10000 == 0:
            print(f"processed {i:,}/{len(targets):,} parent models")

    df["desc_count"] = df["model_id"].map(desc_count).fillna(0).astype(int)
    df["desc_depth"] = df["model_id"].map(desc_depth).fillna(0).astype(int)
    df["active_months"] = df["model_id"].map(lambda m: len(active_months.get(m, set()))).astype(int)
    df["type_diversity"] = df["model_id"].map(lambda m: len(child_types.get(m, set()))).astype(int)
    return df


def summarize_band(sub: pd.DataFrame, band_label: str) -> dict:
    out = {
        "deriv_band": band_label,
        "n_models": int(len(sub)),
        "count_median": float(sub["alltime_deriv_count"].median()),
    }
    for var in ["desc_count", "desc_depth", "active_months", "type_diversity"]:
        vals = sub[var].astype(float)
        out[f"{var}_mean"] = float(vals.mean())
        out[f"{var}_median"] = float(vals.median())
        out[f"{var}_p10"] = float(vals.quantile(0.10))
        out[f"{var}_p90"] = float(vals.quantile(0.90))
        out[f"{var}_max"] = float(vals.max())
        out[f"{var}_iqr"] = float(vals.quantile(0.75) - vals.quantile(0.25))
    return out


def main() -> None:
    print("loading last-month models and all-time structure ...")
    df = load_last_month_with_structure()
    df = df[df["alltime_deriv_count"] > 0].copy()

    rows = []
    for label, lo, hi in BANDS:
        sub = df[(df["alltime_deriv_count"] >= lo) & (df["alltime_deriv_count"] <= hi)].copy()
        if len(sub) == 0:
            continue
        rows.append(summarize_band(sub, label))

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(OUT_DIR, "rq1_raw_count_comparability.csv"), index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
