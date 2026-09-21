#!/usr/bin/env bash
# run_b.sh — the B pipeline: regularized corpus, word-bounded chunks, long-window embedding model.
#
#   bash ab_spelling/run_b.sh smoke     # 20 documents, 1 seed — checks the environment and the model (~10 min)
#   bash ab_spelling/run_b.sh full      # 580 documents: chunk map -> reading sample -> embed -> seeds 42 43 44 -> diagnostics
#   bash ab_spelling/run_b.sh sheet     # naming workbook for the main seed (42): topics_B_s42/topic_sheet.xlsx (+ AI drafts if ab_spelling/drafts/ has them)
#   bash ab_spelling/run_b.sh review    # after editing topic_sheet.xlsx: carry Label / use_in_genre_analysis / Notes into topic_sheet.csv and drafts/
#   bash ab_spelling/run_b.sh pack 9    # critical-reading pack for topic 9: topics_B_s42/reading_pack_T9.md
#   bash ab_spelling/run_b.sh aggregate # chunk -> edition -> work -> genre tables + heatmaps + per-genre topic figures: topics_B_s42/aggregate/ (B_USE=included,candidate)
#   bash ab_spelling/run_b.sh genrefig  # only the per-genre figures (14_genre_figures.py); B_WEIGHT=works|chunks B_USE=all B_GENRES=comedy,tragedy,history B_TOP=20 B_RENORM=1
#   bash ab_spelling/run_b.sh figures   # interactive HTML (topic map, genre x topic, works, table): topics_B_s42/topics_interactive_s42.html
#   bash ab_spelling/run_b.sh map       # chunk-level map (one point per chunk, hover + dropdown highlights): topics_B_s42/chunk_map_s42.html
#                                       # B_DEEP=<DEEP_data.csv> adds company / theater / first-performance (default: the professor's Dropbox copy if present)
#   bash ab_spelling/run_b.sh site      # the whole static site (map, topics, genre, plays, chunks, methods) -> $REPO/docs/ for GitHub Pages
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
SLUG="$(echo "$MODEL" | tr '/' '_' | tr -c 'A-Za-z0-9._-\n' '_')"
NODES=()   # paths contain spaces: pass as an array, never as a word-split string
for cand in "$REPO/build_v3/kept_nodes.csv" "$REPO/../sep6/new_pipeline/out_corpus/corpus-v3-2026-09-08/kept_nodes.csv"; do
  [ -f "$cand" ] && { NODES=(--nodes-csv "$cand"); break; }
done

if [ "$MODE" = "smoke" ]; then
  CH="$OUT_ROOT/chunks_w500_smoke"; RUNS="$OUT_ROOT/runs_smoke_$SLUG"; SEEDS="42"; LIMIT="--limit-docs 20"; MINDF="--min-df 1"
else
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"; SEEDS="42 43 44"; LIMIT=""; MINDF=""
fi
SEED="${B_SEED:-42}"
if [ "$MODE" = "sheet" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  python "$CODE/08_topic_sheet.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --model "$MODEL"
  echo "== sheet: $RUNS/topics_B_s$SEED/topic_sheet.xlsx"; exit 0
fi
if [ "$MODE" = "review" ]; then   # after editing topic_sheet.xlsx: copy Label / use_in_genre_analysis / Notes into topic_sheet.csv + drafts/
  RUNS="$OUT_ROOT/runs_$SLUG"
  python "$CODE/08b_apply_review.py" --runs "$RUNS" --seed "$SEED"; exit 0
fi
if [ "$MODE" = "pack" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  python "$CODE/10_reading_pack.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --topic "${2:?topic id}" --n-works "${B_NWORKS:-5}"; exit 0
fi
if [ "$MODE" = "aggregate" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  python "$CODE/09_aggregate.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --use "${B_USE:-included,candidate}" --min-works "${B_MINWORKS:-10}"
  python "$CODE/14_genre_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --use "${B_USE:-included,candidate}" --min-works "${B_MINWORKS:-10}" --top "${B_TOP:-20}"
  python "$CODE/14_genre_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --use "${B_USE:-included,candidate}" --min-works "${B_MINWORKS:-10}" --top "${B_TOP:-20}" --renorm; exit 0
fi
if [ "$MODE" = "genrefig" ]; then   # e.g. B_WEIGHT=chunks B_USE=all B_GENRES=comedy,tragedy,history  (the old project's figures)
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  python "$CODE/14_genre_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --weight "${B_WEIGHT:-works}" --use "${B_USE:-included,candidate}" \
      --genres "${B_GENRES:-}" --min-works "${B_MINWORKS:-10}" --top "${B_TOP:-20}" ${B_RENORM:+--renorm}; exit 0
fi
if [ "$MODE" = "figures" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  python "$CODE/11_figures.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED"; exit 0
fi
if [ "$MODE" = "site" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  DEEP="${B_DEEP:-$HOME/Library/CloudStorage/Dropbox/Clustering Character Archetypes/early-modern-drama-character-clustering/data/DEEP_data.csv}"
  DEEPARGS=(); [ -f "$DEEP" ] && DEEPARGS=(--deep "$DEEP")
  python "$CODE/13_site.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" --manifest "$MANIFEST" --out "${B_SITE_OUT:-$REPO/docs}" \
      --repo-url "${B_REPO_URL:-https://github.com/a21694114-art/renaissance-drama-corpus-v3}" --credit "${B_CREDIT:-Grace}" ${DEEPARGS[@]+"${DEEPARGS[@]}"}; exit 0
fi
if [ "$MODE" = "map" ]; then
  CH="$OUT_ROOT/chunks_w500"; RUNS="$OUT_ROOT/runs_$SLUG"
  DEEP="${B_DEEP:-$HOME/Library/CloudStorage/Dropbox/Clustering Character Archetypes/early-modern-drama-character-clustering/data/DEEP_data.csv}"
  DEEPARGS=(); [ -f "$DEEP" ] && DEEPARGS=(--manifest "$MANIFEST" --deep "$DEEP")
  python "$CODE/12_map.py" --chunks "$CH" --runs "$RUNS" --seed "$SEED" ${DEEPARGS[@]+"${DEEPARGS[@]}"}; exit 0
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
