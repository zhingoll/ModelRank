# ModelRank

Replication materials for *Beyond Download and Derivative Counts: Identifying Technical Starting Points for Artifact Reuse in AI Software Ecosystems*.

The data cover a 20-month Hugging Face panel from July 2024 to February 2026. The final cumulative analytical graph contains 721,364 models and 705,948 retained derivation edges.

ModelRank measures reuse influence through current first-observed derivation events, a platform popularity signal, and child-to-parent propagation. Comparators include Multi-Signal Temporal PageRank (MTPR), PageRank variants, derivative counts, Downloads, and Likes.

## Materials

| Location | Contents |
| --- | --- |
| `run.py`, `scoring.py`, `baselines.py`, `panel.py` | ModelRank scoring and comparator implementations |
| `compare.py`, `ecosystem.py`, `hr.py` | Method comparisons, ecosystem analyses, and subsequent Hidden Root outcomes |
| `future_reuse.py`, `temporal_components.py`, `parameter_grid.py`, `rq2_reconstruction.py` | Reconstruction of future-reuse outcomes, scores, monthly evaluations and RQ2 summaries |
| `descendants.py`, `initialization.py`, `hr_support.py`, `rq2_summaries.py` | Strict descendant features, initialization sensitivity, matching diagnostics and saved-grid summaries |
| `space_panel.py`, `graph_inputs.py`, `data/derivation_evidence/` | Space score reconstruction, scope-specific graph processing and relation-level evidence |
| `expert.py`, `external.py`, `top_decile.py` | Expert-choice agreement, Space deployment evaluation, and top-decile boundary-tie analyses |
| `tables.py`, `figures.py` | Export of saved result tables and generation of study figures |
| `data/`, `results/` | Analysis definitions, figure inputs, and paper-related results |
| `data/expert/` | Anonymous aggregate votes, method choices, and primary and sensitivity cohorts |
| `data/space/` | Ordered model sample, labels, scores, and association evidence |
| `data/top_decile/` | Monthly candidate populations, scores, and outcomes; statistical settings are in `data/comparison_protocol.json` |
| [EVALUATION.md](EVALUATION.md) | Evaluation definitions, statistical settings, outputs, and worked-example navigation |

## Data

Use the four data archives supplied with this version of the replication package. Extract them into `assets/` at the repository root, preserving their internal directory structure. [data/input_archives.json](data/input_archives.json) lists every archive member and its SHA-256 checksum, together with archive checksums and sizes.

| Archive | Contents |
| --- | --- |
| `core_inputs.zip` | `assets/core/`: 20 monthly panels with population, popularity and reference-score columns; first-observed relations; model metadata |
| `hr_inputs.zip` | `assets/hr/`: matched-pair observations and the selection-stage projection for Hidden Root analyses |
| `space_inputs.zip` | `assets/space/`: the Space cohort's relation clock and ten monthly metadata files |
| `future_metrics.zip` | `assets/future_metrics/`: eight monthly model-ID, Downloads and Likes projections for future-outcome reconstruction |

Public metadata snapshots provide derivation declarations. Parsing these declarations, deduplicating relations and constructing monthly graphs yields the observed relation graphs. The analysis programs retain the frozen model populations and apply the scope- and month-specific exclusions in `data/derivation_evidence/relations.csv` to obtain the analytical graphs. The evidence directory records each excluded relation and its processing basis. `MAIN` governs core scoring, `SPACE` governs the deployment cohort, and `FULL_EVENT` governs first-observed events used to measure future reuse. Each analysis reads its corresponding scope.

Space inputs are included in `data/space/`. The 4,096 models comprise 34 positive, 4,031 negative, 24 undecidable, and seven collection-failure cases. The primary evaluation uses the 4,065 confirmed positive or negative cases. In the score file, `S_C3_Q10` denotes ModelRank and `Submitted Full ModelRank` denotes MTPR. The [evidence guide](data/space/evidence/README.md) links labels to Space associations, historical versions, source locations, and classification explanations.

Expert agreement inputs are included in [data/expert/anonymous_analysis_input.csv](data/expert/anonymous_analysis_input.csv), with [field definitions](data/expert/FIELDS.md). The primary cohort contains 240 anonymous model pairs: 137 decisive expert majorities, 102 majority ties, and one unresolved pair. Fleiss' kappa uses the 239 pairs with all three judgments present. The original 240-pair and shared 238-pair cohorts support sensitivity analyses; their relationship is documented in [EVALUATION.md](EVALUATION.md).

### Model identifiers

GitHub push protection flagged strings within some model identifiers as potential access tokens and blocked the push. To avoid redistributing potentially sensitive strings, this replication package uses a distinct pseudonym for each of the eight source model identifiers containing such strings, consistently across files. All model and relation records are retained, with numerical values and the relative ordering of model identifiers unchanged. These pseudonyms support cross-file matching within the package and should not be used to locate the original repositories on Hugging Face.

## Usage

Use Python 3.9 or later. Run commands from the repository root. The examples place generated files in a sibling `generated/` directory. Use a new output path for each run; `descendants.py` takes an output file, while the other examples with `--output` take directories. Run each analysis as needed.

### 1. Install dependencies

Install the Python packages required for computation and plotting:

```bash
python -m pip install -r requirements.txt
```

### 2. Export result tables

Read the results in `results/` and export CSV views for paper tables, expert-cohort sensitivities, and top-decile comparisons to `../generated/tables/`.

```bash
python tables.py --output ../generated/tables
```

### 3. Generate figures

Read plotting inputs from `data/figures/`, generate six statistical figures, and include the study overview diagram in `../generated/figures/`.

```bash
python figures.py --output ../generated/figures
```

### 4. Compute monthly scores

Use the core data archive to compute 20 months of ModelRank and comparator scores. Write monthly score files and reference-score checks to `../generated/panel/`.

```bash
python panel.py --assets assets/core --output ../generated/panel
```

### 5. Analyze ecosystem roles and domains

Use the monthly scores and model information in the core data archive to compute role distributions, transitions, and cross-domain statistics. Write results to `../generated/ecosystem/`.

```bash
python ecosystem.py --assets assets/core --panel ../generated/panel --output ../generated/ecosystem
```

### 6. Compute method-comparison statistics

Use monthly evaluation values in `results/rq2/monthly_all.csv` for method and component comparisons. `--grid` also computes parameter-grid comparisons. Write results to `../generated/comparisons/` and check them against the reference results.

```bash
python compare.py --grid --output ../generated/comparisons
```

### 7. Analyze subsequent Hidden Root outcomes

Read matched-pair observations, compute subsequent outcome differences and statistical inference, and write results to `../generated/hr/`. `--verify` specifies the reference-result directory for comparison.

```bash
python hr.py --pairs assets/hr/matched_pairs.parquet --output ../generated/hr --verify results/hr
```

### 8. Evaluate Space deployments

Read the ordered model sample, labels, and method scores to compute evaluation metrics and method comparisons. `--replicates 10000` specifies 10,000 bootstrap resamples. Print statistics to the terminal as JSON.

```bash
python external.py space --labels data/space/labels.jsonl --holdout data/space/holdout_ids.txt --scores data/space/scores.parquet --replicates 10000
```

### 9. Compute expert agreement

Read aggregate votes and method choices to compute expert-majority agreement, Wilson intervals, Fleiss' kappa, relation strata, paired comparisons, and score-tie sensitivities. Export results for the primary 240-pair cohort, original 240-pair cohort, and shared 238-pair cohort to `../generated/expert/`. Primary agreement uses 137 decisive pairs; kappa uses 239 complete pairs.

```bash
python expert.py --output ../generated/expert
```

### 10. Analyze top-decile overlap and boundary ties

Use the six monthly candidate populations to reconstruct top-decile sets and their overlap. Compare ModelRank and the two graph-based comparators under model-ID tie-breaking and uniform selection among boundary-tied models. Export selected sets, overlap statistics, outcome metrics, and paired comparisons to `../generated/top_decile/`. [EVALUATION.md](EVALUATION.md) explains the 21 outcomes and inference settings.

```bash
python top_decile.py --output ../generated/top_decile
```

### 11. Reconstruct the full RQ2 evaluation

First reconstruct future outcomes from first-observed relations and monthly child metrics. Then recompute primary and component scores through their temporal state chains, and recompute the parameter configurations. Finally, combine the resulting monthly evaluations and regenerate comparisons and summaries. The first command also evaluates the bundled reference scores; the final combined results use the scores reconstructed by the second and third commands.

```bash
python future_reuse.py --output ../generated/future_reuse
python temporal_components.py --outcomes ../generated/future_reuse --output ../generated/temporal_components
python parameter_grid.py --outcomes ../generated/future_reuse --output ../generated/parameter_grid
python rq2_reconstruction.py --temporal ../generated/temporal_components --parameters ../generated/parameter_grid --output ../generated/rq2_reconstructed
```

For a shorter route that reads the saved monthly evaluations and regenerates the six summary tables, run:

```bash
python rq2_summaries.py --output ../generated/rq2_summaries
```

### 12. Reconstruct supporting analyses

Compute strict descendant features for the final core graph, the July initialization sensitivity, Hidden Root selection and balance statistics, and the separate ten-month Space score panel:

```bash
python descendants.py --assets assets/core --output ../generated/descendants.parquet
python initialization.py --output ../generated/initialization
python hr_support.py --before assets/hr/selection_before_likes.parquet --pairs assets/hr/matched_pairs.parquet --output ../generated/hr_support
python space_panel.py --assets assets/space --output ../generated/space_panel
```

The Space panel contains the full monthly cohort; the deployment evaluation in step 8 uses the fixed 4,096-model sample and its aligned score file. [EVALUATION.md](EVALUATION.md) describes the evaluation scopes and the additional boundary sensitivity.

Reference results are available under `results/`.

## Data Source

The study uses [hfmlsoc/hub_weekly_snapshots](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots), maintained by the Hugging Face ML & Society Team. Source-derived database contents are distributed under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).
