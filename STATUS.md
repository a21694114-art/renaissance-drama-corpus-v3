# Project status

| Item | State |
|---|---|
| Frozen corpus | **v3**, `corpus-v3-2026-09-08` (builder `build_corpus-2026-09-08.v8`, extraction rule `extract-2026-09-08.13`, unit map v16) |
| Regularized view | **r3**, `build_reg_view.py` version `reg-view-2026-09-14.4` (2026-09-14) |
| Independent review | r3 texts, manifests and the three contraction / eight boundary / four restoration regression cases re-checked 2026-09-14 (see `reports/`) |
| Modelling | done (2026-09-25): chunk map v3 (17,422 chunks), Qwen3-Embedding-0.6B, name-masked text, one representative edition per work, HDBSCAN min_samples 10 seed 42 → 63 clusters; all 63 received researcher decisions informed by keywords, work concentration and documented AI-assisted readings of sampled passages (53 in the genre comparison, 6 pending, 4 context only) — see `ab_spelling/README.md`; frozen result files in `ab_spelling/results_masked_hdb10/` |
| Next step | limited K-means 50 comparison on 3–5 core themes; methods / results write-up; evidence site in `docs/` (published) |

Known limitations of r3: EarlyPrint's contextual regularizations (e.g. *then → than*) are accepted
unreviewed; a few contractions that EarlyPrint splits without `join` are emitted with a space
(*'T is*); documents whose EarlyPrint copy omits the text (A04632 masques, A04637 Althorp
entertainment) remain in original spelling.

Not yet in the repository: `texts/` (all-language view), `texts_no_prologue_epilogue/` and its
regularized twin, `kept_nodes.csv` (678 MB) and `node_fates.csv`; a clean-directory rerun of the
reproduction commands; schema fixtures for `test_build_corpus.py`; a regression test for
`build_reg_view.py`. Also not in the repository: `ab_spelling/cast_names_kim.csv` (cast lists derived from
Kim's `corpus_master.xlsx`).
