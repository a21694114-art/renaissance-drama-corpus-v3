#!/usr/bin/env python3
"""16_compare_schemes.py — one table over several clustering schemes of the SAME embeddings.

    python 16_compare_schemes.py --chunks <chunks_w500> --runs <dir1> <dir2> ... [--labels hdb30 hdb10 ...]
                                 [--seeds 42,43,44] [--names <name_mask_tokens.csv>] [--out <md>]

Each --runs dir holds topics_B_s<seed>/ (doc_topics.csv with in_fit, top_words.csv, run.json). Per scheme,
averaged over seeds (main stats on in_fit chunks = representative editions only):
  clusters            number of clusters
  outliers            share of in_fit chunks with topic -1 (0 for k-means by construction)
  single-work         clusters whose largest work holds >= 50 % of the cluster's chunks, and the share of
                      assigned chunks sitting in such clusters
  works/cluster       median number of works with >= 3 chunks in a cluster (breadth of a theme)
  ARI (assigned)      mean adjusted Rand index between seed pairs on chunks assigned in both seeds
  ARI (all)           the same with outliers counted as one class (assignment state included)
  flip share          share of chunks (in_fit) whose assignment STATE (assigned vs outlier) differs between
                      two seeds — the part of the disagreement that ARI (assigned) does not see
  name share          share of the top-10 UNIFORM keywords per cluster (class-TF-IDF over the in_fit chunks,
                      min_df=1, max_df=1.0, the 03 stopword list — the topic sheet's rule, recomputed here for
                      every scheme; 03's own top_words are NOT used because its max_df=0.6 counts topics and
                      removes common thematic words when there are few clusters) that are character names
                      (tokens masked by 01c in >= 50 % of their corpus occurrences — role words such as
                      "senate" or "murderer" that a cast list happened to contain do not count)
  largest             size of the largest cluster (a 1,500-chunk blob is a warning sign)
No score is a verdict, and ARI is a similarity index, not "the share of clusters reproduced": the table is
read together with the clusters themselves (topic sheets / reading samples, 17_sample_clusters.py).
Corrected 2026-09-23 after ChatGPT's review (v1 used 03's keywords and an over-wide name list).
"""
import argparse, csv, json, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

STOP_RE = re.compile(r'\b[a-z]+\b')


def load_stop():
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    import importlib.util
    spec = importlib.util.spec_from_file_location('t03', Path(__file__).resolve().parent / '03_topics.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return set(ENGLISH_STOP_WORDS) | m.STOPWORDS


def uniform_top_words(docs_by_topic, stop, k=10):
    """The topic sheet's keyword rule (05/08): BERTopic ClassTfidfTransformer on one document per cluster, min_df=1, max_df=1.0."""
    import numpy as np
    from sklearn.feature_extraction.text import CountVectorizer
    from bertopic.vectorizers import ClassTfidfTransformer
    topics = sorted(docs_by_topic); corpus = [' '.join(docs_by_topic[t]) for t in topics]
    vec = CountVectorizer(ngram_range=(1, 1), min_df=1, max_df=1.0, token_pattern=r'(?u)\b[a-zA-Z]{2,}\b', stop_words=list(stop))
    X = vec.fit_transform(corpus); C = ClassTfidfTransformer(bm25_weighting=False, reduce_frequent_words=False).fit(X).transform(X).tocsr()
    words = vec.get_feature_names_out(); out = {}
    for i, t in enumerate(topics):
        row = C.getrow(i); order = np.argsort(-row.data)[:k]
        out[t] = [words[row.indices[j]] for j in order if row.data[j] > 0]
    return out


def ari(a, b):
    from sklearn.metrics import adjusted_rand_score
    return adjusted_rand_score(a, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', nargs='+', required=True); ap.add_argument('--labels', nargs='*', default=[])
    ap.add_argument('--seeds', default='42,43,44'); ap.add_argument('--variant', default='B'); ap.add_argument('--names', default='')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(',')]
    csv.field_size_limit(10 ** 8)
    meta = {r['chunk_id']: r for r in csv.DictReader(open(Path(a.chunks) / 'chunk_meta.csv', encoding='utf-8'))}
    stop = load_stop()
    texts = {r['chunk_id']: ' '.join(w for w in STOP_RE.findall(r['text'].lower()) if w not in stop) for r in csv.DictReader(open(Path(a.chunks) / f'chunks_{a.variant}.csv', encoding='utf-8'))}
    # character names = tokens that 01c masked in >= 50 % of their corpus occurrences (a role word such as
    # "senate" that one cast list contained is masked in one play only and does not qualify)
    names = set()
    npath = Path(a.names) if a.names else Path(a.chunks) / 'name_mask_tokens.csv'
    if npath.exists():
        masked = Counter()
        for r in csv.DictReader(open(npath, encoding='utf-8')): masked[r['token'].lower()] += int(r['count'])
        total = Counter()
        for t in texts.values():
            for w in t.split():
                if w in masked: total[w] += 1
        names = {w for w, n in masked.items() if n >= 0.5 * max(total.get(w, 0), 1)}
    labels = a.labels if len(a.labels) == len(a.runs) else [Path(r).name for r in a.runs]

    rows = []
    for lab, rd in zip(labels, a.runs):
        per_seed = {}; assign = {}
        for s in seeds:
            d = Path(rd) / f'topics_{a.variant}_s{s}'
            if not (d / 'doc_topics.csv').exists(): continue
            dt = [r for r in csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8'))]
            fit = [r for r in dt if r.get('in_fit', '1') == '1']
            lab_of = {r['chunk_id']: int(r['topic']) for r in fit}; assign[s] = lab_of
            mem = defaultdict(list)
            for c, t in lab_of.items():
                if t != -1: mem[t].append(c)
            n_out = sum(1 for t in lab_of.values() if t == -1)
            single = 0; single_chunks = 0; breadth = []
            for t, cs in mem.items():
                wk = Counter(meta[c]['work_id'] for c in cs)
                if wk.most_common(1)[0][1] / len(cs) >= 0.5: single += 1; single_chunks += len(cs)
                breadth.append(sum(1 for w, n in wk.items() if n >= 3))
            tw = uniform_top_words({t: [texts[c] for c in cs] for t, cs in mem.items()}, stop, k=10)
            nshare = statistics.mean([sum(1 for w in ws if w in names) / max(len(ws), 1) for ws in tw.values()]) if tw and names else float('nan')
            with open(d / 'top_words_uniform10.csv', 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f); w.writerow(['topic', 'rank', 'word', 'is_name']); [w.writerow([t, i + 1, wd, int(wd in names)]) for t, ws in tw.items() for i, wd in enumerate(ws)]
            run = json.load(open(d / 'run.json'))
            per_seed[s] = {'clusters': len(mem), 'outliers': n_out / max(len(lab_of), 1), 'single': single, 'single_share': single_chunks / max(sum(len(v) for v in mem.values()), 1),
                           'breadth': statistics.median(breadth) if breadth else 0, 'largest': max((len(v) for v in mem.values()), default=0), 'name_share': nshare,
                           'method': run.get('cluster_method', 'hdbscan'), 'k': run.get('kmeans_k'), 'min_samples': run.get('min_samples')}
        if not per_seed: continue
        pairs = [(x, y) for i, x in enumerate(seeds) for y in seeds[i + 1:] if x in assign and y in assign]
        ari_as, ari_all, flips = [], [], []
        for x, y in pairs:
            common = [c for c in assign[x] if c in assign[y]]
            both = [c for c in common if assign[x][c] != -1 and assign[y][c] != -1]
            if both: ari_as.append(ari([assign[x][c] for c in both], [assign[y][c] for c in both]))
            ari_all.append(ari([assign[x][c] for c in common], [assign[y][c] for c in common]))
            flips.append(sum(1 for c in common if (assign[x][c] == -1) != (assign[y][c] == -1)) / max(len(common), 1))
        m = lambda k: statistics.mean(v[k] for v in per_seed.values())
        first = next(iter(per_seed.values()))
        rows.append({'scheme': lab, 'method': first['method'] + (f' k={first["k"]}' if first['method'] == 'kmeans' else f' min_samples={first["min_samples"] or 30}'), 'seeds': len(per_seed),
                     'clusters': round(m('clusters'), 1), 'outliers': round(100 * m('outliers'), 1), 'single_work_clusters': round(m('single'), 1), 'single_work_chunk_share': round(100 * m('single_share'), 1),
                     'median_works_per_cluster': round(m('breadth'), 1), 'largest_cluster': round(m('largest')), 'ari_assigned': round(statistics.mean(ari_as), 3) if ari_as else '',
                     'ari_all': round(statistics.mean(ari_all), 3) if ari_all else '', 'flip_share': round(100 * statistics.mean(flips), 1) if flips else '',
                     'name_share_top10': round(100 * m('name_share'), 1) if names else ''})
    out = Path(a.out) if a.out else Path(a.runs[0]).parent / 'compare_schemes.md'
    with open(out.with_suffix('.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    md = ['# Clustering schemes on the same embeddings', '',
          'Main statistics on the representative editions (in_fit chunks); mean over seeds. single-work = clusters whose largest work holds ≥ 50 % of the chunks. '
          'ARI = adjusted Rand index between seed pairs, a similarity of two partitions (1 = identical, 0 = chance) — NOT the share of clusters reproduced; "assigned" = on chunks assigned in both seeds, "all" = outlier state counted as a class; flip = share of chunks that are an outlier in one seed and assigned in the other. '
          'name share = share of the top-10 uniform keywords (class-TF-IDF over the in_fit chunks, min_df=1, max_df=1.0, the topic sheet\'s rule) that are character names (masked in ≥ 50 % of their occurrences); keywords are computed on the ORIGINAL text, so names can appear even though the embeddings never saw them.', '',
          '| scheme | method | seeds | clusters | outliers % | single-work clusters | chunks in them % | median works/cluster | largest | ARI assigned | ARI all | flip % | name share % |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        md.append(f'| {r["scheme"]} | {r["method"]} | {r["seeds"]} | {r["clusters"]} | {r["outliers"]} | {r["single_work_clusters"]} | {r["single_work_chunk_share"]} | {r["median_works_per_cluster"]} | {r["largest_cluster"]} | {r["ari_assigned"]} | {r["ari_all"]} | {r["flip_share"]} | {r["name_share_top10"]} |')
    out.write_text('\n'.join(md), encoding='utf-8'); print('\n'.join(md)); print(f'→ {out}')


if __name__ == '__main__':
    main()
