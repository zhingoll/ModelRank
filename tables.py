"""Render paper-labelled CSV views from frozen results, not raw experiments.

Run: python tables.py --output /new/directory
Uses only the Python standard library. Inputs are never modified. CSV views
retain full stored precision, so they are not facsimiles of typeset tables.
No score, matching, outcome, confidence interval or p-value is re-estimated.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
S3 = 'S_C3_Q10'
EXCLUDED_TAGS = (
    'multiple-choice any-to-any audio-text-to-text visual-document-retrieval '
    'time-series-forecasting image-to-3d image-text-to-image video-to-video '
    'graph-ml text-to-3d image-text-to-video tabular-classification other '
    'tabular-regression text-retrieval'
).split()


def csv_bytes(rows):
    if not rows:
        raise ValueError('A selected table view is empty')
    fields = list(rows[0])
    if any(set(row) != set(fields) for row in rows):
        raise ValueError('Inconsistent table columns')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def build_views(root=HERE):
    root = Path(root)
    views, sources = {}, {}

    def read(path):
        raw = (root / path).read_bytes()
        sources[path] = hashlib.sha256(raw).hexdigest()
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        rows = list(reader)
        if not rows or not reader.fieldnames or any(None in r for r in rows):
            raise ValueError('Invalid or empty CSV: ' + path)
        return rows

    def add(label, rows, note='Stored results; full precision retained.'):
        if label in views:
            raise ValueError('Duplicate view: ' + label)
        views[label] = {'rows': rows, 'note': note}

    def direct(label, path, **filters):
        rows = read(path)
        for key, values in filters.items():
            allowed = {values} if isinstance(values, str) else set(values)
            rows = [r for r in rows if r[key] in allowed]
        add(label, rows)

    def ts(name):
        return 'results/table_sources/' + name + '.csv'

    direct('deriv-types', ts('rq1_type_summary'))
    for name in ('structure_stats', 'growth', 'dangling'):
        direct('rq1-' + name, ts('rq1_' + name))
    direct('appendix-rq1-rawcount', 'results/rq1/rq1_raw_count_comparability.csv')
    direct('appendix-rq1-sizebias', 'results/rq1/rq1_parent_size_bias.csv')

    cells = {(r['design'], r['band']): r for r in read(ts('single_control_cells'))}
    tests = read(ts('single_control_tests'))
    if len(cells) != 13 or len(tests) != 52:
        raise ValueError('Expected 13 planned single-control bands and 52 tests')
    for design, label in [('download_only', 'rq2-download-control'),
                          ('count_only', 'rq2-rawcount-control')]:
        rows = []
        for test in tests:
            if test['design'] != design:
                continue
            cell = cells[(design, test['band'])]
            metric = test['metric']
            row = dict(test)
            row.update({k: cell[k] for k in ('n', 'n_hi', 'n_lo')})
            row.update(high_mean=cell[metric + '_hi_mean'],
                       low_mean=cell[metric + '_lo_mean'])
            rows.append(row)
        add(label, rows, 'BH per metric over 13 planned bands across both designs. '
            'Nonestimable p=1 is an adjustment placeholder, not an observed null.')
    direct('rq2-joint-control', ts('joint_control_39_cells'))
    for label, metrics in [('appendix-joint-desc', ('desc_count', 'desc_depth')),
                           ('appendix-joint-activity', ('active_months', 'type_diversity'))]:
        direct(label, ts('joint_control_39_bh'), metric=metrics)
        if len(views[label]['rows']) != 78:
            raise ValueError('Expected 39 joint cells per structural metric')
        views[label]['note'] = 'BH is separate for each of four outcomes; retain adverse cells.'

    means = read(ts('rq2_method_means_long'))
    for label, methods in [
        ('rq2-core-panel', (S3, 'AllTime DerivCount', 'Current DerivCount',
                            'Downloads', 'Likes', 'Vanilla PageRank')),
        ('rq2-formulation-panel', (S3, 'MTPR_time_safe_typed',
            'Simplified_MTPR_time_safe_typed', 'EventValue_time_safe_typed',
            'No-Propagation ModelRank')),
    ]:
        add(label, [r for r in means if r['method'] in methods],
            'Long-form method means for all 21 outcomes, including the core table outcomes. '
            'count is the number of eligible months, not models.')
    direct('rq2-core-comparisons', ts('rq2_primary_counts'))
    for label, baseline in [('mtpr', 'MTPR_time_safe_typed'),
                            ('simplified', 'Simplified_MTPR_time_safe_typed'),
                            ('cumulative', 'AllTime DerivCount'),
                            ('no-prop', 'No-Propagation ModelRank'),
                            ('vanilla', 'Vanilla PageRank')]:
        key = 'appendix-mr-' + label + '-21'
        direct(key, 'results/rq2/primary_comparisons_21.csv', baseline=baseline)
        if len(views[key]['rows']) != 21:
            raise ValueError('Expected all 21 comparator outcomes: ' + baseline)
        views[key]['note'] = 'Positive difference favors ModelRank; Holm family is this comparator\'s 21 outcomes.'
    direct('appendix-mtpr-component-summary', ts('mtpr_component_all_family_gate'))
    direct('appendix-construct-checks', ts('construct_counterexamples'))
    direct('construct-quantity-guard', 'results/rq2/grid_family_summaries.csv',
           candidate='S_Q_000', baseline='AllTime DerivCount', family='quantity')
    direct('appendix-parameter-grid', ts('parameter_specs'))
    direct('parameter-stable-results', 'results/rq2/stability_intervals.csv')
    direct('left-boundary-sensitivity', ts('left_boundary_sensitivity'))

    direct('rq2-spaces', 'results/space/method_metrics.csv')
    direct('space-reference-contrasts', 'results/space/reference_contrasts.csv')
    direct('space-all-pairs', 'results/space/all_pairwise_differences.csv')
    views['rq2-spaces']['note'] = 'All three regimes retained; the primary regime is not the whole file.'
    views['space-reference-contrasts']['note'] = 'Seven-reference correction family; do not combine with the 28-pair family.'
    views['space-all-pairs']['note'] = 'Separate all-28-pair correction family.'
    direct('rq2-expert', ts('expert_method_results'))
    for name in ('paired_comparisons', 'strata_results', 'sensitivity_results'):
        direct('expert-' + name, ts('expert_' + name))

    direct('rq3-characteristics', ts('role_characteristics_current'))
    direct('hr-deriv-types', ts('role_type_composition'), method=S3)
    direct('rq3-hr-examples', ts('hr_representative_cases'))
    lt = {r['metric']: r for r in read(ts('hr_exact_download_structure'))}
    pl = {r['metric']: r for r in read(ts('hr_pl_structure'))}
    if set(lt) != set(pl) or len(lt) != 5:
        raise ValueError('Structural comparison metrics do not match')
    add('rq3-structure-comparisons', [dict(metric=k, hr_median=lt[k]['hr_median'],
        lt_median=lt[k]['control_median'], lt_absolute_r=lt[k]['absolute_r'],
        pl_median=pl[k]['pl_median'], pl_absolute_r=pl[k]['absolute_r'],
        matched_pairs=lt[k]['matched_pairs'], pl_n=pl[k]['pl_n']) for k in lt],
        'February exact-download HR-LT comparison and unmatched HR-PL comparison; '
        'not the longitudinal covariate-matched analysis.')
    direct('rq3-monthly-matched-outcomes', 'results/hr/monthly_outcomes.csv', horizon='3')
    direct('rq3-matched-adjusted', 'results/hr/primary_effects.csv')
    direct('hr-earliest-origin-sensitivity', 'results/hr/earliest_origin_effects.csv')
    views['rq3-matched-adjusted']['note'] = 'Final same-origin-Likes restricted sample; all 12 outcomes retained. Restriction is post-diagnostic.'

    thresholds = read('results/roles/threshold_sensitivity_monthly.csv')
    add('rq3-threshold', [r for r in thresholds if r['month'] == '2026-02'])
    add('rq3-threshold-full-panel', thresholds,
        'Complete 120 monthly rows; includes nonestimable months.')
    summary = []
    for percentile in sorted({r['percentile'] for r in thresholds}, key=float):
        group = [r for r in thresholds if r['percentile'] == percentile]
        if len(group) != 20 or len({r['month'] for r in group}) != 20:
            raise ValueError('Expected 20 distinct months per threshold')
        row = {'percentile': percentile, 'months': len(group)}
        for key in ('pr_share', 'pl_share', 'hr_share', 'hr_n', 'absolute_rank_biserial'):
            values = [float(r[key]) for r in group if r[key] != '']
            if not values:
                raise ValueError('No estimable values: ' + key)
            for statistic, value in [('median', median(values)), ('min', min(values)), ('max', max(values))]:
                row[key + '_' + statistic] = value
            if key == 'absolute_rank_biserial':
                row['estimable_months'] = len(values)
        summary.append(row)
    add('appendix-rq3-threshold-monthly', summary,
        'Medians/ranges of saved monthly results. Shares are fractions; effects use estimable months only. No rank test rerun.')
    direct('appendix-rq3-p90-ties', 'results/roles/p90_tie_sensitivity.csv', month='2026-02')
    direct('rq4-transitions', 'results/roles/transition_matrix.csv')
    for label, filename in [('rq5-roles', 'domain_roles'),
                             ('rq5-concentration', 'domain_concentration')]:
        direct(label, 'results/rq5/' + filename + '.csv', method=S3)
        views[label]['note'] = 'Both submitted (primary taxonomy) and crossmodal_reassigned mappings retained.'
    roles = views['rq5-roles']['rows']
    taxonomy = []
    for row in views['rq5-concentration']['rows']:
        if row['domain'] not in ('CV', 'Multimodal'):
            continue
        group = {r['role']: float(r['share']) for r in roles
                 if (r['mapping'], r['domain']) == (row['mapping'], row['domain'])}
        taxonomy.append(dict(domain=row['domain'], mapping=row['mapping'],
            models=row['domain_n'], root_percent=100 * (group['Popular Root'] + group['Hidden Root']),
            hr_percent=100 * group['Hidden Root'], gini=row['gini'],
            top_ten_percent=100 * float(row['top_10_models_share'])))
    add('rq5-taxonomy-sensitivity', taxonomy,
        'Join of saved composition and concentration results, not a new domain analysis.')
    direct('rq5-domain-size-sensitivity', 'results/rq5/domain_size_sensitivity.csv')
    path = 'data/domain_mapping.json'
    raw = (root / path).read_bytes()
    sources[path] = hashlib.sha256(raw).hexdigest()
    mapping = json.loads(raw)
    rows = [dict(pipeline_tag=k, primary_domain=v,
                 alternative_domain=mapping['crossmodal_reassigned'][k], status='mapped')
            for k, v in sorted(mapping['submitted'].items())]
    rows.extend(dict(pipeline_tag=k, primary_domain='', alternative_domain='',
                     status='excluded_rare_tag') for k in EXCLUDED_TAGS)
    add('appendix-domain-map', rows, 'Unknown/missing tags are unmapped. '
        'Four crossmodal tags move from CV to Multimodal; 15 named rare tags remain excluded.')
    # Validate everything before the caller creates any output directory.
    for view in views.values():
        view['payload'] = csv_bytes(view['rows'])
    return views, sources


def render(output, root=HERE):
    output, root = Path(output).resolve(), Path(root).resolve()
    if output.exists():
        raise FileExistsError('Use a new output directory; existing files are never overwritten')
    if output == root or root in output.parents:
        raise ValueError('Keep generated views outside the replication package')
    views, sources = build_views(root)
    index = {'mode': 'saved-result rendering; NOT raw statistical recomputation',
             'precision': 'Full stored numeric precision; no typeset rounding or significance relabelling.',
             'sources_sha256': sources, 'views': {},
             'not_rendered': {
                 'network-comparison/ranking-positioning/fields/params/component-provenance':
                     'Conceptual, literature, schema or method tables; not empirical CSV results.',
                 'data-summary/data-quality':
                     'Only graph counts are covered. Collection totals, provenance, quality exclusions and platform-wide denominators require the frozen source inventory.',
             }}
    output.mkdir(parents=True, exist_ok=False)
    for label, view in views.items():
        name = label + '.csv'
        with (output / name).open('xb') as stream:
            stream.write(view['payload'])
        index['views'][label] = dict(file=name, rows=len(view['rows']), note=view['note'],
            sha256=hashlib.sha256(view['payload']).hexdigest())
    with (output / 'TABLES_INDEX.json').open('x', encoding='utf-8') as stream:
        json.dump(index, stream, indent=2)
        stream.write('\n')
    return index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New directory outside this package')
    parser.add_argument('--list', action='store_true', help='Validate and list views without writing')
    args = parser.parse_args()
    if args.list:
        views, _ = build_views()
        print('\n'.join(views))
    elif args.output:
        result = render(args.output)
        print('Rendered %d saved-result views; no experiments rerun.' % len(result['views']))
    else:
        parser.error('Specify --list or --output')


if __name__ == '__main__':
    main()
