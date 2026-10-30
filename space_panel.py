"""Recompute the ten-month Space score panel from frozen scope inputs."""
import argparse
import gc
from pathlib import Path

import numpy as np
import pandas as pd

from baselines import mtpr_step, pagerank
from graph_clock import month_inputs
from graph_inputs import GraphInputs, K, RELATIONS, require_dag
from primary import primary_score

MONTHS = list(pd.period_range('2024-07', '2025-04', freq='M').astype(str))


class SpaceInputs(GraphInputs):
    def month(self, nodes, month, first_empty=False):
        if month not in MONTHS or first_empty:
            raise ValueError('Space requires its ten-month scope and nonempty first-month events')
        nodes = list(nodes)
        original = self.pair[self.pair.entry_month.le(month)
                             & self.pair.child_id.isin(nodes) & self.pair.parent_id.isin(nodes)]
        pairs = list(original[K].itertuples(index=False, name=None))
        excluded = self.excluded[('SPACE', month)]
        if not excluded <= set(pairs):
            raise ValueError('Recorded Space exclusion absent from monthly population')
        retained = original.loc[[pair not in excluded for pair in pairs]].copy()
        edges, current, typed = month_inputs(self.pair, self.typed, nodes, month, retained)
        require_dag(edges)
        return edges, current, typed


def step(raw, edges, current, typed, previous_full, previous_temporal):
    raw = raw.sort_values('model_id').reset_index(drop=True)
    if raw.empty or raw.model_id.isna().any() or raw.model_id.duplicated().any():
        raise ValueError('Space population must be nonempty and unique')
    ids = raw.model_id.tolist()
    if not all(isinstance(i, str) and i for i in ids):
        raise ValueError('Space model identifiers must be nonempty strings')
    popularity = raw[['downloads', 'likes']].to_numpy(float)
    if not np.isfinite(popularity).all() or (popularity < 0).any():
        raise ValueError('Invalid Space popularity metadata')
    q = dict(zip(ids, .5 * np.log1p(popularity).sum(axis=1)))
    params = dict(zip(ids, raw.params))
    events = list(typed[K + ['relation']].itertuples(index=False, name=None))
    # The Space protocol inherits normalized scores; MAIN inherits probabilities.
    inherited = {i: previous_full.get(i, 1 / len(ids)) for i in ids}
    _, full = mtpr_step(ids, events, q, params, inherited)
    topology = [(c, p, 'pair') for c, p in edges[K].itertuples(index=False, name=None)]
    pair_events = [(c, p, 'pair') for c, p in current[K].itertuples(index=False, name=None)]
    vanilla, temporal = pagerank(ids, topology,
                                {i: previous_temporal.get(i, 1 / len(ids)) for i in ids})
    values, _ = primary_score(ids, raw.downloads, raw.likes, current, edges)
    output = pd.DataFrame(dict(model_id=ids, S_C3_Q10=values))
    output['Submitted Full ModelRank'] = [full[i] for i in ids]
    output['Vanilla PageRank'] = [vanilla[i] for i in ids]
    output['Temporal Vanilla PageRank'] = [temporal[i] for i in ids]
    output['AllTime DerivCount'] = output.model_id.map(edges.parent_id.value_counts()).fillna(0)
    output['Current DerivCount'] = output.model_id.map(current.parent_id.value_counts()).fillna(0)
    output['Downloads'], output['Likes'] = popularity[:, 0], popularity[:, 1]
    if not np.isfinite(output.drop(columns='model_id').to_numpy(float)).all():
        raise ValueError('Nonfinite Space scores')
    return output, full, temporal


def rebuild(assets, output):
    assets, output = Path(assets), Path(output)
    if output.exists():
        raise FileExistsError('Use a new output directory')
    inputs = SpaceInputs(pd.read_parquet(assets / 'first_observed_edges.parquet'), RELATIONS)
    output.mkdir(parents=True)
    full, temporal, trace = {}, {}, []
    for month in MONTHS:
        raw = pd.read_parquet(assets / 'metadata' / (month + '.parquet')).sort_values('model_id')
        edges, current, typed = inputs.month(raw.model_id.tolist(), month)
        scores, full, temporal = step(raw, edges, current, typed, full, temporal)
        scores.to_parquet(output / (month + '.parquet'), index=False)
        trace.append(dict(month=month, nodes=len(raw), edges=len(edges),
                          pair_events=len(current), typed_events=len(typed)))
        pd.DataFrame(trace).to_csv(output / 'reproduction.csv', index=False)
        print(month, len(raw), len(edges), flush=True)
        del raw, edges, current, typed, scores
        gc.collect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rebuild(args.assets, args.output)
