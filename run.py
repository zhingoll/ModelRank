"""Compute one month's ModelRank from frozen metrics and first-observed pairs."""
import argparse
import csv
import math
from pathlib import Path

import numpy as np

from scoring import ScoreConfig, score_month


def compute(metrics, relations, month, first_month='2024-07'):
    ids = [str(r['model_id']) for r in metrics]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError('Metrics must contain each model exactly once')
    popularity = {}
    for row in metrics:
        downloads, likes = float(row['downloads']), float(row['likes'])
        if not all(math.isfinite(v) and v >= 0 for v in (downloads, likes)):
            raise ValueError('Downloads and likes must be finite and nonnegative')
        # Keep NumPy arithmetic identical to the authoritative scoring path.
        popularity[str(row['model_id'])] = .5 * np.log1p(downloads) + .5 * np.log1p(likes)
    first = {}
    for row in relations:
        pair = (str(row['child_id']), str(row['parent_id']))
        entry = str(row['entry_month'])
        first[pair] = min(first.get(pair, entry), entry)
    topology = [(c, p, 'pair') for (c, p), entry in first.items() if entry <= month]
    current = [(c, p, 'pair') for (c, p), entry in first.items()
               if entry == month and month != first_month]
    config = ScoreConfig(name='ModelRank', quality_share=.1, event_share=.9,
                         child_quality=False, type_weight=False, parent_size=False,
                         damping=.85, beta=0.0, direct_blend=0.0,
                         tolerance=1e-8, max_iterations=200, mix_mode='separate')
    result = score_month(ids, topology, current, popularity, {}, {}, config)
    if result.trace.iterations >= config.max_iterations:
        raise ValueError('Iteration limit reached; inspect convergence before using output')
    return result.score_normalized


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metrics', required=True, help='CSV: model_id,downloads,likes')
    parser.add_argument('--relations', required=True, help='CSV: child_id,parent_id,entry_month')
    parser.add_argument('--month', required=True, help='YYYY-MM')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    import datetime
    parsed = datetime.datetime.strptime(args.month, '%Y-%m')
    if parsed.strftime('%Y-%m') != args.month or args.month < '2024-07':
        raise ValueError('Use a month on or after 2024-07 in YYYY-MM format')
    scores = compute(read_csv(args.metrics), read_csv(args.relations), args.month)
    # Do not silently overwrite a researcher's existing result.
    with Path(args.output).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model_id', 'ModelRank'])
        writer.writerows(sorted(scores.items()))


if __name__ == '__main__':
    main()
