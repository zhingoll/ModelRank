"""Compute strict descendant counts and maximum shortest-path depth."""
import argparse
from pathlib import Path

import pandas as pd

from graph_inputs import GraphInputs, K
from strict_descendants import child_adjacency, strict_descendants


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--month', default='2026-02')
    parser.add_argument('--verify', help='Optional frozen descendant reference parquet')
    args = parser.parse_args()
    assets, output = Path(args.assets), Path(args.output)
    if output.exists():
        raise FileExistsError('Use a new output path')
    ids = pd.read_parquet(assets / 'panel' / (args.month + '.parquet')).model_id.astype(str).sort_values().tolist()
    inputs = GraphInputs(pd.read_parquet(assets / 'first_observed_edges.parquet'))
    edges, _, _ = inputs.month(ids, args.month)
    children = child_adjacency(edges[K].itertuples(index=False, name=None), ids)
    records = [(node, *strict_descendants(children, node)) for node in ids]
    result = pd.DataFrame(records, columns=['model_id', 'desc_count', 'desc_depth'])
    if args.verify:
        expected = pd.read_parquet(args.verify).sort_values('model_id').reset_index(drop=True)
        pd.testing.assert_frame_equal(result, expected[result.columns], check_dtype=False, check_exact=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output, index=False)
    print('Strict descendants:', len(result), 'models;', len(edges), 'relations; reference',
          'PASS' if args.verify else 'not supplied', flush=True)


if __name__ == '__main__':
    main()
