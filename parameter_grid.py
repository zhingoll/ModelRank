"""Rebuild the fixed parameter grid and its future-reuse evaluations."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from graph_inputs import GraphInputs, require_dag
from primary import primary_score
from scoring import ScoreConfig, score_month
from reuse import evaluate_candidate_month
from compare import compare_ordered_contrast, validate_monthly_grid

def compute(frame, edges, month, specs, cap_override=None):
    ids = pd.Index(frame.model_id)
    if not len(ids) or ids.hasnans or not ids.is_unique:
        raise ValueError('Invalid node universe')
    obs = frame[['Downloads', 'Likes']].to_numpy(float)
    if not np.isfinite(obs).all() or (obs < 0).any():
        raise ValueError('Invalid observations')
    e = edges[['child_id', 'parent_id', 'entry_month']].copy()
    if (e.isna().any().any() or e.duplicated(['child_id', 'parent_id']).any()
            or e.entry_month.gt(month).any()
            or not e.child_id.isin(ids).all() or not e.parent_id.isin(ids).all()):
        raise ValueError('Invalid origin graph')
    e = e.sort_values(['child_id', 'parent_id']).reset_index(drop=True)
    n = len(ids)
    current = e[e.entry_month.eq(month)]
    c, p = ids.get_indexer(current.child_id), ids.get_indexer(current.parent_id)
    counts = np.bincount(c, minlength=n)
    event = np.bincount(p, weights=1/counts[c], minlength=n)
    matrices, values, traces = {}, {}, []
    for name, spec in specs.items():
        memory = spec['graph_memory_months']
        if memory not in matrices:
            use = e if memory == 'all' else e[e.entry_month.ge(str(pd.Period(month, 'M')-int(memory)+1))]
            a, b = ids.get_indexer(use.child_id), ids.get_indexer(use.parent_id)
            degree = np.bincount(a, minlength=n)
            matrices[memory] = (csr_matrix((1/degree[a], (b, a)), shape=(n, n)), degree == 0, len(use))
        matrix, dangling, topology_count = matrices[memory]
        w, mix, cfg = spec['quality_weights'], spec['teleport_mixture'], spec['pagerank']
        quality = w['downloads']*np.log1p(obs[:, 0]) + w['likes']*np.log1p(obs[:, 1])
        tau, mass = np.zeros(n), 0.
        for share, channel in ((mix['direct_quality'], quality), (mix['current_event'], event)):
            total = channel.sum()
            if share > 0 and total > 0:
                tau += share * channel / total
                mass += share
        tau = tau/mass if mass else np.full(n, 1/n)
        rank = tau.copy()
        cap = cfg['max_iterations'] if cap_override is None else cap_override
        if not isinstance(cap, int) or cap < 1:
            raise ValueError('Invalid iteration cap')
        for iterations in range(1, cap+1):
            new = cfg['damping']*(matrix @ rank + rank[dangling].sum()*tau) + (1-cfg['damping'])*tau
            new /= new.sum()
            residual = float(np.abs(new-rank).sum())
            rank = new
            if residual < cfg['tolerance']:
                break
        result = rank / rank.sum() * n
        if not np.isfinite(result).all() or (result < 0).any() or not np.isclose(result.sum(), n):
            raise ValueError('Invalid score mass')
        values[name] = result
        traces.append(dict(month=month, method=name, nodes=n, current_edges=len(current),
            topology_edges=topology_count, iterations=iterations, residual=residual,
            tolerance=cfg['tolerance'], iteration_cap=cap, cap_reached=iterations == cap,
            converged=residual < cfg['tolerance']))
    return values, traces


def score_origin(frame, edges, month, specs):
    require_dag(edges)
    values, trace = compute(frame, edges, month, specs)
    if not all(t['converged'] for t in trace):
        raise ValueError('A parameter solve did not converge within the fixed cap')
    raw = pd.DataFrame(dict(model_id=frame.model_id, **values))
    aligned = raw.copy()
    current = edges.loc[edges.entry_month.eq(month)]
    anchor, _ = primary_score(frame.model_id, frame.Downloads, frame.Likes, current, edges)
    vanilla, _ = primary_score(frame.model_id, frame.Downloads, frame.Likes, current, edges, vanilla=True)
    ids = frame.model_id.tolist()
    q = dict(zip(ids, .5 * np.log1p(frame.Downloads) + .5 * np.log1p(frame.Likes)))
    events = [(c, p, 'pair') for c, p in current[['child_id', 'parent_id']].itertuples(index=False, name=None)]
    config = ScoreConfig('matched no propagation', .1, .9, child_quality=False,
                        type_weight=False, parent_size=False, damping=0, beta=0)
    no = score_month(ids, [], events, q, {}, {}, config)
    aligned['S_C3_Q10'] = anchor
    aligned['S_D_000'] = [no.score_normalized[i] for i in ids]
    aligned['AllTime DerivCount'] = frame.model_id.map(edges.parent_id.value_counts()).fillna(0).astype(int)
    aligned['Current DerivCount'] = frame.model_id.map(current.parent_id.value_counts()).fillna(0).astype(int)
    aligned['Vanilla PageRank'] = vanilla
    return raw, aligned, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--outcomes', type=Path, required=True, help='Output directory of future_reuse.py')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if output == root or root in output.parents:
        raise ValueError('Keep generated results outside the replication package')
    bindings = {}

    def bind(path):
        path = Path(path).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if str(path) in bindings and bindings[str(path)] != digest:
            raise ValueError('Input changed during computation')
        bindings[str(path)] = digest
        return path

    for name in ('parameter_grid.py', 'primary.py', 'scoring.py', 'graph_inputs.py', 'graph_clock.py', 'reuse.py', 'compare.py'):
        bind(root / name)
    specs = json.loads(bind(root / 'data/parameter_formulae.json').read_text(encoding='utf-8'))
    parameters = pd.read_csv(bind(root / 'results/table_sources/parameter_specs.csv'), float_precision='round_trip')
    protocol = json.loads(bind(root / 'data/comparison_protocol.json').read_text(encoding='utf-8'))
    if len(specs) != 29 or set(specs) != set(parameters.specification_id):
        raise ValueError('Expected the fixed 29-configuration grid')
    for row in parameters.itertuples():
        spec = specs[row.specification_id]
        assert spec['teleport_mixture'] == dict(direct_quality=row.q, current_event=1 - row.q)
        assert spec['quality_weights'] == dict(downloads=row.w_D, likes=row.w_L)
        assert spec['pagerank']['damping'] == row.d
        assert str(spec['graph_memory_months']) == str(row.memory_months)
        assert spec['pagerank']['max_iterations'] == 200 and spec['pagerank']['tolerance'] == 1e-8
    graph = GraphInputs(pd.read_parquet(bind(root / 'assets/core/first_observed_edges.parquet')),
                        bind(root / 'data/derivation_evidence/relations.csv'))
    baselines = ['AllTime DerivCount', 'Current DerivCount', 'Vanilla PageRank']
    methods = list(specs) + baselines
    output.mkdir(parents=True, exist_ok=False)
    all_trace, all_monthly = [], []
    for month in protocol['origins']['three_month']:
        frame = pd.read_parquet(bind(root / 'assets/core/panel' / (month + '.parquet')),
                                columns=['model_id', 'Downloads', 'Likes']).sort_values('model_id').reset_index(drop=True)
        edges, _, _ = graph.month(frame.model_id, month)
        raw, aligned, trace = score_origin(frame, edges, month, specs)
        raw.to_parquet(output / (month + '_raw.parquet'), index=False)
        aligned.to_parquet(output / (month + '_aligned.parquet'), index=False)
        all_trace.extend(trace)
        threshold = frame.Downloads.quantile(.9)
        low = aligned.loc[frame.Downloads.lt(threshold)].reset_index(drop=True)
        outcomes = pd.read_parquet(bind(args.outcomes / (month + '_outcomes.parquet')))
        if low.model_id.tolist() != outcomes.model_id.tolist():
            raise ValueError('Outcome and score populations differ')
        applicable = {family: names for family, names in protocol['metric_families'].items()
                      if family != 'repropagation' or month in protocol['origins']['repropagation']}
        metrics = [m for names in applicable.values() for m in names]
        if set(outcomes.columns) != {'model_id', *metrics}:
            raise ValueError('Outcome columns differ from the origin protocol')
        panel = pd.concat([low, outcomes[metrics]], axis=1)
        evaluated = evaluate_candidate_month(panel, month, methods, {**protocol, 'metric_families': applicable})
        evaluated['scheme'] = 'primary'
        all_monthly.append(evaluated)
        print('PARAMETER_GRID', month, len(frame), len(trace), len(evaluated), flush=True)
        del frame, edges, raw, aligned, low, outcomes, panel
        gc.collect()
    monthly = pd.concat(all_monthly, ignore_index=True)
    validate_monthly_grid(monthly, methods, protocol)
    comparisons = pd.concat([compare_ordered_contrast(monthly, method, baseline, protocol)
                              for method in specs for baseline in baselines], ignore_index=True)
    monthly.to_csv(output / 'monthly.csv', index=False)
    comparisons.to_csv(output / 'comparisons.csv', index=False)
    pd.DataFrame(all_trace).to_csv(output / 'solver_trace.csv', index=False)
    if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in bindings.items()):
        raise ValueError('Input changed during computation')
    report = dict(inputs_sha256=bindings, solves=len(all_trace), monthly_rows=len(monthly),
        comparison_rows=len(comparisons), all_converged=all(t['converged'] for t in all_trace),
        alignment='Anchor and zero-propagation configurations use the independently recomputed primary-method arithmetic')
    (output / 'verification.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

