#!/usr/bin/env python3
"""Compute derivation-type composition by role for the replication package."""

import os
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCORES_PATH = Path("results/shared/modelrank_scores.csv")
EDGES_PATH = Path(os.environ.get("MODELRANK_EDGES_PATH", "data/processed/deriv_edges.csv"))
OUT_PATH = Path("results/rq3/rq3_role_deriv_type_composition.csv")
MONTH = "2026-02"


def assign_roles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    dl_p90 = np.percentile(df["downloads"].to_numpy(), 90)
    mr_p90 = np.percentile(df["score_normalized"].to_numpy(), 90)

    high_dl = df["downloads"].to_numpy() >= dl_p90
    high_mr = df["score_normalized"].to_numpy() >= mr_p90

    role = np.full(len(df), "LT", dtype=object)
    role[high_dl & high_mr] = "PR"
    role[high_dl & ~high_mr] = "PL"
    role[~high_dl & high_mr] = "HR"
    df["role"] = role
    return df


def main() -> None:
    scores = pd.read_csv(ROOT / SCORES_PATH)
    snapshot = scores[scores["month"] == MONTH].copy()
    snapshot = assign_roles(snapshot)
    role_map = snapshot.set_index("model_id")["role"].to_dict()

    edges = pd.read_csv(ROOT / EDGES_PATH, usecols=["parent_id", "relation"])
    edges["role"] = edges["parent_id"].map(role_map)
    edges = edges[edges["role"].notna()].copy()
    edges["relation"] = edges["relation"].fillna("unknown")

    counts = (
        edges.groupby(["relation", "role"]).size().unstack(fill_value=0)
        .reindex(columns=["HR", "PR", "PL", "LT"], fill_value=0)
    )
    counts["Overall"] = counts.sum(axis=1)

    pct = counts.div(counts.sum(axis=0), axis=1) * 100.0
    pct = pct.reset_index().rename(columns={"relation": "Type"})
    out_path = ROOT / OUT_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pct.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
