"""Apply accepted monthly graph masks without changing frozen event clocks."""
import numpy as np
import pandas as pd

K = ['child_id','parent_id']


def project_type_clock(typed_clock):
    # ISO YYYY-MM sorts chronologically; stable first occurrence equals group min.
    return (typed_clock.sort_values('entry_month',kind='stable').drop_duplicates(K)
            [K+['entry_month']].sort_values(K).reset_index(drop=True))


def month_inputs(pair_clock, typed_clock, nodes, month, candidate=None, first_empty=False):
    nodes = list(nodes)
    if not nodes or len(set(nodes)) != len(nodes):
        raise ValueError('Unique nonempty node population required')
    for frame,keys in [(pair_clock,K),(typed_clock,K+['relation'])]:
        if frame[keys+['entry_month']].isna().any().any() or frame.duplicated(keys).any():
            raise ValueError('Invalid frozen clock')
    projected = project_type_clock(typed_clock)
    expected = pair_clock[K+['entry_month']].sort_values(K).reset_index(drop=True)
    if not projected.equals(expected):
        raise ValueError('Pair/type clock mismatch')
    original = pair_clock[pair_clock.entry_month.le(month)&pair_clock.child_id.isin(nodes)&pair_clock.parent_id.isin(nodes)].copy()
    if candidate is None:
        edges = original
    else:
        edges = candidate[K+['entry_month']].copy()
        if edges.isna().any().any() or edges.duplicated(K).any():
            raise ValueError('Invalid candidate edge')
        known = set(original[K+['entry_month']].itertuples(index=False,name=None))
        if not set(edges.itertuples(index=False,name=None)) <= known:
            raise ValueError('Candidate changes the clock or endpoints, or includes future edges')
    current = edges[edges.entry_month.eq(month)].copy()
    if first_empty:
        current = current.iloc[:0].copy()
    types = typed_clock[typed_clock.entry_month.eq(month)&typed_clock.child_id.isin(nodes)&typed_clock.parent_id.isin(nodes)].copy()
    active = set(edges[K].itertuples(index=False,name=None))
    keep = np.fromiter((p in active for p in types[K].itertuples(index=False,name=None)),bool,len(types))
    return edges.reset_index(drop=True),current.reset_index(drop=True),types.loc[keep].reset_index(drop=True)
