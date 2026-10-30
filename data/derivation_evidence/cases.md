# Derivation-relation cases

We represent models by repository identifiers and extract their declared derivation relations. At the level of fixed model versions, a parent precedes the child derived from it, so a derivation chain cannot return to the same version. Repository identifiers can span model updates, while declarations may also be inconsistent. We exclude self-references that do not distinguish parent and child versions and the non-self relations within unresolved cyclic components of each monthly graph. All model nodes and original declarations are retained. The same relation treatment applies to ModelRank and graph-dependent comparators within each analytical scope. The evidence tables record the affected relations and months; they do not assign publisher fault to every excluded declaration.

Source months are analytical input labels, not certified declaration dates. Arrows point from child to declared parent. M = main panel; E = full-event scope; S = Space.

## F01. Ba2han: reciprocal fine-tuning declarations

The saved November 2025 source records for copr-model-muon-2 and sft-model-muon-3 name each other as fine-tuning parents. The structured baseModels field and the tags agree within each record. These declarations form a two-repository cycle in the full-event scope. The available declaration fields identify parent repositories without resolving the parent model versions.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-614ac0d6cbbfa410466d | Ba2han/sft-model-muon-3 | Ba2han/copr-model-muon-2 | 2025-11 |
| REL-80dbbda41c56ee34bf0e | Ba2han/copr-model-muon-2 | Ba2han/sft-model-muon-3 | 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F01-01 |

## F02. BexRedpill: reciprocal declarations with an epoch suffix

The two distilbert-on-polarity-yelp-reviews repositories declare each other as fine-tuning parents in the saved panel records. The existing fixed-revision model-card review also records both directions. The epoch-2 suffix distinguishes repository names but does not establish the parent version used in either derivation. The unresolved reciprocal declarations are excluded in the recorded affected months of all three scopes.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-d26e2f5eb6e47d6855d8 | BexRedpill/distilbert-on-polarity-yelp-reviews-epoch-2 | BexRedpill/distilbert-on-polarity-yelp-reviews | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-e563fa3a0197990d5d43 | BexRedpill/distilbert-on-polarity-yelp-reviews | BexRedpill/distilbert-on-polarity-yelp-reviews-epoch-2 | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F02-01 |
| M | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F02-02 |
| S | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 2 | 2 | F02-03 |

## F03. Demoglab and Sharktunis: reciprocal records with unavailable history

The saved records contain Meringue-to-KARKAR and KARKAR-to-Meringue parent declarations. They form a cycle in the main-panel and full-event scopes. The recorded public-history retrieval returned HTTP 401 for both repositories, leaving the historical parent-version question unresolved. The exclusion rests on the recorded cycle and unresolved versions; the access response does not establish that either repository was absent or that either declaration was false.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-3643b90b28572725d025 | Sharktunis/KARKAR | Demoglab/Meringue | 2026-01, 2026-02 |
| REL-c23db59124a70b5849f4 | Demoglab/Meringue | Sharktunis/KARKAR | 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2026-01, 2026-02 | 2 | 2 | F03-01 |
| M | 2026-01, 2026-02 | 2 | 2 | F03-02 |

## F04. Alisia: opposite declarations in separate source months

The saved August 2025 record for Alisia-x3-7B-Instruct-V1.0-private names Alisia-7B-Instruct-V1.0-private as its parent. Records assigned to September through November contain the opposite declaration. The two directions occur in separate saved source months and form a cycle when accumulated in the full-event scope. Resolving them as model-level derivations requires the corresponding parent versions. The word private is part of the repository identifiers and is not used to infer access permissions.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-96da6deee1d0e9d04399 | Gems234/Alisia-x3-7B-Instruct-V1.0-private | Gems234/Alisia-7B-Instruct-V1.0-private | 2025-08 |
| REL-bc48e6486ff1bac2ca7a | Gems234/Alisia-7B-Instruct-V1.0-private | Gems234/Alisia-x3-7B-Instruct-V1.0-private | 2025-09, 2025-10, 2025-11 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F04-01 |

## F05. DeepThink: reciprocal fine-tuning declarations

The saved April 2025 records for _Spydaz_Web_AGI_DeepThink_R1 and _Spydaz_Web_AGI_DeepThink_R2 contain fine-tuning parent declarations pointing to each other. The resulting two-repository cycle is present in the full-event and Space scopes. R1 and R2 are repository-name suffixes; the saved declarations do not resolve the parent model versions needed to select a derivation direction.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-424441368fd214186d0b | LeroyDyer/_Spydaz_Web_AGI_DeepThink_R1 | LeroyDyer/_Spydaz_Web_AGI_DeepThink_R2 | 2025-04 |
| REL-cca8c90bf6759f147d81 | LeroyDyer/_Spydaz_Web_AGI_DeepThink_R2 | LeroyDyer/_Spydaz_Web_AGI_DeepThink_R1 | 2025-04 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F05-01 |
| S | 2025-04 | 2 | 2 | F05-02 |

## F06. MrRobotoAI numeric and A-series: scope-dependent cyclic components

This case family contains 27 repository identifiers and 109 distinct non-self relations across the recorded scopes and months. Its declarations include merging and fine-tuning. The main-panel history review covers 21 relations; another 88 belong to the expanded scope. The recorded monthly components differ: the main panel has eight-node or nine-node components, Space has a nine-node component, and the full-event scope reaches 27 nodes. Existing history checks for the main-panel subset found unresolved alignment between some early source records and the available repository history. Each relation is therefore presented with its own scope, month and declaration source, and excluded only under the recorded monthly cycle rule.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-04b492a1bb8d02893785 | MrRobotoAI/105 | MrRobotoAI/A6 | 2025-04 |
| REL-04ba28580a027d98c069 | MrRobotoAI/106 | MrRobotoAI/121 | 2025-03 |
| REL-052d52a839963aa13fef | MrRobotoAI/120 | MrRobotoAI/100 | 2025-03 |
| REL-0a0e61a6a27be6fe2d66 | MrRobotoAI/100 | MrRobotoAI/104 | 2025-03 |
| REL-0b0825e4ff80af06736e | MrRobotoAI/A1 | MrRobotoAI/111 | 2025-02 |
| REL-0c2c4e121a62a5a5b9df | MrRobotoAI/A5 | MrRobotoAI/A2 | 2025-04 |
| REL-0cea6bc37ad40581169c | MrRobotoAI/122 | MrRobotoAI/106 | 2025-03 |
| REL-0e490969bda615bba0b4 | MrRobotoAI/115 | MrRobotoAI/102 | 2025-02 |
| REL-0e71e767978dfa1d5437 | MrRobotoAI/103 | MrRobotoAI/122 | 2025-03 |
| REL-0fc2cefa2c5974f416fd | MrRobotoAI/121 | MrRobotoAI/104 | 2025-03 |
| REL-0fd864ae19daf1542999 | MrRobotoAI/120 | MrRobotoAI/103 | 2025-03 |
| REL-114ef89dc97c1c188be3 | MrRobotoAI/A4 | MrRobotoAI/A3 | 2025-04 |
| REL-1254d82342fdcf2fd193 | MrRobotoAI/106 | MrRobotoAI/A7 | 2025-04 |
| REL-153f2d1081b888d048e6 | MrRobotoAI/112 | MrRobotoAI/A3 | 2025-02 |
| REL-1ce9a23d9cf04d3dcccc | MrRobotoAI/122 | MrRobotoAI/102 | 2025-03 |
| REL-215d05312c01b2c389b1 | MrRobotoAI/A6 | MrRobotoAI/A5 | 2025-04 |
| REL-21b2e7b4f3a363ee26ef | MrRobotoAI/109 | MrRobotoAI/112 | 2025-03 |
| REL-22281400ec6449e3c003 | MrRobotoAI/105 | MrRobotoAI/A1 | 2025-04 |
| REL-238472f10b3fdf7e5e08 | MrRobotoAI/A6 | MrRobotoAI/A3 | 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-2f28b8d3379c0abd8ef6 | MrRobotoAI/105 | MrRobotoAI/A7 | 2025-04 |
| REL-2fd4805dd1e8a248944d | MrRobotoAI/106 | MrRobotoAI/120 | 2025-03 |
| REL-3285284e0f7592f8a53a | MrRobotoAI/112 | MrRobotoAI/107 | 2025-02 |
| REL-36768419f21c46411c3a | MrRobotoAI/A2 | MrRobotoAI/A3 | 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-38c17e1e0fc826b3d4be | MrRobotoAI/108 | MrRobotoAI/A2 | 2025-04 |
| REL-3b0decaf362c411ff97c | MrRobotoAI/109 | MrRobotoAI/120 | 2025-03 |
| REL-3b5107c790106067f3ec | MrRobotoAI/102 | MrRobotoAI/A3 | 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-3cf7f5f15d3806a27d10 | MrRobotoAI/A2 | MrRobotoAI/A1 | 2025-02, 2025-04 |
| REL-3e65b293232c97c46f4f | MrRobotoAI/A7 | MrRobotoAI/A2 | 2025-04 |
| REL-464adc399bcec9e7a978 | MrRobotoAI/A1 | MrRobotoAI/107 | 2025-02 |
| REL-4bc618e85ec99a5d4d1b | MrRobotoAI/A2 | MrRobotoAI/102 | 2025-04 |
| REL-4bf1e8094c4d323741d1 | MrRobotoAI/100 | MrRobotoAI/A1 | 2025-04 |
| REL-4ddf5898376a35a60bc9 | MrRobotoAI/A3 | MrRobotoAI/A4 | 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-503eb663d9b3ab72afa8 | MrRobotoAI/113 | MrRobotoAI/102 | 2025-02 |
| REL-504d9c14b88f91bf0e76 | MrRobotoAI/120 | MrRobotoAI/102 | 2025-03 |
| REL-52a4a7e23417311f4527 | MrRobotoAI/A7 | MrRobotoAI/A1 | 2025-04 |
| REL-54634ae4cd4ab5730096 | MrRobotoAI/A8 | MrRobotoAI/A5 | 2025-04 |
| REL-5eade18071ddcdd874d6 | MrRobotoAI/111 | MrRobotoAI/108 | 2025-03 |
| REL-626d539b7194f545e971 | MrRobotoAI/103 | MrRobotoAI/A6 | 2025-04 |
| REL-628b9d46cba7a1e5f74d | MrRobotoAI/112 | MrRobotoAI/104 | 2025-02 |
| REL-62e2c4557a992dce8ad5 | MrRobotoAI/106 | MrRobotoAI/A1 | 2025-04 |
| REL-695bd11eb2b6d5a1e3b3 | MrRobotoAI/100 | MrRobotoAI/A2 | 2025-04 |
| REL-69834472eb6222daedd0 | MrRobotoAI/110 | MrRobotoAI/100 | 2025-05, 2025-06, 2025-07 |
| REL-6a99407951d7260449c1 | MrRobotoAI/A1 | MrRobotoAI/104 | 2025-02 |
| REL-6b5cbc77c66668d22cc4 | MrRobotoAI/A1 | MrRobotoAI/102 | 2025-02 |
| REL-6c2df95e366660dac1e8 | MrRobotoAI/102 | MrRobotoAI/A4 | 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-6ededda3a92f0b10ef9c | MrRobotoAI/108 | MrRobotoAI/101 | 2025-03 |
| REL-6ef7e181121cfe7b26db | MrRobotoAI/107 | MrRobotoAI/A1 | 2025-04 |
| REL-76cc5343283b7c590479 | MrRobotoAI/106 | MrRobotoAI/A8 | 2025-04 |
| REL-76ea8e8a459ff73b119e | MrRobotoAI/101 | MrRobotoAI/A3 | 2025-04 |
| REL-787ae7f42c940ec4c1ea | MrRobotoAI/116 | MrRobotoAI/115 | 2025-02 |
| REL-7a1af368e1f962d33a3d | MrRobotoAI/A6 | MrRobotoAI/A4 | 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-7d0e047173d328977147 | MrRobotoAI/A5 | MrRobotoAI/105 | 2025-05, 2025-06, 2025-07 |
| REL-7d1cb3d7e97e94fda9cf | MrRobotoAI/A2 | MrRobotoAI/111 | 2025-02 |
| REL-7dd3509629247b154b24 | MrRobotoAI/101 | MrRobotoAI/A2 | 2025-04 |
| REL-81ec39e221141f807922 | MrRobotoAI/103 | MrRobotoAI/A1 | 2025-04 |
| REL-842bb6e2e007be0f6f74 | MrRobotoAI/122 | MrRobotoAI/103 | 2025-03 |
| REL-881d2e3b2e08c4a12fcd | MrRobotoAI/111 | MrRobotoAI/102 | 2025-03 |
| REL-882db1779d9c35ac6aa9 | MrRobotoAI/113 | MrRobotoAI/103 | 2025-05, 2025-06, 2025-07 |
| REL-89160d182a9377b232b2 | MrRobotoAI/A2 | MrRobotoAI/116 | 2025-02 |
| REL-8b53b87797c3166c7cc9 | MrRobotoAI/A3 | MrRobotoAI/111 | 2025-02 |
| REL-8d1c6173aa4dc5cb904c | MrRobotoAI/A2 | MrRobotoAI/A4 | 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-8d4d2251eb5d89ec3fde | MrRobotoAI/102 | MrRobotoAI/A1 | 2025-04 |
| REL-8fa1e034b16ee75b92d3 | MrRobotoAI/113 | MrRobotoAI/105 | 2025-02 |
| REL-910bd6dfa828601ad0f7 | MrRobotoAI/103 | MrRobotoAI/120 | 2025-03 |
| REL-930b0d60b314a1425b02 | MrRobotoAI/A4 | MrRobotoAI/106 | 2025-04 |
| REL-9adf2ef88ea829dd61cf | MrRobotoAI/101 | MrRobotoAI/A1 | 2025-04 |
| REL-a0b5cfaaf6cb6581e31b | MrRobotoAI/107 | MrRobotoAI/A8 | 2025-04 |
| REL-a1d0fe86c80e8c0d28ef | MrRobotoAI/105 | MrRobotoAI/120 | 2025-03 |
| REL-a2d5298a14a63cbd1b90 | MrRobotoAI/121 | MrRobotoAI/105 | 2025-03 |
| REL-a5db5ee0e762446d18be | MrRobotoAI/100 | MrRobotoAI/A3 | 2025-04 |
| REL-a7a786fcc277412760a7 | MrRobotoAI/103 | MrRobotoAI/A5 | 2025-04 |
| REL-a871e7f00977076a7c1d | MrRobotoAI/101 | MrRobotoAI/A4 | 2025-04 |
| REL-aa5fa3574bc9e03ca5f4 | MrRobotoAI/111 | MrRobotoAI/100 | 2025-02 |
| REL-abf9fbea2536099287c8 | MrRobotoAI/106 | MrRobotoAI/105 | 2025-03 |
| REL-ac620be511109063c315 | MrRobotoAI/121 | MrRobotoAI/101 | 2025-03 |
| REL-ae7b833c70ee1228bdbf | MrRobotoAI/113 | MrRobotoAI/108 | 2025-02 |
| REL-af2de3ed0349424c5b46 | MrRobotoAI/103 | MrRobotoAI/121 | 2025-03 |
| REL-af3125ba78c256212f9c | MrRobotoAI/104 | MrRobotoAI/102 | 2025-03 |
| REL-afe1ce235effd5e21fca | MrRobotoAI/100 | MrRobotoAI/108 | 2025-03 |
| REL-b1909965bbc3ae22a521 | MrRobotoAI/A8 | MrRobotoAI/A4 | 2025-04 |
| REL-b4a0772479fb48c0db95 | MrRobotoAI/122 | MrRobotoAI/104 | 2025-03 |
| REL-b5e66c7abdbc9b653026 | MrRobotoAI/104 | MrRobotoAI/A1 | 2025-04 |
| REL-b9f56d64676d34ce21e8 | MrRobotoAI/112 | MrRobotoAI/110 | 2025-02 |
| REL-bd391a895462d1bc59b9 | MrRobotoAI/110 | MrRobotoAI/108 | 2025-02 |
| REL-bf3532028009a3d2a8d9 | MrRobotoAI/100 | MrRobotoAI/105 | 2025-03 |
| REL-bf7df2f76eb280bd0bdd | MrRobotoAI/121 | MrRobotoAI/102 | 2025-03 |
| REL-bfc19efde7adf92e7cb7 | MrRobotoAI/A3 | MrRobotoAI/109 | 2025-02 |
| REL-c5a1b06abd5c237b0a6b | MrRobotoAI/106 | MrRobotoAI/102 | 2025-03 |
| REL-c76cec10b4ee12262ca6 | MrRobotoAI/A3 | MrRobotoAI/110 | 2025-02 |
| REL-c88b5483974d564bc1fa | MrRobotoAI/120 | MrRobotoAI/101 | 2025-03 |
| REL-cb0076b771b65dd19d09 | MrRobotoAI/102 | MrRobotoAI/A5 | 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-cc86a02e49ac7daa9eff | MrRobotoAI/115 | MrRobotoAI/105 | 2025-02, 2025-05, 2025-06, 2025-07 |
| REL-ccb66f25a4d38d4299e3 | MrRobotoAI/104 | MrRobotoAI/A5 | 2025-04 |
| REL-cd866b101ccc48f5bf3b | MrRobotoAI/110 | MrRobotoAI/102 | 2025-02 |
| REL-cf051d476b7f46effe3a | MrRobotoAI/105 | MrRobotoAI/A8 | 2025-04 |
| REL-d08f92fbf6380ea7485e | MrRobotoAI/120 | MrRobotoAI/104 | 2025-03 |
| REL-d2b1c5496bee7183d694 | MrRobotoAI/A5 | MrRobotoAI/A6 | 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-d2d0c52a1025e24b6a43 | MrRobotoAI/A3 | MrRobotoAI/112 | 2025-02 |
| REL-d46ecfe324fe1c2ebed9 | MrRobotoAI/104 | MrRobotoAI/A6 | 2025-04 |
| REL-d6acaaad4a3baa8fbbed | MrRobotoAI/113 | MrRobotoAI/111 | 2025-02 |
| REL-da97962fd454f7da56ac | MrRobotoAI/105 | MrRobotoAI/102 | 2025-03 |
| REL-dc75da5be4459f967fef | MrRobotoAI/104 | MrRobotoAI/A7 | 2025-04 |
| REL-e1be9e5545e529577986 | MrRobotoAI/122 | MrRobotoAI/105 | 2025-03 |
| REL-e23a7cd80b6f4aeefc6c | MrRobotoAI/103 | MrRobotoAI/A4 | 2025-04 |
| REL-ebf281d217488fd4506c | MrRobotoAI/121 | MrRobotoAI/103 | 2025-03 |
| REL-f1715cbc55646e77381d | MrRobotoAI/109 | MrRobotoAI/116 | 2025-03 |
| REL-f5b661e45a7da3a7f2bb | MrRobotoAI/A3 | MrRobotoAI/A1 | 2025-04 |
| REL-f692d5241fbd6ab8018b | MrRobotoAI/108 | MrRobotoAI/A1 | 2025-04 |
| REL-f7768300bd1bf25dce13 | MrRobotoAI/A3 | MrRobotoAI/113 | 2025-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 27 | 109 | F06-01 |
| E | 2025-05, 2025-06, 2025-07 | 27 | 108 | F06-02 |
| E | 2025-04 | 27 | 101 | F06-03 |
| E | 2025-03 | 7 | 15 | F06-04 |
| E | 2025-03 | 3 | 4 | F06-05 |
| E | 2025-02 | 2 | 2 | F06-06 |
| M | 2025-05, 2025-06, 2025-07 | 8 | 17 | F06-07 |
| M | 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 9 | 21 | F06-08 |
| S | 2025-04 | 9 | 18 | F06-09 |

## F07. Hathor: a three-repository merge-declaration cycle

The saved August and September 2024 source records contain the parent-declaration path Hathor-v4.1 to Hathor-v4 to Hathor-v3.1 to Hathor-v4.1. These three merge declarations form a directed cycle in the full-event scope. Their version-like repository names do not identify the exact parent model versions used for derivation.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-0afbb83d73071b5707f8 | MrRobotoAI/Hathor-v4.1 | MrRobotoAI/Hathor-v4 | 2024-08, 2024-09 |
| REL-408a8c2ba023fb3cf565 | MrRobotoAI/Hathor-v4 | MrRobotoAI/Hathor-v3.1 | 2024-08, 2024-09 |
| REL-ba8434d66af20c33439f | MrRobotoAI/Hathor-v3.1 | MrRobotoAI/Hathor-v4.1 | 2024-08, 2024-09 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F07-01 |

## F08. Loki and Special-Dark: reciprocal merge declarations

The saved July through September 2024 records contain reciprocal merge-parent declarations between Loki-base and llama3-8B-Special-Dark-v3.1.2c. The two relations form a cycle in the full-event scope. The declarations identify repositories without an established mapping to the parent versions required to resolve the cycle.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-4313d9f2800a5aec2dd4 | MrRobotoAI/llama3-8B-Special-Dark-v3.1.2c | MrRobotoAI/Loki-base | 2024-07, 2024-08, 2024-09 |
| REL-9df9620fd6accd8a3bb7 | MrRobotoAI/Loki-base | MrRobotoAI/llama3-8B-Special-Dark-v3.1.2c | 2024-07, 2024-08, 2024-09 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F08-01 |

## F09. SQAI embeddings: reciprocal fine-tuning declarations

The saved July 2024 records for bge-embedding-model and bge-embedding-model2 declare each other as fine-tuning parents. These relations form a two-repository cycle in the full-event scope. The numerical suffix distinguishes identifiers but does not supply the missing parent-version mapping.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-5903ba8c2346b24bcd5e | SQAI/bge-embedding-model | SQAI/bge-embedding-model2 | 2024-07 |
| REL-9bd4d751b7468deecdeb | SQAI/bge-embedding-model2 | SQAI/bge-embedding-model | 2024-07 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F09-01 |

## F10. MistralCreative: four merge relations among three repositories

The cumulative declarations among MistralCreative-24B, Chat and Instruct contain four non-self merge relations. They include a reciprocal pair between the base-named and Chat repositories and an additional path through Instruct that returns to the base-named repository. Existing history checks record multistep merge descriptions and unresolved alignment for two repositories. The four relations are handled together in each affected monthly component because the available evidence does not establish a consistent set of immediate parent versions.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-34e0d976a6e61ff7d8e1 | Sorawiz/MistralCreative-24B | Sorawiz/MistralCreative-24B-Chat | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-6c0e10ed2a31ab7768b7 | Sorawiz/MistralCreative-24B | Sorawiz/MistralCreative-24B-Instruct | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-b5e6630ab0be40aa4ebd | Sorawiz/MistralCreative-24B-Instruct | Sorawiz/MistralCreative-24B-Chat | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-f5ccc776f1438d5bf998 | Sorawiz/MistralCreative-24B-Chat | Sorawiz/MistralCreative-24B | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 4 | F10-01 |
| M | 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 4 | F10-02 |
| S | 2025-03, 2025-04 | 3 | 4 | F10-03 |

## F11. Creative and Realist: changing historical parent declarations

Fixed-revision model cards document opposite parent declarations at different revisions. The Realist card at revision 975fff9c25996457ec1faccbbd11d7497e7cc6fc names Creative, while the Creative card at revision 5529aa304e0a2a2fcc92d0ff06dc45628defe851 names Realist. The saved source records place these directions in different source months; their accumulation forms the cycle. The available files do not bind both declarations to exact parent model versions. In addition, the Realist README and root merge configuration at revision a82c9ad3a70fe4d2ee6fba69c5ee8e3c93377961 name different inputs in the relevant merge step. The records therefore support version-dependent declaration changes, while the model-version derivation chain remains unresolved.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-aff7e18f64aa7670e235 | Sorawiz/MistralSmall-Creative-24B-Realist | Sorawiz/MistralSmall-Creative-24B | 2025-02 |
| REL-c92aa23f943dcb0805bc | Sorawiz/MistralSmall-Creative-24B | Sorawiz/MistralSmall-Creative-24B-Realist | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F11-01 |
| M | 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F11-02 |
| S | 2025-03, 2025-04 | 2 | 2 | F11-03 |

## F12. Judge models: a three-repository cycle with a source conflict

The saved declarations form the cycle Judge-GPT2 to JudgeLLM2 to JudgeLLM to Judge-GPT2. The JudgeLLM2 model card at revision 956f0e6cf54f8b3d6cc2fb1e5f6a5628b8085e74 both declares JudgeLLM as its base model and states that training started from scratch. This is a direct inconsistency within that source. It applies specifically to the JudgeLLM2 declaration; the other two relations are included in the unresolved cyclic component without being independently classified as the same source conflict.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-4e95f36415c34c879107 | Wonder-Griffin/Judge-GPT2 | Wonder-Griffin/JudgeLLM2 | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-60f649c945a56d34376c | Wonder-Griffin/JudgeLLM | Wonder-Griffin/Judge-GPT2 | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-b07116770e9979972734 | Wonder-Griffin/JudgeLLM2 | Wonder-Griffin/JudgeLLM | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F12-01 |
| M | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F12-02 |
| S | 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 3 | 3 | F12-03 |

## F13. Qw-it and chatbotDema: a later reciprocal declaration

The saved records first contain chatbotDema naming Qw-it in the October 2025 source month, followed by the opposite declaration in February 2026. Both directions are present in the February records. Existing history review records reciprocal parent statements without exact parent-version bindings. The monthly treatment excludes the relations when they participate in the cycle and retains earlier treatment according to the original monthly action records.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-755fd4239c4108236cb1 | irfan0858/Qw-it | irfan0858/chatbotDema | 2026-02 |
| REL-9ae80b639446dde43a1a | irfan0858/chatbotDema | irfan0858/Qw-it | 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2026-02 | 2 | 2 | F13-01 |
| M | 2026-02 | 2 | 2 | F13-02 |

## F14. MNLP: a later reciprocal fine-tuning declaration

The saved source records contain first-mcqa-model naming MNLP_M2_mcqa_model from May 2025 and the reverse direction from August 2025. The existing model-card review records reciprocal fine-tuning statements. The declarations establish the repository-level cycle, while their parent model versions remain unresolved. Exclusions follow the affected monthly components in the main-panel and full-event scopes.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-8fe66617237d6e6a5bd5 | liam-mnlp/first-mcqa-model | liam-mnlp/MNLP_M2_mcqa_model | 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-cb41ebb4fa07ff92599f | liam-mnlp/MNLP_M2_mcqa_model | liam-mnlp/first-mcqa-model | 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F14-01 |
| M | 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F14-02 |

## F15. Bengali POS: reciprocal declarations across checkpoint-like names

The saved panel records contain reciprocal fine-tuning declarations between bengali_pos_v1_300000 and bengali_pos_v1_400000. Existing fixed-revision cards and configuration loading names also record reciprocal references. The numeric suffixes alone do not establish which model version served as the parent. The two relations are excluded in the recorded cyclic months of all three scopes.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-0b41affef491e11576fc | mHossain/bengali_pos_v1_400000 | mHossain/bengali_pos_v1_300000 | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-eb459c3d1cc6e8b6f282 | mHossain/bengali_pos_v1_300000 | mHossain/bengali_pos_v1_400000 | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F15-01 |
| M | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F15-02 |
| S | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 2 | 2 | F15-03 |

## F16. Manifestasi Whisper: repository-name/card-title mismatch and reciprocal declarations

The saved records contain opposite fine-tuning declarations between whisper-tiny-manifestasi-indo and its v2-named repository. The earlier history review found that the card for the repository without the v2 suffix was titled v4, while the other card was titled v2. Repository names and card titles therefore do not provide a complete parent-version mapping. The unresolved cycle is treated according to the main-panel and full-event monthly records.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-7992840570db25a830ae | manifestasi/whisper-tiny-manifestasi-indo | manifestasi/whisper-tiny-manifestasi-indo-v2 | 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-f4684a4ee7b7fbd1b54d | manifestasi/whisper-tiny-manifestasi-indo-v2 | manifestasi/whisper-tiny-manifestasi-indo | 2025-04, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F16-01 |
| M | 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F16-02 |

## F17. Orionshaw: a three-repository fine-tuning cycle

The saved declarations form the path codeparrot-ds to gpt2-belle-sft-offcial-1st to gpt2-belle-sft and back to codeparrot-ds. Existing model-card review records the same cyclic parent statements. The available training descriptions do not resolve the parent versions for this three-repository cycle, so the affected relations are excluded in the recorded main-panel and full-event months.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-06df8e2b3d56350b691d | orionshaw777/codeparrot-ds | orionshaw777/gpt2-belle-sft-offcial-1st | 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-c951aecf2f86f9073dce | orionshaw777/gpt2-belle-sft-offcial-1st | orionshaw777/gpt2-belle-sft | 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-dd238c8e8753043c23a8 | orionshaw777/gpt2-belle-sft | orionshaw777/codeparrot-ds | 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F17-01 |
| M | 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F17-02 |

## F18. Quastrinos: a three-repository cycle across version suffixes

The saved records for the race-openbook model family contain the parent-declaration path v2 to v1 to the repository without a version suffix and back to v2. The existing fixed-card review records all three declarations. The suffix order does not resolve the actual parent model versions, and the three cyclic relations are excluded in the affected months of all three scopes.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-93f1d46d710a38564f74 | quastrinos/race-openbook-finetuned-deberta-v3-large-mcqa-TPU-v2 | quastrinos/race-openbook-finetuned-deberta-v3-large-mcqa-TPU-v1 | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-c668376465e91481ddf0 | quastrinos/race-openbook-finetuned-deberta-v3-large-mcqa-TPU-v1 | quastrinos/race-openbook-finetuned-deberta-v3-large-mcqa-TPU | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-d74dffad700ad3cab3a7 | quastrinos/race-openbook-finetuned-deberta-v3-large-mcqa-TPU | quastrinos/race-openbook-finetuned-deberta-v3-large-mcqa-TPU-v2 | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F18-01 |
| M | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 3 | 3 | F18-02 |
| S | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 3 | 3 | F18-03 |

## F19. DistilHuBERT: reciprocal fine-tuning declarations

The saved records contain reciprocal fine-tuning declarations between distilhubert-finetuned-gtzan and distilhubert-finetuned-finetuned-gtzan. The existing fixed-card review also records both directions. The repeated finetuned token in the repository name does not identify the exact parent version. The unresolved reciprocal relations are excluded in the recorded monthly components of all three scopes.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-194bc0c0ac1fae6c6fb6 | weiren119/distilhubert-finetuned-finetuned-gtzan | weiren119/distilhubert-finetuned-gtzan | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |
| REL-4834bca58b8b76237ace | weiren119/distilhubert-finetuned-gtzan | weiren119/distilhubert-finetuned-finetuned-gtzan | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F19-01 |
| M | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F19-02 |
| S | 2024-07, 2024-08, 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 2 | 2 | F19-03 |

## F20. Yuna v1: fine-tuning and reverse quantization declarations across months

In the saved July and August 2024 records, yuna-ai-v1-full declares yuna-ai-v1 as its fine-tuning parent. Records assigned to September 2024 through June 2025 contain the reverse direction, with yuna-ai-v1 declaring yuna-ai-v1-full as a quantization parent. The two directions occupy separate saved source months and form a cycle in the cumulative full-event and Space graphs. Distinguishing the model versions underlying these two operations requires additional parent-version evidence.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-cb760c39e7e6f2ce991c | yukiarimo/yuna-ai-v1 | yukiarimo/yuna-ai-v1-full | 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06 |
| REL-ce516132c7d2ffab9750 | yukiarimo/yuna-ai-v1-full | yukiarimo/yuna-ai-v1 | 2024-07, 2024-08 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F20-01 |
| S | 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 2 | 2 | F20-02 |

## F21. Yuna v2: fine-tuning and reverse quantization declarations across months

In the saved July and August 2024 records, yuna-ai-v2-full declares yuna-ai-v2 as its fine-tuning parent. Records assigned to September 2024 through July 2025 contain the reverse quantization-parent declaration. These directions occur in separate saved source months and form a cumulative cycle in the full-event and Space scopes. The available declaration records leave the corresponding parent model versions unresolved.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-46cb654934e726adc7b8 | yukiarimo/yuna-ai-v2-full | yukiarimo/yuna-ai-v2 | 2024-07, 2024-08 |
| REL-aca5e62953ab3d7dcf33 | yukiarimo/yuna-ai-v2 | yukiarimo/yuna-ai-v2-full | 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04, 2025-05, 2025-06, 2025-07, 2025-08, 2025-09, 2025-10, 2025-11, 2025-12, 2026-01, 2026-02 | 2 | 2 | F21-01 |
| S | 2024-09, 2024-10, 2024-11, 2024-12, 2025-01, 2025-02, 2025-03, 2025-04 | 2 | 2 | F21-02 |

## F22. Zenlm: reciprocal quantization declarations with unavailable history

The saved February 2026 records contain reciprocal quantization-parent declarations between zen-coder-24b-gguf and zen-coder-24b-mlx. The recorded public-history retrieval returned HTTP 401 for both repositories. The stored declarations establish the cycle in the main-panel and full-event scopes; the exact parent versions remain unresolved. File-format suffixes alone do not determine which direction should be retained.

| Relation ID | Child | Declared parent | Source months |
|---|---|---|---|
| REL-389de9bf16aaec77bf3a | zenlm/zen-coder-24b-gguf | zenlm/zen-coder-24b-mlx | 2026-02 |
| REL-3d77725ba26b36363ae0 | zenlm/zen-coder-24b-mlx | zenlm/zen-coder-24b-gguf | 2026-02 |

| Scope | Exclusion months | Nodes | Relations | Structure |
|---|---|---:|---:|---|
| E | 2026-02 | 2 | 2 | F22-01 |
| M | 2026-02 | 2 | 2 | F22-02 |

## Self-references

The 2,096 self-referencing declarations identify the same child and parent repository. They provide no distinction between the two model versions needed to interpret the record as an inter-model derivation. The affected relations are excluded in the recorded months, with all model nodes and original source records retained.
