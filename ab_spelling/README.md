# ab_spelling — topic model of corpus v3 (the B pipeline)

Chunk-level topic model of the 580 editions / 516 works in corpus v3, built for a comparison
of thematic content across dramatic genres. Everything here runs on the regularized view
(`texts_analysis_en_reg/`, "B"); the original-spelling view ("A") was tried first and dropped
because the long-s glyph alone splits the embedding space (that experiment, `run_ab.sh` and
`04_compare.py`, is kept for the record and is not part of the current pipeline).

Current state (2026-09-25): main analysis = HDBSCAN with `min_samples 10`, seed 42, on
name-masked text with one representative edition per work — 63 clusters, 59.5 % of the
representative editions' chunks unassigned. All 63 clusters received researcher decisions
informed by the keywords, the work concentration and documented AI-assisted readings of sampled
passages (a review of cluster interpretations, not an exhaustive validation of every assigned
chunk): 53 enter the genre comparison (`included`, 36.9 % of the representative editions'
words), 6 are `pending` (reviewed, undecided), 4 are kept for context only. K-means 50 on the same embeddings is kept as a
limited comparison. The evidence site built from this run is in `../docs/`.

## Pipeline

1. **Chunks** (`01_chunk_map.py`) — one chunk map on v3 node indices: consecutive nodes of one
   edition, target 500 words (400–600), cut at node / sentence ends, no overlap, no short
   tails. 17,422 chunks; `chunks_A.csv` (original spelling) and `chunks_B.csv` (regularized)
   hold the same passages.
2. **Name masking** (`01c_mask_names.py`) — character names replaced by `someone`, per play,
   from the cast lists of Kim's character-clustering project (`cast_names_kim.csv`, matched on
   TCP id; `cast_map_overrides.csv` fixes wrong matches). Persons only: places, nations,
   deities, role words and personifications stay. Names that are also common words are masked
   only when capitalised; spelling variants (I/J, u/v, ≥ 0.85 similarity) within the edition
   are caught. 86,736 tokens (1.0 %) replaced; per-edition report in `name_mask_report.csv`.
3. **Embeddings** (`02_embed.py`) — `Qwen/Qwen3-Embedding-0.6B`, 1024-d, max 2048 tokens
   (no chunk is truncated). Per-chunk text hashes; a re-run re-encodes only changed chunks.
4. **Clustering** (`03_topics.py`) — UMAP (5 comp., 15 neighbours, min_dist 0.05, cosine) →
   HDBSCAN (min_cluster_size 30, min_samples 10, eom), seeds 42 / 43 / 44. Fitted on one
   representative edition per work (`edition_selection.csv`: Kim's policy — earliest dated
   edition, Folio for seven Shakespeare plays, Q1 for Lear); the other 64 editions
   (2,052 chunks) are placed afterwards and excluded from the main statistics (`in_fit`).
   `--cluster kmeans --k N` gives the comparison schemes.
5. **Keywords and workbook** (`08_topic_sheet.py`) — class-TF-IDF on one document per cluster
   (min_df 1, max_df 1.0, one stopword list), KeyBERT-style and MMR words, name flags, three
   representative chunks, work concentration, genre mix; written to `topic_sheet.xlsx` with the
   AI drafts and empty `Label` / `Notes` columns.
6. **Review** (`08b_apply_review.py`) — carries the edited workbook back into
   `topic_sheet.csv` (which every later step reads) and into the drafts file; derives
   `review_status` from what changed.
7. **Aggregation** (`09_aggregate.py`) — chunk → edition → work → genre, word-weighted, works
   equal weight, every chunk (outliers included) in the denominator; coverage per genre;
   Kruskal–Wallis with BH correction; heatmaps; a dominant-work check that aggregates each
   concentrated topic again without its dominant work. Genre of a work: British Drama single
   label, else Annals single label, else "other / multi" (`genre_assignment.csv`).
8. **Figures and site** (`14_genre_figures.py`, `12_map.py`, `13_site.py`) — per-genre topic
   figures, the chunk-level interactive map, and the static evidence site in `../docs/`
   (GitHub Pages: map, topics, genre, plays, chunks, methods).

Diagnostics: `05_diagnostics.py` (stability, uniform keywords, work concentration),
`15_crosswalk.py` (cluster matching between two runs), `16_compare_schemes.py` (one table
over HDBSCAN / K-means variants: outliers, single-work clusters, ARI, flip share, name share),
`17_sample_clusters.py` (centre and edge chunks of a few clusters to read).

## Running it

Run from the repository root with the virtual environment active (`~/venv-ab`, Python ≥ 3.11,
`pip install -r ab_spelling/requirements.txt`). The heavy steps need the GPU / MPS: embedding
the corpus takes ~55 min on an M-series Mac; clustering a few minutes per seed.

```
bash ab_spelling/run_b.sh smoke      # 20 editions, one seed — checks the environment
bash ab_spelling/run_b.sh full       # chunk map → reading sample → embed → seeds 42 43 44 → diagnostics (unmasked run)
bash ab_spelling/run_b.sh mask       # masked copy of the chunk texts + per-edition report to review
bash ab_spelling/run_b.sh masked     # embed the masked text → cluster with one edition per work → diagnostics → crosswalk
bash ab_spelling/run_b.sh schemes    # the same embeddings under hdb10 / hdb5 / km30 / km50 / km70 → compare_schemes.md
```

Every later step takes `B_RUNS_SUFFIX` to choose the run; the main analysis is `masked_hdb10`:

```
export B_RUNS_SUFFIX=masked_hdb10
bash ab_spelling/run_b.sh sheet                 # topic_sheet.xlsx with the AI drafts from drafts_masked_hdb10/ (do not re-run after editing the workbook)
bash ab_spelling/run_b.sh review                # after editing the workbook
B_USE=included bash ab_spelling/run_b.sh aggregate   # confirmed topics only (default: included,candidate)
bash ab_spelling/run_b.sh site                  # rebuild ../docs/ — then commit and push
bash ab_spelling/run_b.sh freeze                # copy the small result files of the run into results_masked_hdb10/ (see below)
bash ab_spelling/run_b.sh sample 5              # reading sample of 5 random clusters (or B_TOPICS=6,7,9)
bash ab_spelling/run_b.sh pack 9                # critical-reading pack for one topic
```

Other switches: `B_MODEL`, `B_MAXSEQ`, `B_BATCH`, `B_OUT` (output root), `B_SEED` (main seed),
`B_DEEP` (DEEP export for company / theatre / first-performance fields), `B_WEIGHT`,
`B_GENRES`, `B_TOP`, `B_RENORM` (genre figures), `B_SITE_OUT`, `B_REPO_URL`, `B_CREDIT`.

## Reviewing the workbook

`topic_sheet.xlsx`, sheet `topics`: one row per cluster. The AI columns are `draft_label`,
`pattern_basis` (thematic_discourse / shared_narrative / recurring_role_or_name /
mixed_or_unclear), `use_in_genre_analysis`, `basis` (content note, concentration, suitability
for cross-work comparison), `chunks_read`. The reviewer edits three columns:

- `use_in_genre_analysis` — `included` (enters the genre comparison), `candidate` (proposed,
  not yet confirmed), `contextual_only` (context only — excluded from the comparison: typically
  one work, one story or a mixed cluster; a shared story is not excluded as such), `pending`
  (reviewed, undecided). The AI never writes `included`.
- `Label` — final name; empty means the draft label stands.
- `Notes` — reasons, doubts, what to check; the review of this run cites the chunks read.

`run_b.sh review` validates ids, sizes and values before writing anything, keeps a
`pre_review` snapshot and `.bak` copies, and sets `review_status` (draft_ai → user_confirmed /
user_pending / user_labelled). Work concentration (`dominant_work_share`, `top3_work_share`,
`n_works_ge3`) is a flag to check, not an exclusion rule; the dominant-work check in the
aggregation reports what happens to a concentrated topic's genre result without that work.

## Files in this folder

| File | What it is |
|---|---|
| `run_b.sh` | the driver; all modes and variables are listed in its header |
| `code/01_chunk_map.py` | chunk map v3 (word-bounded, node/sentence boundaries) |
| `code/01c_mask_names.py` | per-play character-name masking |
| `code/02_embed.py` | embeddings with per-chunk hashes and incremental re-encoding |
| `code/03_topics.py` | UMAP + HDBSCAN / K-means, representative-edition fit, placement of other editions |
| `code/05_diagnostics.py` | stability, uniform keywords, concentration, long-s share |
| `code/07_sample_chunks.py` | stratified reading sample of chunks |
| `code/08_topic_sheet.py`, `08b_apply_review.py` | review workbook and its round trip |
| `code/09_aggregate.py` | edition / work / genre tables, tests, heatmaps, dominant-work check |
| `code/10_reading_pack.py` | reading pack for one topic |
| `code/11_figures.py` | interactive topic-level figures (Plotly) |
| `code/12_map.py` | chunk-level interactive map |
| `code/13_site.py` | static site → `../docs/` |
| `code/14_genre_figures.py` | per-genre topic figures |
| `code/15_crosswalk.py`, `16_compare_schemes.py`, `17_sample_clusters.py` | run-to-run matching, scheme table, cluster reading sample |
| `code/01_chunk_map_v2_tokens.py`, `01b_make_A2.py`, `04_compare.py`, `06_recluster_old.py`, `run_ab.sh` | the closed A/B spelling experiment (kept for the record) |
| `edition_selection.csv` | representative edition per work with the policy and basis |
| `cast_map_overrides.csv` | editions whose cast list must be taken from another TCP id |
| `cast_names_kim.csv` | cast lists (from Kim's `corpus_master.xlsx`; not in the public repository) |
| `drafts/`, `drafts_masked_hdb10/` | AI drafts per run (`topic_drafts_B_s42.csv`; `.pre_review.csv` = the drafts before the review); the review writes the decisions back here |
| `results_masked_hdb10/` | frozen result files of the published run (`run_b.sh freeze`): `doc_topics.csv` with `in_fit`, `run.json`, `topic_sheet.csv` with the decisions, the aggregate tables (`config.json`, `genre_assignment.csv`, `genre_coverage.csv`, `genre_topic_mean.csv`, `kruskal_by_topic.csv`, `sensitivity_dominant_work.csv`, …), chunk map and metadata, masking summary, `environment.txt` — enough to trace every published number without the embeddings |
| `requirements.txt` | Python dependencies |

Outputs are written outside the repository, under `../sep6/ab_spelling_out/`:
`chunks_w500/` (chunk map, `chunk_meta.csv`, `chunks_A/B.csv`, `chunks_B_masked.csv`, masking
reports) and one `runs_<model>[_<suffix>]/` per run (`embeddings_B.npy`, `topics_B_s<seed>/`
with `doc_topics.csv`, `run.json`, keyword tables, `topic_sheet.*`, `aggregate/`, maps).

## Notes and limitations

- Roughly 60 % of chunks are HDBSCAN outliers; they stay in every denominator and are reported
  as coverage per genre, never dropped from the corpus.
- Cast lists cover characters as Kim's table names them; nicknames absent from it (e.g. Harry,
  Jack) survive the masking and may still link passages — a possible influence on a few
  clusters, not a demonstrated cause.
- EarlyPrint regularization reaches only part of each text; a few editions keep more of their
  original spelling, which the model can pick up.
- The dominant-work check removes one work at a time; it does not cover several works of one
  author or one story that together dominate a topic. Its p values are exploratory.
- The two clustering schemes share one embedding, so their agreement says nothing about the
  embedding's own biases.
- DEEP fields on the site, and the Annals fallback of the genre rule, come from a full DEEP
  export that is not in the repository; without it `aggregate` warns and keeps the 35
  Annals-placed works in "other / multi", so its genre groups differ from the published ones.
  `cast_names_kim.csv` is not in the repository either. The published analysis is therefore
  traceable from `results_masked_hdb10/`, but not yet reproducible from a fresh clone alone.
