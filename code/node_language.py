#!/usr/bin/env python3
"""
node_language.py - language evidence for every candidate node, straight from the source XML.

For each outermost <l>/<p> candidate (same enumeration as coverage_check.py / extract_units.candidate_nodes)
records the EFFECTIVE xml:lang (nearest ancestor-or-self carrying xml:lang), the raw value, and the XPath of the
element that carries it.  Writes out/node_language.csv keyed by (source_sha256, node_path) and
out/node_language_summary.json (input hashes are NOT involved: this table is derived from the XML alone, so
build_corpus.py cross-checks it against coverage_summary.json by node count).
Language codes are normalised: eng->en, lat->la, grc->grc (kept), fre->fr, ita->it, spa->es, ger->de, dut->nl,
heb->he, wel->cy, gre->grc; unknown raw values are kept verbatim.  Nodes with no xml:lang anywhere get '' and
build_corpus.py falls through to unit language / assumed default.
"""
import os, csv, glob, hashlib, sys, json, datetime
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_units as x
OUT = x.OUT_DIR
XML_LANG = '{http://www.w3.org/XML/1998/namespace}lang'
NORM = {'eng':'en','en':'en','lat':'la','la':'la','grc':'grc','gre':'grc','fre':'fr','fra':'fr','ita':'it','spa':'es','ger':'de','deu':'de','dut':'nl','nld':'nl','heb':'he','wel':'cy','cym':'cy','mul':'mul','und':''}
rows = []; counts = {}
for path in sorted(glob.glob(os.path.join(x.SRC_DIR, '*.xml'))):
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    tree = etree.parse(path, etree.XMLParser(recover=True, huge_tree=True))
    text = tree.getroot().find('t:text', x.NS)
    if text is None: continue
    for el, anc, names in x.candidate_nodes(text):
        if not x.element_text(el): continue
        raw = ''; src = ''
        for a in [el] + list(el.iterancestors()):
            v = a.get(XML_LANG)
            if v: raw = v; src = tree.getpath(a); break
        eff = NORM.get(raw.lower(), raw.lower()) if raw else ''
        rows.append([sha, tree.getpath(el), eff, raw, src]); counts[eff] = counts.get(eff, 0) + 1
with open(os.path.join(OUT, 'node_language.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['source_sha256', 'node_path', 'xml_lang_effective', 'xml_lang_raw', 'lang_source_xpath']); w.writerows(rows)
summary = {'checked_at': datetime.datetime.now().isoformat(timespec='seconds'), 'rule_version': x.RULE_VERSION, 'candidate_nodes_in_xml': len(rows), 'by_effective_language': dict(sorted(counts.items(), key=lambda kv: -kv[1]))}
json.dump(summary, open(os.path.join(OUT, 'node_language_summary.json'), 'w'), indent=1)
print(json.dumps(summary, indent=1))
