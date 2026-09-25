#!/usr/bin/env python3
"""17_sample_clusters.py — a reading sample to judge a clustering scheme: centre AND edge chunks of a few clusters.

    python 17_sample_clusters.py --chunks <chunks_w500> --runs <runs dir> --seed 42 [--topics 3,17,40 | --n 5]
                                 [--works 3] [--chars 700] [--out <md>]

For each chosen cluster (given ids, or --n clusters drawn at random with the seed, restricted to clusters of
>= 60 chunks): the uniform keywords (topic sheet rule), size, works, dominant-work share; then for each of
the --works leading works (by chunk count, representative editions only) the MOST typical chunk (highest
cosine to the cluster centroid) and the LEAST typical one, with title / year / genre / typicality and the
first --chars characters of the ORIGINAL text. Reading the edges is the test of a scheme that assigns every
chunk (k-means): if the edge passages of a cluster are still about the same thing, the cluster holds; if
they are about anything, coverage was bought with noise.
"""
import argparse, csv, random, re
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

STOP_RE = re.compile(r'\b[a-z]+\b')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True); ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--topics', default=''); ap.add_argument('--n', type=int, default=5); ap.add_argument('--works', type=int, default=3); ap.add_argument('--chars', type=int, default=700)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    import importlib.util
    spec = importlib.util.spec_from_file_location('c16', Path(__file__).resolve().parent / '16_compare_schemes.py'); c16 = importlib.util.module_from_spec(spec); spec.loader.exec_module(c16)
    stop = c16.load_stop()
    runs = Path(a.runs); d = runs / f'topics_{a.variant}_s{a.seed}'; ch = Path(a.chunks); csv.field_size_limit(10 ** 8)
    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    text = {r['chunk_id']: r['text'] for r in csv.DictReader(open(ch / f'chunks_{a.variant}.csv', encoding='utf-8'))}
    ids = [r['chunk_id'] for r in csv.DictReader(open(runs / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
    emb = np.load(runs / f'embeddings_{a.variant}.npy').astype(np.float32); emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    row = {c: i for i, c in enumerate(ids)}
    dt = list(csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8')))
    mem = defaultdict(list)
    for r in dt:
        if int(r['topic']) != -1 and r.get('in_fit', '1') == '1': mem[int(r['topic'])].append(r['chunk_id'])
    if a.topics: chosen = [int(x) for x in a.topics.split(',')]
    else:
        big = [t for t, cs in mem.items() if len(cs) >= 60]; random.Random(a.seed).shuffle(big); chosen = sorted(big[:a.n])
    kw = c16.uniform_top_words({t: [' '.join(w for w in STOP_RE.findall(text[c].lower()) if w not in stop) for c in cs] for t, cs in mem.items()}, stop, k=10)
    md = [f'# Reading sample — {runs.name}, seed {a.seed}', '', f'Clusters {", ".join("T%d" % t for t in chosen)}: for each of the {a.works} leading works, the most typical chunk (highest cosine to the centroid) and the least typical one. Representative editions only.', '']
    for t in chosen:
        cs = mem[t]; cen = emb[[row[c] for c in cs]].mean(0); cen /= np.linalg.norm(cen) + 1e-9
        typ = {c: float(emb[row[c]] @ cen) for c in cs}
        wk = Counter(meta[c]['work_id'] for c in cs); dom = wk.most_common(1)[0]
        md += [f'## T{t} — {len(cs)} chunks, {len(wk)} works, largest work {100 * dom[1] / len(cs):.0f} %', '', f'Keywords: {", ".join(kw.get(t, []))}', '',
               f'Typicality across the cluster: median {np.median(list(typ.values())):.3f}, lowest {min(typ.values()):.3f}, highest {max(typ.values()):.3f}', '']
        for w, n in wk.most_common(a.works):
            wc = [c for c in cs if meta[c]['work_id'] == w]; hi = max(wc, key=lambda c: typ[c]); lo = min(wc, key=lambda c: typ[c])
            m = meta[hi]
            md += [f'### {m["title"]} ({m["year"]}, {m["genre_deep"]}) — {n} chunks in this cluster', '']
            for tag, c in (('most typical', hi), ('least typical', lo)):
                md += [f'**{tag}** · chunk {c} · typicality {typ[c]:.3f}', '', '> ' + text[c][:a.chars].replace('\n', ' ') + ('…' if len(text[c]) > a.chars else ''), '']
    out = Path(a.out) if a.out else d / f'reading_sample_{"_".join(str(t) for t in chosen)}.md'
    out.write_text('\n'.join(md), encoding='utf-8'); print(f'→ {out}  ({len(chosen)} clusters)')


if __name__ == '__main__':
    main()
