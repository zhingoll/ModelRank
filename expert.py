"""Recompute the fixed expert-pair evaluation from anonymous vote counts."""
import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from external import EXPERT_METHODS, expert_counts, holm_adjust

CATEGORIES = ('item_1', 'item_2', 'tie')
EXCEPTIONS = {'P036', 'P091'}


def wilson(wins, n):
    if not 0 <= wins <= n:
        raise ValueError('Invalid vote count')
    if not n:
        return math.nan, math.nan
    z = 1.959963984540054
    p, d = wins / n, 1 + z*z/n
    center = (p + z*z/(2*n)) / d
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return center-half, center+half


def bootstrap(values):
    a = list(map(float, values))
    if not a:
        return math.nan, math.nan
    rng = random.Random(2026081701)
    means = sorted(sum(a[rng.randrange(len(a))] for _ in a)/len(a) for _ in range(10000))
    return means[math.floor(.025*9999)], means[math.ceil(.975*9999)]


def relation(a, b):
    if a == b:
        return 'both_tie' if a == 'tie' else 'same_direction'
    return 'comparator_tie' if b == 'tie' else ('modelrank_tie' if a == 'tie' else 'opposite_order')


def validate(frame, original=False):
    base = ['pair_id', 'votes_item_1', 'votes_item_2', 'votes_tie',
            'missing_judgments', 'majority_outcome']
    base += [slug + '_direction' for slug in EXPERT_METHODS.values()]
    extra = ['assigned_comparator', 'original_relation', 'final_relation', 'task']
    if set(frame.columns) != set(base + extra) or frame.isna().any().any():
        raise ValueError('Unexpected fields or missing values')
    expected_ids = {f'P{i:03d}' for i in range(1, 241)}
    if not original:
        registry = json.loads((Path(__file__).resolve().parent/'data/expert/replacement_registry.json').read_text(encoding='utf-8'))
        new_ids = {r['new_pair_id'] for r in registry}
        if len(registry) != 2 or len(new_ids) != 2 or {r['replaces'] for r in registry} != EXCEPTIONS or new_ids & expected_ids:
            raise ValueError('Invalid fixed replacement registry')
        expected_ids = (expected_ids - EXCEPTIONS) | new_ids
    if set(frame.pair_id) != expected_ids or len(frame) != 240:
        raise ValueError('Expected the fixed 240 unique pairs for this cohort')
    pooled = expert_counts(frame[base].to_dict('records'))
    if (frame.groupby('assigned_comparator').size().to_dict()
            != {m: 40 for m in EXPERT_METHODS if m != 'S3'}):
        raise ValueError('Comparator allocation differs from the fixed design')
    cells = frame.groupby(['assigned_comparator', 'task']).size()
    if len(cells) != 24 or not cells.eq(10).all():
        raise ValueError('Expected four task cells per comparator, ten pairs each')
    for row in frame.to_dict('records'):
        expected = relation(row['s3_direction'], row[EXPERT_METHODS[row['assigned_comparator']]+'_direction'])
        if expected != row['final_relation']:
            raise ValueError('Final relation disagrees with the saved directions')
        if row['original_relation'] not in {'opposite_order', 's3_order_baseline_tie'}:
            raise ValueError('Unknown sampling relation')
    changed = frame[frame.original_relation.eq('s3_order_baseline_tie') & frame.final_relation.ne('comparator_tie')]
    if original and (set(changed.pair_id) != EXCEPTIONS or not changed.assigned_comparator.eq('Vanilla PageRank').all()
            or not changed.final_relation.eq('same_direction').all()):
        raise ValueError('The two fixed relation exceptions do not match')
    if not original and len(changed):
        raise ValueError('The repaired cohort must preserve the sampling relation')
    return pooled


def subset_counts(frame):
    records = frame.to_dict('records')
    outcomes = frame.majority_outcome.tolist()
    complete, patterns = [], Counter()
    missing = int(frame.missing_judgments.sum())
    for r in records:
        counts = [int(r['votes_'+c]) for c in CATEGORIES]
        if r['missing_judgments']:
            patterns['incomplete'] += 1
        else:
            complete.append(counts)
            patterns[{1: 'unanimous', 2: 'two_to_one', 3: 'three_way_split'}[sum(n > 0 for n in counts)]] += 1
    observed = sum((sum(n*n for n in c)-3)/6 for c in complete)/len(complete)
    totals = [sum(c[j] for c in complete) for j in range(3)]
    expected = sum((n/(3*len(complete)))**2 for n in totals)
    kappa = 1.0 if expected == observed == 1.0 else (observed-expected)/(1-expected)
    decisive = frame[frame.majority_outcome.isin(CATEGORIES[:2])]
    results = []
    for method, slug in EXPERT_METHODS.items():
        numerator = int(decisive[slug+'_direction'].eq(decisive.majority_outcome).sum())
        low, high = wilson(numerator, len(decisive))
        ties = int(frame[slug+'_direction'].eq('tie').sum())
        results.append(dict(method=method, total_pairs=len(frame), decisive_expert_pairs=len(decisive),
            numerator=numerator, denominator=len(decisive), agreement=numerator/len(decisive),
            wilson_ci95_low=low, wilson_ci95_high=high, method_ties=ties,
            direction_coverage_numerator=len(frame)-ties, direction_coverage_denominator=len(frame),
            direction_coverage=(len(frame)-ties)/len(frame), expert_tie_pairs_excluded=outcomes.count('tie'),
            unresolved_pairs_excluded=outcomes.count('unresolved')))
    return dict(total_pairs=len(frame), valid_judgments=3*len(frame)-missing, missing_judgments=missing,
        majority_outcome_counts=dict(Counter(outcomes)), consensus_pattern_counts=dict(patterns),
        fleiss_kappa_complete_pairs_only=dict(pairs=len(complete), raters_per_pair=3,
            observed_agreement=observed, expected_agreement=expected, kappa=kappa), method_results=results)


def inference(frame):
    d = frame[frame.majority_outcome.isin(CATEGORIES[:2])]
    a = d.s3_direction.eq(d.majority_outcome).to_numpy()
    pairs, sensitivities = [], []
    for method, slug in EXPERT_METHODS.items():
        dirs = d[slug+'_direction']
        b = dirs.eq(d.majority_outcome).to_numpy()
        for mode in ('method_tie_half', 'method_tie_excluded'):
            values = np.where(dirs.eq('tie'), .5, b.astype(float)) if mode.endswith('half') else b[dirs.ne('tie')].astype(float)
            low, high = bootstrap(values)
            sensitivities.append(dict(analysis=mode, method=method, numerator=float(values.sum()),
                denominator=len(values), agreement=float(values.mean()) if len(values) else math.nan,
                ci_low=low, ci_high=high))
        if method != 'S3':
            w, l = int((a & ~b).sum()), int((~a & b).sum())
            low, high = bootstrap(a.astype(float)-b.astype(float))
            pairs.append(dict(comparator=method, n=len(a), mr_only=w, comparator_only=l,
                both_correct=int((a & b).sum()), both_wrong=int((~a & ~b).sum()),
                difference=float(a.mean()-b.mean()), p_value=float(binomtest(w,w+l).pvalue) if w+l else 1.0,
                bootstrap_low=low, bootstrap_high=high))
    for row, p in zip(pairs, holm_adjust([r['p_value'] for r in pairs])):
        row['holm_p'] = float(p)
    return pairs, sensitivities


def strata(frame):
    rows = []
    for (comp, ori, final), g in frame.groupby(['assigned_comparator','original_relation','final_relation']):
        decisive = g.majority_outcome.isin(CATEGORIES[:2])
        mr = int((decisive & g.majority_outcome.eq(g.s3_direction)).sum())
        other = int((decisive & g.majority_outcome.ne(g.s3_direction)).sum())
        low, high = wilson(mr,mr+other)
        rows.append(dict(comparator=comp, original_relation=ori, final_relation=final,
            n=len(g), mr_supported=mr, opposite_to_mr=other,
            comparator_supported=int((decisive & g.majority_outcome.eq(g[EXPERT_METHODS[comp]+'_direction'])).sum()),
            expert_tie=int(g.majority_outcome.eq('tie').sum()), unresolved=int(g.majority_outcome.eq('unresolved').sum()),
            conditional_denominator=mr+other,
            conditional_support_rate=mr/(mr+other) if mr+other else math.nan,
            wilson_low=low, wilson_high=high))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path(__file__).resolve().parent/'data/expert/anonymous_analysis_input.csv')
    parser.add_argument('--original', type=Path, default=Path(__file__).resolve().parent/'data/expert/original240.csv')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    frame = pd.read_csv(args.input)
    original = pd.read_csv(args.original)
    validate(frame)
    validate(original, original=True)
    retained = original[~original.pair_id.isin(EXCEPTIONS)]
    shared = frame[frame.pair_id.isin(retained.pair_id)]
    if not shared.reset_index(drop=True).equals(retained.reset_index(drop=True)):
        raise ValueError('The 238 retained pairs and their order must be unchanged')
    registry = json.loads((Path(__file__).resolve().parent/'data/expert/replacement_registry.json').read_text(encoding='utf-8'))
    for row in registry:
        new = frame.set_index('pair_id').loc[row['new_pair_id']]
        old = original.set_index('pair_id').loc[row['replaces']]
        if new['task'] != old['task'] or new['task'] != row['task'] or new['assigned_comparator'] != old['assigned_comparator']:
            raise ValueError('Replacement task and comparator must match the original slot')
    args.output.mkdir(parents=True, exist_ok=False)
    for label, use in [('candidate240',frame), ('original240',original), ('exclusion238',retained)]:
        pooled = subset_counts(use)
        (args.output/(label+'_pooled.json')).write_text(json.dumps(pooled,indent=2,allow_nan=False), encoding='utf-8')
        pairs, ties = inference(use)
        pd.DataFrame(pairs).to_csv(args.output/(label+'_paired.csv'),index=False)
        pd.DataFrame(ties).to_csv(args.output/(label+'_tie_sensitivity.csv'),index=False)
        pd.DataFrame(strata(use)).to_csv(args.output/(label+'_strata.csv'),index=False)
    print('Completed: primary 240-pair analysis, original-240 and exclusion-238 sensitivities.')


if __name__ == '__main__':
    main()
