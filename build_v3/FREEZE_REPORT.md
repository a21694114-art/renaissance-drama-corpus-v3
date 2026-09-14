# FREEZE REPORT - corpus corpus-v3-2026-09-08

builder build_corpus-2026-09-08.v8; line rule structural; frames on; dry-run False; 2026-09-08T02:37:04

## Included set
- units included: **584** (proposed & confirmed & primary/component & no edition CHECK)
- editions built: **582**; works: **518**
- units NOT included, by reason:
  - not proposed (excluded_proposed): 62
  - not proposed (deferred_extension): 19
  - not proposed (alternate_witness_same_edition): 6
  - not proposed (supplementary): 2
  - not proposed (excluded_from_main): 1

## FREEZE GATE: open

Verified exclusions and approved deferrals do not block (see release_checklist.md).

## Hard-condition failures (0)
- none

## Body node decisions
- applied from body_node_decisions.csv: include 3822, exclude 1892
- pending: 0 nodes in 0 groups

## Frames
- prologue: include: 98
- epilogue: include: 53
- song: include as song: 6
- epilogue: attributed to unbuilt work (not built): 3
- prologue: attributed to unbuilt work (not built): 2
- introduction: include as induction: 2
- induction: include as induction: 2
- preface: include as prologue: 1
- section: include as epilogue: 1
- introduction: attributed to unbuilt work (not built): 1
- epilogue: exclude: 1
- prologue: exclude: 1
- song: exclude: 1
- prologue: include (explicit target unit A18404.1, edition 647): 1
- dumb_show: exclude: 1
- preface: include as induction: 1
- part: include as induction: 1

## DEFERRED to Grace (not in this build, not blocking, reversible) - 0 nodes
- none

## SUPPLEMENTARY (approved; kept OUTSIDE the main corpus in supplementary/ with provenance; not excluded, not deferred) - 6728 nodes in 7 documents
- unit A72573.1 [unit]: 4608 nodes
- container A01227.2 [part>day]: 1198 nodes
- unit A03241.23 [unit]: 620 nodes
- container A18463 [text>panegyric]: 178 nodes
- nodes A01506 [Norwich 1578 Latin poems Ad Solem and Ad Civitatem with printed English translations]: 88 nodes
- container A17342 [sonnet]: 24 nodes
- container A18463 [text>epigram]: 12 nodes

## Node accounting (every candidate node exactly one fate; bound to coverage_check.py)
- distinct input keys: 1055990 (duplicate keys: 0); XML candidate nodes per coverage_summary.json: 1055990 (missing 0, duplicated 0)
- fates: kept (passed the structural rule inside <sp>, or a reviewed node/container decision) 959342; excluded (verified) 89920; pending 0; DEFERRED to Grace 0; SUPPLEMENTARY (approved, outside the main corpus) 6728; total 1055990; sum ok: True
- pending nodes by reason:
  - node decision pending: 0

## Excluded candidate nodes, by reason
- unit not included (excluded_proposed): 56602
- unit not included (alternate_witness_same_edition): 13384
- front/back: frame paratext (single work): 7268
- unit not included (deferred_extension): 5632
- front/back: frame paratext (collection-level (2 works) - volume para): 1326
- node decision exclude (separate_literary_appendix): 968
- unit not included (excluded_from_main): 606
- front/back: frame paratext (no mapped work under this <text>): 567
- container audit exclude (performance_description): 540
- container audit exclude (authorial_description): 379
- node decision exclude (performance_description): 307
- front/back: frame paratext (collection-level (3 works) - volume para): 307
- container audit exclude (non-performance text): 293
- front/back: frame paratext (collection-level (22 works) - volume par): 288
- node decision exclude (dedicatory_or_commendatory_verse): 252
- line rule structural dropped (argument): 238
- front/back: frame paratext (collection-level (36 works) - volume par): 140
- node decision exclude (authorial_description): 104
- front/back: frame decision exclude: 104
- container audit exclude (narrative): 81
- container audit exclude (description): 75
- node decision exclude (meditative_poem_editorial): 54
- front/back: frame attributed to a work not built (A04633.4): 39
- node decision exclude (narrative): 32
- front/back: frame attributed to a work not built (A04633.3): 32
- node decision exclude (descriptive_or_bibliographic_appendage): 30
- node decision exclude (displayed_epigram_editorial): 24
- front/back: frame attributed to a work not built (A04633.1): 24
- node decision exclude (inscription): 23
- node decision exclude (argument): 22
- node decision exclude (heading_or_speaker_cue): 20
- container audit exclude (heading_or_speaker_cue): 18
- container audit exclude (inscription): 16
- line rule structural dropped (title_page): 16
- front/back: frame paratext (collection-level (6 works) - volume para): 14
- node decision exclude (character_list): 12
- node decision exclude (descriptive_catalogue): 11
- line rule structural dropped (dramatis_personae): 8
- line rule structural dropped (to_the_reader): 8
- node decision exclude (lyric_appendix_editorial): 8
- node decision exclude (quotation_in_commentary): 7
- line rule structural dropped (inscription): 6
- node decision exclude (authorial_history_description_or_credit): 5
- front/back: frame paratext (collection-level (10 works) - volume par): 5
- front/back: frame paratext (collection-level (4 works) - volume para): 4
- node decision exclude (source_text_unavailable): 3
- line rule structural dropped (imprimatur): 3
- node decision exclude (descriptive_summary): 3
- node decision exclude (production_credit): 2
- node decision exclude (authorial_performance_description): 2
- node decision exclude (stage_direction): 2
- line rule structural dropped (dedication): 2
- container audit exclude (authorial_note): 1
- line rule structural dropped (descriptions): 1
- node decision exclude (displayed_inscription): 1
- container audit exclude (production_credit): 1

## Text roles in built texts (nodes)
- dramatic_body: 933421
- chorus: 5939
- song: 5547
- speech: 4794
- prologue: 4685
- poem: 2166
- epilogue: 2121
- induction: 669

## Views (files are written only for non-empty documents)
- texts/: every kept node in document order (all languages)
- texts_analysis_en/: kept nodes with language en
- texts_no_prologue_epilogue/: language en and text_role not prologue/epilogue (induction kept)
- texts: non-empty documents 582 / editions 582; works with a non-empty document 518
- texts_analysis_en: non-empty documents 580 / editions 582; works with a non-empty document 516
- texts_no_prologue_epilogue: non-empty documents 580 / editions 582; works with a non-empty document 516
- kept nodes by language: en=955792, la=2183, sco=1364, fr=2, es=1
- language source of kept nodes: en/xml:lang=751028, en/assumed=205766, sco/unit_language.csv (overrides xml:lang)=4608, la/xml:lang=2160, sco/xml:lang=1364, en/node decision=1061, la/node decision=80, fr/xml:lang=1, es/xml:lang=1, fr/node decision=1
- EMPTY in texts_analysis_en: 457 Philotus [all kept nodes non-en: sco=1364]; 1404 Pedantius [all kept nodes non-en: la=675]
- EMPTY in texts_no_prologue_epilogue: 457 Philotus [all kept nodes non-en: sco=1364]; 1404 Pedantius [all kept nodes non-en: la=675]

## Function audit of rule-kept text outside <sp> (container_audits.csv)
- audited containers applied: include 33098 nodes, exclude 1404 nodes
- live worksheet of the pending set: out_corpus/FUNCTION_AUDIT_WORKSHEET_corpus-v3-2026-09-08.csv (0 unit x div-chain rows)
- rule-kept nodes outside <sp> with NO applied container audit: 0 nodes / 0 chars in 0 units - fate pending, NOT in the plan (blocks a real build)

## Read-back reconciliation (real build only)
- files: 1749; mismatches: 0

## Sanity: DEEP play_type of built editions
- Adult Professional: 246
- Occasional: 112
- Boys Professional: 78
- Interlude: 37
- Closet/Unacted: 29
- University/Inns of Court: 28
- Translation: 27
- Professional: 10
- Nonprofessional: 8
- Boys Nonprofessional/School: 3
- Unknown: 2
- Private: 1
- Latin: 1
