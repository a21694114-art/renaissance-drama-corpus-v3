#!/usr/bin/env python3
"""02_embed.py — sentence embeddings for one variant of the chunk set, with a selectable model.

  python 02_embed.py --variant B --chunks <chunks dir> --out <runs dir> \
        [--model Alibaba-NLP/gte-large-en-v1.5] [--max-seq-length 2048] [--batch-size 8] [--limit 500]

Reads  <chunks>/chunks_<variant>.csv   (chunk_id, text)
Writes <out>/embeddings_<variant>.npy   float32 [n_chunks, dim], row order = chunks_<variant>.csv
       <out>/embedding_ids_<variant>.csv
       <out>/embedding_<variant>.json   (model, revision, device, shape, max_seq_length, elapsed, sha256 of ids)

Models tried in this project:
  thenlper/gte-large               512-token window, 1024-d (the 2024 pipeline; batch 16)
  Alibaba-NLP/gte-large-en-v1.5    8192-token window, 1024-d, CLS pooling, trust_remote_code; its custom code
                                   fails on transformers 5.x (no get_extended_attention_mask) — needs transformers<5
  Qwen/Qwen3-Embedding-0.6B        32k window, 1024-d, last-token pooling; documents need no instruction (DEFAULT)
Long-window models: --max-seq-length caps the tokens actually fed to the model (memory on MPS);
set it above the longest chunk (chunk_map_summary.json: tokens_max) so nothing is truncated.
Device: MPS on Apple silicon if available, else CUDA, else CPU.
"""
import argparse, csv, hashlib, json, sys, time
from pathlib import Path

import numpy as np

DEFAULT_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
REMOTE_CODE = {'Alibaba-NLP/gte-large-en-v1.5', 'Alibaba-NLP/gte-base-en-v1.5'}


def pick_device():
    import torch
    if torch.backends.mps.is_available():
        return 'mps'
    if torch.cuda.is_available():
        return 'cuda'
    return 'cpu'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', required=True, help='B (EarlyPrint regularized) — or A / A2 for the closed comparison')
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--model', default=DEFAULT_MODEL)
    ap.add_argument('--revision', default=None, help='pin a Hugging Face revision (commit hash) for reproducibility')
    ap.add_argument('--max-seq-length', type=int, default=2048)
    ap.add_argument('--batch-size', type=int, default=8)
    ap.add_argument('--normalize', action='store_true', help='L2-normalize embeddings (UMAP uses cosine anyway)')
    ap.add_argument('--limit', type=int, default=0, help='first N chunks only (smoke test)')
    a = ap.parse_args()
    from sentence_transformers import SentenceTransformer

    rows = list(csv.DictReader(open(Path(a.chunks) / f'chunks_{a.variant}.csv', encoding='utf-8')))
    if a.limit:
        rows = rows[:a.limit]
    ids = [r['chunk_id'] for r in rows]
    texts = [r['text'] for r in rows]
    if any(not t.strip() for t in texts):
        sys.exit('empty chunk text found — chunk map is inconsistent')
    device = pick_device()
    print(f'variant {a.variant}: {len(texts)} chunks, model {a.model}, device {device}', flush=True)
    kw = {'device': device, 'trust_remote_code': a.model in REMOTE_CODE}
    if a.revision:
        kw['revision'] = a.revision
    model = SentenceTransformer(a.model, **kw)
    model.max_seq_length = a.max_seq_length
    # longest-first ordering makes batches homogeneous in length (faster, steadier memory); order restored after
    order = sorted(range(len(texts)), key=lambda i: -len(texts[i]))
    t0 = time.time()
    emb_sorted = model.encode([texts[i] for i in order], batch_size=a.batch_size, show_progress_bar=True,
                              normalize_embeddings=a.normalize, convert_to_numpy=True).astype(np.float32)
    emb = np.empty_like(emb_sorted)
    emb[order] = emb_sorted
    elapsed = time.time() - t0
    if not np.isfinite(emb).all():
        sys.exit('non-finite values in embeddings — try a smaller --max-seq-length / --batch-size or CPU')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    np.save(out / f'embeddings_{a.variant}.npy', emb)
    with open(out / f'embedding_ids_{a.variant}.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['row', 'chunk_id'])
        for i, cid in enumerate(ids):
            w.writerow([i, cid])
    rev = None
    try:
        rev = model[0].auto_model.config._commit_hash
    except Exception:
        pass
    info = {'variant': a.variant, 'model': a.model, 'revision': a.revision or rev, 'device': device, 'batch_size': a.batch_size,
            'max_seq_length': a.max_seq_length, 'normalized': a.normalize,
            'n_chunks': len(ids), 'dim': int(emb.shape[1]), 'elapsed_seconds': round(elapsed, 1),
            'ids_sha256': hashlib.sha256('\n'.join(ids).encode()).hexdigest(), 'limit': a.limit}
    (out / f'embedding_{a.variant}.json').write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


if __name__ == '__main__':
    main()
