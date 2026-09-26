#!/usr/bin/env bash
# run_b.sh — the B pipeline: regularized corpus, word-bounded chunks, long-window embedding model.
#
#   bash ab_spelling/run_b.sh smoke     # 20 documents, 1 seed — checks the environment and the model (~10 min)
#   bash ab_spelling/run_b.sh full      # 580 documents: chunk map -> reading sample -> embed -> seeds 42 43 44 -> diagnostics
#   bash ab_spelling/run_b.sh sheet     # naming workbook for the main seed (42): topics_B_s42/topic_sheet.xlsx (+ AI drafts if ab_spelling/drafts/ has them)
#   bash ab_spelling/run_b.sh review    # after editing topic_sheet.xlsx: carry Label / use_in_genre_analysis / Notes into topic_sheet.csv and drafts/
#   bash ab_spelling/run_b.sh pack 9    # critical-reading pack for topic 9: topics_B_s42/reading_pack_T9.md
#   bash ab_spelling/run_b.sh aggregate # chunk -> edition -> work -> genre tables + heatmaps + per-genre topic figures: topics_B_s42/aggregate/
#                                       # B_USE=included (confirmed topics only; default included,candidate) — the site reads the choice from aggregate/config.json
#   bash ab_spelling/run_b.sh genrefig  # only the per-genre figures (14_genre_figures.py); B_WEIGHT=works|chunks B_USE=all B_GENRES=comedy,tragedy,history B_TOP=20 B_RENORM=1
#   bash ab_spelling/run_b.sh figures   # interactive HTML (topic map, genre x topic, works, table): topics_B_s42/topics_interactive_s42.html
#   bash ab_spelling/run_b.sh map       # chunk-level map (one point per chunk, hover + dropdown highlights): topics_B_s42/chunk_map_s42.html
#                                       # B_DEEP=<DEEP_data.csv> adds company / theater / first-performance (default: the professor's Dropbox copy if present)
#   bash ab_spelling/run_b.sh site      # the whole static site (map, topics, genre, plays, chunks, methods) -> $REPO/docs/ for GitHub Pages
#   bash ab_spelling/run_b.sh mask      # name-masked copy of the chunk texts + the list of masked/kept names to REVIEW (01c_mask_names.py)
#                                       # optional ab_spelling/name_mask_overrides.csv (scope,token,decision) corrects single decisions; cast_map_overrides.csv fixes cast-list matches; re-run mask after editing
#   bash ab_spelling/run_b.sh masked    # second run on the masked texts: embed (~55 min) -> seeds 42 43 44 with one edition per work -> diagnostics
#                                       # -> crosswalk against the main run; output runs_<model>_masked/ (B_DEDUP=0 keeps all editions in the fit)
#   bash ab_spelling/run_b.sh dedup     # re-cluster the EXISTING embeddings with one edition per work (minutes): runs_<model>_dedup/ + crosswalk
#   bash ab_spelling/run_b.sh schemes   # the masked embeddings under other clustering schemes (B_SCHEMES="hdb10 hdb5 km30 km50 km70"):
#                                       # runs_<model>_masked_<scheme>/ each with seeds 42 43 44, then one table: runs_<model>_masked/compare_schemes.md
#   bash ab_spelling/run_b.sh compare   # only recompute that table from the existing scheme dirs (16_compare_schemes.py)
#   B_RUNS_SUFFIX=masked_km50 bash ab_spelling/run_b.sh sample [5]   # reading sample: centre + edge chunks of N random clusters (17_sample_clusters.py)
#   B_RUNS_SUFFIX=masked_hdb10 bash ab_spelling/run_b.sh freeze   # copy the small result files that let a reader trace the published analysis
#                                       # (doc_topics, run.json, topic_sheet.csv, aggregate tables, chunk map/meta, environment) into ab_spelling/results_<suffix>/
#   B_RUNS_SUFFIX=masked bash ab_spelling/run_b.sh sheet|review|pack|aggregate|genrefig|figures|map|site   # run any later step on that second run
#                                       # (its drafts / decisions live in ab_spelling/drafts_masked/)
#                                       # B_SITE_OUT, B_REPO_URL, B_CREDIT override the output folder, the GitHub link and the footer credit
#
# Environment variables (optional):
#   B_MODEL   embedding model (default Qwen/Qwen3-Embedding-0.6B, 32k window, native in transformers 5;
#             Alibaba-NLP/gte-large-en-v1.5 needs transformers<5 — its custom code broke on 5.x, 2026-09-20)
#   B_MAXSEQ  max tokens fed to the model (default 2048; must exceed chunk_map_summary.json tokens_max)
#   B_BATCH   batch size (default 8)
#   B_OUT     output root (default ../sep6/ab_spelling_out)
# Run from the repository root (renaissance_drama_corpus_v3/) with ~/venv-ab activated.
set -euo pipefail
export PYTHONUNBUFFERED=1   # progress lines reach the terminal through tee immediately
MODE="${1:-smoke}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CODE="$REPO/ab_spelling/code"
OUT_ROOT="${B_OUT:-$REPO/../sep6/ab_spelling_out}"
MANIFEST="$REPO/build_v3/corpus_manifest.csv"
MODEL="${B_MODEL:-Qwen/Qwen3-Embedding-0.6B}"
MAXSEQ="${B_MAXSEQ:-2048}"
BATCH="${B_BATCH:-8}"
SLUG="$(echo "$MODEL" | tr '/' '_' | tr -c 'A-Za-z0-9._\n-' '_')"
RUNS_SUFFIX="${B_RUNS_SUFFIX:+_$B_RUNS_SUFFIX}"         # e.g. B_RUNS_SUFFIX=masked -> runs_<model>_masked/, drafts in ab_spelling/drafts_masked/
DRAFTS_DIR="$REPO/ab_spelling/drafts$RUNS_SUFFIX"
NODES=()   # paths contain spaces: pass as an array, never as a word-split string
for cand in "$REPO/build_v3/kept_nodes.csv" "$REPO/../sep6/new_pipeline/out_corpus/corpus-v3-2026-09-08/kept_nodes.csv"; do
  [ -f "$cand" ] && { NODES=(--nodes-csv "$cand"); break; }
done

if [ "$MODE" = "smoke" ]; then
  CH="$OUT_ROOT/chunks_w500_smoke"; RUNS="$OUT_ROOT/runs_smoke_$SLUG"; SEEDS="42"; LIMIT="--limit-docs 20"; MINDF="--min-df 1"
else
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"; SEEDS="42 43 44"; LIMIT=""; MINDF=""
fi
SEED="${B_SEED:-42}"
if [ "$MODE" = "freeze" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"; D="$RUNS/topics_B_s$SEED"; RES="$REPO/ab_spelling/results$RUNS_SUFFIX"
  mkdir -p "$RES/topics_B_s$SEED/aggregate" "$RES/chunks_w500"
  for f in doc_topics.csv run.json topic_sheet.csv topic_sheet_coverage.csv top_words_uniform10.csv secondary_editions_placed.csv; do [ -f "$D/$f" ] && cp "$D/$f" "$RES/topics_B_s$SEED/"; done
  for f in config.json genre_assignment.csv genre_coverage.csv genre_topic_mean.csv genre_topic_conditional.csv kruskal_by_topic.csv sensitivity_dominant_work.csv other_multi_works.csv work_topic_share.csv aggregate_summary.md; do [ -f "$D/aggregate/$f" ] && cp "$D/aggregate/$f" "$RES/topics_B_s$SEED/aggregate/"; done
  for f in chunk_map.csv chunk_meta.csv chunk_map_summary.json name_mask_summary.json name_mask_report.csv; do [ -f "$CH/$f" ] && cp "$CH/$f" "$RES/chunks_w500/"; done
  [ -f "$RUNS/embedding_B.json" ] && cp "$RUNS/embedding_B.json" "$RES/"
  [ -f "$RUNS/compare_schemes.md" ] && cp "$RUNS/compare_schemes.md" "$RES/"; [ -f "$RUNS/compare_schemes.csv" ] && cp "$RUNS/compare_schemes.csv" "$RES/"
  { echo "python $(python --version 2>&1)"; echo "platform $(uname -sm)"; echo "frozen $(date -u +%Y-%m-%dT%H:%MZ) from $RUNS seed $SEED"; echo; pip freeze; } > "$RES/environment.txt"
  echo "== frozen result files → $RES  (not included: embeddings, chunk texts, cast lists, the DEEP export)"; exit 0
fi

if [ "$MODE" = "sheet" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  python "$CODE/08_topic_sheet.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --model "$MODEL" --drafts "$DRAFTS_DIR/topic_drafts_B_s$SEED.csv"
  echo "== sheet: $RUNS/topics_B_s$SEED/topic_sheet.xlsx"; exit 0
fi
if [ "$MODE" = "review" ]; then   # after editing topic_sheet.xlsx: copy Label / use_in_genre_analysis / Notes into topic_sheet.csv + drafts/
  RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  python "$CODE/08b_apply_review.py" --runs "$RUNS" --seed "$SEED" --drafts "$DRAFTS_DIR/topic_drafts_B_s$SEED.csv"
  echo "== next: B_USE=included bash ab_spelling/run_b.sh aggregate   (then: bash ab_spelling/run_b.sh site; git add docs; commit; push)"; exit 0
fi
if [ "$MODE" = "pack" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  python "$CODE/10_reading_pack.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --topic "${2:?topic id}" --n-works "${B_NWORKS:-5}"; exit 0
fi
if [ "$MODE" = "aggregate" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  DEEP="${B_DEEP:-$HOME/Library/CloudStorage/Dropbox/Clustering Character Archetypes/early-modern-drama-character-clustering/data/DEEP_data.csv}"
  DEEPARGS=(); [ -f "$DEEP" ] && DEEPARGS=(--manifest "$MANIFEST" --deep "$DEEP")   # enables the Annals fallback for compound / missing British Drama labels
  python "$CODE/09_aggregate.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --use "${B_USE:-included,candidate}" --min-works "${B_MINWORKS:-10}" ${DEEPARGS[@]+"${DEEPARGS[@]}"}
  python "$CODE/14_genre_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --use "${B_USE:-included,candidate}" --min-works "${B_MINWORKS:-10}" --top "${B_TOP:-20}"
  python "$CODE/14_genre_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --use "${B_USE:-included,candidate}" --min-works "${B_MINWORKS:-10}" --top "${B_TOP:-20}" --renorm; exit 0
fi
if [ "$MODE" = "genrefig" ]; then   # e.g. B_WEIGHT=chunks B_USE=all B_GENRES=comedy,tragedy,history  (the old project's figures)
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  python "$CODE/14_genre_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --weight "${B_WEIGHT:-works}" --use "${B_USE:-included,candidate}" \
      --genres "${B_GENRES:-}" --min-works "${B_MINWORKS:-10}" --top "${B_TOP:-20}" ${B_RENORM:+--renorm}; exit 0
fi
if [ "$MODE" = "figures" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  python "$CODE/11_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED"; exit 0
fi
if [ "$MODE" = "site" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  DEEP="${B_DEEP:-$HOME/Library/CloudStorage/Dropbox/Clustering Character Archetypes/early-modern-drama-character-clustering/data/DEEP_data.csv}"
  DEEPARGS=(); [ -f "$DEEP" ] && DEEPARGS=(--deep "$DEEP")
  python "$CODE/13_site.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --manifest "$MANIFEST" --out "${B_SITE_OUT:-$REPO/docs}" \
      --repo-url "${B_REPO_URL:-https://github.com/a21694114-art/renaissance-drama-corpus-v3}" --credit "${B_CREDIT:-Grace}" ${DEEPARGS[@]+"${DEEPARGS[@]}"} ${B_USE:+--use "$B_USE"}; exit 0
fi
if [ "$MODE" = "map" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  DEEP="${B_DEEP:-$HOME/Library/CloudStorage/Dropbox/Clustering Character Archetypes/early-modern-drama-character-clustering/data/DEEP_data.csv}"
  DEEPARGS=(); [ -f "$DEEP" ] && DEEPARGS=(--manifest "$MANIFEST" --deep "$DEEP")
  python "$CODE/12_map.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" ${DEEPARGS[@]+"${DEEPARGS[@]}"}; exit 0
fi
if [ "$MODE" = "mask" ]; then
  CH="$OUT_ROOT/chunks_w500"; OVR=(); [ -f "$REPO/ab_spelling/name_mask_overrides.csv" ] && OVR=(--overrides "$REPO/ab_spelling/name_mask_overrides.csv")
  python "$CODE/01c_mask_names.py" --chunks "$CH" --manifest "$MANIFEST" --cast "$REPO/ab_spelling/cast_names_kim.csv" ${OVR[@]+"${OVR[@]}"}
  echo "== review $CH/name_mask_report.csv (per edition) and name_mask_suggestions.csv (not masked); corrections go to ab_spelling/name_mask_overrides.csv (scope,token,decision), then re-run mask"
  echo "== then: caffeinate -i bash ab_spelling/run_b.sh masked"; exit 0
fi
if [ "$MODE" = "masked" ] || [ "$MODE" = "dedup" ]; then
  CH="$OUT_ROOT/chunks_w500"; MAIN="$OUT_ROOT/runs_$SLUG"; RUNS2="$OUT_ROOT/runs_${SLUG}_$MODE"; mkdir -p "$RUNS2"
  exec > >(tee -a "$RUNS2/run_b.log") 2>&1; echo "== run_b.sh $MODE  model $MODEL  $(date)"
  DEDUP="--dedup-editions"; [ "${B_DEDUP:-1}" = "0" ] && DEDUP=""
  if [ "$MODE" = "masked" ]; then
    [ -f "$CH/chunks_B_masked.csv" ] || { echo "no $CH/chunks_B_masked.csv — run: bash ab_spelling/run_b.sh mask"; exit 1; }
    if [ -f "$RUNS2/embeddings_B.npy" ]; then   # stale check: the masked text must be the one these embeddings were computed from
      if python - "$CH/chunks_B_masked.csv" "$RUNS2/embedding_B.json" <<'PY'
import hashlib, json, sys
h = hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest(); j = json.load(open(sys.argv[2]))
sys.exit(0 if j.get('text_sha256') == h else 1)
PY
      then echo "== embeddings up to date"; else
        echo "== the masked text changed since the embeddings were computed: re-encoding only the changed chunks (02_embed --reuse-from)"
        CHG=(); [ -f "$CH/name_mask_changed_chunks.csv" ] && CHG=(--changed "$CH/name_mask_changed_chunks.csv")
        python "$CODE/02_embed.py" --variant B --chunks "$CH" --out "$RUNS2" --text-file "$CH/chunks_B_masked.csv" --model "$MODEL" --max-seq-length "$MAXSEQ" --batch-size "$BATCH" \
            --reuse-from "$RUNS2" ${CHG[@]+"${CHG[@]}"}
      fi
    else
      python "$CODE/02_embed.py" --variant B --chunks "$CH" --out "$RUNS2" --text-file "$CH/chunks_B_masked.csv" --model "$MODEL" --max-seq-length "$MAXSEQ" --batch-size "$BATCH"
    fi
    EMB=(); EMBFILE="$RUNS2/embeddings_B.npy"
  else
    EMB=(--emb-runs "$MAIN"); EMBFILE="$MAIN/embeddings_B.npy"
  fi
  for S in 42 43 44; do   # a topics dir is reused only if it was fitted on exactly these embeddings (sha256 in run.json)
    if [ -f "$RUNS2/topics_B_s$S/run.json" ] && python - "$EMBFILE" "$RUNS2/topics_B_s$S/run.json" <<'PY'
import hashlib, json, sys
sys.exit(0 if json.load(open(sys.argv[2])).get('embeddings_sha256') == hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest() else 1)
PY
    then echo "== topics_B_s$S up to date"; else
      rm -rf "$RUNS2/topics_B_s$S"; python "$CODE/03_topics.py" --variant B --seed "$S" --chunks "$CH" --runs "$RUNS2" $DEDUP ${EMB[@]+"${EMB[@]}"}
    fi
  done
  python "$CODE/05_diagnostics.py" --chunks "$CH" --runs "$RUNS2" --variants B --seeds 42,43,44 || echo "(diagnostics failed — not fatal)"
  python "$CODE/15_crosswalk.py" --old "$MAIN/topics_B_s42" --new "$RUNS2/topics_B_s42" --sheet "$MAIN/topics_B_s42/topic_sheet.csv"
  echo "== done $(date): $RUNS2   crosswalk: $RUNS2/topics_B_s42/crosswalk.md"
  echo "== to continue on this run: B_RUNS_SUFFIX=$MODE bash ab_spelling/run_b.sh sheet   (then review / aggregate / site with the same prefix)"; exit 0
fi
if [ "$MODE" = "compare" ]; then
  CH="$OUT_ROOT/chunks_w500"; BASE="${B_SCHEMES_BASE:-$OUT_ROOT/runs_${SLUG}_masked}"; RUNSET=(); LABELS=()
  for sch in ${B_SCHEMES:-hdb10 hdb5 km30 km50 km70}; do [ -d "${BASE}_$sch" ] && { RUNSET+=("${BASE}_$sch"); LABELS+=("$sch"); }; done
  python "$CODE/16_compare_schemes.py" --chunks "$CH" --runs "$BASE" ${RUNSET[@]+"${RUNSET[@]}"} --labels hdb30 ${LABELS[@]+"${LABELS[@]}"} --out "$BASE/compare_schemes.md"; exit 0
fi
if [ "$MODE" = "sample" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG$RUNS_SUFFIX"
  python "$CODE/17_sample_clusters.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --n "${2:-5}" --works "${B_NWORKS:-3}" ${B_TOPICS:+--topics "$B_TOPICS"}; exit 0
fi
if [ "$MODE" = "schemes" ]; then
  CH="$OUT_ROOT/chunks_w500"; BASE="${B_SCHEMES_BASE:-$OUT_ROOT/runs_${SLUG}_masked}"
  [ -f "$BASE/embeddings_B.npy" ] || { echo "no $BASE/embeddings_B.npy — run masked first"; exit 1; }
  exec > >(tee -a "$BASE/run_b.log") 2>&1; echo "== run_b.sh schemes on $BASE  $(date)"
  DEDUP="--dedup-editions"; [ "${B_DEDUP:-1}" = "0" ] && DEDUP=""
  RUNSET=(); LABELS=()
  for sch in ${B_SCHEMES:-hdb10 hdb5 km30 km50 km70}; do
    RX="${BASE}_$sch"; mkdir -p "$RX"
    for f in embeddings_B.npy embedding_ids_B.csv embedding_B.json embedding_text_hashes_B.csv; do [ -e "$RX/$f" ] || ln -s "$BASE/$f" "$RX/$f"; done
    case "$sch" in
      hdb*) ARGS=(--cluster hdbscan --min-samples "${sch#hdb}");;
      km*)  ARGS=(--cluster kmeans --k "${sch#km}");;
      *) echo "unknown scheme $sch (use hdbN or kmN)"; exit 1;;
    esac
    for S in 42 43 44; do
      UF=(); [ "${sch#hdb}" != "$sch" ] && [ -f "$BASE/topics_B_s$S/umap5.npy" ] && UF=(--umap-from "$BASE/topics_B_s$S")
      [ -f "$RX/topics_B_s$S/run.json" ] || python "$CODE/03_topics.py" --variant B --seed "$S" --chunks "$CH" --runs "$RX" $DEDUP "${ARGS[@]}" ${UF[@]+"${UF[@]}"}
    done
    RUNSET+=("$RX"); LABELS+=("$sch")
  done
  python "$CODE/16_compare_schemes.py" --chunks "$CH" --runs "$BASE" "${RUNSET[@]}" --labels hdb30 "${LABELS[@]}" --out "$BASE/compare_schemes.md"
  echo "== done $(date): $BASE/compare_schemes.md   (to continue on one scheme: B_RUNS_SUFFIX=masked_km50 bash ab_spelling/run_b.sh sheet)"; exit 0
fi
mkdir -p "$RUNS"
LOG="$RUNS/run_b.log"; exec > >(tee -a "$LOG") 2>&1
echo "== run_b.sh $MODE  model $MODEL  $(date)"

[ -f "$CH/chunk_map.csv" ] || python "$CODE/01_chunk_map.py" --corpus "$REPO" --manifest "$MANIFEST" --out "$CH" \
    --target-words 500 --min-words 400 --max-words 600 --tokenizer "$MODEL" --max-tokens "$MAXSEQ" ${NODES[@]+"${NODES[@]}"} $LIMIT
[ -f "$CH/reading_sample.md" ] || python "$CODE/07_sample_chunks.py" --chunks "$CH" --out "$CH/reading_sample.md" --corpus "$REPO" --n 20
[ -f "$RUNS/embeddings_B.npy" ] || python "$CODE/02_embed.py" --variant B --chunks "$CH" --out "$RUNS" \
    --model "$MODEL" --max-seq-length "$MAXSEQ" --batch-size "$BATCH"
for S in $SEEDS; do
  [ -f "$RUNS/topics_B_s$S/run.json" ] || python "$CODE/03_topics.py" --variant B --seed "$S" --chunks "$CH" --runs "$RUNS" $MINDF
done
python "$CODE/05_diagnostics.py" --chunks "$CH" --runs "$RUNS" --variants B --seeds "$(echo $SEEDS | tr ' ' ,)"
echo "== done $(date)"
echo "   chunks:      $CH/chunk_map_summary.json   reading sample: $CH/reading_sample.md"
echo "   diagnostics: $RUNS/diagnostics/diagnostics.md"
