"""Refit all final Hidden-Root effects from the frozen matched-sample asset.

Requires NumPy, pandas, SciPy and PyArrow. No lab imports, generators or network.
Example (paths relative to the slim package):
  python -B hr.py --pairs ../data_assets/hr/matched_pairs.parquet \
      --output ../private_runs/hr_reproduced --verify results/hr

This starts AFTER the final post-diagnostic same-origin-Likes restriction and
outcome materialization; it does not reconstruct matching or raw monthly data.
Associations are observational. PR is role-defined; active-parent is graph-internal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm

COVARIATES = (
    "log_downloads", "log_likes", "model_age_days", "log_parameters", "download_trend",
)
OUTCOMES = (
    "future_download_p90_crossing", "future_pr",
    "future_log_download_change", "future_active_parent",
)
HORIZONS = (1, 3, 6)
PAIR_COLUMNS = (
    "pair_id", "horizon", "hr_month", "hr_model_id", "control_model_id",
    *[f"{side}_{column}" for side in ("hr", "control")
      for column in ("task", *COVARIATES, *OUTCOMES)],
)

# The ten functions below are exact source/AST extractions from temporal.py
# and balance_correction_v1_1/outcomes.py of the frozen HR implementation.
# Keep their row order, rank transforms, ridge, pseudoinverse and cluster rules.

def _clean(y: pd.Series, design: np.ndarray, groups: pd.Series) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    response = pd.to_numeric(y, errors="coerce").to_numpy(float)
    matrix = np.asarray(design, dtype=float)
    cluster = groups.astype(str).to_numpy()
    valid = np.isfinite(response) & np.isfinite(matrix).all(axis=1)
    return response[valid], matrix[valid], cluster[valid]


def _cluster_meat(scores: np.ndarray, groups: np.ndarray) -> np.ndarray:
    _, inverse = np.unique(groups, return_inverse=True)
    summed = np.zeros((int(inverse.max()) + 1, scores.shape[1]), dtype=float)
    np.add.at(summed, inverse, scores)
    return summed.T @ summed


def _cluster_correction(n: int, k: int, groups: np.ndarray) -> float:
    count = len(np.unique(groups))
    if count < 2 or n <= k:
        return 1.0
    return (count / (count - 1)) * ((n - 1) / (n - k))


def _fit_logistic(y: pd.Series, design: np.ndarray, groups: pd.Series,
                  coefficient_index: int) -> dict[str, float]:
    response, matrix, cluster = _clean(y, design, groups)
    if len(response) == 0 or response.min() == response.max():
        raise ValueError("constant binary outcome")
    coefficients = np.zeros(matrix.shape[1], dtype=float)
    ridge = np.eye(matrix.shape[1]) * 1e-8
    ridge[0, 0] = 0.0
    for _ in range(100):
        probability = np.clip(expit(matrix @ coefficients), 1e-9, 1 - 1e-9)
        weights = probability * (1 - probability)
        information = matrix.T @ (matrix * weights[:, None]) + ridge
        score = matrix.T @ (response - probability) - ridge @ coefficients
        step = np.linalg.pinv(information) @ score
        coefficients += step
        if float(np.max(np.abs(step))) < 1e-8:
            break
    probability = np.clip(expit(matrix @ coefficients), 1e-9, 1 - 1e-9)
    weights = probability * (1 - probability)
    bread = np.linalg.pinv(matrix.T @ (matrix * weights[:, None]) + ridge)
    score_rows = matrix * (response - probability)[:, None]
    covariance = bread @ _cluster_meat(score_rows, cluster) @ bread
    covariance *= _cluster_correction(len(response), matrix.shape[1], cluster)
    coefficient = float(coefficients[coefficient_index])
    standard_error = math.sqrt(max(0.0, float(covariance[coefficient_index, coefficient_index])))
    z = coefficient / standard_error if standard_error > 0 else math.copysign(math.inf, coefficient)
    return {"coefficient": coefficient, "standard_error": standard_error,
            "ci_low": coefficient - 1.959963984540054 * standard_error,
            "ci_high": coefficient + 1.959963984540054 * standard_error,
            "p_value": float(2 * norm.sf(abs(z))), "n": float(len(response)),
            "clusters": float(len(np.unique(cluster)))}


def _fit_ols(y: pd.Series, design: np.ndarray, groups: pd.Series,
             coefficient_index: int) -> dict[str, float]:
    response, matrix, cluster = _clean(y, design, groups)
    if len(response) == 0:
        raise ValueError("empty continuous outcome")
    bread = np.linalg.pinv(matrix.T @ matrix)
    coefficients = bread @ matrix.T @ response
    residuals = response - matrix @ coefficients
    score_rows = matrix * residuals[:, None]
    covariance = bread @ _cluster_meat(score_rows, cluster) @ bread
    covariance *= _cluster_correction(len(response), matrix.shape[1], cluster)
    coefficient = float(coefficients[coefficient_index])
    standard_error = math.sqrt(max(0.0, float(covariance[coefficient_index, coefficient_index])))
    z = coefficient / standard_error if standard_error > 0 else math.copysign(math.inf, coefficient)
    return {"coefficient": coefficient, "standard_error": standard_error,
            "ci_low": coefficient - 1.959963984540054 * standard_error,
            "ci_high": coefficient + 1.959963984540054 * standard_error,
            "p_value": float(2 * norm.sf(abs(z))), "n": float(len(response)),
            "clusters": float(len(np.unique(cluster)))}


def apply_holm_family(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    total = len(work)
    work["holm_p_value"] = np.nan
    finite = work.index[np.isfinite(pd.to_numeric(work["p_value"], errors="coerce"))].tolist()
    ordered = sorted(finite, key=lambda index: (float(work.at[index, "p_value"]), index))
    running = 0.0
    for position, index in enumerate(ordered):
        candidate = (total - position) * float(work.at[index, "p_value"])
        running = max(running, candidate)
        work.at[index, "holm_p_value"] = min(1.0, running)
    work["holm_family_size"] = total
    return work


def one_model_one_origin(pairs: pd.DataFrame) -> pd.DataFrame:
    work = pairs.sort_values(["hr_month", "pair_id"], kind="mergesort")
    used: set[str] = set()
    kept: list[int] = []
    for index, row in work.iterrows():
        model_ids = {str(row["hr_model_id"]), str(row["control_model_id"])}
        if model_ids & used:
            continue
        used.update(model_ids)
        kept.append(index)
    return work.loc[kept].reset_index(drop=True)


def fit_horizon_effects(observations: pd.DataFrame, *, horizon: int) -> pd.DataFrame:
    work = observations.copy()
    for column in COVARIATES:
        work[column + "_rank"] = work.groupby("month", sort=False)[column].transform(
            lambda values: values.rank(method="average", pct=True)
        )
    task = pd.get_dummies(work["task"].astype(str), prefix="task", drop_first=True, dtype=float)
    month = pd.get_dummies(work["month"].astype(str), prefix="month", drop_first=True, dtype=float)
    base = np.column_stack([
        np.ones(len(work)),
        *[work[column + "_rank"].to_numpy(float) for column in COVARIATES],
        task.to_numpy(float), month.to_numpy(float), work["is_hr"].to_numpy(float),
    ])
    coefficient_index = base.shape[1] - 1
    rows: list[dict[str, Any]] = []
    for outcome in OUTCOMES:
        model = ("cluster_robust_ols" if outcome == "future_log_download_change"
                 else "cluster_robust_logistic")
        try:
            fit = (_fit_ols if model.endswith("ols") else _fit_logistic)(
                work[outcome], base, work["pair_id"], coefficient_index
            )
            if model.endswith("logistic"):
                effect, low, high = (math.exp(fit["coefficient"]), math.exp(fit["ci_low"]),
                                     math.exp(fit["ci_high"]))
                unit = "odds ratio for HR versus balanced LT"
            else:
                effect, low, high = fit["coefficient"], fit["ci_low"], fit["ci_high"]
                unit = "adjusted log-download difference for HR versus balanced LT"
            rows.append({"horizon": horizon, "outcome": outcome, "model": model, **fit,
                         "effect": effect, "effect_ci_low": low, "effect_ci_high": high,
                         "effect_unit": unit, "status": "ok", "reason": "included"})
        except Exception as exc:
            rows.append({"horizon": horizon, "outcome": outcome, "model": model,
                         "coefficient": np.nan, "standard_error": np.nan,
                         "ci_low": np.nan, "ci_high": np.nan, "p_value": np.nan,
                         "n": float(len(work)), "clusters": float(work["pair_id"].nunique()),
                         "effect": np.nan, "effect_ci_low": np.nan, "effect_ci_high": np.nan,
                         "effect_unit": "coefficient" if model.endswith("ols") else "odds ratio",
                         "status": "not_estimable", "reason": str(exc)})
    return pd.DataFrame(rows)


def _observations(pairs: pd.DataFrame) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for side, indicator in (("hr", 1), ("control", 0)):
        values: dict[str, Any] = {
            "pair_id": pairs["pair_id"], "is_hr": indicator,
            "task": pairs[f"{side}_task"], "month": pairs["hr_month"],
        }
        for column in (*COVARIATES, *OUTCOMES):
            values[column] = pairs[f"{side}_{column}"]
        parts.append(pd.DataFrame(values))
    return pd.concat(parts, ignore_index=True)


def _classify(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    decisions: list[str] = []
    for row in work.itertuples(index=False):
        if row.status != "ok":
            decisions.append("not_estimable")
            continue
        reference = 0.0 if row.outcome == "future_log_download_change" else 1.0
        if row.effect_ci_low > reference:
            decisions.append("positive")
        elif row.effect_ci_high < reference:
            decisions.append("adverse")
        else:
            decisions.append("null")
    work["decision"] = decisions
    return work


def validate_pairs(pairs: pd.DataFrame) -> None:
    if list(pairs.columns) != list(PAIR_COLUMNS):
        raise ValueError("Expected exactly the documented 25 matched-sample columns")
    if pairs.isna().any().any() or not pairs["pair_id"].is_unique:
        raise ValueError("Missing values or duplicate pair IDs")
    if set(pairs["horizon"]) != set(HORIZONS):
        raise ValueError("All three horizons (1, 3, 6) are required")
    if (pairs["hr_model_id"] == pairs["control_model_id"]).any():
        raise ValueError("A model cannot be its own control")
    for side in ("hr", "control"):
        values = pairs[[f"{side}_{c}" for c in (*COVARIATES, *OUTCOMES)]].to_numpy(float)
        if not np.isfinite(values).all():
            raise ValueError("Nonfinite covariate or outcome")
        for outcome in OUTCOMES:
            if outcome != "future_log_download_change":
                if not pairs[f"{side}_{outcome}"].isin([0, 1]).all():
                    raise ValueError("Nonbinary logistic outcome")


def reproduce(pairs: pd.DataFrame) -> dict[str, pd.DataFrame]:
    validate_pairs(pairs)
    primary, sensitivity = [], []
    for horizon in HORIZONS:
        selected = pairs.loc[pairs["horizon"] == horizon].copy()
        unique = one_model_one_origin(selected)
        print(f"H{horizon}: primary={len(selected)}; earliest-origin={len(unique)}", flush=True)
        primary.append(fit_horizon_effects(_observations(selected), horizon=horizon))
        sensitivity.append(fit_horizon_effects(_observations(unique), horizon=horizon))
    tables = {}
    for name, frames in (("primary_effects", primary), ("earliest_origin_effects", sensitivity)):
        # Match the final exact-Likes run, not the older CI-only decision labels.
        result = _classify(apply_holm_family(pd.concat(frames, ignore_index=True)))
        result = result.rename(columns={"decision": "ci_only_direction"})
        result["holm_supported_direction"] = np.where(
            result.status != "ok", "not_estimable", np.where(
                result.holm_p_value < .05, result.ci_only_direction, "no_supported_difference"))
        tables[name + ".csv"] = result
    return tables


def compare_effects(actual: pd.DataFrame, expected: pd.DataFrame) -> dict[str, Any]:
    keys = ["horizon", "outcome"]
    grid = {(h, o) for h in HORIZONS for o in OUTCOMES}
    for table in (actual, expected):
        if len(table) != 12 or table.duplicated(keys).any():
            raise ValueError("Each result must contain all 12 unique rows")
        if set(table[keys].itertuples(index=False, name=None)) != grid:
            raise ValueError("Incomplete horizon/outcome grid")
        if not table["holm_family_size"].eq(12).all():
            raise ValueError("Holm family must retain all 12 outcomes")
    if list(actual.columns) != list(expected.columns):
        raise ValueError("Result schema differs")
    left = actual.sort_values(keys).reset_index(drop=True)
    right = expected.sort_values(keys).reset_index(drop=True)
    errors = {}
    for column in left:
        if pd.api.types.is_numeric_dtype(right[column]):
            a, b = left[column].to_numpy(float), right[column].to_numpy(float)
            if column in ("horizon", "n", "clusters", "holm_family_size"):
                np.testing.assert_array_equal(a, b, err_msg=column)
            else:
                # Allow only floating-point backend/CSV round-trip differences.
                is_p = column in ("p_value", "holm_p_value")
                np.testing.assert_allclose(
                    a, b, rtol=1e-7 if is_p else 1e-8,
                    atol=1e-15 if is_p else 1e-10, equal_nan=True, err_msg=column)
            finite = np.isfinite(a) & np.isfinite(b)
            errors[column] = float(np.max(np.abs(a[finite] - b[finite]))) if finite.any() else None
        else:
            pd.testing.assert_series_equal(left[column], right[column], check_exact=True)
    return {"rows": 12, "all_columns_matched": True, "max_absolute_error": errors}


def read_effects(path: Path) -> pd.DataFrame:
    # 'null' is an inferential direction, not a missing-value token.
    return pd.read_csv(path, keep_default_na=False, na_values=[""])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, required=True, help="Frozen 25-column matched-pair Parquet")
    parser.add_argument("--output", type=Path, required=True, help="New output directory; never overwritten")
    parser.add_argument("--verify", type=Path, help="Directory containing the two saved final CSV tables")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing existing output directory: {args.output}")
    pairs = pd.read_parquet(args.pairs)
    tables = reproduce(pairs)
    verification = {}
    if args.verify is not None:
        for name, table in tables.items():
            verification[name] = compare_effects(table, read_effects(args.verify / name))
    args.output.mkdir(parents=True, exist_ok=False)
    for name, table in tables.items():
        table.to_csv(args.output / name, index=False, lineterminator="\n")
    report = {
        "sample_sha256": hashlib.sha256(args.pairs.read_bytes()).hexdigest(),
        "sample_rows": len(pairs), "sample_columns": len(pairs.columns),
        "pair_counts": {str(h): int((pairs.horizon == h).sum()) for h in HORIZONS},
        "verification": verification,
        "interpretation": "Observational, post-diagnostic matched-sample analysis; not causal.",
    }
    (args.output / "verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
