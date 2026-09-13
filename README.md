# ModelRank

Replication materials for *Beyond Download and Derivative Counts: Identifying Technical Starting Points for Artifact Reuse in AI Software Ecosystems*.

The data cover a 20-month Hugging Face panel from July 2024 to February 2026. The final cumulative analytical graph contains 721,364 models and 707,674 unique declared derivation edges.

ModelRank measures reuse influence through current first-observed derivation events, a platform popularity signal, and child-to-parent propagation. Comparators include Multi-Signal Temporal PageRank (MTPR), PageRank variants, derivative counts, Downloads, and Likes.

## Materials

| Location | Contents |
| --- | --- |
| `run.py`, `scoring.py`, `baselines.py`, `panel.py` | ModelRank scoring and comparator implementations |
| `compare.py`, `ecosystem.py`, `hr.py`, `external.py` | Method comparisons, ecosystem analyses, Hidden Root effects, and external-validation statistics |
| `tables.py`, `figures.py` | Export of saved result tables and generation of study figures |
| `data/`, `results/` | Analysis definitions, figure inputs, and paper-related results |
| `data/expert/` | Anonymous aggregate vote counts, comparator choices, and field definitions for expert agreement analyses |

## Data

Download the archives from the [data download page](https://github.com/zhingoll/ModelRank/releases/tag/r1-submitted-2026-09-10) and extract them into `assets/` at the repository root.

| Archive | Contents |
| --- | --- |
| `core_inputs.zip` | Monthly panels, first-observed relations, model metadata, and MTPR reference scores |
| `hr_inputs.zip` | Matched-pair observations for Hidden Root analyses |
| `space_inputs.zip` | The ordered 4,096-model sample, model-level labels, and scores for eight methods |

In the Space score file, `S_C3_Q10` denotes ModelRank; `Submitted Full ModelRank` is the retained column name for MTPR.

Expert agreement inputs are included in [data/expert/vote_counts.csv](data/expert/vote_counts.csv), with field definitions in [data/expert/FIELDS.md](data/expert/FIELDS.md). The file contains aggregate vote counts and comparator choices for 240 anonymous model pairs. Agreement with a decisive expert majority uses 139 pairs; Fleiss' kappa uses the 239 pairs with all three judgments present.

## Usage

Tested with Python 3.9.13. Run commands from the repository root. Commands with `--output` require a directory that does not already exist. Run each analysis as needed.

### 1. Install dependencies

Install the Python packages required for computation and plotting:

```bash
python -m pip install -r requirements.txt
```

### 2. Export result tables

Read the results in `results/` and export CSV views organized by paper table to `generated/tables/`.

```bash
python tables.py --output generated/tables
```

### 3. Generate figures

Read plotting inputs from `data/figures/`, generate six statistical figures, and include the study overview diagram in `generated/figures/`.

```bash
python figures.py --output generated/figures
```

### 4. Compute monthly scores

Use the core data archive to compute 20 months of ModelRank and comparator scores. Write monthly score files and reference-score checks to `generated/panel/`.

```bash
python panel.py --assets assets/core --output generated/panel
```

### 5. Analyze ecosystem roles and domains

Use the monthly scores and model information in the core data archive to compute role distributions, transitions, and cross-domain statistics. Write results to `generated/ecosystem/`.

```bash
python ecosystem.py --assets assets/core --output generated/ecosystem
```

### 6. Compute method-comparison statistics

Use monthly evaluation values in `results/rq2/monthly_all.csv` for method and component comparisons. `--grid` also computes parameter-grid comparisons. Write results to `generated/comparisons/` and check them against the reference results.

```bash
python compare.py --grid --output generated/comparisons
```

### 7. Analyze subsequent Hidden Root outcomes

Read matched-pair observations, compute subsequent outcome differences and statistical inference, and write results to `generated/hr/`. `--verify` specifies the reference-result directory for comparison.

```bash
python hr.py --pairs assets/hr/matched_pairs.parquet --output generated/hr --verify results/hr
```

### 8. Evaluate Space deployments

Read the ordered model sample, labels, and method scores to compute evaluation metrics and method comparisons. `--replicates 10000` specifies 10,000 bootstrap resamples. Print statistics to the terminal as JSON.

```bash
python external.py space --labels assets/space/labels.jsonl --holdout assets/space/holdout_ids.txt --scores assets/space/scores.parquet --replicates 10000
```

### 9. Compute expert agreement

Read aggregate votes and method choices for 240 anonymous model pairs. Compute agreement with the expert majority and Fleiss' kappa, and print statistics to the terminal as JSON. Agreement uses 139 pairs with a decisive majority; kappa uses the 239 pairs with all three judgments present.

```bash
python external.py expert --votes data/expert/vote_counts.csv
```

Reference results are available under `results/`.

## Data Source

The study uses [hfmlsoc/hub_weekly_snapshots](https://huggingface.co/datasets/hfmlsoc/hub_weekly_snapshots), maintained by the Hugging Face ML & Society Team. Source-derived database contents are distributed under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).
