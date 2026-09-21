#!/usr/bin/env python3
"""01_chunk_map.py — one chunk map for the A/B comparison of original vs regularized spelling.

Chunks are defined ONCE on the v3 node structure and applied identically to both views:
  A = texts_analysis_en/       (original spelling, frozen v3)
  B = texts_analysis_en_reg/   (EarlyPrint-regularized, r3)
Both views have the same 580 files and the same line (= node) count per file, so a chunk is a
range of node indices [node_start, node_end] inside one document.  Whole nodes are accumulated
while the chunk stays within the bound: --chunk-chars (default 2000, the previous pipeline's
rule) or, preferably, --max-tokens N measured with the GTE-large tokenizer (its window is 512
tokens; 2,000 characters of original spelling usually exceed it).  With --bound-on max (default)
a chunk must fit in BOTH variants, so no variant is truncated by the model.  A single node over
the bound is split at the SAME sentence indices in A and B (split_pair), so piece i covers the
same sentences in both; if sentence boundaries cannot be matched the node stays one unsplit chunk
in both variants (counted in long_nodes_unsplit).

Outputs (in --out):
  chunk_map.csv    chunk_id, edition_id, file, node_start, node_end, piece, n_pieces, len_A, len_B
  chunks_A.csv     chunk_id, text          chunks_B.csv   chunk_id, text
  chunk_meta.csv   chunk_id + edition metadata from corpus_manifest.csv (work_id, title, author,
                   year, genre, play type, tcp)
  chunk_map_summary.json
"""
import argparse, csv, json, math, re, sys
from collections import Counter
from pathlib import Path

SENT_END = re.compile(r'[.!?;]["\')\]]?\s')


def sentence_ends(text):
    return [m.end() for m in SENT_END.finditer(text)]


def split_pair(ta, tb, k):
    """Split A and B texts of one node into k pieces at the SAME sentence indices.  Both texts must
    have the same number of sentence ends (punctuation is preserved by regularization); the cut
    sentences are chosen on A by equal sentence count and the same indices are applied to B.
    Returns (pieces_a, pieces_b) or None if boundaries cannot be matched."""
    ea, eb = sentence_ends(ta), sentence_ends(tb)
    if len(ea) != len(eb) or len(ea) < k - 1:
        return None
    n = len(ea)
    idx = sorted({round(j * n / k) - 1 for j in range(1, k)})
    idx = [i for i in idx if 0 <= i < n]
    if len(idx) != k - 1:
        return None
    def cut(text, ends):
        pieces, prev = [], 0
        for i in idx:
            pieces.append(text[prev:ends[i]].strip()); prev = ends[i]
        pieces.append(text[prev:].strip())
        return pieces
    pa, pb = cut(ta, ea), cut(tb, eb)
    if any(not x for x in pa) or any(not x for x in pb):
        return None
    return pa, pb


def make_length(tokenizer, max_tokens):
    """Length function used to bound chunks: real tokenizer count when available (GTE-large has a
    512-token window; the old 2,000-char rule let ~80 % of original-spelling chunks exceed it),
    otherwise characters."""
    if tokenizer is None:
        return (lambda t: len(t)), 'chars'
    def n_tok(t):
        return len(tokenizer(t, add_special_tokens=False, truncation=False)['input_ids'])
    return n_tok, f'tokens({max_tokens})'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True, help='dir containing texts_analysis_en/ and texts_analysis_en_reg/')
    ap.add_argument('--manifest', required=True, help='corpus_manifest.csv of the frozen build')
    ap.add_argument('--out', required=True)
    ap.add_argument('--chunk-chars', type=int, default=2000, help='char bound (used when no tokenizer)')
    ap.add_argument('--max-tokens', type=int, default=0, help='bound chunks by GTE-large token count instead (e.g. 480); needs transformers')
    ap.add_argument('--bound-on', default='max', choices=['A', 'B', 'max'], help='which variant the bound is measured on (max = both must fit)')
    ap.add_argument('--limit-docs', type=int, default=0, help='first N documents only (smoke test)')
    a = ap.parse_args()
    A_DIR = Path(a.corpus) / 'texts_analysis_en'
    B_DIR = Path(a.corpus) / 'texts_analysis_en_reg'
    OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
    meta = {r['edition_id_effective']: r for r in csv.DictReader(open(a.manifest, encoding='utf-8'))}
    tokenizer = None
    if a.max_tokens:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained('thenlper/gte-large')
    length, unit = make_length(tokenizer, a.max_tokens)
    LIMIT = a.max_tokens if a.max_tokens else a.chunk_chars
    def fits(ta, tb):   # used for split pieces of a single long node
        if a.bound_on == 'A': return length(ta) <= LIMIT
        if a.bound_on == 'B': return length(tb) <= LIMIT
        return length(ta) <= LIMIT and length(tb) <= LIMIT

    files = sorted(A_DIR.glob('*.txt'), key=lambda p: int(p.stem.split('__')[0]))
    if a.limit_docs:
        files = files[:a.limit_docs]
    fmap = open(OUT / 'chunk_map.csv', 'w', encoding='utf-8', newline='')
    fA = open(OUT / 'chunks_A.csv', 'w', encoding='utf-8', newline='')
    fB = open(OUT / 'chunks_B.csv', 'w', encoding='utf-8', newline='')
    fM = open(OUT / 'chunk_meta.csv', 'w', encoding='utf-8', newline='')
    wmap = csv.writer(fmap); wmap.writerow(['chunk_id', 'edition_id', 'file', 'node_start', 'node_end', 'piece', 'n_pieces', 'len_A', 'len_B'])
    wA = csv.writer(fA); wA.writerow(['chunk_id', 'text'])
    wB = csv.writer(fB); wB.writerow(['chunk_id', 'text'])
    mcols = ['chunk_id', 'edition_id', 'work_id', 'deep_id', 'title', 'author', 'year', 'genre_deep', 'play_type_deep', 'tcp', 'n_nodes_in_chunk']
    wM = csv.writer(fM); wM.writerow(mcols)

    stats = Counter(); lens = []
    for fa in files:
        ed = fa.stem.split('__')[0]
        fb = B_DIR / fa.name
        if not fb.exists():
            sys.exit(f'missing regularized twin for {fa.name}')
        LA = fa.read_text(encoding='utf-8').split('\n')
        LB = fb.read_text(encoding='utf-8').split('\n')
        if len(LA) != len(LB):
            sys.exit(f'line count differs in {fa.name}: {len(LA)} vs {len(LB)}')
        m = meta[ed]
        idx = 0

        def emit(ns, ne, ta, tb, piece=0, npieces=1):
            nonlocal idx
            cid = f'{ed}_{idx:05d}'; idx += 1
            wmap.writerow([cid, ed, fa.name, ns, ne, piece, npieces, len(ta), len(tb)])
            wA.writerow([cid, ta]); wB.writerow([cid, tb])
            wM.writerow([cid, ed, m['work_id'], m['deep_id_effective'], m['title'], m['author'], m['year_effective'],
                         m['genre_deep'], m['play_type_deep'], m['tcp'], ne - ns + 1])
            stats['chunks'] += 1; lens.append(len(ta))

        # per-node lengths once (token counts of the pieces summed; +2 for the model's special tokens)
        la_len = [length(x) for x in LA]; lb_len = [length(x) for x in LB]
        extra = 2 if tokenizer is not None else 0
        def fits_range(s0, s1):
            sa = sum(la_len[s0:s1 + 1]) + extra; sb = sum(lb_len[s0:s1 + 1]) + extra
            if a.bound_on == 'A': return sa <= LIMIT
            if a.bound_on == 'B': return sb <= LIMIT
            return sa <= LIMIT and sb <= LIMIT
        cur, start = [], 0
        for i, line in enumerate(LA):
            single_ok = fits_range(i, i)
            if not single_ok:
                if cur:
                    emit(start, i - 1, ' '.join(cur), ' '.join(LB[start:i])); cur = []
                k = 2
                while True:
                    sp = split_pair(line, LB[i], k)
                    if sp is None:
                        break
                    if all(fits(x, y) for x, y in zip(*sp)):
                        break
                    k += 1
                    if k > 12:
                        sp = None; break
                if sp is None:
                    emit(i, i, line, LB[i]); stats['long_nodes_unsplit'] += 1
                else:
                    stats['long_nodes_split'] += 1
                    for p, (ta, tb) in enumerate(zip(*sp)):
                        emit(i, i, ta, tb, p, len(sp[0]))
                start = i + 1
                continue
            if cur and not fits_range(start, i):
                emit(start, i - 1, ' '.join(cur), ' '.join(LB[start:i]))
                cur, start = [], i
            cur.append(line)
        if cur:
            emit(start, len(LA) - 1, ' '.join(cur), ' '.join(LB[start:]))
        stats['docs'] += 1
    for f in (fmap, fA, fB, fM):
        f.close()
    lens.sort()
    summary = {'docs': stats['docs'], 'chunks': stats['chunks'], 'bound': f'{LIMIT} {unit} on {a.bound_on}',
               'long_nodes_split': stats['long_nodes_split'], 'long_nodes_unsplit': stats['long_nodes_unsplit'],
               'len_A_min': lens[0], 'len_A_median': lens[len(lens) // 2], 'len_A_max': lens[-1],
               'chunks_under_200_chars': sum(1 for x in lens if x < 200)}
    (OUT / 'chunk_map_summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
