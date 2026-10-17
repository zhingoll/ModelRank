# ModelRank

Replication materials for *Beyond Download and Derivative Counts: Identifying Technical Starting Points for Artifact Reuse in AI Software Ecosystems*.

The data cover a 20-month Hugging Face panel from July 2024 to February 2026. The final cumulative analytical graph contains 721,364 models and 707,674 unique declared derivation edges.

ModelRank measures reuse influence through current first-observed derivation events, a platform popularity signal, and child-to-parent propagation. Comparators include Multi-Signal Temporal PageRank (MTPR), PageRank variants, derivative counts, Downloads, and Likes.

## Materials

| Location | Contents |
| --- | --- |
| `run.py`, `scoring.py`, `baselines.py`, `panel.py` | ModelRank scoring and comparator implementations |
| `compare.py`, `ecosystem.py`, `hr.py` | Method comparisons, ecosystem analyses, and subsequent Hidden Root outcomes |
| `expert.py`, `external.py`, `top_decile.py` | Expert-choice agreement, Space deployment evaluation, and top-decile boundary-tie analyses |
| `tables.py`, `figures.py` | Export of saved result tables and generation of study figures |
| `data/`, `results/` | Analysis definitions, figure inputs, and paper-related results |
| `data/expert/` | Anonymous aggregate votes, method choices, and primary and sensitivity cohorts |
| `data/space/` | Ordered model sample, labels, scores, and association evidence |
| `data/top_decile/` | Monthly candidate populations, scores, and outcomes; statistical settings are in `data/comparison_protocol.json` |
| [EVALUATION.md](EVALUATION.md) | Evaluation definitions, statistical settings, outputs, and worked-example navigation |

## Data

Download `core_inputs.zip` and `hr_inputs.zip` from the [data download page](https://github.com/zhingoll/ModelRank/releases/tag/r1-submitted-2026-09-10) and extract them into `assets/` at the repository root. They provide `assets/core/` and `assets/hr/`, respectively.

| Archive | Contents |
| --- | --- |
| `core_inputs.zip` | Monthly panels, first-observed relations, model metadata, and MTPR reference scores |
| `hr_inputs.zip` | Matched-pair observations for Hidden Root analyses |

Space inputs are included in `data/space/`. The 4,096 models comprise 34 positive, 4,031 negative, 24 undecidable, and seven collection-failure cases. The primary evaluation uses the 4,065 confirmed positive or negative cases. In the score file, `S_C3_Q10` denotes ModelRank and `Submitted Full ModelRank` denotes MTPR. The [evidence guide](data/space/evidence/README.md) links labels to Space associations, historical versions, source locations, and classification explanations.

Expert agreement inputs are included in [data/expert/anonymous_analysis_input.csv](data/expert/anonymous_analysis_input.csv), with [field definitions](data/expert/FIELDS.md). The primary cohort contains 240 anonymous model pairs: 137 decisive expert majorities, 102 majority ties, and one unresolved pair. Fleiss' kappa uses the 239 pairs with all three judgments present. The original 240-pair and shared 238-pair cohorts support sensitivity analyses; their relationship is documented in [EVALUATION.md](EVALUATION.md).

## Usage

Use Python 3.9 or later. Run commands from the repository root. The examples place generated files in a sibling `generated/` directory. Commands with `--output` require a directory that does not already exist. Run each analysis as needed.

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
python ecosystem.py --assets assets/core --output ../generated/ecosystem
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

Reference results are available under `results/`.

## Data Source

The study uses [hfmlsoc/hub_weekly_snapshots](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots), maintained by the Hugging Face ML & Society Team. Source-derived database contents are distributed under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).
