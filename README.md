# Renaissance Drama Corpus v3

A corpus of early modern English drama (1520–1641) prepared for computational analysis,
built from the EEBO-TCP XML with DEEP metadata and a spelling-regularized view derived from
EarlyPrint. 582 editions of 518 works; 580 English analysis documents (46.5 M characters).

Each line in the frozen original-spelling output is linked in `kept_nodes.csv` to a source
file (SHA-256), an XPath and a text hash. The regularized view retains the same document
names and line order, so each line can be linked back to that source node. Selection rules
and contextual decisions are recorded in code and tables; the builder checks their
applicable provenance and consistency constraints on each run. The current release is **v3** (frozen 2026-09-08); the regularized view is
**r3** (2026-09-14).

## Pipeline

```
EEBO-TCP XML (469 files) + DEEP metadata
   │
   ▼  1. unit extraction — split collections into plays, tag every <l>/<p> with provenance
   ▼  2. work mapping — attach each unit to a DEEP work / edition; choose witnesses
   ▼  3. performance-text selection — keep spoken, sung and recited text; record every decision
   ▼  4. verification — coverage, regression tests, freeze gate, read-back
   ▼  5. spelling regularization — align to EarlyPrint, apply its `reg` (separate view)
   ▼
texts_analysis_en/  ·  texts_analysis_en_reg/  ·  supplementary/  ·  manifests
   │
   ▼  6. chunking — ~500-word chunks cut at node / sentence ends (17,422)         ab_spelling/
   ▼  7. name masking — character names → "someone", play by play, from cast lists
   ▼  8. embedding — Qwen3-Embedding-0.6B on the masked text
   ▼  9. clustering — UMAP + HDBSCAN on one representative edition per work; K-means kept as a comparison
   ▼ 10. review — keywords, AI drafts, workbook; every cluster read and classified by hand
   ▼ 11. genre comparison — chunk → edition → work → genre; dominant-work check
   ▼
docs/  —  evidence site: map · topics · genre · plays · chunks · methods
```

Steps 1–5 are documented below; steps 6–11 in `ab_spelling/README.md`, and the parameters actually
used on the site's Methods page.

### 1. Sources

- **EEBO-TCP**: 469 XML files (Phase I and II), identified by TCP id (`A00456` …). The files
  themselves are not redistributed. All 469 source ids and SHA-256 values are recorded in
  `build_v3/inputs_units_manifest.csv`; `build_v3/corpus_manifest.csv` identifies the sources
  used by the selected editions.
- **DEEP** (Database of Early English Playbooks, Farmer & Lesser): work, edition, date, genre
  and playing-company metadata; the extract used is `decision_tables/deep_min.csv`.
- **EarlyPrint** (Northwestern / Washington University in St. Louis): linguistically annotated
  EEBO-TCP, used for the regularized view only. The local download contains 466 files;
  the English views use 461 distinct source files, whose Bitbucket commits and SHA-256
  values are recorded in `build_v3_reg/reg_manifest.csv`.

### 2. Units and work mapping (`extract_units.py`, `build_unit_map.py`)

A TCP file may hold one play, a collection of plays, or a play bound with other material.
`extract_units.py` splits each file into units — one per inner `<text>` of a `<group>`, one
per top-level division of a collection, with further splits where a division contains several
work-type divisions (masque, entertainment, pageant, play, tragedy, comedy, interlude,
dialogue). Residual content outside the identified divisions is retained as candidate
material, and front/back matter is recorded separately. The candidate universe comprises
outermost `<l>`/`<p>` nodes under the text, excluding nodes inside containers such as
`<speaker>`, `<stage>`, `<note>`, `<head>`, `<gap>`, `<figure>` and `<fw>`. Each candidate
carries its source/node location, structural context and source SHA-256 (1,055,990 nodes).
Per-node text hashes are recorded in the relevant decision and retained-node tables.

`build_unit_map.py` attaches units to DEEP works and editions (one-to-one TCP ids, title
matching, collection order), with recorded overrides and corrections in `decision_tables/`.
`edition_witness_selection.csv` selects a representative where multiple source transcriptions
are assigned to the same effective edition; `date_resolutions.csv` records date decisions;
`deep_additions.csv` supplies verified DEEP records missing or incorrectly represented in the
local extract; edition-correction files and `manual_overrides.csv` record other mappings.

An XML unit, an edition document and a work are different levels. Components belonging to
one selected edition can form one output document. Separate editions of the same work may
remain separate documents; the work count groups documents by DEEP `work_id`. Duplicate
metadata rows do not create duplicate copies of the same source text.

### 3. Performance-text selection (`node_language.py`, `frames_attribution.py`, `build_corpus.py`)

The corpus targets language presented as spoken, sung or recited in performance. Selection
combines structural XML rules with recorded contextual judgments developed with Claude and
ChatGPT. Research-scope and policy choices were set by the researcher; the scripts apply
those decisions and verify provenance and consistency.

Reviewed chorus, narrator and single-speaker passages outside `<sp>` can be retained
(Seneca translations, early plays, masques). Publishing and editorial matter, including
book-level dedications and plot summaries, is excluded under the recorded rules and
decisions. Borderline material is assessed in context. The principal decision records are:

- `container_audits.csv` (606 audit records), `body_node_decisions.csv` (5,802 individual nodes,
  each with its text hash), `frames_rules.csv` / `frames_decisions.csv` (prologues, epilogues,
  inductions, choruses and songs printed in front or back matter, attributed to their edition);
- `policy_decisions.csv`: the eight corpus-wide policy choices (e.g. printed English
  translations of Latin speeches are included with `relation = translation`; a prologue shared
  by two plays is included once);
- `unit_language.csv` / `node_language.py`: language per node (`en`, `la`, `sco`, `fr`, `es`),
  overriding TCP's `xml:lang` where it is wrong.

Material that belongs to the printed book but not to the analysis boundary — unattributed
prologues, a Scots play outside DEEP's scope, Latin civic poems — is written to
`supplementary/` with full provenance rather than dropped. Of the 1,055,990 candidate nodes,
959,342 are kept, 89,920 excluded with a reason, 6,728 supplementary; none pending.

### 4. Verification (`coverage_check.py`, `test_build_corpus.py`)

- Extraction coverage: candidates independently enumerated from the source XML are
  reconciled against the extraction tables (0 missing, 0 duplicated). The builder also
  assigns each candidate exactly one fate.
- Regression suite: 51 tests on `build_corpus.py` contracts. These are separate from the
  checks of the EarlyPrint regularization step.
- Freeze gate: the dry-run reports validation failures and unresolved decisions without
  releasing a corpus. A formal build is blocked by the implemented integrity checks,
  including stale node-decision hashes, unresolved required decisions, duplicate node
  claims and failed reconciliation.
- Read-back: all 1,749 emitted text files, including supplementary texts, were checked
  against their planned node sequences (0 mismatches). A separate reproduction run
  regenerated the frozen outputs and verified matching file hashes.

### 5. Spelling regularization (`build_reg_view.py`, view r3)

Original spelling is kept in `texts_analysis_en/`. A second view applies EarlyPrint's
regularized spelling (`reg`) token by token:

1. each kept node is aligned to a candidate EarlyPrint `<l>`/`<p>` using exact anchors,
   monotone fuzzy pairing and subsequence matching for lacunae or merged blocks. EarlyPrint
   can supply corrected transcriptions and restored letters or words where available;
   pairing alone does not establish that every source gap has been restored;
2. within that block the node's own words are aligned to EarlyPrint tokens; tokens EarlyPrint
   links with `join` (contractions: *I+le*, *'T+is*) are one unit, so a span never cuts a
   contraction, and a node whose first or last word cannot be located is not taken from
   EarlyPrint;
3. `reg` is applied as EarlyPrint gives it, with three mechanical guards: garbage values (no
   letters, mixed inner case, a POS tag leaked into `reg`) are ignored, proper nouns whose
   `reg` is lower-cased keep their form (*Iago*, not *jago*), and split sub-tokens are glued
   back. EarlyPrint's contextual choices (*then → than*, 11,918 times) are accepted unreviewed.

Nodes without an acceptable block or word-span match keep their v3 text with only long *s*
and word-initial *VV* normalized. Result: 99.53 % of nodes paired (a coverage figure, not a
verified accuracy); accepted `reg` values used for 1,653,784 of 8,685,320 token positions
(19.0 %); 82,909 distinct
surface → reg pairs (`build_v3_reg/reg_pairs_texts_analysis_en.csv`). The EarlyPrint copies
of A04632 and A04637 omit certain ending masques/entertainments and the Althorp text,
respectively, so the affected documents use the fallback text. Whether regularization improves embeddings is to
be tested against the original-spelling view with an identical, node-based chunk map.

## Files

| Path | Content |
|---|---|
| `texts_analysis_en/` | **analysis corpus, original spelling**: 580 English documents, one line per kept node; file name `<edition_id>__<TCP id>.txt` |
| `texts_analysis_en_reg/` | the same 580 documents, line for line, EarlyPrint-regularized |
| `supplementary/` | 7 documents outside the analysis boundary, with provenance |
| `build_v3/corpus_manifest.csv` | one row per edition: DEEP work/edition ids, title, author, year, genre, company type, TCP id and source SHA-256, witness role, node counts by role/language, SHA-256 of each view |
| `build_v3/` | `supplementary_manifest.csv`, `supplementary_nodes.csv`, `excluded_nodes_summary.csv`, `inputs_unit_map.csv`, `inputs_units_manifest.csv`, `FREEZE_REPORT.md`, `release_checklist.md` |
| `build_v3_reg/` | `reg_manifest.csv` (per-document alignment and replacement counts, EarlyPrint commit + SHA-256), `reg_pairs_*.csv`, `unaligned_nodes.jsonl`, `summary.json` |
| `decision_tables/` | curated metadata and decision tables; generated extraction tables are created during rebuilding (see §2–3) |
| `code/` | the pipeline scripts, in run order (see §2–5) |
| `reports/` | build reports for each version and for the regularized view (in Chinese) — the internal record of how the tables were arrived at |

The repository directly distributes the two English views listed above. The frozen build
also produces an all-language view (`texts/`) and an English view without prologues and
epilogues (`texts_no_prologue_epilogue/`); regularization also produces
`texts_no_prologue_epilogue_reg/`. These additional views are not currently included here.

Also omitted because of size are `kept_nodes.csv` (one row per kept node and view, 678 MB)
and `node_fates.csv`. They are generated by `build_corpus.py` and provide the detailed
source-to-output audit trail. A full rebuild requires the source XML matching the recorded
hashes; the published TXT files can be used without rebuilding.

## Corpus at a glance (v3)

| | |
|---|---|
| Editions / works | 582 / 518 |
| Years | 1520–1641 |
| Source files | 469 EEBO-TCP XML |
| Kept nodes | 959,342 (en 955,792 · la 2,183 · sco 1,364 · fr 2 · es 1) |
| Kept nodes by role | dramatic body 933,421 · chorus 5,939 · song 5,547 · speech 4,794 · prologue 4,685 · poem 2,166 · epilogue 2,121 · induction 669 |
| English analysis view | 580 documents, 46,498,315 characters |
| Regularized view | 580 documents, 45,835,479 characters, accepted `reg` values used at 19.0 % of token positions |

## Topic model and evidence site

The chunk-level topic model built on this corpus, its review workbook and the aggregation by
genre live in `ab_spelling/` (see its README). The static evidence site generated from it —
interactive map, one page per topic, play and chunk, genre comparison, methods — is in `docs/`
and published at https://a21694114-art.github.io/renaissance-drama-corpus-v3/.

## Reproducing

The scripts use Python 3.10 and `lxml`; other imports are from the standard library.
Before running, obtain the 469 TCP XML files listed in
`build_v3/inputs_units_manifest.csv`, verify their hashes and place them in
`tcp_drama/` at the repository root. Obtain the pinned EarlyPrint XML files and their
download manifest for the regularized view.

The current scripts read decision tables from their own directory. Copy the published
tables into `code/` before running. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install lxml

cp decision_tables/*.csv code/
cp decision_tables/*.json code/
cd code

python extract_units.py
python coverage_check.py
python node_language.py
python build_unit_map.py
python frames_attribution.py
python test_build_corpus.py
python build_corpus.py --version corpus-v3-2026-09-08 --dry-run
# Continue only after resolving any failures or pending decisions reported above.
python build_corpus.py --version corpus-v3-2026-09-08
python build_reg_view.py \
  --ep-dir "/absolute/path/to/earlyprint/xml" \
  --ep-manifest "/absolute/path/to/download_manifest.csv" \
  --out out_corpus/corpus-v3-reg-2026-09-14-r3
```

Replace the two absolute paths with the actual EarlyPrint locations. The outputs are
created under `code/out/` and `code/out_corpus/`; they are not written into the published
TXT directories at the repository root. A formal corpus build refuses to overwrite an
existing release directory. The 51-test suite uses schemas from the generated `out/`
tables, which is why it follows extraction and mapping in this sequence.


## Versions

| Version | Date | Content |
|---|---|---|
| corpus v1 | 2026-09-07 | first audited build (577 editions) |
| corpus v2 | 2026-09-08 | collection splits and DEEP reconnections (582 editions) |
| **corpus v3** | 2026-09-08 | eight policy decisions applied; supplementary material separated — **current** |
| reg r3 | 2026-09-14 | EarlyPrint-regularized view of v3 (join-group token spans) — **current** |

Details of each version are in `reports/`.

## Sources and licences

- EEBO-TCP texts: Text Creation Partnership, Phase I (public domain) and Phase II (freely
  available since 2021).
- DEEP: Database of Early English Playbooks, ed. Alan B. Farmer and Zachary Lesser.
- EarlyPrint: Martin Mueller, Anupam Basu et al.; the project specifies
  [CC BY-NC 3.0 Unported for its texts](https://earlyprint.org/about/#licenses).
  EarlyPrint is used for the regularized view.

These notices describe the upstream materials. A separate licence for this project's
code and decision tables has not yet been specified.