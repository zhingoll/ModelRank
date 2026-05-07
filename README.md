# ModelRank Replication Package

This repository contains a minimal replication package for the paper
“Beyond Download and Derivative Counts: Identifying Technical Starting Points in Open Model Ecosystems”.

The package is organized around the final results reported in the paper rather than the full local project history. It includes:

- analysis scripts that directly support the reported results;
- result tables used by the main text and appendix;
- figure-generation scripts for the final paper figures;
- an environment specification for the `modelrank` Conda environment.

This repository does not include the paper source files (`.tex`) or internal review/debugging utilities.

## Repository layout

- `scripts/`
  - `rq1/` to `rq5/`: analysis scripts grouped by research question.
  - `figures/`: scripts that generate the final paper figures from the provided result files.
- `results/`
  - `rq1/` to `rq5/`: result files used by the corresponding research question.
  - `shared/`: shared result files required by multiple analyses or figure scripts.
- `releases/`
  - notes about large files that are not tracked in the Git repository and should be provided as GitHub Release assets.

## Environment

Create the environment with:

```bash
conda env create -f environment.yml
conda activate modelrank
```

## What is included

The package contains the result files that are directly referenced by the final main-text and appendix tables and figures. It is therefore designed to support replication of the reported results, not to preserve all intermediate exploratory analyses from the local working directory.

## Large files and processed inputs

Some scripts require large processed inputs that are not suitable for the Git repository itself.

- `results/shared/modelrank_scores.csv` is required by some figure scripts and downstream analyses.
- several analysis scripts also expect processed monthly inputs derived from the Hugging Face snapshot source.

These large files should be distributed as GitHub Release assets for the repository. See `releases/README.md`.

## Source data

The underlying source dataset is `hfmlsoc/hub_weekly_snapshots`, which is publicly available on Hugging Face. This repository focuses on the scripts and analytical outputs needed to reproduce the results reported in the paper.

## Notes

- Script names have been cleaned for public release where necessary to remove local version suffixes such as `v2` or `v3`.
- Internal audit, debugging, and manuscript-preparation utilities are intentionally excluded from this minimal package.
