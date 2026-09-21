#!/usr/bin/env python3
"""07_sample_chunks.py — draw a stratified reading sample of chunks (default 20) for a manual check
of the chunking rule: are chunks readable units, do cuts fall at sensible places, are long
speeches split acceptably, do short works look right?

  python 07_sample_chunks.py --chunks <chunks dir> --out <file.md> [--n 20] [--seed 7] [--variant B]

Strata = play type (chunk_meta.play_type_deep) × length tercile (len_B_words); chunks with flags
(long_node_piece / long_node_unsplit / short_doc / under_min) are over-sampled so the exceptions
get looked at.  Writes a Markdown file: one section per chunk with metadata, flags, the
neighbouring node text before/after the cut (context lines), and the chunk text.
"""
import argparse, csv, random
from collections import defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--variant', default='B')
    ap.add_argument('--corpus', default='', help='corpus dir (texts_analysis_en_reg/) to show the node before/after each cut')
    a = ap.parse_args()
    ch = Path(a.chunks)
    cmap = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_map.csv', encoding='utf-8'))}
    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    text = {r['chunk_id']: r['text'] for r in csv.DictReader(open(ch / f'chunks_{a.variant}.csv', encoding='utf-8'))}
    ids = list(cmap)
    lens = sorted(int(cmap[c]['len_B_words']) for c in ids)
    t1, t2 = lens[len(lens) // 3], lens[2 * len(lens) // 3]
    def tercile(c):
        w = int(cmap[c]['len_B_words'])
        return 'short' if w < t1 else ('mid' if w < t2 else 'long')
    strata = defaultdict(list)
    for c in ids:
        key = ('flagged', cmap[c]['flags']) if cmap[c]['flags'] else (meta[c]['play_type_deep'] or 'unknown', tercile(c))
        strata[key].append(c)
    rng = random.Random(a.seed)
    keys = sorted(strata, key=lambda k: (k[0] != 'flagged', k))
    for k in keys:
        rng.shuffle(strata[k])
    picked = []
    n_flag = min(a.n // 4, sum(len(strata[k]) for k in keys if k[0] == 'flagged'))
    # a quarter from flagged strata, the rest round-robin over play type × tercile
    fk = [k for k in keys if k[0] == 'flagged']; ok = [k for k in keys if k[0] != 'flagged']
    i = 0
    while len(picked) < n_flag and fk:
        k = fk[i % len(fk)]
        if strata[k]:
            picked.append((k, strata[k].pop()))
        else:
            fk.remove(k); continue
        i += 1
    i = 0
    while len(picked) < a.n and ok:
        k = ok[i % len(ok)]
        if strata[k]:
            picked.append((k, strata[k].pop()))
        else:
            ok.remove(k); continue
        i += 1
    docs = {}
    def node_text(fn, i):
        if not a.corpus:
            return None
        if fn not in docs:
            p = Path(a.corpus) / 'texts_analysis_en_reg' / fn
            docs[fn] = p.read_text(encoding='utf-8').split('\n') if p.exists() else []
        L = docs[fn]
        return L[i] if 0 <= i < len(L) else None
    md = [f'# Reading sample: {len(picked)} chunks (variant {a.variant}, seed {a.seed})', '',
          f'Length terciles (words): short < {t1} ≤ mid < {t2} ≤ long. Read for: is this a readable unit? does the cut fall at a sensible place? '
          'is a split speech still intelligible? Note anything odd next to the chunk id.', '']
    for k, c in picked:
        m, r = meta[c], cmap[c]
        md += [f'## {c} — {m["title"]} ({m["author"]}, {m["year"]}; {m["play_type_deep"]}; work {m["work_id"]})',
               f'stratum: {k[0]} / {k[1]} · nodes {r["node_start"]}–{r["node_end"]} · {r["len_B_words"]} words · tokens {r["len_B_tokens"] or "?"} · flags: {r["flags"] or "—"}', '']
        before = node_text(r['file'], int(r['node_start']) - 1); after = node_text(r['file'], int(r['node_end']) + 1)
        if before is not None:
            md += [f'> *(node before the cut)* {before[:300]}{"…" if len(before) > 300 else ""}', '']
        md += [text[c], '']
        if after is not None:
            md += [f'> *(node after the cut)* {after[:300]}{"…" if len(after) > 300 else ""}', '']
        md.append('---')
    Path(a.out).write_text('\n'.join(md), encoding='utf-8')
    print(f'{len(picked)} chunks written to {a.out}; strata used: {sorted({k for k, _ in picked})}')


if __name__ == '__main__':
    main()
