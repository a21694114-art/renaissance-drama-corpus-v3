# Project status

| Item | State |
|---|---|
| Frozen corpus | **v3**, `corpus-v3-2026-09-08` (builder `build_corpus-2026-09-08.v8`, extraction rule `extract-2026-09-08.13`, unit map v16) |
| Regularized view | **r3**, `build_reg_view.py` version `reg-view-2026-09-14.4` (2026-09-14) |
| Independent review | r3 texts, manifests and the three contraction / eight boundary / four restoration regression cases re-checked 2026-09-14 (see `reports/`) |
| Modelling | not yet run |
| Next step | A/B experiment: embeddings on `texts_analysis_en_reg/` vs `texts_analysis_en/` with one chunk map defined on v3 node indices, same model and random seed |

Known limitations of r3: EarlyPrint's contextual regularizations (e.g. *then → than*) are accepted
unreviewed; a few contractions that EarlyPrint splits without `join` are emitted with a space
(*'T is*); documents whose EarlyPrint copy omits the text (A04632 masques, A04637 Althorp
entertainment) remain in original spelling.

Not yet in the repository: `texts/` (all-language view), `texts_no_prologue_epilogue/` and its
regularized twin, `kept_nodes.csv` (678 MB) and `node_fates.csv`; a clean-directory rerun of the
reproduction commands; schema fixtures for `test_build_corpus.py`; a regression test for
`build_reg_view.py`.
