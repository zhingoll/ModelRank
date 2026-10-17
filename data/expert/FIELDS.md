# Expert-Choice Analysis Fields

`anonymous_analysis_input.csv` contains the primary 240-pair cohort.
`original240.csv` contains the original cohort. `replacement_registry.json`
maps the two replaced pairs; the remaining 238 pairs are shared unchanged.
`item_1` and `item_2` identify the two alternatives within each pair.

| Field | Meaning |
| --- | --- |
| `pair_id` | Anonymous pair identifier |
| `votes_item_1`, `votes_item_2`, `votes_tie` | Numbers of judgments choosing each alternative or a tie |
| `missing_judgments` | Requested judgments without a substantive label; this count and the three vote counts sum to three |
| `majority_outcome` | Outcome receiving at least two votes; otherwise `unresolved` |
| `s3_direction` | ModelRank choice |
| `full_modelrank_direction` | MTPR choice, retaining the source column name |
| `alltime_derivcount_direction` | Cumulative derivative-count choice |
| `current_derivcount_direction` | Current derivative-count choice |
| `vanilla_pagerank_direction` | Vanilla PageRank choice |
| `downloads_direction`, `likes_direction` | Downloads and Likes choices |
| `assigned_comparator` | Comparator group used to sample the pair |
| `original_relation` | ModelRank-comparator score relationship at sampling |
| `final_relation` | ModelRank-comparator score relationship in the analysis scores |
| `task` | Task category used for stratified sampling |

Method directions are `item_1`, `item_2`, or `tie`. A direction selects the
higher-scoring model. A score tie and an expert majority tie are separate
observations; an expert tie means no clear suitability advantage.
The relation fields distinguish opposite ordering, comparator ties, and
same-direction ordering. There are six comparator groups of 40 pairs, each
with ten pairs per task category.

The primary cohort has 137 decisive expert majorities, 102 majority ties and
one unresolved pair. Agreement uses the 137 decisive pairs and gives score
ties zero credit. Sensitivities give half credit to score ties or exclude
them with their corresponding denominator. Fleiss' kappa uses 239 pairs with
all three substantive judgments. The original and shared cohorts provide
sensitivity comparisons, with 139 and 137 decisive pairs, respectively.

From the repository root:

```bash
python expert.py --output ../generated/expert
```

The command exports pooled JSON summaries and CSV tables for all three cohorts.
Output method names `S3` and `Full ModelRank` correspond to ModelRank and MTPR,
respectively. See [the evaluation guide](../../EVALUATION.md) for confidence
intervals, paired tests, relation strata and multiple-comparison families.
