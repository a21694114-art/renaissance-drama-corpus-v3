#!/usr/bin/env python3
"""10_reading_pack.py — a critical-reading pack for ONE topic: full chunks from different works
(different authors first), the cluster's edge, and a near-miss outside the cluster.

  python 10_reading_pack.py --chunks <chunks dir> --runs <runs dir> --seed 42 --topic 9 \
        [--n-works 5] [--out <md file>]

Selection (all by cosine to the topic centroid of the saved embeddings):
  core       one chunk per work — the member nearest the centroid — for the N works that contribute
             most chunks, preferring works whose raw author string has not been used yet;
  edge       the member farthest from the centroid (what the cluster still includes);
  near-miss  the non-member (another topic or HDBSCAN outlier) closest to the centroid (what it
             excludes) — a boundary example for the interpretation.
Each entry prints chunk_id, title, author, year, genre_deep, play_type_deep, edition, node range,
similarity, and the FULL regularized text (variant B).  Interpretation lines are left blank: they
are written by the reader, not generated.
"""
import argparse, csv
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--topic', type=int, required=True); ap.add_argument('--n-works', type=int, default=5)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'
    out = Path(a.out) if a.out else d / f'reading_pack_T{a.topic}.md'
    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    cmap = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_map.csv', encoding='utf-8'))}
    texts = {r['chunk_id']: r['text'] for r in csv.DictReader(open(ch / f'chunks_{a.variant}.csv', encoding='utf-8'))}
    labels = {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8'))}
    ids = [r['chunk_id'] for r in csv.DictReader(open(runs / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
    emb = np.load(runs / f'embeddings_{a.variant}.npy').astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    row_of = {c: i for i, c in enumerate(ids)}
    sheet = {}
    if (d / 'topic_sheet.csv').exists():
        sheet = {int(r['topic']): r for r in csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8'))}

    m = [c for c, t in labels.items() if t == a.topic]
    if not m:
        raise SystemExit(f'topic {a.topic} has no members')
    cent = emb[[row_of[c] for c in m]].mean(axis=0); cent /= np.linalg.norm(cent) + 1e-9
    sim = emb @ cent
    works = Counter(meta[c]['work_id'] for c in m)
    by_work = defaultdict(list)
    for c in m: by_work[meta[c]['work_id']].append(c)
    # core: N works, distinct authors first
    chosen, used_auth = [], set()
    ranked = [w for w, _ in works.most_common()]
    for pass_ in (0, 1):
        for w in ranked:
            if len(chosen) >= a.n_works: break
            if w in chosen: continue
            auth = meta[by_work[w][0]]['author']
            if pass_ == 0 and auth in used_auth: continue
            chosen.append(w); used_auth.add(auth)
    core = [max(by_work[w], key=lambda c: sim[row_of[c]]) for w in chosen]
    edge = min(m, key=lambda c: sim[row_of[c]])
    non = [c for c in ids if labels[c] != a.topic]
    near = max(non, key=lambda c: sim[row_of[c]])

    def entry(kind, c):
        r, cm = meta[c], cmap[c]
        return [f'### {kind}: {c} — *{r["title"]}* ({r["author"]}, {r["year"]})',
                f'genre_deep: {r["genre_deep"]} · play_type_deep: {r["play_type_deep"]} · edition {r["edition_id"]} · nodes {cm["node_start"]}–{cm["node_end"]} · '
                f'{cm["len_B_words"]} words · cos to centroid {sim[row_of[c]]:.3f} · topic in this seed: {labels[c]}', '',
                texts[c], '', '**Candidate interpretation (reader):** ', '', '**Counter-reading / limits (reader):** ', '', '---', '']
    s = sheet.get(a.topic, {})
    md = [f'# Reading pack — topic {a.topic} (seed {a.seed})', '',
          f'size {len(m)} chunks · {len(works)} works · dominant work {s.get("dominant_work", "")} ({s.get("dominant_work_share", "")}) · '
          f'draft label (AI, unconfirmed): {s.get("draft_label", "")}', '',
          f'class-TF-IDF: {s.get("ctfidf_top10", "")}', f'KeyBERT: {s.get("keybert_top10", "")}', f'MMR: {s.get("mmr_top10", "")}', '',
          'Works in this topic (chunks): ' + '; '.join(f'{meta[by_work[w][0]]["title"][:45]} — {meta[by_work[w][0]]["author"][:30]} ({n})' for w, n in works.most_common(12)), '',
          'How to read: core = one chunk per work nearest the centroid; edge = the member farthest from the centroid; near-miss = the closest chunk the model did NOT put here. '
          'Name the content from the texts first; genre labels are metadata to compare against afterwards.', '', '---', '']
    for c in core: md += entry('core', c)
    md += entry('edge (weakest member)', edge)
    md += entry('near-miss (outside the topic)', near)
    out.write_text('\n'.join(md), encoding='utf-8')
    print(f'topic {a.topic}: {len(core)} core + edge + near-miss → {out}')
    for c in core + [edge, near]:
        print(f'  {c:12s} {meta[c]["title"][:40]:40s} {meta[c]["author"][:25]:25s} {meta[c]["genre_deep"][:20]:20s} sim={sim[row_of[c]]:.3f} topic={labels[c]}')


if __name__ == '__main__':
    main()
