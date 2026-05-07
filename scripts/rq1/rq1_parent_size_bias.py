#!/usr/bin/env python3
"""
RQ1 parent-size bias audit.

Question:
    For similar raw derivative counts, does parent model size still change the
    downstream structural meaning of those counts?

Output:
    output_v3/rq1_parent_size_bias.csv
"""
import os
from collections import defaultdict, deque

import numpy as np
import pandas as pd

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v3")
DATA_DIR = os.environ.get("MODELRANK_DATA_DIR", "data_new/monthly")
LAST = "2026-02"

COUNT_BANDS = [
    ("1", 1, 1),
    ("2", 2, 2),
    ("3-4", 3, 4),
    ("5-8", 5, 8),
    ("9+", 9, float("inf")),
]


def load_last_month_with_size_and_structure() -> pd.DataFrame:
    scores = pd.read_csv(
        os.path.join(OUT_DIR, "modelrank_scores.csv"),
        usecols=["month", "model_id", "downloads"],
    )
    df = scores[scores["month"] == LAST].copy()

    models = pd.read_csv(
        os.path.join(DATA_DIR, "deriv_models.csv"),
        usecols=["id", "params"],
    ).rename(columns={"id": "model_id", "params": "parent_params"})
    df = df.merge(models, on="model_id", how="left")

    edges = pd.read_csv(
        os.path.join(DATA_DIR, "deriv_edges.csv"),
        usecols=["parent_id", "child_id", "relation", "child_created"],
    )
    alltime_counts = edges.groupby("parent_id").size().rename("alltime_deriv_count")
    df = df.merge(alltime_counts, left_on="model_id", right_index=True, how="left")
    df["alltime_deriv_count"] = df["alltime_deriv_count"].fillna(0).astype(int)

    children_of = defaultdict(list)
    active_months = defaultdict(set)
    for row in edges.itertuples(index=False):
        children_of[row.parent_id].append(row.child_id)
        cm = row.child_created[:7]
        if cm:
            active_months[row.parent_id].add(cm)

    targets = set(df.loc[df["alltime_deriv_count"] > 0, "model_id"])
    desc_count = {}
    for i, model_id in enumerate(targets, start=1):
        seen = set()
        queue = deque([model_id])
        while queue:
            node = queue.popleft()
            for child in children_of.get(node, []):
                if child not in seen:
                    seen.add(child)
                    queue.append(child)
        desc_count[model_id] = len(seen)
        if i % 10000 == 0:
            print(f"processed {i:,}/{len(targets):,} parent models")

    df["desc_count"] = df["model_id"].map(desc_count).fillna(0).astype(int)
    df["active_months"] = df["model_id"].map(lambda m: len(active_months.get(m, set()))).astype(int)
    return df


def main() -> None:
    print("loading last-month models with size and structure ...")
    df = load_last_month_with_size_and_structure()
    df = df[(df["alltime_deriv_count"] > 0) & df["parent_params"].notna() & (df["parent_params"] > 0)].copy()

    df["size_bin"] = pd.qcut(
        np.log1p(df["parent_params"]),
        q=3,
        labels=["Small", "Medium", "Large"],
        duplicates="drop",
    )

    rows = []
    for count_label, lo, hi in COUNT_BANDS:
        sub = df[(df["alltime_deriv_count"] >= lo) & (df["alltime_deriv_count"] <= hi)].copy()
        for size_label in ["Small", "Medium", "Large"]:
            cell = sub[sub["size_bin"] == size_label].copy()
            if len(cell) == 0:
                continue
            rows.append({
                "deriv_band": count_label,
                "size_bin": size_label,
                "n_models": int(len(cell)),
                "median_params": float(cell["parent_params"].median()),
                "desc_count_mean": float(cell["desc_count"].mean()),
                "desc_count_median": float(cell["desc_count"].median()),
                "desc_count_p90": float(cell["desc_count"].quantile(0.90)),
                "active_months_mean": float(cell["active_months"].mean()),
                "active_months_median": float(cell["active_months"].median()),
                "downloads_median": float(cell["downloads"].median()),
            })

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(OUT_DIR, "rq1_parent_size_bias.csv"), index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
