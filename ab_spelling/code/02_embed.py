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
    ap.add_argument('--text-file', default='', help='read the texts from this csv (chunk_id,text) instead of chunks_<variant>.csv — e.g. chunks_B_masked.csv from 01c_mask_names.py; the output files keep the variant name')
    ap.add_argument('--reuse-from', default='', help='runs dir with an earlier embeddings_<variant>.npy of the same chunk ids: vectors of chunks whose text is unchanged are copied, only changed chunks are re-encoded (changed = per-chunk text hashes differ, or the ids listed in --changed)')
    ap.add_argument('--changed', default='', help='csv (chunk_id) listing the chunks whose text changed since --reuse-from (01c writes name_mask_changed_chunks.csv); used when the earlier run has no per-chunk hashes')
    a = ap.parse_args()
    from sentence_transformers import SentenceTransformer

    csv.field_size_limit(10 ** 8)
    text_path = Path(a.text_file) if a.text_file else Path(a.chunks) / f'chunks_{a.variant}.csv'
    rows = list(csv.DictReader(open(text_path, encoding='utf-8')))
    if a.limit:
        rows = rows[:a.limit]
    ids = [r['chunk_id'] for r in rows]
    texts = [r['text'] for r in rows]
    if any(not t.strip() for t in texts):
        sys.exit('empty chunk text found — chunk map is inconsistent')
    import hashlib as _hl
    hashes = [_hl.sha1(t.encode('utf-8')).hexdigest() for t in texts]
    reuse = None
    if a.reuse_from:
        rd = Path(a.reuse_from); old = np.load(rd / f'embeddings_{a.variant}.npy')
        old_ids = [r['chunk_id'] for r in csv.DictReader(open(rd / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
        if old_ids != ids: sys.exit('--reuse-from: chunk ids differ from the current text file — cannot reuse')
        hp = rd / f'embedding_text_hashes_{a.variant}.csv'
        if hp.exists():
            oldh = {r['chunk_id']: r['sha1'] for r in csv.DictReader(open(hp, encoding='utf-8'))}
            todo = [i for i, c in enumerate(ids) if oldh.get(c) != hashes[i]]
        elif a.changed and Path(a.changed).exists():
            ch_ids = {r['chunk_id'] for r in csv.DictReader(open(a.changed, encoding='utf-8'))}
            todo = [i for i, c in enumerate(ids) if c in ch_ids]
        else:
            sys.exit('--reuse-from: the earlier run has no embedding_text_hashes file and no --changed list was given')
        reuse = (old, todo)
        print(f'reuse: {len(ids) - len(todo)} vectors copied from {rd}, {len(todo)} chunks re-encoded', flush=True)
    device = pick_device()
    print(f'variant {a.variant}: {len(texts)} chunks from {text_path.name}, model {a.model}, device {device}', flush=True)
    kw = {'device': device, 'trust_remote_code': a.model in REMOTE_CODE}
    if a.revision:
        kw['revision'] = a.revision
    model = SentenceTransformer(a.model, **kw)
    model.max_seq_length = a.max_seq_length
    # longest-first ordering makes batches homogeneous in length (faster, steadier memory); order restored after
    todo_idx = reuse[1] if reuse else list(range(len(texts)))
    order = sorted(todo_idx, key=lambda i: -len(texts[i]))
    t0 = time.time()
    if order:
        emb_new = model.encode([texts[i] for i in order], batch_size=a.batch_size, show_progress_bar=True,
                               normalize_embeddings=a.normalize, convert_to_numpy=True).astype(np.float32)
    if reuse:
        emb = reuse[0].astype(np.float32).copy()
        if order: emb[order] = emb_new
    else:
        emb = np.empty_like(emb_new); emb[order] = emb_new
    elapsed = time.time() - t0
    if not np.isfinite(emb).all():
        sys.exit('non-finite values in embeddings — try a smaller --max-seq-length / --batch-size or CPU')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if reuse and (out / f'embeddings_{a.variant}.npy').exists():   # keep the previous vectors and record next to the new ones
        (out / f'embeddings_{a.variant}.npy').replace(out / f'embeddings_{a.variant}.prev.npy')
        if (out / f'embedding_{a.variant}.json').exists(): (out / f'embedding_{a.variant}.json').replace(out / f'embedding_{a.variant}.prev.json')
    np.save(out / f'embeddings_{a.variant}.npy', emb)
    with open(out / f'embedding_text_hashes_{a.variant}.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['chunk_id', 'sha1']); w.writerows(zip(ids, hashes))
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
            'ids_sha256': hashlib.sha256('\n'.join(ids).encode()).hexdigest(), 'limit': a.limit, 'text_file': text_path.name,
            'text_sha256': hashlib.sha256(open(text_path, 'rb').read()).hexdigest(),
            'reused_from': a.reuse_from or None, 'n_recomputed': len(todo_idx)}
    (out / f'embedding_{a.variant}.json').write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


if __name__ == '__main__':
    main()
