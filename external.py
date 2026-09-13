"""Standalone frozen external-validation statistics; never writes input files.

Python 3.9+, numpy; pandas and pyarrow only for Space parquet input.
CLI prints JSON to stdout. No raw expert returns or laboratory imports.
Space --replicates 10000 reproduces percentile intervals and paired inference;
--replicates 0 computes point estimates only, explicitly without inference.
Expert CSV requires anonymous pair_id, three vote counts, missing_judgments,
majority_outcome and seven method-direction columns. Keep pending data private.
"""

from __future__ import annotations

import itertools
import math
from typing import Mapping, Sequence

import numpy as np


REGIMES = (
    "confirmed-only",
    "undecidable-negative",
    "undecidable-positive",
    "undecidable-excluded",
)
METRICS = ("AUROC", "AP", "Top-1% lift", "Top-5% lift", "Top-10% lift")
_VALID_STATES = {
    "confirmed_positive",
    "confirmed_negative_complete",
    "undecidable",
    "collection_failure",
}


def _arrays(labels: Sequence[int], scores: Sequence[float]) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(labels, dtype=int)
    s = np.asarray(scores, dtype=float)
    if y.ndim != 1 or s.ndim != 1 or len(y) != len(s):
        raise ValueError("labels and scores must be equal-length one-dimensional arrays")
    if not np.isin(y, [0, 1]).all():
        raise ValueError("labels must be binary")
    if not np.isfinite(s).all():
        raise ValueError("scores must be finite")
    return y, s


def auroc(labels: Sequence[int], scores: Sequence[float]) -> float:
    """AUROC via the Mann-Whitney identity with average ranks for ties."""
    y, s = _arrays(labels, scores)
    positives = int(y.sum())
    negatives = len(y) - positives
    if positives == 0 or negatives == 0:
        return math.nan
    order = np.argsort(s, kind="mergesort")
    sorted_scores = s[order]
    ranks = np.empty(len(s), dtype=float)
    start = 0
    while start < len(s):
        end = start + 1
        while end < len(s) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    rank_sum = float(ranks[y == 1].sum())
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def average_precision(labels: Sequence[int], scores: Sequence[float]) -> float:
    """Non-interpolated AP, grouping equal scores before each recall step."""
    y, s = _arrays(labels, scores)
    positives = int(y.sum())
    if positives == 0:
        return math.nan
    order = np.argsort(-s, kind="mergesort")
    ys = y[order]
    ss = s[order]
    cumulative_positive = 0
    cumulative_total = 0
    value = 0.0
    start = 0
    while start < len(y):
        end = start + 1
        while end < len(y) and ss[end] == ss[start]:
            end += 1
        group_positive = int(ys[start:end].sum())
        cumulative_positive += group_positive
        cumulative_total += end - start
        value += (group_positive / positives) * (cumulative_positive / cumulative_total)
        start = end
    return value


def top_k_lift(
    model_ids: Sequence[str], labels: Sequence[int], scores: Sequence[float], fraction: float
) -> float:
    ids = np.asarray(model_ids, dtype=str)
    y, s = _arrays(labels, scores)
    if len(ids) != len(y) or not 0 < fraction <= 1:
        raise ValueError("invalid model IDs or top-k fraction")
    prevalence = float(y.mean()) if len(y) else math.nan
    if not np.isfinite(prevalence) or prevalence == 0:
        return math.nan
    count = max(1, int(math.ceil(len(y) * fraction)))
    order = np.lexsort((ids, -s))
    return float(y[order[:count]].mean() / prevalence)


def labels_for_regime(states: Sequence[str], regime: str) -> tuple[np.ndarray, np.ndarray]:
    state = np.asarray(states, dtype=str)
    unknown = set(state) - _VALID_STATES
    if unknown:
        raise ValueError(f"unknown model state(s): {sorted(unknown)}")
    if regime not in REGIMES:
        raise ValueError(f"unknown sensitivity regime: {regime}")
    confirmed = np.isin(state, ["confirmed_positive", "confirmed_negative_complete"])
    include = confirmed.copy()
    if regime in {"undecidable-negative", "undecidable-positive"}:
        include |= state == "undecidable"
    selected = state[include]
    labels = (selected == "confirmed_positive").astype(int)
    if regime == "undecidable-positive":
        labels[selected == "undecidable"] = 1
    return include, labels


def holm_adjust(p_values: Sequence[float]) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    result = np.full(len(p), np.nan)
    valid = np.flatnonzero(np.isfinite(p))
    if len(valid) == 0:
        return result
    order = valid[np.argsort(p[valid], kind="mergesort")]
    running = 0.0
    total = len(order)
    for position, index in enumerate(order):
        running = max(running, min(1.0, (total - position) * p[index]))
        result[index] = running
    return result


def _metric_value(
    metric: str, model_ids: np.ndarray, labels: np.ndarray, scores: np.ndarray
) -> float:
    if metric == "AUROC":
        return auroc(labels, scores)
    if metric == "AP":
        return average_precision(labels, scores)
    fractions = {"Top-1% lift": 0.01, "Top-5% lift": 0.05, "Top-10% lift": 0.10}
    return top_k_lift(model_ids, labels, scores, fractions[metric])


def weighted_bootstrap_metrics(
    model_ids: Sequence[str],
    labels: Sequence[int],
    scores: Sequence[float],
    counts: np.ndarray,
) -> np.ndarray:
    """Evaluate all five metrics for multinomial bootstrap count rows.

    Count weighting is exactly equivalent to expanding each sampled model the
    indicated number of times, while avoiding per-replicate sorting.
    """
    ids = np.asarray(model_ids, dtype=str)
    y, s = _arrays(labels, scores)
    weight = np.asarray(counts, dtype=np.int64)
    if weight.ndim != 2 or weight.shape[1] != len(y) or (weight < 0).any():
        raise ValueError("bootstrap counts must be a nonnegative matrix with one column per model")
    if len(ids) != len(y) or not np.all(weight.sum(axis=1) == len(y)):
        raise ValueError("bootstrap counts must encode fixed-size model resamples")
    result = np.full((weight.shape[0], len(METRICS)), np.nan, dtype=float)
    total_positive = weight @ y
    total_negative = len(y) - total_positive

    ascending = np.argsort(s, kind="mergesort")
    asc_scores = s[ascending]
    asc_starts = np.r_[0, np.flatnonzero(asc_scores[1:] != asc_scores[:-1]) + 1]
    asc_weight = weight[:, ascending]
    asc_positive = asc_weight * y[ascending]
    asc_negative = asc_weight * (1 - y[ascending])
    group_positive = np.add.reduceat(asc_positive, asc_starts, axis=1)
    group_negative = np.add.reduceat(asc_negative, asc_starts, axis=1)
    negative_before = np.cumsum(group_negative, axis=1) - group_negative
    numerator = np.sum(group_positive * (negative_before + 0.5 * group_negative), axis=1)
    denominator = total_positive * total_negative
    np.divide(numerator, denominator, out=result[:, 0], where=denominator > 0)

    descending = np.argsort(-s, kind="mergesort")
    desc_scores = s[descending]
    desc_starts = np.r_[0, np.flatnonzero(desc_scores[1:] != desc_scores[:-1]) + 1]
    desc_weight = weight[:, descending]
    desc_positive = desc_weight * y[descending]
    desc_negative = desc_weight * (1 - y[descending])
    group_positive = np.add.reduceat(desc_positive, desc_starts, axis=1)
    group_total = group_positive + np.add.reduceat(desc_negative, desc_starts, axis=1)
    cumulative_positive = np.cumsum(group_positive, axis=1)
    cumulative_total = np.cumsum(group_total, axis=1)
    precision = np.divide(
        cumulative_positive, cumulative_total,
        out=np.zeros_like(cumulative_positive, dtype=float), where=cumulative_total > 0,
    )
    ap_numerator = np.sum(group_positive * precision, axis=1)
    np.divide(ap_numerator, total_positive, out=result[:, 1], where=total_positive > 0)

    top_order = np.lexsort((ids, -s))
    top_weight = weight[:, top_order]
    top_labels = y[top_order]
    cumulative = np.cumsum(top_weight, axis=1)
    before = cumulative - top_weight
    for column, fraction in enumerate((0.01, 0.05, 0.10), start=2):
        count = max(1, int(math.ceil(len(y) * fraction)))
        included = np.clip(count - before, 0, top_weight)
        top_positive = included @ top_labels
        numerator = top_positive * len(y)
        denominator = count * total_positive
        np.divide(numerator, denominator, out=result[:, column], where=denominator > 0)
    return result


def bootstrap_bundle(
    model_ids: Sequence[str],
    labels: Sequence[int],
    scores: Mapping[str, Sequence[float]],
    reference: str,
    replicates: int,
    seed: int,
    *,
    chunk_size: int = 128,
) -> dict[str, list[dict[str, object]]]:
    """Compute method intervals and paired reference contrasts in one bootstrap.

    All methods consume the same multinomial model-resampling counts.  Chunking
    limits memory without changing the frozen sample size or statistical rule.
    """
    ids = np.asarray(model_ids, dtype=str)
    y = np.asarray(labels, dtype=int)
    arrays = {name: np.asarray(value, dtype=float) for name, value in scores.items()}
    if reference not in arrays or replicates <= 0 or chunk_size <= 0 or len(y) == 0:
        raise ValueError("invalid paired bootstrap inputs")
    if len(ids) != len(y) or any(len(value) != len(y) for value in arrays.values()):
        raise ValueError("all paired bootstrap arrays must have equal length")
    distributions = {
        method: np.full((replicates, len(METRICS)), np.nan, dtype=float) for method in arrays
    }
    rng = np.random.default_rng(seed)
    probability = np.full(len(y), 1.0 / len(y))
    offset = 0
    while offset < replicates:
        batch = min(chunk_size, replicates - offset)
        counts = rng.multinomial(len(y), probability, size=batch)
        for method, method_scores in arrays.items():
            distributions[method][offset:offset + batch] = weighted_bootstrap_metrics(
                ids, y, method_scores, counts
            )
        offset += batch

    points = {
        method: np.asarray([_metric_value(metric, ids, y, value) for metric in METRICS])
        for method, value in arrays.items()
    }
    method_rows: list[dict[str, object]] = []
    for method in arrays:
        for column, metric in enumerate(METRICS):
            values = distributions[method][:, column]
            valid = values[np.isfinite(values)]
            estimate = points[method][column]
            if not np.isfinite(estimate) or len(valid) == 0:
                low = high = math.nan
                status = "non-estimable"
            else:
                low, high = (float(value) for value in np.quantile(valid, [0.025, 0.975]))
                status = "estimable"
            method_rows.append({
                "metric": metric, "method": method,
                "estimate": float(estimate) if np.isfinite(estimate) else math.nan,
                "ci_low": low, "ci_high": high,
                "valid_bootstrap_replicates": int(len(valid)), "status": status,
            })

    contrast_rows: list[dict[str, object]] = []
    for method in arrays:
        if method == reference:
            continue
        for column, metric in enumerate(METRICS):
            difference = distributions[reference][:, column] - distributions[method][:, column]
            valid = difference[np.isfinite(difference)]
            estimate = points[reference][column] - points[method][column]
            if not np.isfinite(estimate) or len(valid) == 0:
                low = high = raw_p = math.nan
                status = "non-estimable"
            else:
                low, high = (float(value) for value in np.quantile(valid, [0.025, 0.975]))
                denominator = len(valid) + 1
                lower_tail = (int(np.count_nonzero(valid <= 0)) + 1) / denominator
                upper_tail = (int(np.count_nonzero(valid >= 0)) + 1) / denominator
                raw_p = min(1.0, 2.0 * min(lower_tail, upper_tail))
                status = "estimable"
            contrast_rows.append({
                "metric": metric, "reference": reference, "method": method,
                "estimate": float(estimate) if np.isfinite(estimate) else math.nan,
                "ci_low": low, "ci_high": high, "raw_p_value": raw_p,
                "holm_p_value": math.nan, "valid_bootstrap_replicates": int(len(valid)),
                "status": status,
            })
    for metric in METRICS:
        indices = [index for index, row in enumerate(contrast_rows) if row["metric"] == metric]
        adjusted = holm_adjust([float(contrast_rows[index]["raw_p_value"]) for index in indices])
        for index, value in zip(indices, adjusted):
            contrast_rows[index]["holm_p_value"] = float(value)
    pairwise_rows: list[dict[str, object]] = []
    for left, right in itertools.combinations(arrays, 2):
        for column, metric in enumerate(METRICS):
            distribution = distributions[left][:, column] - distributions[right][:, column]
            valid = distribution[np.isfinite(distribution)]
            left_point, right_point = points[left][column], points[right][column]
            estimate = left_point - right_point
            if not np.isfinite(estimate) or len(valid) == 0:
                low = high = raw_p = math.nan
                status = "non-estimable"
            else:
                low, high = (float(value) for value in np.quantile(valid, [0.025, 0.975]))
                denominator = len(valid) + 1
                lower_tail = (int(np.count_nonzero(valid <= 0)) + 1) / denominator
                upper_tail = (int(np.count_nonzero(valid >= 0)) + 1) / denominator
                raw_p = min(1.0, 2.0 * min(lower_tail, upper_tail))
                status = "estimable"
            pairwise_rows.append({
                "metric": metric, "left_method": left, "right_method": right,
                "left_estimate": float(left_point) if np.isfinite(left_point) else math.nan,
                "right_estimate": float(right_point) if np.isfinite(right_point) else math.nan,
                "difference": float(estimate) if np.isfinite(estimate) else math.nan,
                "ci_low": low, "ci_high": high, "raw_p_value": raw_p,
                "valid_bootstrap_replicates": int(len(valid)), "status": status,
            })
    return {
        "method_metrics": method_rows,
        "reference_contrasts": contrast_rows,
        "all_pairwise_differences": pairwise_rows,
    }


METHODS = ('S_C3_Q10', 'Submitted Full ModelRank', 'AllTime DerivCount',
           'Current DerivCount', 'Vanilla PageRank', 'Temporal Vanilla PageRank',
           'Downloads', 'Likes')
REFERENCE = 'S_C3_Q10'

def analyze_arrays(
    model_ids: Sequence[str],
    states: Sequence[str],
    scores: Mapping[str, Sequence[float]],
    *,
    replicates: int,
    seed: int,
) -> dict[str, list[dict[str, object]]]:
    if tuple(scores) != METHODS:
        raise ValueError("analysis requires exactly the eight frozen methods in frozen order")
    ids = np.asarray(model_ids, dtype=str)
    state = np.asarray(states, dtype=str)
    arrays = {name: np.asarray(value, dtype=float) for name, value in scores.items()}
    method_rows: list[dict[str, object]] = []
    contrast_rows: list[dict[str, object]] = []
    pairwise_rows: list[dict[str, object]] = []
    cached: dict[tuple[tuple[bool, ...], tuple[int, ...]], dict[str, list[dict[str, object]]]] = {}
    for regime in REGIMES:
        mask, labels = labels_for_regime(state, regime)
        regime_ids = ids[mask]
        regime_scores = {name: value[mask] for name, value in arrays.items()}
        context = {
            "regime": regime,
            "n": int(len(labels)),
            "positive_count": int(labels.sum()),
            "negative_count": int(len(labels) - labels.sum()),
        }
        cache_key = (tuple(bool(value) for value in mask), tuple(int(value) for value in labels))
        if cache_key not in cached:
            cached[cache_key] = bootstrap_bundle(
                regime_ids, labels, regime_scores, REFERENCE, replicates, seed
            )
        bundle = cached[cache_key]
        method_rows.extend({**context, **row} for row in bundle["method_metrics"])
        contrast_rows.extend({**context, **row} for row in bundle["reference_contrasts"])
        pairwise_rows.extend({**context, **row} for row in bundle["all_pairwise_differences"])
    return {
        "method_metrics": method_rows,
        "reference_contrasts": contrast_rows,
        "all_pairwise_differences": pairwise_rows,
    }


EXPERT_METHODS = {
    'S3': 's3', 'Full ModelRank': 'full_modelrank',
    'AllTime DerivCount': 'alltime_derivcount',
    'Current DerivCount': 'current_derivcount',
    'Vanilla PageRank': 'vanilla_pagerank', 'Downloads': 'downloads',
    'Likes': 'likes',
}
CATEGORIES = ('item_1', 'item_2', 'tie')
VOTE_FIELDS = ('pair_id', 'votes_item_1', 'votes_item_2', 'votes_tie',
               'missing_judgments', 'majority_outcome')


def expert_counts(rows):
    """Primary agreement (method ties wrong), Wilson CI and complete-case kappa."""
    from collections import Counter
    fields = set(VOTE_FIELDS) | {s + '_direction' for s in EXPERT_METHODS.values()}
    if len(rows) != 240 or any(set(r) != fields for r in rows):
        raise ValueError('require all 240 pairs and only the anonymous schema')
    ids = [r['pair_id'] for r in rows]
    if len(set(ids)) != 240 or any(not x for x in ids):
        raise ValueError('pair IDs must be unique and nonempty')
    complete = []
    outcomes = []
    missing_total = 0
    patterns = Counter()
    for row in rows:
        counts = [row['votes_' + c] for c in CATEGORIES] + [row['missing_judgments']]
        if any(str(v) not in {'0', '1', '2', '3'} for v in counts):
            raise ValueError('vote counts must be nonnegative integers up to three')
        counts = list(map(int, counts))
        if sum(counts) != 3:
            raise ValueError('votes plus missing must equal three')
        winners = [c for c, n in zip(CATEGORIES, counts[:3]) if n >= 2]
        outcome = winners[0] if winners else 'unresolved'
        if row['majority_outcome'] != outcome:
            raise ValueError('saved majority does not match vote counts')
        outcomes.append(outcome)
        missing_total += counts[3]
        if counts[3] == 0:
            complete.append(counts[:3])
            patterns[{1: 'unanimous', 2: 'two_to_one', 3: 'three_way_split'}[
                sum(n > 0 for n in counts[:3])]] += 1
        else:
            patterns['incomplete'] += 1
        if any(row[s + '_direction'] not in CATEGORIES for s in EXPERT_METHODS.values()):
            raise ValueError('invalid method direction')
    if not complete:
        raise ValueError('no complete pairs for kappa')
    observed = sum((sum(n*n for n in c) - 3) / 6 for c in complete) / len(complete)
    totals = [sum(c[j] for c in complete) for j in range(3)]
    expected = sum((n / (3 * len(complete)))**2 for n in totals)
    kappa = 1.0 if expected == observed == 1.0 else (observed-expected)/(1-expected)
    methods = []
    decisive = [i for i, v in enumerate(outcomes) if v in CATEGORIES[:2]]
    for name, slug in EXPERT_METHODS.items():
        direction = [r[slug + '_direction'] for r in rows]
        numerator = sum(direction[i] == outcomes[i] for i in decisive)
        n = len(decisive)
        p = numerator/n if n else math.nan
        z = 1.959963984540054
        denom = 1 + z*z/n if n else math.nan
        center = (p + z*z/(2*n))/denom if n else math.nan
        half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/denom if n else math.nan
        ties = direction.count('tie')
        methods.append(dict(method=name, total_pairs=240, decisive_expert_pairs=n,
                            numerator=numerator, denominator=n, agreement=p,
                            wilson_ci95_low=center-half, wilson_ci95_high=center+half,
                            method_ties=ties, direction_coverage_numerator=240-ties,
                            direction_coverage_denominator=240, direction_coverage=(240-ties)/240,
                            expert_tie_pairs_excluded=outcomes.count('tie'),
                            unresolved_pairs_excluded=outcomes.count('unresolved')))
    return dict(total_pairs=240, valid_judgments=720-missing_total,
                missing_judgments=missing_total, majority_outcome_counts=dict(Counter(outcomes)),
                consensus_pattern_counts=dict(patterns),
                fleiss_kappa_complete_pairs_only=dict(pairs=len(complete), raters_per_pair=3,
                    observed_agreement=observed, expected_agreement=expected, kappa=kappa),
                method_results=methods,
                scope='primary agreement and Wilson intervals; no expert paired/sensitivity inference')


def space_metrics(model_ids, states, scores, replicates=0, seed=20260812):
    """All four label regimes; failures always excluded; paired Holm families separate."""
    ids = np.asarray(model_ids, dtype=str)
    if ids.ndim != 1 or not len(ids) or len(set(ids)) != len(ids) or any(not x for x in ids):
        raise ValueError('nonempty unique IDs required')
    if len(states) != len(ids) or tuple(scores) != METHODS or replicates < 0:
        raise ValueError('invalid states, eight-method order, or replicate count')
    for s in scores.values():
        _arrays(np.zeros(len(ids), dtype=int), s)
    if replicates:
        result = analyze_arrays(ids, states, scores, replicates=replicates, seed=seed)
        pairwise = result['all_pairwise_differences']
        for regime in REGIMES:
            for metric in METRICS:
                rows = [r for r in pairwise if r['regime'] == regime and r['metric'] == metric]
                for row, p in zip(rows, holm_adjust([r['raw_p_value'] for r in rows])):
                    row['holm_p_value'] = float(p)
        return result
    rows = []
    for regime in REGIMES:
        mask, y = labels_for_regime(states, regime)
        for method, scores_ in scores.items():
            s = np.asarray(scores_, dtype=float)[mask]
            for metric in METRICS:
                rows.append(dict(regime=regime, n=len(y), positive_count=int(y.sum()),
                                 negative_count=int(len(y)-y.sum()), method=method,
                                 metric=metric, estimate=_metric_value(metric, ids[mask], y, s)))
    return dict(method_metrics=rows, scope='point estimates only; no bootstrap inference')


def main():
    import argparse
    import csv
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    space = sub.add_parser('space')
    space.add_argument('--labels', type=Path, required=True, help='corrected model JSONL ledger')
    space.add_argument('--holdout', type=Path, required=True, help='frozen ordered IDs, UTF-8 text')
    space.add_argument('--scores', type=Path, required=True, help='final corrected score parquet')
    space.add_argument('--replicates', type=int, default=0)
    expert = sub.add_parser('expert')
    expert.add_argument('--votes', type=Path, required=True, help='anonymous count CSV; requires permission')
    args = parser.parse_args()
    if args.command == 'expert':
        with args.votes.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
                raise ValueError('duplicate CSV columns')
            result = expert_counts(list(reader))
    else:
        import pandas as pd
        ids = args.holdout.read_text(encoding='utf-8-sig').splitlines()
        ledger = [json.loads(line) for line in args.labels.read_text(encoding='utf-8').splitlines() if line.strip()]
        if len(ids) != 4096 or ids != [r['model_id'] for r in ledger]:
            raise ValueError('require exact ordered 4096-model ledger/holdout match')
        if [r['model_ordinal'] for r in ledger] != list(range(4096)):
            raise ValueError('ledger ordinal mismatch')
        panel = pd.read_parquet(args.scores, columns=['model_id', *METHODS])
        if panel.model_id.isna().any() or panel.model_id.duplicated().any():
            raise ValueError('invalid score panel IDs')
        selected = panel.set_index('model_id').loc[ids]
        result = space_metrics(ids, [r['state'] for r in ledger],
                               {m: selected[m].to_numpy(float) for m in METHODS}, args.replicates)
    def clean(value):
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return None if isinstance(value, float) and not math.isfinite(value) else value
    print(json.dumps(clean(result), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
