"""Recompute RQ2 summaries from monthly observations and fixed comparison plans.

Run from the repository root: python -B rq2_summaries.py --output ../generated/rq2_summaries
Counts summarize all 21 outcomes per comparator. Stability intervals contain
the anchor-connected grid values with the same four-part decision signature.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from compare import compare_ordered_contrast, summarize_families, validate_monthly_grid

ANCHOR = 'S_C3_Q10'
FAMILIES = ('quantity', 'descendant_quality', 'repropagation', 'adoption_breadth')
GRID_BASELINES = ('AllTime DerivCount', 'Current DerivCount', 'Vanilla PageRank')
PRIMARY_BASELINES = (*GRID_BASELINES, 'Downloads', 'Likes', 'MTPR_time_safe_typed',
                     'Simplified_MTPR_time_safe_typed', 'EventValue_time_safe_typed',
                     'No-Propagation ModelRank')
COMPONENTS = ('No child quality', 'No parent size', 'No type weight', 'No event injection',
              'No quality teleport', 'No temporal inheritance', 'No PageRank propagation')


def method_means(monthly, protocol):
    methods = sorted(monthly.method.unique())
    validate_monthly_grid(monthly, methods, protocol)
    mapping = {metric: family for family, metrics in protocol['metric_families'].items() for metric in metrics}
    statistic = np.where(monthly.metric.eq('future_active_parent_binary_3m'), 'auc', 'lift')
    if not monthly.family.eq(monthly.metric.map(mapping)).all() or not monthly.statistic.eq(statistic).all():
        raise ValueError('Metric family or statistic differs from the fixed protocol')
    if not np.isfinite(monthly[['value', 'base_value', 'candidate_n']].to_numpy(float)).all():
        raise ValueError('Nonfinite monthly observations')
    cells = monthly.groupby(['month', 'metric'])
    if cells.base_value.nunique().gt(1).any() or cells.candidate_n.nunique().gt(1).any():
        raise ValueError('Methods use different evaluation populations')
    return monthly.groupby(['family', 'metric', 'statistic', 'method'], sort=True).value.agg(['mean', 'count']).reset_index()


def validate_contrasts(table, pairs, protocol):
    metrics = {m for values in protocol['metric_families'].values() for m in values}
    expected = {(c, b, m) for c, b in pairs for m in metrics}
    keys = ['candidate', 'baseline', 'metric']
    if (table[keys].isna().any().any() or table.duplicated(keys).any()
            or set(table[keys].itertuples(index=False, name=None)) != expected):
        raise ValueError('Incomplete or unexpected comparison grid')
    if not table.decision.isin(['win', 'tie', 'loss']).all() or not table.holm_family_size.eq(21).all():
        raise ValueError('Invalid decision or Holm family size')


def primary_counts(table, protocol):
    validate_contrasts(table, [(ANCHOR, b) for b in PRIMARY_BASELINES], protocol)
    result = table.groupby(['baseline', 'decision']).size().unstack(fill_value=0)
    result = result.reindex(columns=['win', 'tie', 'loss'], fill_value=0).reset_index()
    result.columns.name = None
    return result


def family_results(monthly, reference, pairs, protocol):
    validate_contrasts(reference, pairs, protocol)
    parts = []
    keys = ['candidate', 'baseline', 'metric']
    for candidate, baseline in pairs:
        actual = compare_ordered_contrast(monthly, candidate, baseline, protocol)
        expected = reference[reference.candidate.eq(candidate) & reference.baseline.eq(baseline)]
        pd.testing.assert_frame_equal(actual[list(expected.columns)].sort_values(keys).reset_index(drop=True),
            expected.sort_values(keys).reset_index(drop=True), check_dtype=False, rtol=1e-10, atol=1e-12)
        parts.append(summarize_families(monthly, actual, candidate, baseline, protocol))
    return pd.concat(parts, ignore_index=True)


def continuous_anchor_interval(parameters, states, anchor):
    values, flags = list(map(float, parameters)), list(states)
    if (len(values) != len(flags) or anchor not in values or not np.isfinite(values).all()
            or len(set(values)) != len(values) or values != sorted(values)
            or not all(isinstance(v, (bool, np.bool_)) for v in flags)):
        raise ValueError('Expected a unique ordered finite grid with an aligned Boolean anchor state')
    left = right = values.index(float(anchor))
    target = flags[left]
    while left > 0 and flags[left - 1] == target:
        left -= 1
    while right + 1 < len(flags) and flags[right + 1] == target:
        right += 1
    return [values[left], values[right]]


def selection_signature(families, candidate):
    selected = families[families.candidate.eq(candidate)]
    keys = ['baseline', 'family']
    expected = {(b, f) for b in GRID_BASELINES for f in FAMILIES}
    if (selected.duplicated(keys).any() or set(selected[keys].itertuples(index=False, name=None)) != expected
            or not selected.family_positive_gate.map(lambda v: isinstance(v, (bool, np.bool_))).all()
            or not np.isfinite(selected[['family_material_index', 'family_ci_high']].to_numpy(float)).all()):
        raise ValueError('Expected all twelve unique finite family rows and Boolean gates')
    alltime = selected[selected.baseline.eq('AllTime DerivCount')]
    vanilla = selected[selected.baseline.eq('Vanilla PageRank')]
    guards = []
    for baseline in GRID_BASELINES[:2]:
        row = selected[selected.baseline.eq(baseline) & selected.family.eq('quantity')].iloc[0]
        guards.append(bool(row.family_material_index <= -1. and row.family_ci_high < 0.))
    return (bool(alltime.loc[~alltime.family.eq('quantity'), 'family_positive_gate'].any()),
            bool(vanilla.family_positive_gate.any()), *guards)


def stability_intervals(parameters, families):
    defaults = {'quality_share': ('q', .1), 'damping': ('d', .85),
                'download_weight': ('w_D', .5), 'graph_memory': ('memory_months', 10000.)}
    if parameters.specification_id.isna().any() or not parameters.specification_id.is_unique:
        raise ValueError('Invalid parameter identifiers')
    if set(parameters.specification_id) != set(families.candidate):
        raise ValueError('Parameter and family candidate grids differ')
    anchor_signature = selection_signature(families, ANCHOR)
    rows = []
    for dimension, (column, default) in defaults.items():
        members = parameters[parameters.analysis_dimensions.str.split('|').map(lambda values: dimension in values)].copy()
        members['parameter_numeric'] = members[column].map(lambda value: 10000. if str(value) == 'all' else float(value))
        members = members.sort_values('parameter_numeric', kind='mergesort')
        if members.loc[members.specification_id.eq(ANCHOR), 'parameter_numeric'].tolist() != [default]:
            raise ValueError('Parameter dimension is missing its fixed anchor')
        states = [selection_signature(families, c) == anchor_signature for c in members.specification_id]
        lower, upper = continuous_anchor_interval(members.parameter_numeric, states, default)
        display = lambda value: 'all' if dimension == 'graph_memory' and value == 10000. else float(value)
        rows.append(dict(dimension=dimension, anchor=display(default), stable_lower=display(lower),
                         stable_upper=display(upper), anchor_signature='|'.join(str(v).lower() for v in anchor_signature),
                         grid_states='|'.join(str(v).lower() for v in states)))
    return pd.DataFrame(rows)


def reproduce(root):
    paths = ['data/comparison_protocol.json', 'results/rq2/monthly_all.csv',
             'results/rq2/primary_comparisons_21.csv', 'results/rq2/mtpr_ablation_comparisons.csv',
             'results/rq2/grid_comparisons.csv', 'results/table_sources/parameter_specs.csv',
             'data/top_decile/populations.csv', 'compare.py', 'rq2_summaries.py']
    bindings = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}
    read = lambda p: pd.read_csv(root / p, float_precision='round_trip')
    protocol = json.loads((root / paths[0]).read_text())
    monthly, primary, components, grid, parameters, population = [read(p) for p in paths[1:7]]
    expected_methods = {ANCHOR, *PRIMARY_BASELINES, *COMPONENTS, *parameters.specification_id}
    if len(parameters) != 29 or len(expected_methods) != 45 or set(monthly.method) != expected_methods:
        raise ValueError('The fixed 29-configuration, 45-method grid is required')
    means = method_means(monthly, protocol)
    counts = primary_counts(primary, protocol)
    # Validate the primary decisions against the same monthly inputs before counting them.
    for baseline in PRIMARY_BASELINES:
        actual = compare_ordered_contrast(monthly, ANCHOR, baseline, protocol)
        expected = primary[primary.baseline.eq(baseline)]
        pd.testing.assert_frame_equal(actual[list(expected.columns)].sort_values('metric').reset_index(drop=True),
            expected.sort_values('metric').reset_index(drop=True), check_dtype=False, rtol=1e-10, atol=1e-12)
    component_families = family_results(monthly, components,
        [('MTPR_time_safe_typed', b) for b in COMPONENTS], protocol)
    grid_families = family_results(monthly, grid,
        [(c, b) for c in parameters.specification_id for b in GRID_BASELINES], protocol)
    gates = component_families.groupby('baseline').family_positive_gate.agg(['sum', 'count', 'all']).reset_index()
    if not gates['count'].eq(4).all():
        raise ValueError('Each component must retain all four families')
    if population.month.duplicated().any() or set(population.month) != set(protocol['origins']['three_month']):
        raise ValueError('Invalid origin population grid')
    if not np.isfinite(population[['candidate_n', 'download_p90']].to_numpy(float)).all():
        raise ValueError('Nonfinite population audit fields')
    for row in population.itertuples():
        if not monthly.loc[monthly.month.eq(row.month), 'candidate_n'].eq(row.candidate_n).all():
            raise ValueError('Population counts differ from monthly evaluation')
    population = population.sort_values('month').reset_index(drop=True)
    population['methods'] = len(expected_methods)
    tables = {'table_sources/rq2_method_means_long.csv': means,
              'table_sources/rq2_primary_counts.csv': counts,
              'table_sources/mtpr_component_all_family_gate.csv': gates,
              'rq2/grid_family_summaries.csv': grid_families,
              'rq2/stability_intervals.csv': stability_intervals(parameters, grid_families),
              'rq2/population_audit.csv': population}
    if any(hashlib.sha256((root / p).read_bytes()).hexdigest() != h for p, h in bindings.items()):
        raise ValueError('Input changed during computation')
    return tables, component_families, bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.output.resolve() == root or root in args.output.resolve().parents:
        raise ValueError('Keep generated summaries outside the replication package')
    tables, _, bindings = reproduce(root)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, frame in tables.items():
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False, lineterminator='\n')
    report = dict(inputs_sha256=bindings, outputs={n: len(f) for n, f in tables.items()},
                  scope='Summaries and paired inference from fixed monthly observations')
    (args.output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
