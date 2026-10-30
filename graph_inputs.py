"""Construct the main analysis graph using scope-specific monthly exclusions."""
import json
from collections import defaultdict, deque
from pathlib import Path

import pandas as pd

from graph_clock import K, month_inputs, project_type_clock

MONTHS = list(pd.period_range('2024-07', '2026-02', freq='M').astype(str))
SCOPES = {'MAIN': set(MONTHS), 'FULL_EVENT': set(MONTHS), 'SPACE': set(MONTHS[:10])}
RELATIONS = Path(__file__).resolve().parent / 'data/derivation_evidence/relations.csv'


def require_dag(edges):
    children, indegree = defaultdict(list), defaultdict(int)
    for child, parent in edges[K].itertuples(index=False, name=None):
        children[parent].append(child)
        indegree[child] += 1
        indegree[parent] += 0
    queue = deque(node for node, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        parent = queue.popleft()
        visited += 1
        for child in children.get(parent, ()):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if visited != len(indegree):
        raise ValueError('Analysis graph contains a cycle; verify the monthly exclusion input')


class GraphInputs:
    def __init__(self, ledger, relations=RELATIONS):
        self.typed = ledger[K + ['relation', 'entry_month']].copy()
        if self.typed.isna().any().any() or self.typed.duplicated(K + ['relation']).any():
            raise ValueError('Invalid frozen typed clock')
        if not self.typed.entry_month.isin(MONTHS).all():
            raise ValueError('Frozen clock month outside study')
        if not all(isinstance(v, str) and v for v in self.typed.to_numpy().ravel()):
            raise ValueError('Nonempty string clock fields required')
        self.pair = project_type_clock(self.typed)
        records = pd.read_csv(relations, keep_default_na=False, dtype=str)
        if records.relation_id.duplicated().any() or records.duplicated(['child_id', 'declared_parent_id']).any():
            raise ValueError('Duplicate relation mask')
        self.excluded = defaultdict(set)
        for row in records.itertuples(index=False):
            scopes = json.loads(row.excluded_months_by_scope)
            if not isinstance(scopes, dict) or not set(scopes) <= set(SCOPES):
                raise ValueError('Unknown exclusion scope')
            for scope, months in scopes.items():
                if (not isinstance(months, list) or len(months) != len(set(months))
                        or not set(months) <= SCOPES[scope]):
                    raise ValueError('Invalid exclusion months')
                for month in months:
                    self.excluded[(scope, month)].add((row.child_id, row.declared_parent_id))

    def month(self, nodes, month, first_empty=False):
        if month not in MONTHS:
            raise ValueError('Month outside the frozen MAIN study')
        nodes = list(nodes)
        original = self.pair[self.pair.entry_month.le(month)
                             & self.pair.child_id.isin(nodes) & self.pair.parent_id.isin(nodes)]
        pairs = list(original[K].itertuples(index=False, name=None))
        excluded = self.excluded[('MAIN', month)]
        if not excluded <= set(pairs):
            raise ValueError('Recorded exclusion is absent from the current scope/month graph')
        retained = original.loc[[pair not in excluded for pair in pairs]].copy()
        edges, current, typed = month_inputs(self.pair, self.typed, nodes, month,
                                             candidate=retained, first_empty=first_empty)
        require_dag(edges)
        return edges, current, typed
