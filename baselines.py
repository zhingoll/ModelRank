"""Core comparison methods; callers must supply each study's frozen graph scope."""
from collections import Counter

import numpy as np

from scoring import ScoreConfig, score_month


def _ids(model_ids):
    ids = sorted(str(i) for i in model_ids)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('A nonempty unique model population is required')
    return ids


def direct_counts(model_ids, edges):
    ids = _ids(model_ids)
    nodes = set(ids)
    # Relation labels must not count the same child twice for one parent.
    pairs = {(str(c), str(p)) for c, p, _ in edges if str(c) in nodes and str(p) in nodes}
    counts = Counter(p for c, p in pairs)
    return {i: counts[i] for i in ids}


def pagerank(model_ids, edges, previous=None):
    """Return vanilla and temporal PageRank probabilities for the supplied graph."""
    ids = _ids(model_ids)
    pairs = sorted({(str(c), str(p), 'pair') for c, p, _ in edges})
    uniform = dict.fromkeys(ids, 1.0)
    config = ScoreConfig('Vanilla PageRank', 1.0, 0.0, child_quality=False,
                         type_weight=False, parent_size=False, beta=0.0)
    result = score_month(ids, pairs, (), uniform, {}, {}, config)
    vanilla = dict(result.scores)
    temporal = dict(vanilla)
    if previous:
        values = np.array([max(0.0, float(previous.get(i, 0.0))) for i in ids])
        if not np.isfinite(values).all():
            raise ValueError('Previous PageRank must be finite')
        if values.sum() > 0:
            values /= float(values.sum())
            mixed = .85 * np.array([vanilla[i] for i in ids]) + .15 * values
            mixed /= float(mixed.sum())
            temporal = dict(zip(ids, map(float, mixed)))
    return vanilla, temporal


def mtpr_step(model_ids, current_typed_edges, popularity, parent_parameters, previous=None):
    """One frozen MTPR step on the monthly typed-event graph (not cumulative)."""
    ids = _ids(model_ids)
    if set(ids) - set(popularity):
        raise ValueError('Popularity inputs must cover the complete model population')
    config = ScoreConfig('MTPR', quality_share=1.0, event_share=.8,
                         child_quality=True, type_weight=True, parent_size=True,
                         damping=.85, beta=.15, direct_blend=.10,
                         alpha=.3, kappa=.5, parameter_backfill=66955779.0,
                         tolerance=1e-8, max_iterations=200, mix_mode='raw')
    edges = sorted({(str(c), str(p), str(r).lower()) for c, p, r in current_typed_edges})
    result = score_month(ids, edges, edges, popularity, parent_parameters, previous or {}, config)
    if result.trace.iterations >= config.max_iterations:
        raise ValueError('MTPR iteration limit reached; inspect convergence')
    # Return probabilities for inheritance and node-count-normalized paper scores.
    return dict(result.scores), dict(result.score_normalized)
