"""Rebuild the frozen 20-month core score panel without the original workspace."""
import argparse
import gc
from pathlib import Path

import numpy as np
import pandas as pd

from baselines import direct_counts, mtpr_step, pagerank
from scoring import ScoreConfig, score_month

MONTHS = [str(m) for m in pd.period_range('2024-07', '2026-02', freq='M')]


def rebuild(assets, output, until='2026-02'):
    assets, output = Path(assets), Path(output)
    if until not in MONTHS:
        raise ValueError('End month is outside the frozen study')
    if output.exists():
        raise FileExistsError('Use a new output directory')
    ledger = pd.read_parquet(assets / 'first_observed_edges.parquet')
    ledger = ledger[['child_id', 'parent_id', 'relation', 'entry_month']].astype(str)
    pair = ledger.groupby(['child_id', 'parent_id'], as_index=False).entry_month.min()
    metadata = pd.read_parquet(assets / 'models.parquet').drop_duplicates('id', keep='last')
    params = {str(i): None if pd.isna(p) else float(p) for i, p in zip(metadata.id, metadata.params)}
    output.mkdir(parents=True)
    previous_mtpr, previous_temporal = {}, {}
    checks = []
    config = ScoreConfig('ModelRank', .1, .9, child_quality=False, type_weight=False,
                         parent_size=False, beta=0.0)
    for month in MONTHS[:MONTHS.index(until) + 1]:
        frame = pd.read_parquet(assets / 'panel' / (month + '.parquet')).sort_values('model_id')
        if frame.model_id.duplicated().any() or frame.empty:
            raise ValueError('Invalid frozen model population')
        ids = frame.model_id.astype(str).tolist()
        q = dict(zip(ids, .5 * np.log1p(frame.Downloads.to_numpy(float)) + .5 * np.log1p(frame.Likes.to_numpy(float))))
        topology = [(str(c), str(p), 'pair') for c, p in pair.loc[pair.entry_month.le(month), ['child_id', 'parent_id']].itertuples(index=False, name=None)]
        events = [] if month == MONTHS[0] else [(str(c), str(p), 'pair') for c, p in pair.loc[pair.entry_month.eq(month), ['child_id', 'parent_id']].itertuples(index=False, name=None)]
        typed = list(ledger.loc[ledger.entry_month.eq(month), ['child_id', 'parent_id', 'relation']].itertuples(index=False, name=None))
        result = score_month(ids, topology, events, q, {}, {}, config)
        values = np.array([result.score_normalized[i] for i in ids])
        reference = frame.S_C3_Q10.to_numpy(float)
        delta = float(np.max(np.abs(values - reference)))
        if not np.allclose(values, reference, rtol=1e-10, atol=1e-10):
            raise ValueError('ModelRank differs from frozen scores: ' + month)
        if result.trace.iterations >= config.max_iterations:
            raise ValueError('ModelRank iteration limit reached')
        previous_mtpr, mtpr = mtpr_step(ids, typed, q, params, previous_mtpr)
        vanilla, _ = pagerank(ids, topology)
        _, previous_temporal = pagerank(ids, typed, previous_temporal)
        cumulative, current = direct_counts(ids, topology), direct_counts(ids, events)
        table = pd.DataFrame({'model_id': ids, 'ModelRank': values,
            'MTPR': [mtpr[i] for i in ids],
            'Vanilla PageRank': [vanilla[i] * len(ids) for i in ids],
            'Temporal Vanilla PageRank': [previous_temporal[i] * len(ids) for i in ids],
            'Cumulative Derivative Count': [cumulative[i] for i in ids],
            'Current Derivative Count': [current[i] for i in ids],
            'Downloads': frame.Downloads.to_numpy(), 'Likes': frame.Likes.to_numpy()})
        mtpr_delta = None
        expected_mtpr = assets / 'mtpr_reference' / (month + '.parquet')
        if expected_mtpr.exists():
            expected = pd.read_parquet(expected_mtpr).sort_values('model_id')
            if expected.model_id.astype(str).tolist() != ids:
                raise ValueError('MTPR reference node mismatch')
            mtpr_delta = float(np.max(np.abs(table.MTPR.to_numpy() - expected.ModelRank.to_numpy())))
            if not np.allclose(table.MTPR, expected.ModelRank, rtol=1e-9, atol=1e-9):
                raise ValueError('MTPR differs from frozen scores: ' + month)
        table.to_parquet(output / (month + '.parquet'), index=False)
        checks.append({'month': month, 'nodes': len(ids), 'ModelRank_max_error': delta,
                       'MTPR_max_error': mtpr_delta})
        pd.DataFrame(checks).to_csv(output / 'reproduction.csv', index=False)
        print(month, len(ids), delta, mtpr_delta, flush=True)
        del table, frame, result, topology, events, typed, vanilla, cumulative, current
        gc.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--until', default='2026-02')
    args = parser.parse_args()
    rebuild(args.assets, args.output, args.until)
