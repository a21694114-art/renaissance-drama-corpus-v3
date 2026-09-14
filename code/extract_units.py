#!/usr/bin/env python3
"""
extract_units.py  —  candidate-text extraction from TCP TEI-XML, with full coverage.

RULE_VERSION below.  This script does NOT decide what is dialogue or what is a play. It
produces candidate lines with provenance; inclusion is decided later (materialize_txt.py for
the line rule, unit_map.csv for the work rule).  Coverage guarantee (checked by
coverage_check.py): every outermost <l>/<p> under TEI/text that is not inside a dropped
container appears EXACTLY ONCE in lines.csv (body) or frontback_lines.csv (front/back).

Inputs   ../tcp_drama/*.xml   (the 469 ORIGINAL TCP files; nothing else)
         deep_min.csv         (only to know which TCP ids are DEEP "Collection" records)
Outputs  out/lines.csv, out/frontback_lines.csv, out/units_manifest.csv, out/parse_log.csv

Unit splitting
  text/group/text                      -> one unit per inner <text> (recursive)
  single body + DEEP Collection        -> one unit per top-level <div> of the body
  second-level subsplit                -> when a container holds >=2 work-type divs and no
                                          act/scene: one unit per work div PLUS ONE RESIDUAL
                                          unit (<id>.0) holding everything else in the
                                          container (prologues, epilogues, songs, notes...),
                                          so nothing is lost.  `part` divs count as works
                                          only when their heads carry part numbers.
  every sub-unit records parent_unit so components can be re-associated in the map.
"""
RULE_VERSION = 'extract-2026-09-08.13'

import os, re, csv, glob, hashlib
from collections import Counter
from lxml import etree

HERE     = os.path.dirname(os.path.abspath(__file__))
SRC_DIR  = os.path.join(HERE, '..', 'tcp_drama')
OUT_DIR  = os.path.join(HERE, 'out')
DEEP_MIN = os.path.join(HERE, 'deep_min.csv')
os.makedirs(OUT_DIR, exist_ok=True)

TEI = 'http://www.tei-c.org/ns/1.0'
NS  = {'t': TEI}
def ln(e):
    return etree.QName(e).localname if isinstance(e.tag, str) else ''

DROP_CONTAINERS = {'speaker', 'stage', 'note', 'head', 'gap', 'figure', 'fw'}

# ---------------------------------------------------------------- text of one <l>/<p>
def element_text(el):
    def walk(e, is_root):
        n = ln(e)
        if n in DROP_CONTAINERS:
            return e.tail or ''
        if n == 'g' and 'EOLhyphen' in (e.get('ref') or ''):
            return (e.tail or '').lstrip()
        buf = e.text or ''
        for c in e:
            buf += walk(c, False)
        return buf if is_root else buf + (e.tail or '')
    return re.sub(r'\s+', ' ', walk(el, True)).strip()

def excl(el, exclude):
    """True if `el` itself or any ancestor is one of the excluded elements (explicit splits exclude sibling <p>/<head>/<sp>, not only divs)."""
    return any(a is x for a in [el, *el.iterancestors()] for x in exclude)

def candidate_nodes(container, exclude=()):
    """Outermost <l>/<p> under `container`, not inside a dropped container, not inside any
    element of `exclude` (used for residual units).  Yields elements in document order."""
    for el in container.iter():
        n = ln(el)
        if n not in ('l', 'p'): continue
        anc = list(el.iterancestors())
        if excl(el, exclude): continue
        names = [ln(a) for a in anc]
        if any(m in DROP_CONTAINERS for m in names): continue
        if any(m in ('l', 'p') for m in names): continue
        yield el, anc, names

def lines_with_provenance(container, tree, exclude=()):
    out = []; n_sp = 0; dropped = Counter()
    for el in container.iter():
        n = ln(el)
        if n == 'sp' and not excl(el, exclude): n_sp += 1
        if n in ('stage', 'note'): dropped[n] += 1
    for el, anc, names in candidate_nodes(container, exclude):
        t = element_text(el)
        if not t: continue
        div_path = '>'.join((a.get('type') or '?') for a in reversed(anc) if ln(a) == 'div')
        out.append({'in_sp': int('sp' in names), 'div_path': div_path,
                    'parent': names[0] if names else '', 'node_path': tree.getpath(el), 'text': t})
    return out, n_sp, dropped

def missing_gaps(el, exclude=()):
    """TCP <gap reason="missing"> inside the unit: (count, total extent text) - evidence that the
    source copy lacks pages, i.e. zero output may mean 'not transcribed', not 'no text'."""
    n = 0; ext = []
    for g in el.iter('{%s}gap' % TEI):
        if excl(g, exclude): continue
        if (g.get('reason') or '').startswith('missing'):
            n += 1; ext.append(g.get('extent') or '?')
    return n, ';'.join(ext)[:120]

def trailer_text(el, exclude=()):
    out = []
    for t in el.iter():
        if ln(t) in ('trailer', 'closer') and not excl(t, exclude):
            s = re.sub(r'\s+', ' ', ''.join(t.itertext())).strip()
            if s: out.append(s[:120])
    return ' || '.join(out)[:300]

WORK_HEAD_TYPES = ('play', 'tragedy', 'comedy', 'masque', 'interlude', 'entertainment', 'pageant', 'dialogue', 'part')
def first_head(el, exclude=()):
    for d in el.iter('{%s}div' % TEI):
        if excl(d, exclude): continue
        if (d.get('type') or '') in WORK_HEAD_TYPES:
            h = d.find('t:head', NS)
            if h is not None and not excl(h, exclude) and ''.join(h.itertext()).strip():
                return re.sub(r'\s+', ' ', ''.join(h.itertext())).strip()[:120]
    for h in el.iter('{%s}head' % TEI):
        if excl(h, exclude): continue
        s = re.sub(r'\s+', ' ', ''.join(h.itertext())).strip()
        if s: return s[:120]
    return ''

def front_types(text_el):
    fr = text_el.find('t:front', NS)
    if fr is None: return ''
    return ';'.join(sorted({d.get('type') or '?' for d in fr.iter('{%s}div' % TEI)}))

# ---------------------------------------------------------------- units
# a unit = dict(uid, kind, div_type, node, text_el, exclude, parent)
def U(uid, kind, dtype, node, tel, exclude=(), parent=''):
    return {'uid': uid, 'kind': kind, 'div_type': dtype, 'node': node, 'tel': tel, 'exclude': tuple(exclude), 'parent': parent}

def units_from_text(text_el, base_id, is_collection):
    units = []
    grp = text_el.find('t:group', NS)
    if grp is not None:
        for k, sub in enumerate(grp.findall('t:text', NS), 1):
            units.extend(units_from_text(sub, f'{base_id}.{k}', is_collection=False))
        return units
    body = text_el.find('t:body', NS)
    if body is None:
        return units
    if is_collection:
        kids = [d for d in body if ln(d) == 'div']
        k = 0
        for d in kids:
            k += 1
            units.append(U(f'{base_id}.{k}', 'body_div', d.get('type') or '', d, text_el, parent=base_id))
        # residual of the collection body: <l>/<p> not inside any top-level div (rare)
        units.append(U(f'{base_id}.0', 'residual', 'residual', body, text_el, exclude=kids, parent=base_id))
    else:
        units.append(U(base_id, 'single' if '.' not in base_id else 'group_text', '', body, text_el))
    return units

WORK_TYPES = {'masque', 'maque', 'entertainment', 'pageant', 'play', 'tragedy', 'comedy', 'interlude', 'dialogue'}
WRAPPERS   = {'collection_of_masques', 'text', 'masques', 'entertainments', 'section'}
# Units whose <div type="section"> children are SEPARATE works (evidence in manual_overrides.csv).
# Not a general rule: A02732's nine sections are parts of ONE entertainment and must not be split.
FORCE_SPLIT_SECTIONS = {'A04632.13'}   # Jonson 1616: Highgate / Theobalds 1606 / Theobalds 1607 inside the Althorp 'Satyre' text
PART_HEAD  = re.compile(r'\b(firste?|seconde?|thirde?|fourth|fift|fifth|1|2|3|4|5|i|ii|iii|iv|v)\.?\s+(part|parte)\b|\b(part|parte)\s+(the\s+)?(firste?|seconde?|thirde?|1|2|3|i|ii|iii)\b|\b(prima|secunda|tertia)\s+pars\b|\b(prim[ae]|secund[ae]|terti[ae])\s+partis\b', re.I)  # "The Second Part of ..." / "Secunda pars" = separate work (Latin added 2026-09-07 for A10440 Gentleness and Nobility)

def work_divs(container, uid=''):
    kids = [d for d in container if ln(d) == 'div']
    wrapper = None
    if len(kids) == 1 and (kids[0].get('type') or '') in WRAPPERS:
        wrapper = kids[0]; kids = [d for d in wrapper if ln(d) == 'div']
    types = [(d.get('type') or '') for d in kids]
    if 'act' in types or 'scene' in types:
        return [], wrapper
    w = [d for d in kids if (d.get('type') or '') in WORK_TYPES]
    if uid in FORCE_SPLIT_SECTIONS:
        w = [d for d in kids if (d.get('type') or '') == 'section']
    parts = [d for d in kids if (d.get('type') or '') == 'part']
    min_w = 1 if (ln(container) == 'div' and (container.get('type') or '') in WORK_TYPES) else 2   # a work nested inside a work is split off
    if not w and len(parts) >= 2:
        heads = [''.join(h.itertext()) for d in parts for h in [d.find('t:head', NS)] if h is not None]
        ptype = (container.get('type') or '') if ln(container) == 'div' else ''
        if sum(1 for h in heads if PART_HEAD.search(h)) >= 1 or ptype in ('entertainment', 'entertainments', 'pageant'):
            w = parts                                              # otherwise parts are internal sections
    return (w if len(w) >= min_w else []), wrapper

def subsplit(u, depth=0):
    if depth >= 3 or u['kind'] == 'residual':
        return [u]
    w, wrapper = work_divs(u['node'], u['uid'])
    if not w:
        return [u]
    container = wrapper if wrapper is not None else u['node']
    out = []
    for i, d in enumerate(w, 1):
        out.extend(subsplit(U(f"{u['uid']}.{i}", 'work_div', d.get('type') or '', d, u['tel'], parent=u['uid']), depth + 1))
    # residual: everything in the ORIGINAL node except the work divs
    out.append(U(f"{u['uid']}.0", 'residual', 'residual', u['node'], u['tel'], exclude=w, parent=u['uid']))
    return out

# ---------------------------------------------------------------- explicit splits (evidence-based)
# A unit whose node mixes several DEEP works, or hides one work among poems, is divided by CHILD RANGES
# (1-based element positions = XPath *[n]) of a named container element.  XML and XPaths are untouched;
# every candidate node of the old unit is assigned to exactly one new unit; 'residual' keeps the rest.
# Evidence: ChatGPT corpus_v1 source review 2026-09-07 (source_split_plan.json) + Claude reading of the
# source heads 2026-09-08.  Not a general rule.
EXPLICIT_SPLITS = {
    # Middleton, Honourable Entertainments 1621: one <div type="part"> prints THREE works -
    # children 1-8 Sir Francis Jones's at Easter (DEEP 5078.08), 9-13 Lords of the Council by Sheriff Allen
    # (5078.09; head 'Here followes the ... Entertainments of the Lords ... The first Entertainment'),
    # 14-30 Lords of the Council by Sheriff Ducie (5078.10; head 'The last Entertainment ...').
    'A07502.2.4': {'container': '/*/*[2]/*[2]/*[2]/*[9]', 'parts': [('1', 1, 8, 'part'), ('2', 9, 13, 'part'), ('3', 14, 30, 'part')], 'residual': False},
    # Gascoigne, Posies 1575, 'Flowers': the Montague Masque (DEEP 5007.01) = poem divs 35-38 of the poems div
    # (35 the masque speech; 36-38 the Actor's spoken continuation: 'the Actor tooke maister Tho. Bro. by the
    # hand ... with these words', 'saying thus', 'the Actor did make an ende thus').  The other poems = residual.
    'A01514.1': {'container': '/*/*[2]/*[2]/*[1]/*[2]/*', 'parts': [('1', 35, 38, 'poem')], 'residual': True},
}

def apply_explicit_splits(units, tree):
    out = []
    for u in units:
        sp = EXPLICIT_SPLITS.get(u['uid'])
        if not sp:
            out.append(u); continue
        hits = tree.xpath(sp['container'])
        if len(hits) != 1: raise SystemExit(f"explicit split {u['uid']}: container {sp['container']} matched {len(hits)} elements")
        C = hits[0]
        if not (C is u['node'] or any(a is u['node'] for a in C.iterancestors())): raise SystemExit(f"explicit split {u['uid']}: container is not inside the unit node")
        kids = [k for k in C if isinstance(k.tag, str)]           # element children only (XPath *[n] positions)
        taken = []
        for suf, lo, hi, dtype in sp['parts']:
            sel = kids[lo - 1:hi]
            if len(sel) != hi - lo + 1: raise SystemExit(f"explicit split {u['uid']}: range {lo}-{hi} exceeds {len(kids)} children")
            taken += sel
            nu = U(f"{u['uid']}.{suf}", 'work_div', dtype, C, u['tel'], exclude=[k for k in kids if not any(k is s for s in sel)] + list(u['exclude']), parent=u['uid'])
            nu['child_range'] = f"{tree.getpath(C)} children {lo}-{hi}"
            out.append(nu)
        if sp['residual']:
            r = U(f"{u['uid']}.0", 'residual', 'residual', u['node'], u['tel'], exclude=list(u['exclude']) + taken, parent=u['uid'])
            r['child_range'] = f"all except {tree.getpath(C)} children " + ','.join(f'{lo}-{hi}' for _, lo, hi, _ in sp['parts'])
            out.append(r)
        elif len(taken) != len(kids):
            raise SystemExit(f"explicit split {u['uid']}: parts do not cover all {len(kids)} children and no residual is declared")
    return out

def all_text_elements(text_el):
    yield text_el
    grp = text_el.find('t:group', NS)
    if grp is not None:
        for sub in grp.findall('t:text', NS):
            yield from all_text_elements(sub)

# ---------------------------------------------------------------- main
def main():
    coll = {r['TCP'] for r in csv.DictReader(open(DEEP_MIN, newline='', encoding='utf-8')) if r['record_type'] == 'Collection'}
    files = sorted(glob.glob(os.path.join(SRC_DIR, '*.xml')))
    print(f'{len(files)} source files; {len(coll)} DEEP collection records; rule {RULE_VERSION}')
    manifest, plog = [], []
    lf = open(os.path.join(OUT_DIR, 'lines.csv'), 'w', newline='', encoding='utf-8'); lw = csv.writer(lf)
    lw.writerow(['unit_id', 'parent_unit', 'seq', 'tcp', 'source_file', 'source_sha256', 'node_path', 'div_path', 'in_sp', 'parent', 'n_chars', 'rule_version', 'text'])
    ff = open(os.path.join(OUT_DIR, 'frontback_lines.csv'), 'w', newline='', encoding='utf-8'); fw = csv.writer(ff)
    fw.writerow(['tcp', 'text_node_path', 'section', 'seq', 'source_sha256', 'node_path', 'div_path', 'in_sp', 'parent', 'n_chars', 'rule_version', 'text'])
    for path in files:
        tcp = os.path.basename(path)[:-4]; fname = os.path.basename(path)
        sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
        well_formed = True
        try:
            tree = etree.parse(path)
        except etree.XMLSyntaxError:
            well_formed = False
            tree = etree.parse(path, etree.XMLParser(recover=True, huge_tree=True))
        root = tree.getroot()
        text_el = root.find('t:text', NS)
        if text_el is None:
            plog.append([tcp, fname, sha, well_formed, 'NO <text>', 0]); continue
        for tel in all_text_elements(text_el):
            for section in ('front', 'back'):
                sec = tel.find(f't:{section}', NS)
                if sec is None: continue
                L, _, _ = lines_with_provenance(sec, tree)
                for i, r in enumerate(L, 1):
                    fw.writerow([tcp, tree.getpath(tel), section, i, sha, r['node_path'], r['div_path'], r['in_sp'], r['parent'], len(r['text']), RULE_VERSION, r['text']])
        structure = 'group' if text_el.find('t:group', NS) is not None else ('collection_body' if tcp in coll else 'single_body')
        units = apply_explicit_splits([s for u in units_from_text(text_el, tcp, is_collection=(tcp in coll)) for s in subsplit(u)], tree)
        plog.append([tcp, fname, sha, well_formed, structure, len(units)])
        for u in units:
            L, n_sp, dropped = lines_with_provenance(u['node'], tree, u['exclude'])
            if u['kind'] == 'residual' and not L:
                continue                                    # empty residual: nothing to record
            for i, r in enumerate(L, 1):
                lw.writerow([u['uid'], u['parent'], i, tcp, fname, sha, r['node_path'], r['div_path'], r['in_sp'], r['parent'], len(r['text']), RULE_VERSION, r['text']])
            fr = u['tel'].find('t:front', NS); bk = u['tel'].find('t:back', NS)
            manifest.append({
                'unit_id': u['uid'], 'parent_unit': u['parent'], 'tcp': tcp, 'source_file': fname, 'source_sha256': sha,
                'unit_node_path': tree.getpath(u['node']), 'unit_child_range': u.get('child_range', ''), 'kind': u['kind'], 'div_type': u['div_type'], 'div_n': (u['node'].get('n') or '') if ln(u['node'])=='div' else '',
                'head': first_head(u['node'], u['exclude']), 'trailer_text': trailer_text(u['node'], u['exclude']),
                'missing_gaps': missing_gaps(u['node'], u['exclude'])[0], 'missing_extent': missing_gaps(u['node'], u['exclude'])[1],
                'n_sp': n_sp, 'n_lines': len(L),
                'chars_in_sp': sum(len(r['text']) for r in L if r['in_sp']),
                'chars_outside_sp_unclassified': sum(len(r['text']) for r in L if not r['in_sp']),
                'div_paths_present': ';'.join(sorted({r['div_path'].split('>')[-1] for r in L}))[:200],
                'dropped_stage': dropped['stage'], 'dropped_note': dropped['note'],
                'has_front': fr is not None, 'has_back': bk is not None, 'front_div_types': front_types(u['tel']),
                'well_formed': well_formed, 'rule_version': RULE_VERSION,
            })
    lf.close(); ff.close()
    with open(os.path.join(OUT_DIR, 'units_manifest.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(manifest[0].keys())); w.writeheader(); w.writerows(manifest)
    with open(os.path.join(OUT_DIR, 'parse_log.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['tcp', 'source_file', 'source_sha256', 'well_formed', 'structure', 'n_units']); w.writerows(plog)
    kinds = Counter(m['kind'] for m in manifest)
    print(f'wrote {len(manifest)} candidate units ({sum(1 for m in manifest if m["n_lines"]==0)} with zero candidate lines); kinds: {dict(kinds)}')

if __name__ == '__main__':
    main()
