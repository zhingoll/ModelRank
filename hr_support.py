"""Reproduce exact-Likes selection counts and matched-sample covariate balance.

python -B hr_support.py --before assets/hr/selection_before_likes.parquet \
    --pairs assets/hr/matched_pairs.parquet --output ../generated/hr_support

Before/after refer to the exact same-origin Likes restriction, after the
retain-first allocation. These tables do not estimate subsequent outcomes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

COVARIATES = ('log_downloads', 'log_likes', 'model_age_days', 'log_parameters', 'download_trend')
BEFORE_COLUMNS = ('pair_id', 'horizon', 'hr_month', 'hr_model_id', 'control_model_id',
                  'hr_log_likes', 'control_log_likes')


def support_tables(before, after):
    if list(before.columns) != list(BEFORE_COLUMNS):
        raise ValueError('Expected the seven documented pre-restriction fields')
    required = list(BEFORE_COLUMNS) + [side + '_' + c for side in ('hr', 'control')
                                      for c in COVARIATES if c != 'log_likes']
    for frame, columns in ((before, BEFORE_COLUMNS), (after, required)):
        if not set(columns) <= set(frame.columns):
            raise ValueError('Incomplete pair fields')
        if frame[list(columns)].isna().any().any() or not frame.pair_id.is_unique:
            raise ValueError('Missing fields or duplicate pair IDs')
        if set(frame.horizon) != {1, 3, 6}:
            raise ValueError('All three horizons are required')
        if frame.hr_model_id.eq(frame.control_model_id).any():
            raise ValueError('A model cannot be its own control')
    numeric = ['hr_log_likes', 'control_log_likes']
    if not np.isfinite(before[numeric].to_numpy(float)).all():
        raise ValueError('Nonfinite pre-restriction Likes')
    numeric = [side + '_' + c for side in ('hr', 'control') for c in COVARIATES]
    if not np.isfinite(after[numeric].to_numpy(float)).all():
        raise ValueError('Nonfinite matched covariates')
    selected = before.loc[before.hr_log_likes.eq(before.control_log_likes)]
    if set(selected.pair_id) != set(after.pair_id):
        raise ValueError('Final pairs differ from the exact-Likes subset')
    try:
        pd.testing.assert_frame_equal(
            selected.sort_values('pair_id').reset_index(drop=True),
            after[list(BEFORE_COLUMNS)].sort_values('pair_id').reset_index(drop=True),
            check_dtype=False, check_exact=True)
    except AssertionError as exc:
        raise ValueError('Matched pair identity or origin fields changed') from exc
    selection, monthly, balances = [], [], []
    for h in (1, 3, 6):
        b, a = before[before.horizon.eq(h)], after[after.horizon.eq(h)]
        selection.append(dict(horizon=h, before_pairs=len(b), after_pairs=len(a),
            retention=len(a) / len(b), before_distinct_hr=b.hr_model_id.nunique(),
            after_distinct_hr=a.hr_model_id.nunique(),
            before_positive_likes_pairs=int(b.hr_log_likes.gt(0).sum()),
            after_positive_likes_pairs=int(a.hr_log_likes.gt(0).sum())))
        for month, group in b.groupby('hr_month', sort=True):
            monthly.append(dict(horizon=h, origin_month=month, before=len(group),
                                after=int(a.hr_month.eq(month).sum())))
        for c in COVARIATES:
            left, right = a['hr_' + c].to_numpy(float), a['control_' + c].to_numpy(float)
            lm, rm = float(np.mean(left)), float(np.mean(right))
            pooled = math.sqrt(max(0., (float(np.var(left, ddof=1)) +
                                       float(np.var(right, ddof=1))) / 2.)) if len(a) > 1 else 0.
            smd = (lm - rm) / pooled if pooled > 0 else (
                0. if lm == rm else math.copysign(math.inf, lm - rm))
            balances.append(dict(horizon=h, covariate=c, pairs=len(a), hr_mean=lm,
                control_mean=rm, standardized_mean_difference=smd, absolute_smd=abs(smd),
                passes_0_10=bool(abs(smd) <= .10)))
    return {'selection.csv': pd.DataFrame(selection),
            'selection_monthly.csv': pd.DataFrame(monthly), 'balance.csv': pd.DataFrame(balances)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--pairs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    before = pd.read_parquet(args.before)
    pairs = pd.read_parquet(args.pairs)
    tables = support_tables(before, pairs)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, table in tables.items():
        table.to_csv(args.output / name, index=False, lineterminator='\n')
    report = {'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (args.before, args.pairs)},
              'before_pairs': len(before), 'after_pairs': len(pairs),
              'rows': {name: len(table) for name, table in tables.items()}}
    (args.output / 'inputs.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
