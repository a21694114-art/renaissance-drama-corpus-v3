#!/usr/bin/env python3
"""03_topics.py — BERTopic on one variant with the previous pipeline's settings.

  python 03_topics.py --variant A --seed 42 --chunks <chunks dir> --runs <runs dir>

Reads  <chunks>/chunks_<variant>.csv, <runs>/embeddings_<variant>.npy, <runs>/embedding_ids_<variant>.csv
Writes <runs>/topics_<variant>_s<seed>/
         doc_topics.csv      chunk_id, topic
         topic_info.csv      topic, count, name
         top_words.csv       topic, rank, word, ctfidf
         run.json            settings, vocabulary size, n_topics, outlier share, cluster sizes, min_df used
         umap5.npy / hdbscan_labels.csv   the reduced embeddings and raw cluster labels

Settings (unchanged from 07_topic_modeling/code/topic_modeling_keywords.py):
  UMAP(n_components=5, n_neighbors=15, min_dist=0.05, metric=cosine, random_state=seed)
  HDBSCAN(min_cluster_size=30, min_samples=None, metric=euclidean, cluster_selection_method=eom)
  --dedup-editions (2026-09-23): the editions of one work are witnesses of the same text, not
    independent evidence for a cluster, and a text present twice doubles its own density. With this
    flag UMAP and HDBSCAN are fitted on ONE edition per work (the one with most chunks; ties → lowest
    edition id), and the chunks of the other editions are then placed with umap.transform +
    hdbscan.approximate_predict (label + strength; noise stays -1). doc_topics.csv still lists every
    chunk; run.json records the primary editions and how the secondary chunks were placed.
  --emb-runs <dir>: read embeddings_<variant>.npy / embedding_ids from another runs dir (re-cluster an
    existing embedding into a new runs dir without copying 70 MB).
  CountVectorizer(unigrams, min_df=10, max_df=0.6, token_pattern [a-zA-Z]{2,})
  NOTE: BERTopic fits the vectorizer on one concatenated document PER TOPIC, so min_df/max_df count
  topics, not chunks (a word must occur in >=10 topics and <=60 % of topics) — exactly as in the old
  pipeline. With few topics (smoke test) min_df=10 is impossible; run_ab.sh passes --min-df 1 there.
  c-TF-IDF texts = chunk text lower-cased, alphabetic tokens only, the previous stopword list removed.
  The SAME stopword list is used for A and B; it contains both modern and early-modern function words.
KeyBERT/MMR relabelling is not applied here: the comparison is between c-TF-IDF representations.
"""
import argparse, csv, hashlib, json, re, time
from pathlib import Path

import numpy as np

STOPWORDS = set("""
i me my myself we our ours ourselves you your yours yourself yourselves he him his himself she her hers herself it its itself they them their theirs themselves what which who whom this that these those am is are was were be been being have has had having do does did doing a an the and but if or because as until while of at by for with about against between into through during before after above below to from up down in out on off over under again further then once here there when where why how all any both each few more most other some such no nor not only own same so than too very s t can will just don should now
thou thee thy thine ye hath doth art shalt hast didst wilt shall would could might must unto tis ’tis
haue doe ile ll vs wil hee saye nowe maye theyr dyd whiche mee vnto don
come good man did make let like owe yet thus may go goe goeth came cometh yes yea yeay nay
say sayst know knowest speak speaketh speake think thinkest thinke
sir hys thys wyll yf hym suche nat wolde thu shee selfe le em se thynge
soft verily marry troth well oh bee ha ane syr tyme lyke whych yow welth lyfe wynde neuer
th whil whilst vpon vppon vp vntill giue tell told telleth deuyll myne longe
""".split())
# sklearn's ENGLISH_STOP_WORDS is added at run time (it was the base of the previous list).


def clean(text, stop):
    words = re.findall(r'\b[a-z]+\b', text.lower())
    return ' '.join(w for w in words if w not in stop)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', required=True, help='A (original), A2 (long-s/VV normalized only), B (EarlyPrint regularized)')
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--runs', required=True)
    ap.add_argument('--min-df', type=int, default=10, help='counts TOPICS in BERTopic c-TF-IDF; use 1 for small smoke runs')
    ap.add_argument('--max-df', type=float, default=0.6)
    ap.add_argument('--dedup-editions', action='store_true', help='fit on one edition per work; place the other editions afterwards')
    ap.add_argument('--emb-runs', default='', help='runs dir holding embeddings_<variant>.npy (default: --runs)')
    ap.add_argument('--cluster', choices=['hdbscan', 'kmeans'], default='hdbscan', help='hdbscan (UMAP-5 + HDBSCAN, outliers allowed) or kmeans (spherical k-means on the L2-normalised embeddings, every chunk assigned; as Kim 2026)')
    ap.add_argument('--k', type=int, default=50, help='k for --cluster kmeans')
    ap.add_argument('--min-samples', type=int, default=None, help='HDBSCAN min_samples (default None = min_cluster_size 30); lower = fewer outliers')
    ap.add_argument('--umap-from', default='', help='topics dir of another run with the SAME seed and fit set: reuse its umap5.npy instead of refitting UMAP')
    ap.add_argument('--edition-selection', default='', help='csv with work_id, edition_id, chosen (Y) — the representative edition per work (default: <chunks>/edition_selection.csv, else ab_spelling/edition_selection.csv, else the fullest text)')
    a = ap.parse_args()
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
    from umap import UMAP
    from hdbscan import HDBSCAN
    from bertopic import BERTopic

    stop = set(ENGLISH_STOP_WORDS) | STOPWORDS
    runs = Path(a.runs); eruns = Path(a.emb_runs) if a.emb_runs else runs
    ids = [r['chunk_id'] for r in csv.DictReader(open(eruns / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
    emb = np.load(eruns / f'embeddings_{a.variant}.npy')
    assert emb.shape[0] == len(ids), 'embeddings and ids differ in length'
    text_by_id = {r['chunk_id']: r['text'] for r in csv.DictReader(open(Path(a.chunks) / f'chunks_{a.variant}.csv', encoding='utf-8'))}
    docs = [clean(text_by_id[c], stop) for c in ids]
    keep = np.array([len(d) > 0 for d in docs])
    docs_k = [d for d, k in zip(docs, keep) if k]
    ids_k = [c for c, k in zip(ids, keep) if k]
    emb_k = emb[keep]
    print(f'variant {a.variant} seed {a.seed}: {len(ids_k)} chunks after cleaning ({int((~keep).sum())} empty dropped)', flush=True)

    # UMAP + HDBSCAN are run explicitly (same parameters as the old pipeline) so that the cluster
    # count is known before c-TF-IDF; BERTopic then only builds the topic representation on the
    # given labels (its "manual topic modeling" mode).  The reduced embeddings and raw labels are saved.
    from bertopic.dimensionality import BaseDimensionalityReduction
    from bertopic.cluster import BaseCluster
    t0 = time.time()
    umap_model = UMAP(n_components=5, n_neighbors=15, min_dist=0.05, metric='cosine', random_state=a.seed)
    dedup = None
    if a.cluster == 'kmeans':
        from sklearn.cluster import KMeans
        from collections import Counter, defaultdict
        embn = emb_k / np.clip(np.linalg.norm(emb_k, axis=1, keepdims=True), 1e-12, None)   # cosine geometry
        if a.dedup_editions:
            meta = {r['chunk_id']: r for r in csv.DictReader(open(Path(a.chunks) / 'chunk_meta.csv', encoding='utf-8'))}
            per_ed = Counter(meta[c]['edition_id'] for c in ids_k); eds_of = defaultdict(set)
            for c in ids_k: eds_of[meta[c]['work_id']].add(meta[c]['edition_id'])
            sel_path = next((p_ for p_ in [Path(a.edition_selection)] * bool(a.edition_selection) + [Path(a.chunks) / 'edition_selection.csv', Path(__file__).resolve().parent.parent / 'edition_selection.csv'] if p_.exists()), None)
            chosen = {r['work_id']: r['edition_id'] for r in csv.DictReader(open(sel_path, encoding='utf-8')) if r.get('chosen', '').strip().upper() == 'Y'} if sel_path else {}
            primary = {chosen[w] if w in chosen and chosen[w] in eds else min(eds, key=lambda e: (-per_ed[e], int(e))) for w, eds in eds_of.items()}
            is_p = np.array([meta[c]['edition_id'] in primary for c in ids_k])
        else:
            is_p = np.ones(len(ids_k), dtype=bool)
        km = KMeans(n_clusters=a.k, n_init=10, random_state=a.seed).fit(embn[is_p])
        labels = np.empty(len(ids_k), dtype=int); labels[is_p] = km.labels_
        if (~is_p).any(): labels[~is_p] = km.predict(embn[~is_p])
        reduced = np.zeros((len(ids_k), 5), dtype=np.float32)   # no UMAP in this scheme (placeholder so that downstream files exist)
        strength = np.ones(len(ids_k), dtype=np.float32)
        if a.dedup_editions:
            dedup = {'primary_editions': sorted(primary, key=int), 'n_primary_chunks': int(is_p.sum()), 'n_secondary_chunks': int((~is_p).sum()),
                     'secondary_placed_share': 1.0, 'secondary_strength_median': None, 'rule': 'one edition per work fitted; others placed by kmeans.predict',
                     'edition_policy': f'edition_selection.csv ({sel_path})' if sel_path else 'fullest text per work'}
            placed = [(c, int(l), 1.0) for c, l, p_ in zip(ids_k, labels, is_p) if not p_]
        hdbscan_model = None
    elif a.dedup_editions:
        from collections import Counter, defaultdict
        import hdbscan as _hdb
        meta = {r['chunk_id']: r for r in csv.DictReader(open(Path(a.chunks) / 'chunk_meta.csv', encoding='utf-8'))}
        per_ed = Counter(meta[c]['edition_id'] for c in ids_k); eds_of = defaultdict(set)
        for c in ids_k: eds_of[meta[c]['work_id']].add(meta[c]['edition_id'])
        sel_path = next((p_ for p_ in [Path(a.edition_selection)] * bool(a.edition_selection) + [Path(a.chunks) / 'edition_selection.csv', Path(__file__).resolve().parent.parent / 'edition_selection.csv'] if p_.exists()), None)
        chosen = {}
        if sel_path:
            for r in csv.DictReader(open(sel_path, encoding='utf-8')):
                if r.get('chosen', '').strip().upper() == 'Y': chosen[r['work_id']] = r['edition_id']
        primary = set()
        for wid, eds in eds_of.items():
            if wid in chosen and chosen[wid] in eds: primary.add(chosen[wid])
            else: primary.add(min(eds, key=lambda e: (-per_ed[e], int(e))))   # fullest text (ties: lowest id)
        policy = f'edition_selection.csv ({sel_path}) for {sum(1 for w in eds_of if w in chosen and chosen[w] in eds_of[w])} works; fullest text for the rest' if sel_path else 'fullest text per work (most chunks; ties lowest id)'
        is_p = np.array([meta[c]['edition_id'] in primary for c in ids_k])
        print(f'dedup: {len(eds_of)} works, {len(primary)} primary editions with {int(is_p.sum())} chunks; {int((~is_p).sum())} chunks of {len(per_ed) - len(primary)} secondary editions placed afterwards; policy: {policy}', flush=True)
        reduced = np.empty((len(ids_k), 5), dtype=np.float32)
        up = Path(a.umap_from) / 'umap5.npy' if a.umap_from else None
        if up and up.exists() and np.load(up).shape[0] == len(ids_k):
            reduced[:] = np.load(up); print(f'UMAP reused from {up}', flush=True)
        else:
            reduced[is_p] = umap_model.fit_transform(emb_k[is_p])
        hdbscan_model = HDBSCAN(min_cluster_size=30, min_samples=a.min_samples, metric='euclidean', cluster_selection_method='eom', prediction_data=True)
        labels = np.full(len(ids_k), -1, dtype=int); labels[is_p] = hdbscan_model.fit_predict(reduced[is_p])
        strength = np.ones(len(ids_k), dtype=np.float32)
        if (~is_p).any():
            if not (up and up.exists()): reduced[~is_p] = umap_model.transform(emb_k[~is_p])
            lab2, str2 = _hdb.approximate_predict(hdbscan_model, reduced[~is_p])
            labels[~is_p] = lab2; strength[~is_p] = str2
        sec_labels = labels[~is_p]
        dedup = {'primary_editions': sorted(primary, key=int), 'n_primary_chunks': int(is_p.sum()), 'n_secondary_chunks': int((~is_p).sum()),
                 'secondary_placed_share': round(float((sec_labels != -1).mean()), 4) if len(sec_labels) else None,
                 'secondary_strength_median': round(float(np.median(strength[~is_p][sec_labels != -1])), 4) if (sec_labels != -1).any() else None,
                 'rule': 'one edition per work fitted; others placed by umap.transform + hdbscan.approximate_predict', 'edition_policy': policy}
        placed = [(c, int(l), float(st)) for c, l, st, p_ in zip(ids_k, labels, strength, is_p) if not p_]
    else:
        reduced = umap_model.fit_transform(emb_k)
        hdbscan_model = HDBSCAN(min_cluster_size=30, min_samples=a.min_samples, metric='euclidean', cluster_selection_method='eom')
        labels = hdbscan_model.fit_predict(reduced)
    n_clusters = int(len(set(labels)) - (1 if -1 in labels else 0))
    outlier = float((labels == -1).mean())
    sizes = sorted((int((labels == c).sum()) for c in set(labels) if c != -1), reverse=True)
    print(f'HDBSCAN: {n_clusters} clusters, outlier share {outlier:.3f}, largest {sizes[:5]}, smallest {sizes[-3:]}', flush=True)
    # BERTopic fits the vectorizer on one document per topic (incl. the outlier topic), so min_df is
    # bounded by max_df * n_docs; keep the requested value when possible and record what was used.
    n_docs_ctfidf = n_clusters + (1 if outlier > 0 else 0)
    min_df_eff = min(a.min_df, max(1, int(a.max_df * n_docs_ctfidf)))
    if min_df_eff != a.min_df:
        print(f'min_df lowered from {a.min_df} to {min_df_eff} because only {n_docs_ctfidf} topic documents exist', flush=True)
    vectorizer = CountVectorizer(ngram_range=(1, 1), min_df=min_df_eff, max_df=a.max_df, token_pattern=r'(?u)\b[a-zA-Z]{2,}\b')
    model = BERTopic(embedding_model=None, umap_model=BaseDimensionalityReduction(), hdbscan_model=BaseCluster(),
                     vectorizer_model=vectorizer, calculate_probabilities=False, verbose=True)
    topics, _ = model.fit_transform(docs_k, embeddings=emb_k, y=labels)
    elapsed = time.time() - t0

    out = runs / f'topics_{a.variant}_s{a.seed}'; out.mkdir(parents=True, exist_ok=True)
    np.save(out / 'umap5.npy', reduced.astype(np.float32))
    if dedup:
        with open(out / 'secondary_editions_placed.csv', 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f); w.writerow(['chunk_id', 'hdbscan_label', 'strength']); w.writerows(placed)
    with open(out / 'hdbscan_labels.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['chunk_id', 'hdbscan_label'])
        for c, l in zip(ids_k, labels):
            w.writerow([c, int(l)])
    with open(out / 'doc_topics.csv', 'w', encoding='utf-8', newline='') as f:   # in_fit: 1 = chunk of a representative edition (used to fit), 0 = placed afterwards
        w = csv.writer(f); w.writerow(['chunk_id', 'topic', 'in_fit'])
        fit_flags = is_p if dedup else np.ones(len(ids_k), dtype=bool)
        for c, t, p_ in zip(ids_k, topics, fit_flags):
            w.writerow([c, int(t), int(p_)])
    info = model.get_topic_info()
    info[['Topic', 'Count', 'Name']].rename(columns={'Topic': 'topic', 'Count': 'count', 'Name': 'name'}).to_csv(out / 'topic_info.csv', index=False)
    with open(out / 'top_words.csv', 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(['topic', 'rank', 'word', 'ctfidf'])
        for t in sorted(set(int(x) for x in topics)):
            for rank, (word, score) in enumerate(model.get_topic(t) or [], 1):
                w.writerow([t, rank, word, round(float(score), 6)])
    topics_arr = np.array(topics)
    run = {'variant': a.variant, 'seed': a.seed, 'n_chunks': len(ids_k), 'n_topics': int(len(set(topics)) - (1 if -1 in topics else 0)),
           'outlier_share': round(float((topics_arr == -1).mean()), 4),
           'vocabulary_size': int(len(model.vectorizer_model.get_feature_names_out())),
           'hdbscan_clusters': n_clusters, 'hdbscan_outlier_share': round(outlier, 4), 'cluster_sizes_top10': sizes[:10],
           'min_df_requested': a.min_df, 'min_df_used': min_df_eff,
           'cluster_method': a.cluster, 'kmeans_k': a.k if a.cluster == 'kmeans' else None, 'min_samples': a.min_samples,
           'settings': {'umap': None if a.cluster == 'kmeans' else dict(n_components=5, n_neighbors=15, min_dist=0.05, metric='cosine', random_state=a.seed),
                        'hdbscan': None if a.cluster == 'kmeans' else dict(min_cluster_size=30, min_samples=a.min_samples, metric='euclidean', cluster_selection_method='eom'),
                        'kmeans': dict(n_clusters=a.k, n_init=10, random_state=a.seed, input='L2-normalised embeddings') if a.cluster == 'kmeans' else None,
                        'vectorizer': dict(ngram_range=[1, 1], min_df=min_df_eff, max_df=a.max_df, token_pattern='[a-zA-Z]{2,}'),
                        'stopwords': 'sklearn ENGLISH_STOP_WORDS + previous pipeline list (identical for A and B)'},
           'elapsed_seconds': round(elapsed, 1), 'dedup_editions': dedup, 'embeddings_from': str(eruns),
           'embeddings_sha256': hashlib.sha256(open(eruns / f'embeddings_{a.variant}.npy', 'rb').read()).hexdigest(),
           'n_in_fit': int(fit_flags.sum()), 'outlier_share_in_fit': round(float((topics_arr[fit_flags] == -1).mean()), 4)}
    (out / 'run.json').write_text(json.dumps(run, indent=1))
    print(json.dumps({k: v for k, v in run.items() if k != 'settings'}, indent=1))


if __name__ == '__main__':
    main()
