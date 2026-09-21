#!/usr/bin/env bash
# run_ab.sh — A/B: original spelling (A), long-s/VV-normalized only (A2), EarlyPrint-regularized (B); same chunk map, same settings.
#
#   bash run_ab.sh smoke      # 20 documents, 1 seed  (~10 min on Apple silicon)  — check the pipeline
#   bash run_ab.sh full       # 580 documents, seeds 42 43 44, chunk map v2 (token-bounded) -> chunks_v2/, runs_v2/
#                             # variants: B only by default (the analysis input); AB_VARIANTS="A A2 B" to repeat the comparison
#   bash run_ab.sh diag       # only 05_diagnostics on the FIRST run (chunks/, runs/): leaf vs eom, uniform keywords, work concentration
#
# Run from the repository root (renaissance_drama_corpus_v3/). Needs the environment in
# ab_spelling/requirements.txt (python3 -m venv .venv-ab && source .venv-ab/bin/activate &&
# pip install -r ab_spelling/requirements.txt). Outputs go to ../sep6/ab_spelling_out/ by default.
set -euo pipefail
MODE="${1:-smoke}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CODE="$REPO/ab_spelling/code"
OUT_ROOT="${AB_OUT:-$REPO/../sep6/ab_spelling_out}"
REG_PAIRS="$REPO/build_v3_reg/reg_pairs_texts_analysis_en.csv"
MANIFEST="$REPO/build_v3/corpus_manifest.csv"

if [ "$MODE" = "smoke" ]; then
  CH="$OUT_ROOT/chunks_smoke"; RUNS="$OUT_ROOT/runs_smoke"; SEEDS="42"; LIMIT="--limit-docs 20"; MINDF="--min-df 1"
else
  # v2 chunk map: bounded by GTE-large tokens in BOTH variants, long nodes split at shared sentence indices
  CH="$OUT_ROOT/chunks_v2"; RUNS="$OUT_ROOT/runs_v2"; SEEDS="42 43 44"; LIMIT="--max-tokens 480"; MINDF=""
fi
if [ "$MODE" = "diag" ]; then
  CH="$OUT_ROOT/chunks"; RUNS="$OUT_ROOT/runs"
  python "$CODE/05_diagnostics.py" --chunks "$CH" --runs "$RUNS" --variants A,B --seeds 42,43,44
  echo "== diagnostics written to $RUNS/diagnostics/"; exit 0
fi
VARIANTS="${AB_VARIANTS:-B}"
mkdir -p "$RUNS"
LOG="$RUNS/run_ab.log"; exec > >(tee -a "$LOG") 2>&1
echo "== run_ab.sh $MODE  $(date)"

[ -f "$CH/chunk_map.csv" ] || python "$CODE/01_chunk_map.py" --corpus "$REPO" --manifest "$MANIFEST" --out "$CH" $LIMIT
case " $VARIANTS " in *" A2 "*) [ -f "$CH/chunks_A2.csv" ] || python "$CODE/01b_make_A2.py" "$CH";; esac
for V in $VARIANTS; do
  [ -f "$RUNS/embeddings_$V.npy" ] || python "$CODE/02_embed.py" --variant "$V" --chunks "$CH" --out "$RUNS"
done
for S in $SEEDS; do
  for V in $VARIANTS; do
    [ -f "$RUNS/topics_${V}_s$S/run.json" ] || python "$CODE/03_topics.py" --variant "$V" --seed "$S" --chunks "$CH" --runs "$RUNS" $MINDF
  done
done
if [ "$VARIANTS" != "B" ]; then python "$CODE/04_compare.py" --chunks "$CH" --runs "$RUNS" --reg-pairs "$REG_PAIRS" --pairs A2:B,A:A2,A:B; fi
python "$CODE/05_diagnostics.py" --chunks "$CH" --runs "$RUNS" --variants "$(echo $VARIANTS | tr ' ' ,)" --seeds 42,43,44
echo "== done $(date)  report: $RUNS/compare/compare_report.md"
