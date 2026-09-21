#!/usr/bin/env python3
"""05_diagnostics.py — cheap diagnostics on saved runs; no embedding, no UMAP.

  python 05_diagnostics.py --chunks <chunks dir> --runs <runs dir> --variants A,B --seeds 42,43,44

For every topics_<V>_s<seed>/ found:
  1. leaf vs eom: re-run HDBSCAN on the saved umap5.npy with cluster_selection_method='leaf'
     (same min_cluster_size) and report cluster count / outlier share next to the saved eom labels.
     Answers "is A's collapse only a too-coarse level of the cluster tree?"
  2. uniform diagnostic keywords: BERTopic's own ClassTfidfTransformer (default settings) on the
     SAVED labels with a fixed, declared vectorizer (min_df=1, max_df=1.0, same stopwords as 03) so
     keyword tables of different runs are filtered the same way — removes the min_df side-effect
     ChatGPT found (A42 vocab 35,045 vs A43 2,928).  Written to topics_<V>_s<seed>/top_words_uniform.csv,
     keyed by the FINAL BERTopic topic id (doc_topics.csv), as is every table here (v2, 2026-09-21).
  3. work concentration: for each cluster the share of chunks from its dominant DEEP work_id and
     the number of works; summary = clusters with >=80 % / >=90 % from one work.
  4. long-s check: share of chunks containing ſ in the ORIGINAL text (chunks_A.csv) per cluster,
     and how well "has ſ" predicts the largest split (max over clusters of |share - 0.5|).
Writes <runs>/diagnostics/diagnostics.json and diagnostics.md.
"""
import argparse, csv, json, re
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

STOP_RE = re.compile(r'\b[a-z]+\b')


def load_stop():
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    import importlib.util, sys
    here = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('t03', here / '03_topics.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return set(ENGLISH_STOP_WORDS) | m.STOPWORDS


def ctfidf_top_words(docs_by_topic, stop, k=10):
    """Standard BERTopic class-TF-IDF (bertopic.vectorizers.ClassTfidfTransformer, default settings)
    on one concatenated document per topic with a uniform vectorizer (min_df=1, max_df=1.0)."""
    from sklearn.feature_extraction.text import CountVectorizer
    from bertopic.vectorizers import ClassTfidfTransformer
    topics = sorted(docs_by_topic)
    corpus = [' '.join(docs_by_topic[t]) for t in topics]
    vec = CountVectorizer(ngram_range=(1, 1), min_df=1, max_df=1.0, token_pattern=r'(?u)\b[a-zA-Z]{2,}\b', stop_words=list(stop))
    X = vec.fit_transform(corpus)
    C = ClassTfidfTransformer(bm25_weighting=False, reduce_frequent_words=False).fit(X).transform(X).tocsr()
    words = vec.get_feature_names_out()
    out = {}
    for i, t in enumerate(topics):
        row = C.getrow(i)
        order = np.argsort(-row.data)[:k]
        out[t] = [(words[row.indices[j]], float(row.data[j])) for j in order if row.data[j] > 0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--runs', required=True)
    ap.add_argument('--variants', default='A,B')
    ap.add_argument('--seeds', default='42,43,44')
    ap.add_argument('--min-cluster-size', type=int, default=30)
    a = ap.parse_args()
    from hdbscan import HDBSCAN
    runs = Path(a.runs); out = runs / 'diagnostics'; out.mkdir(exist_ok=True)
    stop = load_stop()
    meta = {r['chunk_id']: r for r in csv.DictReader(open(Path(a.chunks) / 'chunk_meta.csv', encoding='utf-8'))}
    has_s = {r['chunk_id']: ('ſ' in r['text']) for r in csv.DictReader(open(Path(a.chunks) / 'chunks_A.csv', encoding='utf-8'))}
    texts = {}
    results = {}; md = ['# Diagnostics on saved runs', '', 'Topic ids = final BERTopic ids (doc_topics.csv). Keywords = bertopic ClassTfidfTransformer, uniform vectorizer (min_df=1, max_df=1.0).', '']
    for V in a.variants.split(','):
        texts[V] = {r['chunk_id']: r['text'] for r in csv.DictReader(open(Path(a.chunks) / f'chunks_{V}.csv', encoding='utf-8'))}
        for s in a.seeds.split(','):
            d = runs / f'topics_{V}_s{s}'
            if not (d / 'umap5.npy').exists():
                continue
            # FINAL BERTopic topic ids (doc_topics.csv), the same numbering as topic_sheet / 08; the raw
            # HDBSCAN labels of hdbscan_labels.csv map one-to-one onto them (see 08's id_map sheet)
            ids = [r['chunk_id'] for r in csv.DictReader(open(d / 'doc_topics.csv'))]
            labels = np.array([int(r['topic']) for r in csv.DictReader(open(d / 'doc_topics.csv'))])
            raw_ids = [r['chunk_id'] for r in csv.DictReader(open(d / 'hdbscan_labels.csv'))]
            assert raw_ids == ids, 'doc_topics.csv and hdbscan_labels.csv row order differ'
            red = np.load(d / 'umap5.npy')
            # 1. leaf
            leaf = HDBSCAN(min_cluster_size=a.min_cluster_size, min_samples=None, metric='euclidean', cluster_selection_method='leaf').fit_predict(red)
            n_leaf = int(len(set(leaf)) - (1 if -1 in leaf else 0)); out_leaf = float((leaf == -1).mean())
            with open(d / 'hdbscan_labels_leaf.csv', 'w', newline='') as f:
                w = csv.writer(f); w.writerow(['chunk_id', 'leaf_label'])
                for c, l in zip(ids, leaf): w.writerow([c, int(l)])
            # 2. uniform keywords on saved (eom) labels
            docs_by_topic = defaultdict(list)
            for c, l in zip(ids, labels):
                if l != -1:
                    docs_by_topic[int(l)].append(' '.join(w for w in STOP_RE.findall(texts[V][c].lower()) if w not in stop))
            tw = ctfidf_top_words(docs_by_topic, stop)
            with open(d / 'top_words_uniform.csv', 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f); w.writerow(['topic', 'rank', 'word', 'ctfidf'])
                for t in sorted(tw):
                    for r, (wd, sc) in enumerate(tw[t], 1): w.writerow([t, r, wd, round(sc, 6)])
            # 3. work concentration; 4. long-s
            conc = {}; s_share = {}
            for t in sorted(docs_by_topic):
                members = [c for c, l in zip(ids, labels) if l == t]
                works = Counter(meta[c]['work_id'] for c in members)
                conc[t] = {'n': len(members), 'n_works': len(works), 'dominant_share': round(works.most_common(1)[0][1] / len(members), 3),
                           'dominant_work': works.most_common(1)[0][0]}
                s_share[t] = round(sum(has_s[c] for c in members) / len(members), 3)
            n_cl = len(conc)
            res = {'eom_clusters': n_cl, 'eom_outlier': round(float((labels == -1).mean()), 4),
                   'leaf_clusters': n_leaf, 'leaf_outlier': round(out_leaf, 4),
                   'clusters_ge80_one_work': sum(1 for v in conc.values() if v['dominant_share'] >= 0.8),
                   'clusters_ge90_one_work': sum(1 for v in conc.values() if v['dominant_share'] >= 0.9),
                   'chunks_in_ge90_clusters': sum(v['n'] for v in conc.values() if v['dominant_share'] >= 0.9),
                   'longs_share_by_cluster_minmax': [min(s_share.values()), max(s_share.values())] if s_share else None,
                   'clusters_longs_pure': sum(1 for v in s_share.values() if v <= 0.05 or v >= 0.95),
                   'work_concentration': conc, 'longs_share': s_share}
            results[f'{V}_s{s}'] = res
            md += [f'## {V} seed {s}', '',
                   f'- eom: {n_cl} clusters, outliers {res["eom_outlier"]:.1%}; **leaf**: {n_leaf} clusters, outliers {out_leaf:.1%}',
                   f'- clusters with ≥90 % of chunks from one work: {res["clusters_ge90_one_work"]} of {n_cl} ({res["chunks_in_ge90_clusters"]} chunks); ≥80 %: {res["clusters_ge80_one_work"]}',
                   f'- long-s share per cluster ranges {res["longs_share_by_cluster_minmax"]}; clusters that are ≥95 % pure in ſ-presence: {res["clusters_longs_pure"]} of {n_cl}', '',
                   '| cluster | n | works | dominant work share | ſ share | uniform top words |', '|---|---:|---:|---:|---:|---|']
            for t in sorted(conc, key=lambda t: -conc[t]['n'])[:15]:
                md.append(f'| {t} | {conc[t]["n"]} | {conc[t]["n_works"]} | {conc[t]["dominant_share"]} | {s_share[t]} | {", ".join(w for w, _ in tw.get(t, []))} |')
            md.append('')
            print(f'{V} s{s}: eom {n_cl} / leaf {n_leaf} clusters; ≥90% one-work clusters {res["clusters_ge90_one_work"]}; ſ-pure clusters {res["clusters_longs_pure"]}', flush=True)
    (out / 'diagnostics.json').write_text(json.dumps(results, indent=1))
    (out / 'diagnostics.md').write_text('\n'.join(md), encoding='utf-8')
    print('written', out)


if __name__ == '__main__':
    main()
