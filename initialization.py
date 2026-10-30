"""Reproduce July sensitivity to treating initial visible pairs as event input."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

from graph_inputs import GraphInputs, require_dag
from primary import primary_score

MONTH = '2024-07'
K = ['child_id', 'parent_id']


def validate_population(frame, scores=False):
    if (frame.empty or frame.model_id.isna().any() or not frame.model_id.is_unique
            or not all(isinstance(v, str) and v for v in frame.model_id)):
        raise ValueError('Unique nonempty model identifiers required')
    columns = ['Downloads', 'Likes'] + (['main', 'alternative'] if scores else [])
    values = frame[columns].to_numpy(float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Finite nonnegative population inputs required')
    if scores and not np.allclose(frame[['main', 'alternative']].sum(), len(frame), rtol=1e-10, atol=0):
        raise ValueError('Each score vector must sum to the population size')


def role(downloads, signal):
    d = np.asarray(downloads) >= np.quantile(downloads, .9)
    s = np.asarray(signal) >= np.quantile(signal, .9)
    return np.select([d & s, d & ~s, ~d & s], ['PR', 'PL', 'HR'], default='LT')


def summarize(frame):
    validate_population(frame, scores=True)
    a, b = frame['main'].to_numpy(), frame.alternative.to_numpy()
    ha, hb = a >= np.quantile(a, .9), b >= np.quantile(b, .9)
    return dict(nodes=len(frame), main_p90=float(np.quantile(a, .9)),
                alternative_p90=float(np.quantile(b, .9)),
                main_high=int(ha.sum()), alternative_high=int(hb.sum()),
                high_intersection=int((ha & hb).sum()), high_union=int((ha | hb).sum()),
                spearman=float(spearmanr(a, b).statistic),
                kendall=float(kendalltau(a, b, variant='b').statistic),
                reuse_high_jaccard=float((ha & hb).sum() / (ha | hb).sum()),
                role_changes=int((role(frame.Downloads, a) != role(frame.Downloads, b)).sum()),
                max_abs_score_difference=float(abs(a - b).max()),
                mean_abs_score_difference=float(abs(a - b).mean()))


def calculate(frame, edges):
    validate_population(frame)
    if (edges[K + ['entry_month']].isna().any().any() or edges.duplicated(K).any()
            or not edges.entry_month.eq(MONTH).all()
            or not edges.child_id.isin(frame.model_id).all()
            or not edges.parent_id.isin(frame.model_id).all()):
        raise ValueError('Unique July pairs within the complete population required')
    require_dag(edges)
    main, main_trace = primary_score(frame.model_id, frame.Downloads, frame.Likes, edges.iloc[:0], edges)
    alternative, alt_trace = primary_score(frame.model_id, frame.Downloads, frame.Likes, edges, edges)
    scores = frame[['model_id', 'Downloads', 'Likes']].copy()
    scores['main'], scores['alternative'] = main, alternative
    metrics = summarize(scores)
    quality_present = (.5 * np.log1p(frame.Downloads) + .5 * np.log1p(frame.Likes)).sum() > 0

    def input_mass(event_present):
        q, e = (.1 if quality_present else 0.), (.9 if event_present else 0.)
        return (q / (q + e), e / (q + e)) if q + e else (0., 0.)

    mq, me = input_mass(False)
    aq, ae = input_mass(alt_trace['event_mass'] > 0)
    summary = dict(month=MONTH, nodes=len(frame),
        initialization_pair_events_main=main_trace['event_pairs'],
        initialization_pair_events_sensitivity=alt_trace['event_pairs'],
        topology_pairs=main_trace['topology_pairs'],
        **{k: metrics[k] for k in ['max_abs_score_difference', 'mean_abs_score_difference',
                                  'spearman', 'kendall', 'reuse_high_jaccard', 'role_changes']},
        main_quality_input_mass=mq, main_event_input_mass=me,
        sensitivity_quality_input_mass=aq, sensitivity_event_input_mass=ae)
    return scores, summary, dict(main=main_trace, alternative=alt_trace, threshold_details=metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if output == root or root in output.parents:
        raise ValueError('Keep generated results outside the replication package')
    paths = ['assets/core/panel/2024-07.parquet', 'assets/core/first_observed_edges.parquet',
             'data/derivation_evidence/relations.csv', 'initialization.py',
             'primary.py', 'graph_inputs.py', 'graph_clock.py']
    digest = lambda p: hashlib.sha256((root / p).read_bytes()).hexdigest()
    bindings = {p: digest(p) for p in paths}
    frame = pd.read_parquet(root / paths[0], columns=['model_id', 'Downloads', 'Likes'])
    ledger = pd.read_parquet(root / paths[1])
    edges, current, _ = GraphInputs(ledger).month(frame.model_id, MONTH, first_empty=True)
    if not current.empty:
        raise ValueError('Main initialization requires empty event input')
    scores, summary, trace = calculate(frame, edges)
    if any(digest(p) != h for p, h in bindings.items()):
        raise ValueError('Input changed during computation')
    output.mkdir(parents=True, exist_ok=False)
    scores.to_parquet(output / 'scores.parquet', index=False)
    edges.to_parquet(output / 'edges.parquet', index=False)
    pd.DataFrame([summary]).to_csv(output / 'left_boundary_sensitivity.csv', index=False)
    report = dict(inputs_sha256=bindings, trace=trace,
        role_boundary='Each score vector uses its own linear P90, including ties',
        month=MONTH, later_month_scores_changed=False, parameter_search=False)
    (output / 'verification.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
