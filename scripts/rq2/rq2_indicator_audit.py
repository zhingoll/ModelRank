#!/usr/bin/env python3
"""
Audit the full RQ2 indicator suite.

Outputs:
  - output_v3/rq2_indicator_overview.csv
  - output_v3/rq2_indicator_redundancy.csv
"""
import os

import numpy as np
import pandas as pd

OUT_DIR = os.environ.get("MODELRANK_OUT_DIR", "output_v3")


def main() -> None:
    summary = pd.read_csv(os.path.join(OUT_DIR, "rq2_indicator_suite_summary.csv"))
    monthly = pd.read_csv(os.path.join(OUT_DIR, "rq2_indicator_suite_monthly.csv"))

    overview_rows = []
    for metric, g in summary.groupby("metric"):
        layer = g["layer"].iloc[0]
        g = g.copy()
        has_auc = g["mean_auc"].notna().any()
        primary_col = "mean_auc" if has_auc else "mean_lift"
        g = g.sort_values(primary_col, ascending=False)
        ranks = g[primary_col].rank(method="min", ascending=False)

        mr = g[g["method"] == "ModelRank"].iloc[0]
        smr = g[g["method"] == "Simplified-MR"].iloc[0]
        atd = g[g["method"] == "AllTimeDerivCount"].iloc[0]

        overview_rows.append({
            "layer": layer,
            "metric": metric,
            "primary_col": primary_col,
            "best_method": g.iloc[0]["method"],
            "best_value": g.iloc[0][primary_col],
            "modelrank_primary": mr[primary_col],
            "modelrank_rank": int(ranks[g["method"] == "ModelRank"].iloc[0]),
            "simplified_primary": smr[primary_col],
            "simplified_rank": int(ranks[g["method"] == "Simplified-MR"].iloc[0]),
            "alltime_primary": atd[primary_col],
            "alltime_rank": int(ranks[g["method"] == "AllTimeDerivCount"].iloc[0]),
            "modelrank_minus_simplified": mr[primary_col] - smr[primary_col],
            "modelrank_minus_alltime": mr[primary_col] - atd[primary_col],
        })

    overview = pd.DataFrame(overview_rows).sort_values(["layer", "metric"])
    overview.to_csv(os.path.join(OUT_DIR, "rq2_indicator_overview.csv"), index=False)

    # Redundancy audit: correlate metric lift profiles across month x method cells
    lift_pivot = monthly.pivot_table(
        index=["month", "method"],
        columns="metric",
        values="lift",
    )
    corr = lift_pivot.corr(method="spearman")

    rows = []
    metrics = list(corr.columns)
    for i, left in enumerate(metrics):
        for right in metrics[i + 1:]:
            val = corr.loc[left, right]
            rows.append({
                "metric_left": left,
                "metric_right": right,
                "spearman_corr_lift_profiles": float(val),
                "abs_corr": float(abs(val)),
            })
    redundancy = pd.DataFrame(rows).sort_values("abs_corr", ascending=False)
    redundancy.to_csv(os.path.join(OUT_DIR, "rq2_indicator_redundancy.csv"), index=False)

    print("=== Indicator overview ===")
    print(overview.to_string(index=False))
    print("\n=== ModelRank primary-rank counts ===")
    print(overview["modelrank_rank"].value_counts().sort_index().to_string())
    print("\n=== Best-method counts ===")
    print(overview["best_method"].value_counts().to_string())
    print("\n=== Top redundancy pairs (|rho| >= 0.95) ===")
    top = redundancy[redundancy["abs_corr"] >= 0.95]
    if len(top) == 0:
        print("None")
    else:
        print(top.head(40).to_string(index=False))


if __name__ == "__main__":
    main()
