"""Rebuild top-decile overlap and tie sensitivity from monthly evaluation inputs."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from external import auroc
from compare import compare_ordered_contrast

METHODS = ['S_C3_Q10', 'AllTime DerivCount', 'Vanilla PageRank']


def selection(ids, scores):
    ids, s = np.asarray(ids,str), np.asarray(scores,float)
    if not len(ids) or len(ids) != len(s) or len(set(ids)) != len(ids) or not np.isfinite(s).all():
        raise ValueError('Nonempty unique IDs and finite aligned scores are required')
    k = max(1, math.ceil(.1*len(ids)))
    idx = np.lexsort((ids,-s))[:k]
    cutoff = float(s[idx[-1]])
    high, tied = s > cutoff, s == cutoff
    slots = k-int(high.sum())
    return dict(idx=idx,high=high,tied=tied,k=k,cutoff=cutoff,
        boundary_ties=int(tied.sum()),boundary_slots=slots,boundary_partial=slots<int(tied.sum()))


def lift_values(y, selection):
    y = np.asarray(y,float)
    if len(y) != len(selection['high']) or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError('Finite nonnegative aligned outcomes are required')
    base = max(float(y.mean()),1e-9)
    actual = float(y[selection['idx']].mean()/base)
    expected = (y[selection['high']].sum()+selection['boundary_slots']*y[selection['tied']].mean())/selection['k']/base
    return actual, float(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path(__file__).resolve().parent/'data/top_decile')
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    protocol = json.loads((Path(__file__).resolve().parent/'data/comparison_protocol.json').read_text(encoding='utf-8'))
    origins = protocol['origins']['three_month']
    population = pd.read_csv(args.input/'populations.csv').set_index('month')
    if population.index.duplicated().any() or set(population.index) != set(origins):
        raise ValueError('Population metadata must cover each origin exactly once')
    args.output.mkdir(parents=True,exist_ok=False)
    overlaps, monthly, uniform, lifts = [], [], [], []
    for month in origins:
        frame = pd.read_parquet(args.input/(month+'.parquet'))
        applicable = [(metric,family) for family, metrics in protocol['metric_families'].items()
            if family != 'repropagation' or month in protocol['origins']['repropagation'] for metric in metrics]
        columns = ['model_id','Downloads']+METHODS+[m for m,_ in applicable]
        if set(frame.columns) != set(columns) or frame.isna().any().any():
            raise ValueError('Unexpected columns or missing inputs: '+month)
        threshold = float(population.loc[month,'download_p90'])
        if len(frame) != population.loc[month,'candidate_n'] or not frame.Downloads.lt(threshold).all():
            raise ValueError('Candidate population does not match its fixed low-download band')
        ids = frame.model_id.to_numpy(str)
        selections = {m:selection(ids,frame[m]) for m in METHODS}
        a,b = selections[METHODS[1]],selections[METHODS[2]]
        sa,sb = set(ids[a['idx']]),set(ids[b['idx']])
        overlaps.append(dict(month=month,candidate_n=len(frame),download_p90=threshold,k=a['k'],
            intersection=len(sa & sb),union=len(sa | sb),jaccard=len(sa & sb)/len(sa | sb),identical_sets=sa==sb,
            count_cutoff=a['cutoff'],vpr_cutoff=b['cutoff'],count_boundary_ties=a['boundary_ties'],
            vpr_boundary_ties=b['boundary_ties'],count_boundary_slots=a['boundary_slots'],
            vpr_boundary_slots=b['boundary_slots'],count_partial=a['boundary_partial'],vpr_partial=b['boundary_partial']))
        selected = pd.DataFrame({'model_id':sorted(sa | sb)})
        selected['selected_count'] = selected.model_id.isin(sa)
        selected['selected_vpr'] = selected.model_id.isin(sb)
        selected.to_csv(args.output/('selected_'+month+'.csv'),index=False)
        for metric,family in applicable:
            y = frame[metric].to_numpy(float)
            statistic = 'auc' if metric == 'future_active_parent_binary_3m' else 'lift'
            for method in METHODS:
                if statistic == 'auc':
                    actual = expected = auroc(y,frame[method].to_numpy(float))
                else:
                    actual,expected = lift_values(y,selections[method])
                    lifts.append(dict(month=month,method=method,metric=metric,recomputed_lift=actual,
                        boundary_expected_lift=expected,tie_rule_delta=expected-actual))
                row = dict(scheme='primary',month=month,metric=metric,family=family,statistic=statistic,
                    method=method,value=actual,candidate_n=len(frame),base_value=float(y.mean()))
                monthly.append(row)
                uniform.append({**row,'value':expected})
        print(month, len(frame), 'candidates; Jaccard',overlaps[-1]['jaccard'],flush=True)
    original,alternative = pd.DataFrame(monthly),pd.DataFrame(uniform)
    changes = []
    for method in METHODS[1:]:
        left = compare_ordered_contrast(original,METHODS[0],method,protocol)
        right = compare_ordered_contrast(alternative,METHODS[0],method,protocol)
        changes.append(left.merge(right,on=['candidate','baseline','metric'],suffixes=('_original','_uniform'),validate='one_to_one'))
    for name,frame in [('set_overlap',pd.DataFrame(overlaps)),('monthly_original',original),
                       ('monthly_uniform',alternative),('lift_and_boundary_sensitivity',pd.DataFrame(lifts)),
                       ('comparison_sensitivity',pd.concat(changes,ignore_index=True))]:
        frame.to_csv(args.output/(name+'.csv'),index=False)


if __name__ == '__main__':
    main()
