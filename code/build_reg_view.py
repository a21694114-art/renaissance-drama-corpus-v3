#!/usr/bin/env python3
"""build_reg_view.py  (reg-view-2026-09-14.4)

Derive spelling-regularized views of a frozen corpus build from EarlyPrint XML.

    v3 kept nodes (TCP XPath + text hash)  --align-->  EarlyPrint <l>/<p> blocks (block level)
    aligned node  --token alignment-->  the SPAN of EarlyPrint tokens that corresponds to this node only
    span re-emitted with `reg` applied (mechanical guards only); unaligned / unlocatable nodes -> v3 text
    with only long-s -> s and word-initial VV -> W.

Change in .4: contractions that EarlyPrint splits with join= (I+le, 'T+is, wee+le) are matched as one unit, so a
span never cuts a contraction; a node whose first or last word cannot be located is not taken from EarlyPrint.

Why token spans (change in .3): EarlyPrint sometimes merges two TCP lines (or a line + speaker label + next
line) into one <l>.  Emitting the whole block duplicated the neighbour's words and re-imported speaker labels.
Now each node keeps only the EarlyPrint tokens its own words align to; extra tokens are admitted only as
gap fills (the node has a <gap>) or as a bounded insertion inside the matched span.

The frozen v3 build is never modified.  Output is a sibling directory under out_corpus/.

Rules applied to a `reg` value (documented for the paper):
  1. reject garbage: no letters, mixed inner case (tIED), or equal to the token's POS tag;
  2. proper nouns (pos nn*/np*): accept reg only if it keeps the initial capital (Moore->Moor yes, Iago->jago no);
  3. join="right"/"left" sub-tokens are glued (Wee+le -> we'll);
  4. everything else: reg accepted as given.  No contextual review (then/than etc. accepted as EarlyPrint has them).

Usage (from new_pipeline/):
  python3 build_reg_view.py --ep-dir <earlyprint xml dir> --out out_corpus/<dir> [--editions 838,80,731]
                            [--resume] [--max-seconds 165]
  The run stops cleanly after the current source file once --max-seconds is exceeded; rerun with --resume.
  Per-view pair counts are flushed after every source file, so interrupted chunks lose nothing.
"""
import argparse, csv, difflib, hashlib, json, re, time
from collections import Counter, defaultdict
from pathlib import Path
from lxml import etree

VERSION = 'reg-view-2026-09-14.4'
HERE = Path(__file__).resolve().parent
CORPUS = HERE / 'out_corpus' / 'corpus-v3-2026-09-08'
SOURCE = HERE.parent / 'tcp_drama'
VIEWS = ['texts_analysis_en', 'texts_no_prologue_epilogue']
DROP = {'speaker', 'stage', 'note', 'head', 'gap', 'figure', 'fw'}
OPEN_PC = set('([{“‘«')
FUZZY_MIN = 0.85          # block-level similarity for the fuzzy pass
LOOKAHEAD = 60            # blocks searched forward inside a replace window
SPAN_MIN_COVER = 0.75     # share of the node's words that must align inside the chosen EarlyPrint block
XMLID = '{http://www.w3.org/XML/1998/namespace}id'


def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_text(s): return sha_bytes(s.encode('utf-8'))
def ln(e): return etree.QName(e).localname if isinstance(e.tag, str) else ''


# ---- exact copy of the v3 extractor's node text (extract_units.py element_text) ----
def element_text(el):
    def walk(e, is_root):
        n = ln(e)
        if n in DROP:
            return e.tail or ''
        if n == 'g' and 'EOLhyphen' in (e.get('ref') or ''):
            return (e.tail or '').lstrip()
        buf = e.text or ''
        for c in e:
            buf += walk(c, False)
        return buf if is_root else buf + (e.tail or '')
    return re.sub(r'\s+', ' ', walk(el, True)).strip()


def canon(s):
    """Comparison key: alphanumerics only, lower-case, long s -> s, VV/vv -> w (TCP prints W as VV)."""
    return ''.join(c.lower().replace('ſ', 's') for c in s if c.isalnum()).replace('vv', 'w')


def candidates(root):
    """Outermost <l>/<p> under <text>, not inside a dropped container (same as the pilot audit)."""
    for e in root.iter():
        if ln(e) not in ('l', 'p'):
            continue
        names = [ln(a) for a in e.iterancestors()]
        if 'text' in names and not (set(names) & (DROP | {'l', 'p'})):
            yield e


def ep_tokens(e):
    if ln(e) in DROP:
        return
    if ln(e) in ('w', 'pc'):
        yield e
        return
    for ch in e:
        yield from ep_tokens(ch)


def surface(w):
    return ''.join(w.itertext()).strip()


def block_key(e):
    return ''.join(canon(surface(w)) for w in ep_tokens(e))


def body_gaps(el):
    """<gap> elements of a TCP node that lie in its emitted text (not inside a dropped container)."""
    out = []
    def walk(e):
        for c in e:
            n = ln(c)
            if n == 'gap':
                out.append(c)
            elif n not in DROP:
                walk(c)
    walk(el)
    return out


def fallback_text(t):
    t = t.replace('ſ', 's')
    t = re.sub(r'\bVV', 'W', t)
    t = re.sub(r'\bvv', 'w', t)
    t = re.sub(r'\bVv', 'W', t)
    return t


def reg_garbage(reg, pos):
    if not re.search(r'[A-Za-z]', reg):
        return True
    if re.search(r'[a-z][A-Z]', reg):
        return True
    if pos and reg == pos:
        return True
    return False


def emit_tokens(toks, stats, pairs):
    """Rebuild text from a list of EarlyPrint <w>/<pc> tokens with reg applied."""
    pieces, glue_next = [], False
    for tok in toks:
        txt = surface(tok)
        if not txt:
            continue
        if ln(tok) == 'pc':
            if txt in OPEN_PC:
                pieces.append((' ' if pieces else '') + txt); glue_next = True
            else:
                pieces.append(txt); glue_next = False
            continue
        stats['tokens'] += 1
        reg, pos, join = tok.get('reg'), tok.get('pos') or '', tok.get('join') or ''
        out = txt.replace('ſ', 's')
        if reg:
            stats['reg_available'] += 1
            if reg_garbage(reg, pos):
                stats['reg_rejected_garbage'] += 1
            elif (pos.startswith('nn') or pos.startswith('np')) and not reg[:1].isupper():
                stats['reg_rejected_name_lowercased'] += 1
            else:
                out = reg; stats['reg_applied'] += 1
                if reg.lower() != txt.replace('ſ', 's').lower():
                    pairs[(txt.replace('ſ', 's').lower(), reg.lower())] += 1
        sep = '' if (glue_next or join in ('left', 'both') or not pieces) else ' '
        pieces.append(sep + out)
        glue_next = join in ('right', 'both')
    return re.sub(r'\s+', ' ', ''.join(pieces)).strip()


def is_subsequence(short, long):
    it = iter(long)
    return all(ch in it for ch in short)


def word_similar(a, b):
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if len(short) >= 4 and len(short) / len(long) >= 0.5 and is_subsequence(short, long):
        return True          # gap-truncated word inside its filled form (oged / toged)
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.75


def text_with_gap_marks(el):
    """v3 node text, but every <gap> leaves a standalone ◊ token so edge gaps can be located."""
    def walk(e, is_root):
        n = ln(e)
        if n == 'gap':
            # letter-level gaps stay inside their word (fe◊tile); word/line-level gaps become a standalone mark
            mark = '◊' if 'letter' in (e.get('extent') or '') else ' ◊ '
            return mark + (e.tail or '')
        if n in DROP:
            return e.tail or ''
        if n == 'g' and 'EOLhyphen' in (e.get('ref') or ''):
            return (e.tail or '').lstrip()
        buf = e.text or ''
        for c in e:
            buf += walk(c, False)
        return buf if is_root else buf + (e.tail or '')
    return re.sub(r'\s+', ' ', walk(el, True)).strip()


def join_groups(toks):
    """Group EarlyPrint tokens linked by join="right"/"left"/"both" (I + le = Ile, 'T + is = 'Tis) into
    indivisible units.  Returns a list of token lists in document order."""
    groups = []
    for t in toks:
        j = t.get('join') or ''
        if groups and (groups[-1][-1].get('join') in ('right', 'both') or j in ('left', 'both')):
            groups[-1].append(t)
        else:
            groups.append([t])
    return groups


def node_span(block, el, prev_words=(), next_words=()):
    """Locate the tokens of `block` that correspond to this TCP node.

    Returns (token_list, info) or (None, reason).  Matching works on join-groups (a contraction split by
    EarlyPrint is one unit), so a span never starts or ends inside a contraction.  Only EarlyPrint units the
    node's own words align to are kept; unmatched units between them are admitted (bounded); units
    before/after the aligned run are admitted only where the node itself has a whole-word <gap> at that edge
    and the words are not the neighbouring node's.  A node whose first or last word finds no unit at all is
    not emitted from EarlyPrint (fallback), so edge words are never silently dropped."""
    groups = join_groups(list(ep_tokens(block)))
    g_canon = [''.join(canon(surface(t)) for t in g if ln(t) == 'w') for g in groups]
    g_pos = [i for i, c in enumerate(g_canon) if c]
    ep_words = [g_canon[i] for i in g_pos]
    raw = text_with_gap_marks(el).split()
    lead_gap = 0
    for t in raw:
        if canon(t): break
        lead_gap += t.count('◊')
    trail_gap = 0
    for t in reversed(raw):
        if canon(t): break
        trail_gap += t.count('◊')
    tcp_words = [canon(t) for t in raw if canon(t)]
    if not tcp_words or not ep_words:
        return None, 'empty'
    sm = difflib.SequenceMatcher(None, tcp_words, ep_words, autojunk=False)
    first = last = None
    matched_src = set()
    inner_ins = lead_ins = trail_ins = 0
    ops = sm.get_opcodes()
    for idx, (op, a, b, c, d) in enumerate(ops):
        if op == 'equal':
            matched_src.update(range(a, b))
            first = c if first is None else first
            last = d - 1
        elif op == 'replace':
            hits, p, i = [], c, a
            while i < b:
                j = next((j for j in range(p, d) if ep_words[j] == tcp_words[i]), None)
                if j is not None:
                    hits.append(j); matched_src.add(i); p = j + 1; i += 1; continue
                found = False
                # many-to-one: EarlyPrint joined words the source prints apart (a nother / some body / how ere)
                for j in range(p, min(d, p + 3)):
                    for k in (2, 3):
                        cat = ''.join(tcp_words[i:i + k])
                        if i + k <= b and (cat == ep_words[j] or (len(cat) >= 4 and word_similar(cat, ep_words[j]))):
                            hits.append(j); matched_src.update(range(i, i + k)); p = j + 1; i += k; found = True; break
                    if found: break
                if found: continue
                # one-to-many: source word that EarlyPrint prints as several units
                for j in range(p, min(d, p + 3)):
                    for k in (2, 3):
                        cat = ''.join(ep_words[j:j + k])
                        if j + k <= d and (cat == tcp_words[i] or (len(cat) >= 4 and word_similar(tcp_words[i], cat))):
                            hits.extend(range(j, j + k)); matched_src.add(i); p = j + k; i += 1; found = True; break
                    if found: break
                if found: continue
                j = next((j for j in range(p, d) if word_similar(tcp_words[i], ep_words[j])), None)
                if j is not None:
                    hits.append(j); matched_src.add(i); p = j + 1
                i += 1
            if hits:
                first = hits[0] if first is None else first
                last = hits[-1]
                inner_ins += (hits[-1] - hits[0] + 1) - len(hits)
            elif first is not None and idx < len(ops) - 1:
                inner_ins += d - c
        elif op == 'insert':
            if first is None:
                lead_ins = d - c
            elif idx == len(ops) - 1:
                trail_ins = d - c
            else:
                inner_ins += d - c
    if first is None or len(matched_src) / len(tcp_words) < SPAN_MIN_COVER:
        return None, 'low_cover'
    # the node's own first and last words must be located, or nothing of it is taken from EarlyPrint
    if 0 not in matched_src or (len(tcp_words) - 1) not in matched_src:
        return None, 'edge_word_unmatched'
    n_gaps = sum(t.count('◊') for t in raw)
    if inner_ins > max(3, 0.3 * len(tcp_words)) + 2 * n_gaps:
        return None, 'too_many_insertions'
    if trail_gap and trail_ins:
        k = min(trail_ins, trail_gap + 1)
        extra = ep_words[last + 1:last + 1 + k]
        if not (next_words and tuple(extra) == tuple(next_words[:len(extra)])):
            last = min(last + k, len(ep_words) - 1)
    if lead_gap and lead_ins:
        k = min(lead_ins, lead_gap + 1)
        extra = ep_words[first - k:first]
        if not (prev_words and tuple(extra) == tuple(prev_words[-len(extra):])):
            first = max(first - k, 0)
    gs, ge = g_pos[first], g_pos[last]
    # opening punctuation immediately before, closing punctuation after (up to the next word unit)
    i = gs - 1
    while i >= 0 and not g_canon[i] and all(surface(t) in OPEN_PC for t in groups[i]) and (first == 0 or i > g_pos[first - 1]):
        gs = i; i -= 1
    i = ge + 1
    while i < len(groups) and not g_canon[i] and (last == len(g_pos) - 1 or i < g_pos[last + 1]):
        ge = i; i += 1
    span = [t for g in groups[gs:ge + 1] for t in g]
    return span, {'matched': len(matched_src), 'n_words': len(tcp_words), 'ep_units_in_block': len(ep_words),
                  'span_units': last - first + 1, 'inner_ins': inner_ins}


def align(ok, ek, has_gap):
    """pass 1: exact monotone anchors; pass 2: greedy monotone pairing inside replace windows.
    Blocks may be shared by consecutive nodes (EarlyPrint merged lines); the token span step separates them."""
    mapping, how = {}, {}
    sm = difflib.SequenceMatcher(None, ok, ek, autojunk=False)
    for op, a, b, c, d in sm.get_opcodes():
        if op == 'equal':
            for oi, ei in zip(range(a, b), range(c, d)):
                if ok[oi]:
                    mapping[oi] = ei; how[oi] = 'exact'
        elif op == 'replace':
            j = c
            for oi in range(a, b):
                if not ok[oi] or j >= d:
                    continue
                best, bj, kind = 0.0, None, None
                for ej in range(j, min(d, j + LOOKAHEAD)):
                    m = difflib.SequenceMatcher(None, ok[oi], ek[ej], autojunk=False)
                    if m.real_quick_ratio() >= FUZZY_MIN and m.quick_ratio() >= FUZZY_MIN:
                        r = m.ratio()
                        if r >= FUZZY_MIN and r > best:
                            best, bj, kind = r, ej, 'fuzzy'
                            if r > 0.98:
                                break
                    if bj is None and len(ok[oi]) >= 8 and len(ek[ej]) > len(ok[oi]) and len(ok[oi]) / len(ek[ej]) >= 0.4 and is_subsequence(ok[oi], ek[ej]):
                        best, bj, kind = 1.0, ej, ('gapfill' if has_gap[oi] else 'merged')
                        break
                if bj is not None:
                    mapping[oi] = bj; how[oi] = kind
                    j = bj if kind == 'merged' else bj + 1      # a merged block may serve the next node too
    return mapping, how


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ep-dir', required=True)
    ap.add_argument('--ep-manifest', default=None, help='download_manifest.csv (commit/sha per file)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--editions', default=None, help='comma-separated edition ids (test runs)')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--max-seconds', type=float, default=0, help='stop cleanly after the current file once exceeded')
    args = ap.parse_args()
    EP = Path(args.ep_dir); OUT = Path(args.out)
    only = set(args.editions.split(',')) if args.editions else None
    for v in VIEWS:
        (OUT / (v + '_reg')).mkdir(parents=True, exist_ok=True)
    (OUT / '_state').mkdir(exist_ok=True)
    log = open(OUT / 'build.log', 'a')
    def say(*a):
        s = ' '.join(str(x) for x in a); print(s, flush=True); log.write(s + '\n'); log.flush()
    say(f'== {VERSION} start {time.strftime("%Y-%m-%d %H:%M:%S")} resume={args.resume} corpus={CORPUS} ep={EP}')

    sha2tcp = {}
    for p in sorted(SOURCE.glob('*.xml')):
        sha2tcp[sha_bytes(p.read_bytes())] = p.stem
    ep_meta = {}
    if args.ep_manifest:
        for r in csv.DictReader(open(args.ep_manifest, encoding='utf-8')):
            ep_meta[r['tcp_id']] = {'commit': r.get('commit'), 'sha256': r.get('sha256')}
    manifest = {r['edition_id_effective']: r for r in csv.DictReader(open(CORPUS / 'corpus_manifest.csv', encoding='utf-8'))}

    # --- stream kept_nodes.csv once into per-(view, edition) node lists (memory-safe) ---
    nodes_dir = OUT / '_nodes'
    if not (args.resume and nodes_dir.exists()):
        nodes_dir.mkdir(exist_ok=True)
        buf, started = defaultdict(list), set()
        def flush(key):
            with open(nodes_dir / f'{key[0]}__{key[1]}.tsv', 'a' if key in started else 'w', encoding='utf-8') as h:
                h.write(''.join(buf[key]))
            started.add(key); buf[key] = []
        with open(CORPUS / 'kept_nodes.csv', encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f):
                if r['view'] not in VIEWS or (only and r['edition_id'] not in only):
                    continue
                key = (r['view'], r['edition_id'])
                buf[key].append('\t'.join([r['out_index'], r['source_sha256'], r['node_path'], r['text_sha256'], r['text_role']]) + '\n')
                if len(buf[key]) >= 5000:
                    flush(key)
        for key in list(buf):
            if buf[key]:
                flush(key)
        say('node lists written:', len(buf))

    per_tcp = defaultdict(lambda: defaultdict(list))
    for p in sorted(nodes_dir.glob('*.tsv')):
        view, ed = p.stem.split('__', 1)
        if only and ed not in only:
            continue
        with open(p, encoding='utf-8') as f:
            first = f.readline().split('\t')
        tcp = sha2tcp.get(first[1])
        if not tcp:
            say(f'!! edition {ed}: source sha not found among tcp_drama files'); continue
        per_tcp[tcp][ed].append(view)

    mpath = OUT / 'reg_manifest.csv'
    done = set()
    if args.resume and mpath.exists():
        for r in csv.DictReader(open(mpath, encoding='utf-8')):
            done.add((r['view'], r['edition_id']))
    mf = open(mpath, 'a' if args.resume else 'w', encoding='utf-8', newline='')
    mw = csv.writer(mf)
    count_keys = ['n_nodes', 'aligned_exact', 'aligned_fuzzy', 'aligned_gapfill', 'aligned_merged', 'span_fallback', 'unaligned_fallback',
                  'tokens', 'reg_available', 'reg_applied', 'reg_rejected_garbage', 'reg_rejected_name_lowercased',
                  'tcp_letter_gaps_in_aligned_nodes', 'tcp_word_gaps_in_aligned_nodes', 'ep_gaps_in_aligned_blocks']
    fields = ['view', 'edition_id', 'file', 'tcp', 'ep_commit', 'ep_sha256'] + count_keys + \
             ['node_cov_pct', 'char_cov_pct', 'n_chars_v3_file', 'n_chars_reg_file', 'sha256_v3', 'sha256_reg', 'hash_mismatch']
    if not args.resume or not done:
        mw.writerow(fields)
    uf = open(OUT / 'unaligned_nodes.jsonl', 'a' if args.resume else 'w', encoding='utf-8')
    # per-view pair counters, persisted after every source file (chunk-safe)
    pairs = {v: Counter() for v in VIEWS}
    pairs_paths = {v: OUT / '_state' / f'pairs_{v}.csv' for v in VIEWS}
    if args.resume:
        for v in VIEWS:
            if pairs_paths[v].exists():
                for a, b, n in csv.reader(open(pairs_paths[v], encoding='utf-8')):
                    pairs[v][(a, b)] = int(n)
    def save_pairs():
        for v in VIEWS:
            tmp = pairs_paths[v].with_suffix('.tmp')
            with open(tmp, 'w', encoding='utf-8', newline='') as f:
                w = csv.writer(f)
                for (a, b), n in pairs[v].items():
                    w.writerow([a, b, n])
            tmp.replace(pairs_paths[v])

    t0 = time.time()
    stopped_early = False
    for n_tcp, (tcp, eds) in enumerate(sorted(per_tcp.items()), 1):
        if all((v, ed) in done for ed, vs in eds.items() for v in vs):
            continue
        if args.max_seconds and time.time() - t0 > args.max_seconds:
            stopped_early = True
            say(f'-- time budget reached before {tcp}; rerun with --resume'); break
        epp = EP / f'{tcp}.xml'
        if not epp.exists():
            say(f'!! {tcp}: no EarlyPrint file; editions {list(eds)} will be fallback-only')
        ot = etree.parse(str(SOURCE / f'{tcp}.xml'))
        ob = list(candidates(ot.getroot()))
        by_path = {ot.getpath(e): i for i, e in enumerate(ob)}
        ok = [canon(element_text(e)) for e in ob]
        has_gap = [bool(body_gaps(e)) for e in ob]
        if epp.exists():
            et = etree.parse(str(epp))
            eb = list(candidates(et.getroot()))
            ek = [block_key(e) for e in eb]
            mapping, how = align(ok, ek, has_gap)
            ep_sha = sha_bytes(epp.read_bytes())
        else:
            eb, ek, mapping, how, ep_sha = [], [], {}, {}, ''
        meta = ep_meta.get(tcp, {})
        for ed, views in sorted(eds.items()):
            for view in views:
                if (view, ed) in done:
                    continue
                st = Counter(); lines_v3, lines_reg = [], []
                mismatch = 0
                with open(nodes_dir / f'{view}__{ed}.tsv', encoding='utf-8') as f:
                    rows = [l.rstrip('\n').split('\t') for l in f]
                rows.sort(key=lambda r: int(r[0]))
                els, texts = [], []
                for r in rows:
                    hits = ot.xpath(r[2])
                    els.append(hits[0] if len(hits) == 1 else None)
                    texts.append(element_text(els[-1]) if els[-1] is not None else '')
                words = [[canon(w) for w in t.split() if canon(w)] for t in texts]
                for ri, (out_index, ssha, node_path, tsha, role) in enumerate(rows):
                    el, text = els[ri], texts[ri]
                    if el is None or sha_text(text) != tsha:
                        mismatch += 1
                    lines_v3.append(text)
                    st['n_nodes'] += 1
                    oi = by_path.get(ot.getpath(el)) if el is not None else None
                    record = None
                    if oi is not None and oi in mapping:
                        blk = eb[mapping[oi]]
                        gaps = body_gaps(el)
                        span, info = node_span(blk, el, words[ri - 1] if ri else (), words[ri + 1] if ri + 1 < len(rows) else ())
                        if span is not None:
                            st['aligned_' + how[oi]] += 1; st['chars_aligned'] += len(text)
                            st['tcp_letter_gaps_in_aligned_nodes'] += sum(1 for g in gaps if 'letter' in (g.get('extent') or ''))
                            st['tcp_word_gaps_in_aligned_nodes'] += sum(1 for g in gaps if 'word' in (g.get('extent') or ''))
                            st['ep_gaps_in_aligned_blocks'] += sum(1 for g in blk.iter() if ln(g) == 'gap')
                            new = emit_tokens(span, st, pairs[view]) or fallback_text(text)
                            lines_reg.append(new)
                        else:
                            st['span_fallback'] += 1
                            lines_reg.append(fallback_text(text))
                            record = {'status': 'span_fallback', 'reason': info, 'ep_block': blk.get(XMLID),
                                      'ep_text': ' '.join(surface(w) for w in ep_tokens(blk))[:300]}
                    else:
                        st['unaligned_fallback'] += 1
                        lines_reg.append(fallback_text(text))
                        cand = ''
                        if oi is not None and eb:
                            best = max(((difflib.SequenceMatcher(None, ok[oi], ek[j], autojunk=False).ratio(), j) for j in range(max(0, oi - 40), min(len(eb), oi + 40))), default=(0, None))
                            cand = {'similarity': round(best[0], 4), 'ep_block': eb[best[1]].get(XMLID) if best[1] is not None else None,
                                    'ep_text': ' '.join(surface(w) for w in ep_tokens(eb[best[1]]))[:300] if best[1] is not None else ''}
                        record = {'status': 'unaligned', 'best_candidate': cand}
                    if record:
                        uf.write(json.dumps(dict({'view': view, 'edition_id': ed, 'tcp': tcp, 'out_index': int(out_index), 'node_path': node_path,
                                                  'text_role': role, 'text': text[:500]}, **record), ensure_ascii=False) + '\n')
                v3_join = '\n'.join(lines_v3); reg_join = '\n'.join(lines_reg)
                fname = manifest[ed]['file']
                with open(OUT / (view + '_reg') / fname, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(reg_join)
                nn = st['n_nodes'] or 1
                aligned = st['aligned_exact'] + st['aligned_fuzzy'] + st['aligned_gapfill'] + st['aligned_merged']
                row = {'view': view, 'edition_id': ed, 'file': fname, 'tcp': tcp, 'ep_commit': meta.get('commit', ''), 'ep_sha256': ep_sha or meta.get('sha256', '')}
                row.update({k: st[k] for k in count_keys})
                row.update({'node_cov_pct': round(100 * aligned / nn, 2), 'char_cov_pct': round(100 * st['chars_aligned'] / (sum(map(len, lines_v3)) or 1), 2),
                            'n_chars_v3_file': len(v3_join), 'n_chars_reg_file': len(reg_join),
                            'sha256_v3': sha_text(v3_join), 'sha256_reg': sha_text(reg_join), 'hash_mismatch': mismatch})
                expected = manifest[ed].get(f'sha256[{view}]', '')
                if expected and expected != row['sha256_v3']:
                    say(f'!! {view} {ed}: kept nodes do not reproduce the frozen v3 file')
                    row['hash_mismatch'] = row['hash_mismatch'] or 'file'
                mw.writerow([row[k] for k in fields]); mf.flush()
        save_pairs()
        say(f'[{n_tcp}/{len(per_tcp)}] {tcp} blocks tcp={len(ob)} ep={len(eb)} editions={list(eds)} {time.time() - t0:.0f}s')
    mf.close(); uf.close()

    for v in VIEWS:
        with open(OUT / f'reg_pairs_{v}.csv', 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f); w.writerow(['surface_lower', 'reg_lower', 'count'])
            for (a, b), n in pairs[v].most_common():
                w.writerow([a, b, n])
    if not stopped_early:
        inputs = {'version': VERSION, 'built_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'corpus_build': str(CORPUS),
                  'kept_nodes_sha256': sha_bytes((CORPUS / 'kept_nodes.csv').read_bytes()), 'corpus_manifest_sha256': sha_bytes((CORPUS / 'corpus_manifest.csv').read_bytes()),
                  'ep_dir': str(EP), 'ep_manifest': args.ep_manifest, 'rules': __doc__.split('Rules applied')[1].split('Usage')[0].strip(),
                  'fuzzy_min': FUZZY_MIN, 'lookahead': LOOKAHEAD, 'span_min_cover': SPAN_MIN_COVER, 'views': VIEWS}
        (OUT / 'inputs_manifest.json').write_text(json.dumps(inputs, ensure_ascii=False, indent=1))
        say('== done', time.strftime('%Y-%m-%d %H:%M:%S'))


if __name__ == '__main__':
    main()
