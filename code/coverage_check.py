#!/usr/bin/env python3
"""
coverage_check.py — independent reconciliation of source XML against the candidate tables.

Enumerates, straight from the XML, every outermost <l>/<p> under TEI/text (body, front, back,
recursively through <group>) that is not inside a dropped container and has non-empty text.
Then checks that each (source_sha256, node_path) appears EXACTLY ONCE in
out/lines.csv ∪ out/frontback_lines.csv.  Writes out/coverage_report.csv and exits non-zero
if anything is missing or duplicated.
"""
import os, csv, glob, hashlib, sys
from collections import defaultdict, Counter
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_units as x
HERE = x.HERE; OUT = x.OUT_DIR
csv.field_size_limit(10**9)

seen = Counter()
for fn in ('lines.csv', 'frontback_lines.csv'):
    for r in csv.DictReader(open(os.path.join(OUT, fn), encoding='utf-8')):
        seen[(r['source_sha256'], r['node_path'])] += 1

rows = []; tot_expected = 0; tot_missing = 0; tot_dup = 0
for path in sorted(glob.glob(os.path.join(x.SRC_DIR, '*.xml'))):
    tcp = os.path.basename(path)[:-4]
    sha = hashlib.sha256(open(path, 'rb').read()).hexdigest()
    tree = etree.parse(path, etree.XMLParser(recover=True, huge_tree=True))
    text = tree.getroot().find('t:text', x.NS)
    if text is None: continue
    expected = []
    for el, anc, names in x.candidate_nodes(text):
        if x.element_text(el): expected.append(tree.getpath(el))
    missing = [p for p in expected if seen.get((sha, p), 0) == 0]
    dup = [p for p in expected if seen.get((sha, p), 0) > 1]
    tot_expected += len(expected); tot_missing += len(missing); tot_dup += len(dup)
    rows.append([tcp, len(expected), len(expected) - len(missing), len(missing), len(dup), ';'.join(missing[:5]), ';'.join(dup[:5])])
with open(os.path.join(OUT, 'coverage_report.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['tcp', 'candidate_nodes_in_xml', 'covered', 'missing', 'duplicated', 'missing_examples', 'duplicate_examples']); w.writerows(rows)
import json, datetime
def _sha(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
summary = {'checked_at': datetime.datetime.now().isoformat(timespec='seconds'), 'rule_version': x.RULE_VERSION,
           'inputs': {fn: _sha(os.path.join(OUT, fn)) for fn in ('lines.csv', 'frontback_lines.csv')},
           'source_files': len(rows), 'candidate_nodes_in_xml': tot_expected, 'missing': tot_missing, 'duplicated': tot_dup,
           'table_keys_total': sum(seen.values()), 'table_keys_distinct': len(seen)}
json.dump(summary, open(os.path.join(OUT, 'coverage_summary.json'), 'w'), indent=1)
print(f'candidate nodes in XML: {tot_expected:,} | missing from tables: {tot_missing:,} | claimed twice: {tot_dup:,} | table rows {sum(seen.values()):,} / distinct keys {len(seen):,}')
bad = [r for r in rows if r[3] or r[4]]
print(f'files with gaps or duplicates: {len(bad)}')
for r in bad[:15]: print('  ', r[0], 'missing', r[3], 'dup', r[4], r[5][:80])
sys.exit(1 if bad else 0)
