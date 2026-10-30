# Derivation-relation evidence

The tables describe 2,253 distinct repository-level relations: 2,096 self-references and 157 non-self relations in cyclic components. The 22 case families organize connected non-self relations across analytical scopes and months.

## Files

| File | Contents and use |
|---|---|
| `cases.md` | Explanations of all 22 non-self case families, relation lists, monthly component sizes, and the shared explanation for self-references. |
| `relations.csv` | Child and declared-parent identifiers, case family, source observations, exclusion months by scope, reason, and applied action for each relation. |
| `observations.csv` | Links each relation to a saved declaration record and its analytical source month. |
| `declarations.jsonl` | Repository identifiers, original `base_model:` tags, and the original `baseModels` field where present, with source-file row locators. |
| `sources.csv` | Snapshot filenames, dataset location, analytical source months, and source date labels. |
| `monthly_structures.json` | Complete node and relation sets for the 53 scope-specific structure variants and their applicable months. |
| `historical_sources.csv` | Fixed-revision public URLs for the 100 historical files used in the case explanations, grouped by case family. |

## Tracing a relation

Find its `relation_id` in `relations.csv`. Follow that ID in `observations.csv`, then use `declaration_id` to locate the corresponding record in `declarations.jsonl`. The declaration record identifies the source file through `source_id`; `sources.csv` supplies its filename and dataset location. Row ordinals are zero-based positions in the original Parquet file.

The declaration records contain the fields used to inspect parent declarations. `base_model_tags` preserves every original tag beginning with `base_model:` in the selected source row; other metadata tags are not part of this field. `baseModels`, when present, retains its saved value and representation.

Use `case_family` to find the explanation in `cases.md`. For non-self relations, `monthly_structures.json` identifies the exact node and relation set in each affected scope and month. `historical_sources.csv` supplies version-specific document locations where historical files were available.

## Reading the scopes and dates

`MAIN` denotes the main analytical panel, `FULL_EVENT` the full-event scope, and `SPACE` the Space validation scope. These populations overlap; their relation counts should not be added to obtain a distinct total.

Relations are represented as child to declared parent. A case family groups relations across months; its full relation list need not occur as one cyclic component in every month. The structure records show the corresponding monthly components.

Source months and date labels identify the saved analytical inputs. They are not independently certified declaration dates. Exclusion months identify when a relation was excluded from the analytical graph of the specified scope. The original declarations and model nodes are retained.
