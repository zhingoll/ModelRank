"""Frozen arithmetic for the primary ModelRank score and its pair graph."""
import numpy as np
import pandas as pd
from scipy import sparse


def primary_score(ids, downloads, likes, current_edges, all_edges, vanilla=False):
    ids = list(map(str, ids))
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Unique complete node universe required')
    n = len(ids)
    index = pd.Index(ids)
    def positions(frame):
        pairs = frame[['child_id', 'parent_id']].drop_duplicates()
        a, b = index.get_indexer(pairs.child_id.astype(str)), index.get_indexer(pairs.parent_id.astype(str))
        keep = (a >= 0) & (b >= 0)
        return a[keep], b[keep]
    a, b = positions(all_edges)
    degree = np.bincount(a, minlength=n)
    matrix = sparse.csr_matrix((1 / degree[a], (b, a)), shape=(n, n))
    c, p = positions(current_edges)
    counts = np.bincount(c, minlength=n)
    event = np.bincount(p, weights=1 / counts[c], minlength=n)
    d, l = np.asarray(downloads, float), np.asarray(likes, float)
    if len(d) != n or len(l) != n or not np.isfinite(d).all() or not np.isfinite(l).all() or (d < 0).any() or (l < 0).any():
        raise ValueError('Finite nonnegative platform inputs required')
    q = .5 * np.log1p(d) + .5 * np.log1p(l)
    if vanilla:
        tau = np.full(n, 1 / n)
    else:
        tau = np.zeros(n)
        mass = 0.
        for share, values in ((.1, q), (.9, event)):
            if values.sum() > 0:
                tau += share * values / values.sum()
                mass += share
        tau = tau / mass if mass else np.full(n, 1 / n)
    rank = tau.copy()
    converged = False
    for iterations in range(1, 201):
        updated = .85 * (matrix @ rank + rank[degree == 0].sum() * tau) + .15 * tau
        updated /= updated.sum()
        change = float(abs(updated - rank).sum())
        rank = updated
        if change < 1e-8:
            converged = True
            break
    if not converged:
        raise ValueError('Independent solver reached iteration limit')
    return rank / rank.sum() * n, dict(iterations=iterations, converged=True,
        residual_change=change, event_mass=float(event.sum()), topology_pairs=len(a), event_pairs=len(c))
