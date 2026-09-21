#!/usr/bin/env python3
"""06_recluster_old.py — re-run the OLD pipeline's UMAP+HDBSCAN on the OLD cached embeddings in
the CURRENT environment.  Separates "environment changed" from "input changed".

  python 06_recluster_old.py --npy "/Users/grace/Desktop/new meta/embedding/embeddings_gte_chunk2000.npy" \
        --ids "/Users/grace/Desktop/new meta/embedding/embeddings_chunk_ids.csv" \
        --chunks-csv "/Users/grace/Desktop/new meta/chunking/chunks_chunk2000.csv" --out <runs dir>/old_baseline

Old result to compare against: 75 topics, 15,616 of 27,104 chunks outliers (57.6 %), seed 42.
Same parameters as 03_topics.py (UMAP 5/15/0.05/cosine, HDBSCAN 30/eom).  Also reports the long-s
split test on the old chunks: does "chunk text contains ſ" predict the clusters?
"""
import argparse, csv, json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--npy', required=True); ap.add_argument('--ids', required=True)
    ap.add_argument('--chunks-csv', required=True, help='old chunks_chunk2000.csv (chunk_id, chunk_text)')
    ap.add_argument('--out', required=True); ap.add_argument('--seeds', default='42,43')
    a = ap.parse_args()
    from umap import UMAP
    from hdbscan import HDBSCAN
    emb = np.load(a.npy)
    ids = [r['chunk_id'] for r in csv.DictReader(open(a.ids, encoding='utf-8-sig'))]
    assert len(ids) == emb.shape[0], f'ids {len(ids)} vs embeddings {emb.shape[0]}'
    has_s = {}
    for r in csv.DictReader(open(a.chunks_csv, encoding='utf-8-sig')):
        has_s[r['chunk_id']] = 'ſ' in r['chunk_text']
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    res = {'n_chunks': len(ids), 'dim': int(emb.shape[1]), 'share_with_longs': round(sum(has_s.get(c, False) for c in ids) / len(ids), 4)}
    for s in [int(x) for x in a.seeds.split(',')]:
        red = UMAP(n_components=5, n_neighbors=15, min_dist=0.05, metric='cosine', random_state=s).fit_transform(emb)
        for method in ('eom', 'leaf'):
            lab = HDBSCAN(min_cluster_size=30, min_samples=None, metric='euclidean', cluster_selection_method=method).fit_predict(red)
            n = int(len(set(lab)) - (1 if -1 in lab else 0)); o = float((lab == -1).mean())
            sizes = sorted((int((lab == c).sum()) for c in set(lab) if c != -1), reverse=True)
            # long-s purity per cluster
            pure = 0
            for c in set(lab):
                if c == -1: continue
                m = [i for i, l in enumerate(lab) if l == c]
                sh = sum(has_s.get(ids[i], False) for i in m) / len(m)
                pure += (sh <= 0.05 or sh >= 0.95)
            res[f'seed{s}_{method}'] = {'clusters': n, 'outlier_share': round(o, 4), 'largest': sizes[:5], 'longs_pure_clusters': pure}
            print(f'seed {s} {method}: {n} clusters, outliers {o:.1%}, largest {sizes[:5]}, ſ-pure clusters {pure}', flush=True)
            with open(out / f'labels_s{s}_{method}.csv', 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['chunk_id', 'label'])
                for c, l in zip(ids, lab): w.writerow([c, int(l)])
        np.save(out / f'umap5_s{s}.npy', red.astype(np.float32))
    (out / 'recluster_old.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
