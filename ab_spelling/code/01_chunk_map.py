#!/usr/bin/env python3
"""01_chunk_map.py (v3) — word-bounded chunk map on the v3 node structure, for a long-window
embedding model.

Rule (final, 2026-09-20):
  * unit = consecutive nodes (lines) of one edition in texts_analysis_en_reg/ (B); the same node
    ranges are also materialized from texts_analysis_en/ (A) so long-s diagnostics still work;
  * target 500 words, allowed 400–600 (--target-words/--min-words/--max-words), measured on B by
    whitespace words; cuts only at node boundaries;
  * a single node longer than --max-words is split at sentence ends into k = ceil(words/target)
    near-equal pieces, at the SAME sentence indices in A and B (split_pair); if the sentence
    counts of A and B differ the node is kept whole and flagged long_node_unsplit (the model
    window is large enough, the flag only marks the exception);
  * the chunks of one document are chosen by dynamic programming: minimize the squared distance
    of every chunk length to the target, with a penalty below --min-words and a hard cap at
    --max-words; a cut that coincides with a structural boundary (change of the XML parent of the
    node, from --nodes-csv when given) is rewarded so scene/act edges are preferred;
  * no overlap; no short tail: the DP balances the last chunks instead of leaving a remainder;
  * an edition shorter than --min-words in total is one chunk, flagged short_doc;
  * with --tokenizer the final B text of every chunk is counted with that model's tokenizer and the
    count written to chunk_map.csv (len_B_tokens); --max-tokens warns if any chunk exceeds it.

Outputs (in --out): chunk_map.csv, chunks_A.csv, chunks_B.csv, chunk_meta.csv, chunk_map_summary.json
  chunk_map.csv: chunk_id, edition_id, file, node_start, node_end, piece_start, piece_end, n_pieces_end,
                 len_A_chars, len_B_chars, len_B_words, len_B_tokens, flags
"""
import argparse, csv, json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

SENT_END = re.compile(r'[.!?;]["\')\]]?\s')


def sentence_ends(text):
    return [m.end() for m in SENT_END.finditer(text)]


def split_pair(ta, tb, k):
    """Split A and B texts of one node into k pieces at the SAME sentence indices (equal sentence
    counts required).  Returns (pieces_a, pieces_b) or None."""
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


def words(t):
    return len(t.split())


def load_boundaries(nodes_csv):
    """file -> set of out_index whose XML parent differs from the previous kept node's parent
    (= a structural boundary before that node).  Any nodes table with columns file, out_index and
    node_path works (kept_nodes.csv / supplementary_nodes.csv of the v3 build)."""
    b = defaultdict(set); prev = {}
    with open(nodes_csv, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r.get('view', 'texts_analysis_en') != 'texts_analysis_en':   # kept_nodes.csv lists every view
                continue
            fn, i, p = r['file'], int(r['out_index']), r['node_path'].rsplit('/', 1)[0]
            if fn in prev and prev[fn] != p:
                b[fn].add(i)
            prev[fn] = p
    return b


def segment(lengths, boundary, target, lo, hi):
    """DP over units: returns list of (start, end) unit index ranges (end inclusive)."""
    n = len(lengths)
    INF = float('inf')
    f = [INF] * (n + 1); back = [-1] * (n + 1); f[0] = 0.0
    def cost(L):
        c = ((L - target) / 100.0) ** 2
        if L < lo:
            c += 4.0 + ((lo - L) / 50.0) ** 2
        return c
    for i in range(1, n + 1):
        total = 0
        j = i - 1
        while j >= 0:
            total += lengths[j]
            if total > hi and j != i - 1:
                break
            c = f[j] + cost(total) - (0.5 if (j in boundary and j > 0) else 0.0)
            if total > hi:          # single over-long unit: allowed, but costed as such
                c += 100.0
            if c < f[i]:
                f[i] = c; back[i] = j
            j -= 1
    out, i = [], n
    while i > 0:
        out.append((back[i], i - 1)); i = back[i]
    return out[::-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', required=True, help='dir containing texts_analysis_en/ and texts_analysis_en_reg/')
    ap.add_argument('--manifest', required=True, help='corpus_manifest.csv of the frozen build')
    ap.add_argument('--out', required=True)
    ap.add_argument('--target-words', type=int, default=500)
    ap.add_argument('--min-words', type=int, default=400)
    ap.add_argument('--max-words', type=int, default=600)
    ap.add_argument('--nodes-csv', default='', help='kept_nodes.csv of the build: structural boundaries preferred as cut points')
    ap.add_argument('--tokenizer', default='', help='HF model id whose tokenizer counts the final chunks (e.g. Alibaba-NLP/gte-large-en-v1.5)')
    ap.add_argument('--max-tokens', type=int, default=0, help='warn if a chunk exceeds this many tokens')
    ap.add_argument('--limit-docs', type=int, default=0, help='first N documents only (smoke test)')
    a = ap.parse_args()
    A_DIR = Path(a.corpus) / 'texts_analysis_en'
    B_DIR = Path(a.corpus) / 'texts_analysis_en_reg'
    OUT = Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
    meta = {r['edition_id_effective']: r for r in csv.DictReader(open(a.manifest, encoding='utf-8'))}
    boundaries = load_boundaries(a.nodes_csv) if a.nodes_csv else {}
    tok = None
    if a.tokenizer:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(a.tokenizer, trust_remote_code=True)

    files = sorted(A_DIR.glob('*.txt'), key=lambda p: int(p.stem.split('__')[0]))
    if a.limit_docs:
        files = files[:a.limit_docs]
    fmap = open(OUT / 'chunk_map.csv', 'w', encoding='utf-8', newline='')
    fA = open(OUT / 'chunks_A.csv', 'w', encoding='utf-8', newline='')
    fB = open(OUT / 'chunks_B.csv', 'w', encoding='utf-8', newline='')
    fM = open(OUT / 'chunk_meta.csv', 'w', encoding='utf-8', newline='')
    wmap = csv.writer(fmap)
    wmap.writerow(['chunk_id', 'edition_id', 'file', 'node_start', 'node_end', 'piece_start', 'piece_end', 'n_pieces_end', 'len_A_chars', 'len_B_chars', 'len_B_words', 'len_B_tokens', 'flags'])
    wA = csv.writer(fA); wA.writerow(['chunk_id', 'text'])
    wB = csv.writer(fB); wB.writerow(['chunk_id', 'text'])
    mcols = ['chunk_id', 'edition_id', 'work_id', 'deep_id', 'title', 'author', 'year', 'genre_deep', 'play_type_deep', 'tcp', 'n_nodes_in_chunk', 'len_B_words']
    wM = csv.writer(fM); wM.writerow(mcols)

    stats = Counter(); wlens = []; tlens = []
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
        bset = boundaries.get(fa.name, set())

        # units: nodes, long nodes pre-split at shared sentence indices
        units = []   # dicts: ns, ne, piece, n_pieces, ta, tb, w, boundary, flag
        for i, (ta, tb) in enumerate(zip(LA, LB)):
            w = words(tb)
            if w > a.max_words:
                sp = None
                k0 = max(2, math.ceil(w / a.target_words))
                for k in range(k0, k0 + 6):
                    sp = split_pair(ta, tb, k)
                    if sp is not None and all(words(x) <= a.max_words for x in sp[1]):
                        break
                    if sp is not None and k == k0 + 5:
                        sp = None
                if sp is None:
                    units.append(dict(ns=i, ne=i, piece=0, n_pieces=1, ta=ta, tb=tb, w=w, boundary=(i in bset), flag='long_node_unsplit'))
                    stats['long_nodes_unsplit'] += 1
                else:
                    stats['long_nodes_split'] += 1
                    for p, (xa, xb) in enumerate(zip(*sp)):
                        units.append(dict(ns=i, ne=i, piece=p, n_pieces=len(sp[0]), ta=xa, tb=xb, w=words(xb), boundary=(i in bset and p == 0), flag='long_node_piece'))
            else:
                units.append(dict(ns=i, ne=i, piece=0, n_pieces=1, ta=ta, tb=tb, w=w, boundary=(i in bset), flag=''))
        total_w = sum(u['w'] for u in units)
        if total_w < a.min_words:
            ranges = [(0, len(units) - 1)]; doc_flag = 'short_doc'; stats['short_docs'] += 1
        else:
            ranges = segment([u['w'] for u in units], {j for j, u in enumerate(units) if u['boundary']}, a.target_words, a.min_words, a.max_words)
            doc_flag = ''
        idx = 0
        for (s, e) in ranges:
            us = units[s:e + 1]
            ta = ' '.join(u['ta'] for u in us if u['ta']); tb = ' '.join(u['tb'] for u in us if u['tb'])
            wb = sum(u['w'] for u in us)
            # piece_start / piece_end: which sentence-piece of node_start / node_end the chunk begins / ends with
            # (0 when that node is whole); n_pieces_end = piece count of node_end
            piece_start, piece_end, npieces = us[0]['piece'], us[-1]['piece'], us[-1]['n_pieces']
            flags = sorted({u['flag'] for u in us if u['flag']} | ({doc_flag} if doc_flag else set()))
            if wb < a.min_words and not doc_flag:
                flags.append('under_min'); stats['chunks_under_min'] += 1
            if wb > a.max_words:
                stats['chunks_over_max'] += 1
            ntok = ''
            if tok is not None:
                ntok = len(tok(tb, add_special_tokens=True, truncation=False)['input_ids'])
                tlens.append(ntok)
                if a.max_tokens and ntok > a.max_tokens:
                    stats['chunks_over_max_tokens'] += 1
            cid = f'{ed}_{idx:05d}'; idx += 1
            wmap.writerow([cid, ed, fa.name, us[0]['ns'], us[-1]['ne'], piece_start, piece_end, npieces, len(ta), len(tb), wb, ntok, ';'.join(flags)])
            wA.writerow([cid, ta]); wB.writerow([cid, tb])
            wM.writerow([cid, ed, m['work_id'], m['deep_id_effective'], m['title'], m['author'], m['year_effective'],
                         m['genre_deep'], m['play_type_deep'], m['tcp'], us[-1]['ne'] - us[0]['ns'] + 1, wb])
            stats['chunks'] += 1; wlens.append(wb)
        stats['docs'] += 1
        if stats['docs'] % 50 == 0:
            print(f'{stats["docs"]} docs, {stats["chunks"]} chunks', flush=True)
    for f in (fmap, fA, fB, fM):
        f.close()
    wlens.sort(); tlens.sort()
    summary = {'docs': stats['docs'], 'chunks': stats['chunks'],
               'rule': f'target {a.target_words} words, allowed {a.min_words}-{a.max_words}, measured on B, cuts at node boundaries, DP-balanced',
               'boundaries_from': a.nodes_csv or None,
               'long_nodes_split': stats['long_nodes_split'], 'long_nodes_unsplit': stats['long_nodes_unsplit'],
               'short_docs': stats['short_docs'], 'chunks_under_min': stats['chunks_under_min'], 'chunks_over_max': stats['chunks_over_max'],
               'words_min': wlens[0], 'words_p10': wlens[len(wlens) // 10], 'words_median': wlens[len(wlens) // 2],
               'words_p90': wlens[9 * len(wlens) // 10], 'words_max': wlens[-1]}
    if tlens:
        summary.update({'tokenizer': a.tokenizer, 'tokens_median': tlens[len(tlens) // 2], 'tokens_p99': tlens[99 * len(tlens) // 100],
                        'tokens_max': tlens[-1], 'chunks_over_max_tokens': stats['chunks_over_max_tokens'], 'max_tokens': a.max_tokens})
    (OUT / 'chunk_map_summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
