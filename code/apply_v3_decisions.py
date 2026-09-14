#!/usr/bin/env python3
"""Apply the eight close-out decisions for corpus v3 (2026-09-08).
Grace forwarded ChatGPT's proposal (corpus_audit/corpus_v2_review/给Claude的v2确认与八项收尾建议.md) for implementation;
that forwarding is recorded as the decision (policy_decisions.csv) - no other approval date is invented.

'supplementary' = kept OUTSIDE the main corpus, in supplementary/ with provenance (builder v8 fate); it records an analysis
boundary, NOT a judgement that the material is non-dramatic or that its performance function is settled.

  1 Heywood A03241.23 (620)               -> unit supplementary
  2 printed English translations (42)     -> 11 speech translations INCLUDED (language en, relation translation, original node linked
                                             when printed); 31 Norwich poem translations -> supplementary (with the Latin poems)
  3 Lyndsay A72573.1 (4,608, Scots)       -> unit supplementary; language sco by unit_language.csv override (TCP xml:lang=eng is wrong)
  4 Phillis Funerall A01227.2 part>day    -> container supplementary
  5 Bushell pillar sonnet A17342 (24)     -> container supplementary
  6 Edinburgh epigrams + panegyric A18463 -> containers supplementary
  7 Norwich Latin poems A01506 (57)       -> node decisions supplementary (one document with their 31 English translations)
  8 Byron shared prologue A18404 (24)     -> frames_decisions include, target_unit_id A18404.1 (Conspiracy, edition 647), role prologue
Every node row is verified against out/lines.csv (unit, node_path, text hash).  Nothing is silently overwritten.
"""
import csv, hashlib, json, os
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
REVIEW = os.path.expanduser('~/mnt/corpus_audit/corpus_v2_review')
TODAY = '2026-09-08'
DECIDED_BY = "Grace 2026-09-08: forwarded ChatGPT's eight-item proposal (给Claude的v2确认与八项收尾建议.md) for implementation; ChatGPT close-out review 2026-09-08 drafted the wording"
SRC = 'policy_decisions.csv 2026-09-08 (ChatGPT v2 close-out proposal forwarded by Grace); applied by Claude 2026-09-08'
def rd(p): return list(csv.DictReader(open(p, encoding='utf-8')))
def wr(p, rows, fields):
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows({k: r.get(k, '') for k in fields} for r in rows)
def sha(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()

TOUCH = {'A01506', 'A02732', 'A07513', 'A20053', 'A03241.23', 'A72573.1', 'A01227.2', 'A17342', 'A18463', 'A18404.1'}
L = {}; byunit = defaultdict(dict)
for r in csv.DictReader(open(os.path.join(OUT, 'lines.csv'), encoding='utf-8')):
    if r['unit_id'] in TOUCH: L[(r['source_sha256'], r['node_path'])] = r; byunit[r['unit_id']][int(r['seq'])] = r
man = {r['unit_id']: r for r in rd(os.path.join(OUT, 'units_manifest.csv'))}
NL = {}
for r in csv.DictReader(open(os.path.join(OUT, 'node_language.csv'), encoding='utf-8')): NL[(r['source_sha256'], r['node_path'])] = r['xml_lang_effective']

# ================= 0. policy_decisions.csv (new)
POL = [
 ('1', 'Heywood, Pleasant Dialogues 1637, Sundry Fancies (A03241.23, 620 nodes)', 'supplementary', 'Performance-frame candidates (prologues/epilogues/presenter speeches) whose work/witness/occasion attribution is not established; kept as separately documented supplementary material; never appended to another edition on a title match.'),
 ('2', 'Printed English translations of performed foreign-language speeches (42 nodes)', 'include 11 speech translations; 31 Norwich poem translations supplementary', 'Judged by the text function of a speech, not by whether English was spoken on the day; language=en, relation=translation, original node linked when printed; the Limbert farewell (A01506 seq 439) is recorded as not delivered according to the source; the Dutchmen speech (A02732 seq 126) has no printed original. Not generalised to poem translations.'),
 ('3', "Lyndsay, Ane Satyre of the Thrie Estaitis 1602 (A72573.1, 4,608 nodes)", 'supplementary (language sco)', 'Outside the DEEP sampling frame; no DEEP edition/work id invented; not merged into the main all-language texts/; language sco by reviewed unit override (TCP xml:lang=eng).'),
 ('4', "Fraunce, Phillis Funerall (A01227.2 part>day, 1,198 nodes, twelve day divisions)", 'supplementary', "Narrative funeral elegy: third-person narration links the laments; the book itself separates the pastoral from the funeral part; not converted piecemeal into dramatic dialogue."),
 ('5', "Bushell's Rock 1636, 'A Sonnet within the pillar of the Table at the Banquet' (A17342, 24 lines)", 'supplementary', 'Placement and direct address do not establish performance use; performance function left undetermined (not asserted never sung).'),
 ('6', "Edinburgh 1633 (A18463): EPIGRAMME group (12 lines) and Walter Forbes's panegyric (178 lines)", 'supplementary', 'Related to the entry but printed as independent poems; evidence insufficient to treat them as performance speech; not marked as verified unperformed.'),
 ('7', 'Norwich 1578 Latin poems Ad Solem / Ad Civitatem (A01506, 57 nodes) with their printed English translations (31 nodes)', 'supplementary (one document)', 'Function decision precedes language decision: poems of undetermined performance function do not enter the main corpus through the English view.'),
 ('8', "Byron's Conspiracy and Tragedy 1608, shared prologue (A18404, 24 lines)", 'include once, on the Conspiracy (A18404.1 / work 274 / edition 647 / DEEP 5069.01), role prologue', "Printed before the first play and names 'our Conspirator'; editorial attribution by printed sequence and wording, not proof that it served Part 1 only; relevance to both plays recorded; not duplicated into Part 2; the no-prologue/epilogue view still drops it."),
]
PF = os.path.join(HERE, 'policy_decisions.csv')
assert not os.path.exists(PF), 'policy_decisions.csv already exists'
wr(PF, [{'id': i, 'material': m, 'decision': d, 'decided_by': DECIDED_BY, 'decided_on': TODAY, 'basis': b, 'source': "ChatGPT 给Claude的v2确认与八项收尾建议.md + evidence JSON (corpus_v2_review/)", 'note': "'supplementary' records the analysis boundary of this corpus version; it is not a judgement that the material is non-dramatic"} for i, m, d, b in POL],
   ['id', 'material', 'decision', 'decided_by', 'decided_on', 'basis', 'source', 'note'])
print('policy_decisions.csv: 8 rows')

# ================= 1. manual_overrides.csv: Heywood + Lyndsay -> supplementary
OVF = os.path.join(HERE, 'manual_overrides.csv'); ov = rd(OVF); ovf = list(ov[0].keys()); n = 0
for r in ov:
    if r['unit_id'] == 'A03241.23':
        assert r['inclusion_status'] == 'deferred_to_grace'; r['inclusion_status'] = 'supplementary'
        r['evidence'] += ' | SUPPLEMENTARY per policy_decisions.csv #1 (2026-09-08): separately documented performance-frame material outside the main corpus.'; n += 1
    if r['unit_id'] == 'A72573.1':
        assert r['inclusion_status'] == 'deferred_to_grace'; r['inclusion_status'] = 'supplementary'; r['relation'] = 'outside_deep_scope'
        r['evidence'] += ' | SUPPLEMENTARY per policy_decisions.csv #3 (2026-09-08): Scots text outside the DEEP sampling frame, kept with source unit id, language sco (unit_language.csv override), no DEEP id invented.'; n += 1
assert n == 2; wr(OVF, ov, ovf); print('manual_overrides.csv: 2 rows changed')

# ================= 2. unit_language.csv: Lyndsay sco (override of xml:lang=eng)
ULF = os.path.join(HERE, 'unit_language.csv'); ul = rd(ULF); ulf = list(ul[0].keys()) + (['overrides_xml_lang'] if 'overrides_xml_lang' not in ul[0] else [])
assert 'A72573.1' not in {r['unit_id'] for r in ul}
ul.append({'unit_id': 'A72573.1', 'language': 'sco', 'overrides_xml_lang': 'yes',
           'basis': "Lyndsay, Ane Satyre of the thrie Estaitis (Edinburgh 1602): Scots text; TCP tags the whole file xml:lang=eng (4,614 nodes 'en' in node_language.csv), which is wrong for this text. Supplementary document, language sco, not in the English views.",
           'source': 'policy_decisions.csv #3 (2026-09-08)', 'status': 'applied'})
wr(ULF, ul, ulf); print('unit_language.csv:', len(ul), 'rows')

# ================= 3. container_audits.csv: deferred -> supplementary (items 4, 5, 6)
CAF = os.path.join(HERE, 'container_audits.csv'); ca = rd(CAF); caf = list(ca[0].keys()); n = 0
for r in ca:
    k = (r['unit_id'], r['div_path_filter'])
    if r['decision_default'] == 'deferred' and k in {('A01227.2', 'part>day'), ('A17342', 'sonnet'), ('A18463', 'text>epigram'), ('A18463', 'text>panegyric')}:
        item = {'A01227.2': '4', 'A17342': '5', 'A18463': '6'}[r['unit_id']]
        r['decision_default'] = 'supplementary'; r['decided_on'] = TODAY
        r['basis'] = r['basis'].replace('DEFERRED TO GRACE', 'SUPPLEMENTARY (policy_decisions.csv #%s, 2026-09-08; was deferred)' % item, 1)
        if r['unit_id'] == 'A18463' and r['div_path_filter'] == 'text>panegyric': r['basis'] = r['basis'].replace("Drummond's Panegyric", "the panegyric signed Walter Forbes (not Drummond; ChatGPT bibliographic_clarifications.json)")
        if r['unit_id'] == 'A18463' and r['div_path_filter'] == 'text>epigram': r['basis'] = r['basis'].replace('two epigrams', 'an EPIGRAMME group (12 lines)')
        if r['unit_id'] == 'A01227.2': r['basis'] = r['basis'].replace('eleven days', 'twelve day divisions')
        r['source'] += ' | ' + SRC; n += 1
    if r['unit_id'] == 'A01506' and r['decision_default'] == 'exclude' and 'translation' in r['div_path_filter']:
        r['basis'] += ' | 2026-09-08: superseded for every node under this chain by node decisions (policy_decisions.csv #2/#7: speech translations included, poem translations supplementary); row kept as a safety net.'; r['source'] += ' | ' + SRC
assert n == 4; wr(CAF, ca, caf); print('container_audits.csv:', len(ca), 'rows;', n, 'deferred -> supplementary')

# ================= 4. body_node_decisions.csv: translations (item 2) + Norwich poems (item 7)
NDF = os.path.join(HERE, 'body_node_decisions.csv'); nd = rd(NDF); ndf = list(nd[0].keys())
for c in ('supplementary_group', 'relation', 'translation_of'):
    if c not in ndf: ndf.append(c)
idx = {(r['source_sha256'], r['node_path']): r for r in nd}
E = json.load(open(os.path.join(REVIEW, 'english_speech_translation_11_recommendations.json'), encoding='utf-8'))
GROUP = 'Norwich 1578 Latin poems Ad Solem and Ad Civitatem with printed English translations'
def original_for(x):
    """nearest preceding kept non-English node in a speech/oration/version chain of the same unit = the printed original"""
    u = x['unit_id']; s = int(x['seq'])
    for q in range(s - 1, max(0, s - 20), -1):
        r = byunit[u].get(q)
        if not r: continue
        dk = (r['source_sha256'], r['node_path']); lang = (idx.get(dk) or {}).get('language') or NL.get(dk, '')   # node decision language beats xml:lang (A02732 Latin tagged eng)
        inner = r['div_path'].split('>')[-1]
        if lang not in ('en', 'unk', '') and inner in ('oration', 'subsection', 'version', 'section', 'speech'):
            return f"{u} seq {q} {r['node_path']} ({lang}; {r['div_path']}): {r['text'][:60]}"
    return ''
n_inc = 0
for x in E['speech_nodes']:
    key = (x['source_sha256'], x['node_path']); r = L.get(key); assert r and r['unit_id'] == x['unit_id'], key
    assert sha(r['text']) == x['text_sha256'], key
    orig = original_for(x)
    if x['unit_id'] == 'A02732' and x['seq'] == '126': orig = 'no printed original: the account says the Dutchmen\'s speech was delivered in Latin and prints it in English (source statement; no node invented)'
    assert orig, x
    row = idx.get(key)
    if row is None:
        row = {k: '' for k in ndf}; row.update(source_sha256=key[0], node_path=key[1], unit_id=x['unit_id'], seq=r['seq'], div_path=r['div_path'], container_node_path=man[x['unit_id']]['unit_node_path'], text_sha256=x['text_sha256']); nd.append(row); idx[key] = row
    else:
        assert row['decision'] == 'exclude' and row['exclusion_category'] == 'printed_translation', row
        row['basis'] = '(was: exclude printed_translation) ' + row['basis']
    row.update(decision='include', text_role='speech', language='en', exclusion_category='', relation='translation', translation_of=orig,
               basis=x['basis'] + ' ' + (row.get('basis', '') if row.get('basis', '').startswith('(was') else ''), source=SRC + ' (english_speech_translation_11_recommendations.json; text hash verified)',
               status='applied', decided_on=TODAY, decision_basis_type='editorial_function_assessment', historical_performance_status=x['historical_performance_status'])
    n_inc += 1
    print(f"  include translation {x['unit_id']} seq {x['seq']} <- {orig[:70]}")
n_supp = 0
for x in E['poetry_translation_nodes_recommended_supplementary']:
    key = (x['source_sha256'], x['node_path']); r = L.get(key); assert r and r['unit_id'] == 'A01506' and sha(r['text']) == x['text_sha256'], key
    assert key not in idx, key
    row = {k: '' for k in ndf}
    row.update(source_sha256=key[0], node_path=key[1], unit_id='A01506', seq=r['seq'], div_path=r['div_path'], container_node_path=man['A01506']['unit_node_path'], text_sha256=x['text_sha256'],
               decision='supplementary', text_role='poem', language='en', supplementary_group=GROUP, relation='translation', translation_of='A01506 Latin poem under /*/*[2]/*[2]/*[6] (seq 440-467, la; translation div /*/*[2]/*[2]/*[7] mirrors its structure), same supplementary document',
               basis='Printed English translation of the Norwich Latin poems; performance function of the poems undetermined -> supplementary with the originals (policy_decisions.csv #7), not admitted through the English view.',
               source=SRC + ' (english_speech_translation_11_recommendations.json; text hash verified)', status='applied', decided_on=TODAY, decision_basis_type='editorial_function_assessment')
    nd.append(row); idx[key] = row; n_supp += 1
n_lat = 0
for row in nd:
    if row['unit_id'] == 'A01506' and row['decision'] == 'deferred':
        assert row['container_node_path'] in ('/*/*[2]/*[2]/*[10]', '/*/*[2]/*[2]/*[6]'), row['container_node_path']
        row.update(decision='supplementary', supplementary_group=GROUP, text_role='poem', status='applied', decided_on=TODAY)
        row['basis'] = 'SUPPLEMENTARY (policy_decisions.csv #7, 2026-09-08; was deferred): ' + row['basis']; row['source'] += ' | ' + SRC; n_lat += 1
assert n_lat == 57, n_lat
wr(NDF, nd, ndf); print(f'body_node_decisions.csv: {len(nd)} rows; translations included {n_inc}, poem translations supplementary {n_supp}, Latin poems supplementary {n_lat};', Counter(r['decision'] for r in nd))

# ================= 5. frames_decisions.csv: Byron prologue -> include on A18404.1
FDF = os.path.join(HERE, 'frames_decisions.csv'); fd = rd(FDF); fdf = list(fd[0].keys()) + (['target_unit_id'] if 'target_unit_id' not in fd[0] else [])
B = json.load(open(os.path.join(REVIEW, 'byron_prologue_attribution_recommendation.json'), encoding='utf-8'))
assert B['target_unit_id'] == 'A18404.1' and B['target_edition_id_effective'] == '647'
um = {r['unit_id']: r for r in rd(os.path.join(OUT, 'unit_map.csv'))}
assert um['A18404.1']['edition_id_effective'] == '647' and um['A18404.1']['inclusion_status'] == 'proposed', um['A18404.1']['edition_id_effective']
FB = {(r['source_sha256'], r['node_path']): r for r in csv.DictReader(open(os.path.join(OUT, 'frontback_lines.csv'), encoding='utf-8')) if r['tcp'] == 'A18404'}
for x in B['nodes']:
    r = FB[(x['source_sha256'], x['node_path'])]; assert sha(r['text']) == x['text_sha256'] and r['section'] == 'front' and r['div_path'] == 'prologue'
assert len(B['nodes']) == 24
n = 0
for r in fd:
    if (r['tcp'], r['text_node_path'], r['section'], r['innermost_div']) == ('A18404', '/*/*[2]', 'front', 'prologue'):
        assert r['decision'] == 'deferred'
        r.update(decision='include', text_role='prologue', target_unit_id='A18404.1', status='applied', decided_on=TODAY,
                 basis="INCLUDE ONCE on the Conspiracy (A18404.1 / work 274 / edition 647 / DEEP 5069.01), role prologue: " + B['basis'] + " (was deferred 2026-09-07)", source=r['source'] + ' | ' + SRC + ' (byron_prologue_attribution_recommendation.json; 24 node hashes verified)'); n += 1
assert n == 1; wr(FDF, fd, fdf); print('frames_decisions.csv:', len(fd), 'rows; Byron prologue -> include on A18404.1')
print('done')
