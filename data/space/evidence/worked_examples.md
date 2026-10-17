# Reading the Space evidence

## Evidence and labels

Classification is based on version-pinned repository sources and metadata preserved at the audit time. A qualifying association first appears between June 1, 2025, and May 31, 2026, inclusive (UTC); the Space is publicly accessible at audit, has a different owner from the model, and has repository evidence connecting the exact target model to an application execution path. The evidence records identify the source revision, file and relevant lines for each explanation.

A model is positive when at least one association qualifies. Otherwise, unresolved evidence yields an undecidable outcome; a negative label requires complete association auditing with no qualifying deployment. Collection failures are recorded separately. Construction denotes training, fine-tuning, merging or other model-building operations defined in the codebook. The descriptions below are author-prepared summaries of the cited evidence and, where applicable, the expert assessments.

## Exact-model application use: association 1381

For `VietAI/gpt-neo-1.3B-vietnamese-news` in `quangkhoa11/book-describer`, the first recorded association is October 27, 2025, 08:24:06 UTC. The preceding revision lacks the association, the owners differ, and the preserved audit response records public accessibility. At revision `c5d5a141ac38d96529fd4176abb3867f6c0b09cd`, `app.py` names the exact model at line 5, constructs its text-generation pipeline at line 6, invokes that pipeline at line 15, connects the callback to the Gradio interface at line 19, and includes the launch call at line 27. This source path and the recorded temporal, ownership and accessibility evidence support a qualifying association under the repository-evidence definition.

## Association before the outcome window: association 0

The association between `4-alokk/llama-3-8b-English-to-Hinglish` and `Granther/try-this-model` is recorded on September 23, 2024, 20:53:06 UTC, before the outcome window. The first-present revision is `5e8c4b7350f8104d083e2fd8e097ced336ad56a9`. This association is excluded from the new-deployment outcome by the temporal criterion. All seven recorded associations for this model precede the window, and the retained enumeration is complete, supporting a negative label for this outcome.

## Unresolved historical container binding: association 1679

For `cross-encoder/ms-marco-TinyBERT-L2-v2` in `ArtemBolgov/leaderboard`, the recorded association time is March 28, 2026, 19:04:11 UTC. At revision `f31bf4b05cc011b1cf84518d869b9ebd9922f54b`, the Dockerfile selects a mutable `latest` image tag. The version-like reference on the following line is commented out. The available historical evidence leaves the identity and contents of the container used by that revision unresolved. The association has incomplete historical evidence and remains undecidable.

## Unclosed application statement: association 1322

For `TheBloke/dolphin-2.5-mixtral-8x7b-GPTQ` in `Agaris38/dolphin-mixtral-2.5-8x7b`, the complete `app.py` at revision `c6f65d8d02378ed2fd7db4e5c6affdbac58e0eb8` contains target-model loading and generation code at lines 5-17. The 590-byte file ends with an unclosed `.launch(` statement at line 19, causing static parsing to fail. Its bytes match the Git object recorded for that revision. The available historical evidence is insufficient to establish a valid application path serving the target model. Both expert assessments classify the association as `insufficient_information` (undecidable), with no affirmative construction evidence.

## Unresolved model identity after checkpoint loading: association 2245

For `microsoft/beit-base-finetuned-ade-640-640` in `ceruka/candle-graph`, `app.py` at revision `1ff1e9e5b7c5b63f5fd79fe65c2e5e45597425a6` initializes a BEiT backbone from the target repository and adds a classification head. Line 51 attempts to load an external checkpoint into this composite model before the normal inference path. If loading fails after model assignment, the exception handler retains the model object, leaving a possible inference path through the callback. The available historical evidence leaves both the resulting parameter identity and the occurrence of this alternative execution path unresolved. Both expert assessments classify the association as `insufficient_information` (undecidable), with no affirmative construction evidence.
