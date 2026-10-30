# Space association evidence

## Package files

Counts describe model records, association records, file locators or explanations, as specified in each row.

| File | Contents and use |
| --- | --- |
| `models.csv` | Labels and collection observations for 4,096 models; starting point for checking each model outcome. |
| `associations.csv` | 4,595 model-Space associations, with historical conditions, classifications and evidence origins. |
| `source_files.csv` | 11,565 version-pinned file locators covering 1,208 associations, for inspecting the historical source files. |
| `evidence_explanations.json` | 999 association-specific explanations with source operations and supporting file and line references. |
| `worked_examples.md` | Five examples illustrating application use, temporal exclusion and unresolved evidence. |
| `README.md` | Deployment criteria, field definitions and instructions for following the linked records. |

## Follow a label to its evidence

`models.csv` contains the analysis label and collection observations for each of the 4,096 evaluated models. Join `model_id` to `associations.csv` for the 4,595 model-Space associations. Join `association_ordinal` to `source_files.csv` for 11,565 historical file locators, and to `evidence_explanations.json` for 999 association-specific source explanations. `worked_examples.md` illustrates qualifying application use, temporal exclusion and unresolved historical evidence.

The source explanations identify the target model, Space, historical revision, relevant operations and supporting file locations. Other associations have criterion codes in `objective_basis_code`, including temporal exclusions, ownership conditions, provenance gaps and the worked application example. These fields allow a reader to follow the evidence used for a classification and identify the precise requirement left unresolved.

## Deployment criteria and model labels

The outcome window runs from June 1, 2025, through May 31, 2026, inclusive in UTC. A qualifying association first appears within this window; the Space is publicly accessible at audit, its owner differs from the model owner, and repository evidence connects the exact model to application use. Application-use evidence connects target selection and loading to subsequent inference, generation, evaluation or an application operation. A selectable target can qualify through an explicit application branch even when another model is the default.

A model is positive when at least one association qualifies. A negative label requires complete association auditing with no qualifying deployment. Unresolved evidence yields an undecidable label, and incomplete collection has a separate collection-failure label. An excluded association can therefore belong to a positive model supported by another association. The analysis labels here comprise 34 positive, 4,031 negative, 24 undecidable and seven collection-failure models.

A complete standalone target-model application can satisfy the source-use criterion when the Space configuration selects another application. The evidence records identify both paths and their execution prerequisites. A callback mismatch that blocks inference under the declared interface version leaves that source path unresolved.

## Read the tables

In `models.csv`, `model_state` is the analysis label. The `recorded_` fields describe the retained collection ledger; `enumeration_observation`, `collection_error_type`, `observation_utc`, `http_status` and `enumeration_url` describe the preserved query observation. A successful empty response and a transport error represent different collection outcomes. The analysis label combines the collection outcome with the reviewed association evidence, where associations are present.

In `associations.csv`, `first_present_sha` and `predecessor_sha`, with their timestamps, locate the association transition. `window_position`, `independent_owner` and the public-access fields record the other deployment criteria. `association_class` gives the association classification, while `model_state` matches the model table. `classification_origin` distinguishes retained classifications, author evidence reconciliation, independent expert supplements, author application-binding review and author source-criterion reconciliation. `AUTHOR_SOURCE_CRITERION_RECONCILIATION` identifies the latter. `basis_documentation_status` indicates the accompanying explanation or criterion record.

In `source_files.csv`, `source_url` identifies a repository file at a fixed revision or an upstream library source at the declared version. `VERSION_PINNED_UPSTREAM_SOURCE` identifies the library reference used to check a callback contract. `source_line_count` and `target_literal_lines` retain file lengths and literal target-name locations from the original index. Added locators provide the relevant spans in `evidence_line_ranges`. `VERSION_PINNED_SOURCE_LOCATOR` identifies these added file references. `GIT_BLOB_VERIFIED` identifies sources whose bytes match a recorded Git object. `DOCUMENTED_SANITIZED_COPY` identifies a redacted source: the indexed `index.html` for association 3487 has an exposed credential removed, and its line positions refer to the retained redacted copy. Literal name locations help navigate a file; the application context determines their evidentiary role.

`evidence_explanations.json` contains author-prepared summaries of public-source evidence, informed by recorded assessments where applicable. Its `sources` field supplies the file and line ranges supporting each description. Repository identifiers and quoted source text retain their original forms.

For association 3487, [the retained redacted index.html](sanitized_sources/3487/index.html) supplies the source and line positions cited in its explanation. The file preserves the source text with the credential replaced by `[REDACTED_HF_TOKEN]`.

## Interpret recorded reasons

`first_association_before_window` and `first_association_after_window` exclude an association by time; `owner_not_independent` identifies the same-owner condition. `SOURCE_EXPLANATION_AVAILABLE` links to an association-specific description. `EXACT_MODEL_PIPELINE_CONNECTED_TO_GRADIO_CALLBACK` identifies the worked application example. Read these codes together with the classification and supporting fields.

`no_reachable_absent_predecessor` and `NO_TRANSITION_IN_PRESERVED_HISTORY` record unresolved temporal provenance under their respective preserved histories. `duplicate_provenance_origin_unresolved` records an unresolved source origin. `required_evidence_unavailable`, `HISTORICAL_RUNTIME_BINDING_UNAVAILABLE` and `AUDIT_METADATA_VERIFIED_HISTORICAL_COMMIT_INVENTORY_UNAVAILABLE` identify the missing evidence relevant to the decision. Missing historical contents, checkpoint identity or application binding remain explicit in the affected explanation. Repositories sharing an implementation retain separate model, Space and revision records; runtime observations are identified when available.
