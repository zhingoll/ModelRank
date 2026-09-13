"""Reproduce current ModelRank roles, transitions and cross-domain statistics."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROLES = ['Popular Root', 'Popular Leaf', 'Hidden Root', 'Long Tail']


def roles(frame):
    result = frame[['model_id', 'Downloads', 'S_C3_Q10']].copy()
    high_d = result.Downloads >= result.Downloads.quantile(.9)
    high_s = result.S_C3_Q10 >= result.S_C3_Q10.quantile(.9)
    result['role'] = np.select([high_d & high_s, high_d & ~high_s, ~high_d & high_s], ROLES[:3], default=ROLES[3])
    return result


def verify(result, path, key, method=False):
    expected = pd.read_csv(path, float_precision='round_trip')
    if method:
        expected = expected.loc[expected.method == 'S_C3_Q10']
    pd.testing.assert_frame_equal(result[expected.columns].sort_values(key).reset_index(drop=True),
        expected.sort_values(key).reset_index(drop=True), check_dtype=False, atol=1e-12, rtol=1e-10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assets, output = Path(args.assets), Path(args.output)
    root = Path(__file__).resolve().parent
    if output.exists():
        raise FileExistsError('Use a new output directory')
    output.mkdir(parents=True)
    previous = None
    distributions, transitions = [], []
    for month in pd.period_range('2024-07', '2026-02', freq='M').astype(str):
        frame = roles(pd.read_parquet(assets / 'panel' / (month + '.parquet')))
        (output / 'roles').mkdir(exist_ok=True)
        frame[['model_id','role']].to_parquet(output / 'roles' / (month + '.parquet'), index=False)
        for name, count in frame.role.value_counts().items():
            distributions.append({'version':'corrected', 'month':month, 'role':name, 'count':int(count),
                                  'n':len(frame), 'share':count/len(frame), 'download_p90':frame.Downloads.quantile(.9)})
        if previous is not None:
            joined = previous[['model_id','role']].merge(frame[['model_id','role']], on='model_id', validate='one_to_one', suffixes=('_origin','_future'))
            for left in ROLES:
                selected = joined.loc[joined.role_origin == left]
                for right in ROLES:
                    count = int((selected.role_future == right).sum())
                    transitions.append({'version':'corrected', 'month':month, 'origin_role':left,
                                        'future_role':right, 'count':count, 'row_total':len(selected),
                                        'rate':count/len(selected) if len(selected) else 0.0})
        previous = frame
    dist, trans = pd.DataFrame(distributions), pd.DataFrame(transitions)
    matrix = trans.groupby(['version','origin_role','future_role'], as_index=False)['count'].sum()
    matrix['row_total'] = matrix.groupby('origin_role')['count'].transform('sum')
    matrix['rate'] = matrix['count']/matrix.row_total
    for name, data, key in [('role_distribution', dist, ['month','role']),
                            ('transitions_monthly', trans, ['month','origin_role','future_role']),
                            ('transition_matrix', matrix, ['origin_role','future_role'])]:
        verify(data, root / 'results/roles' / (name + '.csv'), key)
        data.to_csv(output / (name + '.csv'), index=False)
    metadata = pd.read_parquet(assets / 'models.parquet').drop_duplicates('id',keep='last')
    tagged = frame.merge(metadata[['id','pipeline_tag']], left_on='model_id',right_on='id',how='left',validate='one_to_one')
    ledger = pd.read_parquet(assets / 'first_observed_edges.parquet')
    nodes = set(frame.model_id)
    parents = set(ledger.loc[ledger.entry_month.le('2026-02') & ledger.child_id.isin(nodes) & ledger.parent_id.isin(nodes), 'parent_id'])
    config = json.loads((root / 'data/domain_mapping.json').read_text())
    domain_rows, concentration, sizes = [], [], []
    for mapping in ['submitted','crossmodal_reassigned']:
        tagged['domain'] = tagged.pipeline_tag.fillna('').map(config[mapping])
        for domain, group in tagged.dropna(subset=['domain']).groupby('domain',sort=True):
            common = {'method':'S_C3_Q10','mapping':mapping,'domain':domain,'domain_n':len(group)}
            for role in ROLES:
                count = int((group.role == role).sum())
                domain_rows.append({**common,'role':role,'count':count,'share':count/len(group)})
            signal = group.S_C3_Q10
            ordered, total, n = np.sort(signal.to_numpy(float)), float(signal.sum()), len(group)
            gini = 0.0 if total == 0 else 2*np.dot(np.arange(1,n+1),ordered)/(n*total)-(n+1)/n
            parent_count = int(group.model_id.isin(parents).sum())
            concentration.append({**common,'gini':gini,'top_10_models_share':float(signal.nlargest(10).sum()/total),
                'top_10_percent_share':float(signal.nlargest(math.ceil(.1*n)).sum()/total),
                'ever_parent_count':parent_count,'ever_parent_share':parent_count/n})
            sizes.extend({**common,'minimum_domain_size':minimum,'included':n>=minimum} for minimum in (0,5000,10000,25000))
    for name, records, key in [('domain_roles',domain_rows,['mapping','domain','role']),
                               ('domain_concentration',concentration,['mapping','domain']),
                               ('domain_size_sensitivity',sizes,['mapping','domain','minimum_domain_size'])]:
        data = pd.DataFrame(records)
        verify(data, root / 'results/rq5' / (name + '.csv'), key, method=True)
        data.to_csv(output / (name + '.csv'), index=False)
    print('20 monthly role assignments; 6 summary tables match frozen current-ModelRank references.')


if __name__ == '__main__':
    main()
