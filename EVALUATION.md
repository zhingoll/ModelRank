# ModelRank Evaluation Materials

This package provides inputs, analysis programs and results for expert-choice
agreement, Space deployment evaluation, future-reuse comparisons, and top-decile
overlap and boundary ties. Run the commands from this directory with Python 3.9 or later.

## Setup

Install the numerical, statistical and Parquet dependencies:

```bash
python -m pip install -r requirements.txt
```

## Expert-Choice Agreement

`data/expert/anonymous_analysis_input.csv` contains the 240 pairs used in the
primary analysis. Six comparator groups each contain 40 pairs, with ten pairs
per task category within each group. Each row contains aggregate vote counts,
the majority outcome, seven score directions, the assigned comparator, sampling
and final score relations, and the task category.

`item_1` and `item_2` identify the alternatives within a pair. A majority outcome
requires at least two of the three requested judgments. `tie` records a majority
judgment of no clear suitability advantage; `unresolved` records the absence of
a majority outcome. The primary cohort contains 137 decisive-majority pairs,
102 majority ties and one unresolved pair. `missing_judgments` records judgments
without a substantive label.

The score-direction columns use `item_1`, `item_2`, or `tie`.
`s3_direction` denotes ModelRank and `full_modelrank_direction` denotes MTPR.
The other columns identify cumulative derivative count, current derivative
count, Vanilla PageRank, Downloads and Likes. Output names `S3` and
`Full ModelRank` retain these same ModelRank and MTPR mappings.

`original240.csv` supplies the original cohort for sensitivity analysis.
`replacement_registry.json` maps its two replaced pair identifiers to the
primary cohort. The cohorts share 238 unchanged pairs. The exclusion
sensitivity uses those 238 pairs. The original and exclusion cohorts contain
139 and 137 decisive-majority pairs, respectively.

Compute agreement, Wilson intervals, complete-pair Fleiss' kappa, relation
strata, six paired comparisons with Holm correction, and score-tie sensitivities
for all three cohorts:

```bash
python -B expert.py --output ../generated/expert
```

The outputs have `candidate240`, `original240`, and `exclusion238` prefixes.
`candidate240` identifies the primary analysis; the other two identify
sensitivities. Each generated cohort has a pooled JSON summary and CSV tables
of paired comparisons, strata and tie treatments. Stored results are in
`results/expert/`. The primary and exclusion cohorts contain the same decisive
pairs and share the stored `candidate240_paired.csv` and
`candidate240_tie_sensitivity.csv` tables. Each cohort has its own stored
pooled summary and stratum table.

Primary agreement uses decisive expert choices and gives a tied score zero
credit. The sensitivities assign half credit to score ties or exclude them,
reporting the applicable denominator. Strata separately report expert support
for the higher ModelRank score, the opposite choice, expert ties and unresolved
pairs. Within each stratum, conditional support divides ModelRank-supported expert
choices by decisive expert choices for which ModelRank gives a non-tied
direction, with a 95% Wilson interval. Decisive expert choices with tied
ModelRank scores are reported separately in `mr_tie_decisive`. The paired tests
use exact two-sided McNemar tests and Holm correction across six comparators.
Paired and tie-sensitivity intervals use 10,000 pair resamples with seed
2026081701. These analyses describe the sampled difficult model pairs.

## Space Deployment Evaluation

`data/space/holdout_ids.txt` fixes the order of 4,096 models. `labels.jsonl`
contains model ordinals, identifiers and outcome states; `scores.parquet`
contains the eight corresponding scores. `S_C3_Q10` denotes ModelRank and
`Submitted Full ModelRank` denotes MTPR.

The labels comprise 34 positive, 4,031 negative, 24 undecidable and seven
collection-failure models. The primary analysis uses the 4,065 confirmed
positive or negative models. The
[association evidence guide](data/space/evidence/README.md) connects model
labels to Space associations, historical versions, source locations and
classification explanations. Its file table and five worked examples explain
how to inspect the evidence for a label.

Calculate AUROC, average precision and Top-1%/5%/10% lift for all eight
comparators under the three distinct label regimes:

```bash
python -B external.py space --labels data/space/labels.jsonl --holdout data/space/holdout_ids.txt --scores data/space/scores.parquet
```

Add confidence intervals and paired comparisons using 10,000 bootstrap
resamples with seed 20260812:

```bash
python -B external.py space --labels data/space/labels.jsonl --holdout data/space/holdout_ids.txt --scores data/space/scores.parquet --replicates 10000
```

Both commands print JSON. The bootstrap command produces 120 metric rows
and 105 ModelRank-reference contrasts.
Corresponding reported tables are in `results/space/`. Collection failures
are excluded. Undecidable cases are excluded, assigned negative or assigned
positive according to the regime. The primary `confirmed-only` regime uses
the confirmed population; the other two regimes assign undecidable cases
negative or positive. Holm correction covers seven ModelRank-reference
contrasts separately for each metric and regime.

## Top-Decile Overlap and Boundary Ties

`data/top_decile/2025-06.parquet` through `2025-11.parquet` contain model
identifiers, Downloads, ModelRank, cumulative derivative count, Vanilla
PageRank and future-reuse outcomes. Candidates have downloads strictly below
their origin month's P90. `populations.csv` records population sizes and
thresholds; `data/comparison_protocol.json` specifies outcome families and
inference settings shared with the method comparisons.

Outcomes cover the following three months. Repropagation outcomes also follow
the children for three months after their first-observed event and use June
through August origins. Other outcomes use all six origins.

Rebuild the two comparator top-decile sets, their intersections and Jaccard
overlap, and the boundary-tie counts. Recalculate ModelRank and comparator
outcomes under model-ID tie-breaking and uniform selection among models tied
at the selection boundary:

```bash
python -B top_decile.py --output ../generated/top_decile
```

Selection orders scores from highest to lowest, then model identifiers in
ascending order, and selects `ceil(0.1 * candidate_n)` models. The uniform
sensitivity computes the exact expected outcome for the available boundary
slots. AUROC uses the full candidate population and is unchanged by the
top-decile tie rule. The default boundary rule is exact score equality. The
additional sensitivity groups scores within the fixed `log1p` distance of
`1e-12` at the boundary:

```bash
python -B top_decile.py --boundary-rule near_log_1e12 --output ../generated/top_decile_near
```

Outputs include six selected-set files, overlap statistics, 324 lift rows,
342 monthly metric rows per tie rule, and 42 comparisons of 21 outcomes against
each of the two comparators. `compare.py` implements origin-month paired
inference, 95% t intervals, 10,000 deterministic resamples for directional
support, and Holm correction within each 21-outcome comparison family.

## Future-Reuse Reconstruction

The four-command reconstruction route in [README.md](README.md) rebuilds
model-level outcomes, scores and monthly evaluations before computing RQ2
contrasts. It uses the frozen populations and popularity values in
`assets/core/panel/`, the first-observed relation clock, the `FULL_EVENT`
exclusions for future events, and the monthly child metrics in
`assets/future_metrics/`. Scoring uses the `MAIN` analytical graphs. Exclusion
records are applied in their recorded scope and month.

Candidates have origin-month Downloads strictly below P90. The 21 outcomes
comprise three quantity, ten descendant-quality, four repropagation and four
adoption-breadth measures. `future_active_parent_binary_3m` uses AUROC; the other 20
use Top-10% lift. Repropagation uses three origin months with complete
follow-up; the remaining outcomes use six. These outcomes measure subsequent
direct reuse and its observed properties. Expert-choice agreement separately
measures task suitability in the sampled pairs.

`temporal_components.py` rebuilds 17 monthly states, including the history
before the six evaluation origins. `parameter_grid.py` evaluates the 29
configurations specified in `data/parameter_formulae.json` and
`results/table_sources/parameter_specs.csv`. Both consume the model-level
outcomes generated by `future_reuse.py`. `rq2_reconstruction.py` requires
overlapping method evaluations to agree exactly before combining them.
The combined grid contains 45 methods or configurations, 5,130 monthly
metric rows and 2,163 paired contrasts, and supplies six summary tables.

`compare.py` reads the statistical settings in `data/comparison_protocol.json`.
It applies paired origin-month t tests and 95% t intervals, Holm correction
across the 21 outcomes of each contrast, and 10,000 deterministic bootstrap
resamples for directional support. The material-difference thresholds are
0.01 for AUROC and 0.1 for lift; family-level decisions use the recorded
protocol. `rq2_summaries.py` provides the shorter saved-grid route to the same
summary tables.

The expert and top-decile commands require a new output directory for each
run so that existing results remain intact.
