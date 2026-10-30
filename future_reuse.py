"""Rebuild RQ2 future outcomes from fixed first events and monthly metric rows."""
import argparse
import gc
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from graph_inputs import GraphInputs, MONTHS
from reuse import METRIC_FAMILIES, build_reuse_inputs, build_reuse_outcomes, evaluate_candidate_month
from compare import validate_monthly_grid, compare_ordered_contrast

METHODS = ['S_C3_Q10', 'AllTime DerivCount', 'Current DerivCount', 'Vanilla PageRank',
           'Downloads', 'Likes', 'MTPR_time_safe_typed', 'Simplified_MTPR_time_safe_typed',
           'No-Propagation ModelRank', 'EventValue_time_safe_typed']


def event_ledger(graph):
    parts = []
    for month in MONTHS:
        blocked = graph.excluded[('FULL_EVENT', month)]
        visible = graph.pair.loc[graph.pair.entry_month.le(month)]
        if not blocked <= set(visible[['child_id', 'parent_id']].itertuples(index=False, name=None)):
            raise ValueError('FULL_EVENT exclusion is absent from its month')
        current = graph.pair.loc[graph.pair.entry_month.eq(month)].copy()
        retained = [(c, p) not in blocked for c, p in current[['child_id', 'parent_id']].itertuples(index=False, name=None)]
        parts.append(current.loc[retained])
    result = pd.concat(parts, ignore_index=True)
    if result.duplicated(['child_id', 'parent_id']).any():
        raise ValueError('Duplicate first pair event')
    result['relation'] = 'pair'
    return result


def quality_for_children(source, children):
    source = source.drop_duplicates('id', keep='last').copy()
    source['id'] = source['id'].astype(str)
    source = source.set_index('id')
    ordered = pd.Index([str(item) for item in children], name='model_id')
    selected = source.reindex(ordered)
    selected = selected[['downloads', 'likes']].apply(pd.to_numeric, errors='coerce').fillna(0.0)
    selected = selected.clip(lower=0.0).reset_index()
    if not selected.model_id.is_unique or not np.isfinite(selected[['downloads', 'likes']].to_numpy(float)).all():
        raise ValueError('Invalid normalized future metrics')
    return dict(zip(selected.model_id, zip(selected.downloads.astype(float), selected.likes.astype(float))))


def validate_quality(quality, by_month, months):
    if set(quality) != set(months):
        raise ValueError('Future quality months do not match the required window')
    for month in months:
        children = {c for _, c in by_month.get(month, [])}
        if set(quality[month]) != children:
            raise ValueError('Future quality child coverage differs from first-event children')
        values = np.asarray(list(quality[month].values()), dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError('Invalid future quality values')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scores', type=Path, help='Complete monthly score panels; defaults to bundled reference panels')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if output == root or root in output.parents:
        raise ValueError('Keep generated results outside the replication package')
    scores = (args.scores or root / 'assets/core/panel').resolve()
    bindings = {}

    def bind(path):
        path = Path(path).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if str(path) in bindings and bindings[str(path)] != digest:
            raise ValueError('Input changed during computation')
        bindings[str(path)] = digest
        return path

    for name in ('future_reuse.py', 'reuse.py', 'compare.py', 'graph_inputs.py', 'graph_clock.py'):
        bind(root / name)
    protocol = json.loads(bind(root / 'data/comparison_protocol.json').read_text(encoding='utf-8'))
    origins = protocol['origins']['three_month']
    reprop = protocol['origins']['repropagation']
    if origins != MONTHS[11:17] or reprop != origins[:3]:
        raise ValueError('Use the fixed six origins and three repropagation origins')
    if {m: f for f, metrics in protocol['metric_families'].items() for m in metrics} != METRIC_FAMILIES:
        raise ValueError('Outcome registry differs from the fixed protocol')
    ledger = pd.read_parquet(bind(root / 'assets/core/first_observed_edges.parquet'))
    graph = GraphInputs(ledger, bind(root / 'data/derivation_evidence/relations.csv'))
    events = event_ledger(graph)
    by_month, future_count = build_reuse_inputs(events, MONTHS)
    needed = sorted({m for origin in origins for m in MONTHS[MONTHS.index(origin) + 1:MONTHS.index(origin) + 4]})
    quality, source_audit = {}, []
    for month in needed:
        children = sorted({c for _, c in by_month.get(month, [])})
        raw = pd.read_parquet(bind(root / 'assets/future_metrics' / (month + '.parquet')))
        if set(raw.columns) != {'id', 'downloads', 'likes'}:
            raise ValueError('Expected the three-field metric source projection')
        quality[month] = quality_for_children(raw, children)
        source_audit.append(dict(month=month, source_rows=len(raw), requested_children=len(children),
                                 absent_children=len(set(children) - set(raw.id.astype(str)))))
    validate_quality(quality, by_month, needed)
    output.mkdir(parents=True, exist_ok=False)
    events.to_parquet(output / 'retained_pair_events.parquet', index=False)
    monthly, audit = [], []
    for month in origins:
        frame = pd.read_parquet(bind(scores / (month + '.parquet')))
        if frame.model_id.isna().any() or not frame.model_id.is_unique:
            raise ValueError('Invalid complete score population')
        values = frame[METHODS].to_numpy(float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError('Invalid monthly scores')
        threshold = float(frame.Downloads.quantile(.9))
        low = frame.loc[frame.Downloads.lt(threshold)].copy()
        outcomes = build_reuse_outcomes(low, month, quality, by_month, future_count, MONTHS)
        evaluated = evaluate_candidate_month(outcomes, month, METHODS, protocol)
        applicable = [m for m, f in METRIC_FAMILIES.items() if f != 'repropagation' or month in reprop]
        evaluated = evaluated[evaluated.metric.isin(applicable)].copy()
        evaluated['scheme'] = 'primary'
        if not np.isfinite(evaluated[['value', 'base_value']].to_numpy(float)).all():
            raise ValueError('Nonfinite evaluation result')
        monthly.append(evaluated)
        outcomes[['model_id'] + applicable].to_parquet(output / (month + '_outcomes.parquet'), index=False)
        audit.append(dict(month=month, population=len(frame), candidate_n=len(low),
                          download_p90=threshold, outcome_columns=len(applicable), metric_rows=len(evaluated)))
        print('FUTURE_REUSE', month, len(low), len(evaluated), flush=True)
        del outcomes, frame, low, evaluated
        gc.collect()
    monthly = pd.concat(monthly, ignore_index=True)
    validate_monthly_grid(monthly, METHODS, protocol)
    comparison = pd.concat([compare_ordered_contrast(monthly, METHODS[0], m, protocol) for m in METHODS[1:]], ignore_index=True)
    monthly.to_csv(output / 'monthly.csv', index=False)
    comparison.to_csv(output / 'comparisons.csv', index=False)
    for path, digest in bindings.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError('Input changed during computation')
    report = dict(inputs_sha256=bindings, event_rows=len(events), origins=audit,
                  quality_projection_audit=source_audit, monthly_rows=len(monthly), comparison_rows=len(comparison),
                  scope='Future outcomes and inference; scores consumed from the specified complete panels')
    (output / 'verification.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
