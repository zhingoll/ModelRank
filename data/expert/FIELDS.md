# Expert Agreement Inputs

`vote_counts.csv` contains aggregate judgments for the 240 model pairs in the
R1 submitted study. Each row represents one anonymous pair; `item_1` and
`item_2` refer to its two alternatives.

| Field | Meaning |
| --- | --- |
| `pair_id` | Anonymous pair identifier |
| `votes_item_1`, `votes_item_2`, `votes_tie` | Numbers of judgments choosing each alternative or a tie |
| `missing_judgments` | Number of missing judgments out of three requested |
| `majority_outcome` | Outcome receiving at least two votes; otherwise `unresolved` |
| `s3_direction` | ModelRank choice |
| `full_modelrank_direction` | MTPR choice, retaining the source column name |
| `alltime_derivcount_direction` | Cumulative derivative-count choice |
| `current_derivcount_direction` | Current derivative-count choice |
| `vanilla_pagerank_direction` | Vanilla PageRank choice |
| `downloads_direction`, `likes_direction` | Downloads and Likes choices |

Method directions are `item_1`, `item_2`, or `tie`. Agreement is evaluated on
the 139 pairs with a decisive expert majority. A method tie does not count as
agreement with a decisive majority. Fleiss' kappa uses the 239 pairs with all
three judgments present.

From the repository root:

```bash
python external.py expert --votes data/expert/vote_counts.csv
```

The command prints agreement rates, Wilson intervals, direction coverage and
Fleiss' kappa as JSON. Output method names `S3` and `Full ModelRank` correspond
to ModelRank and MTPR, respectively.

CSV SHA-256: `19e18fc7806f5bcd038a7543eef72abb249e738d1332681a8b5e1f5ce3954f08`.
