#!/usr/bin/env python3
"""Apply the LIMITED fix list of ChatGPT's corpus_v1 review (2026-09-07) to the decision tables.
Run once, after extract_units.py rule extract-2026-09-08.13 (explicit splits) has been re-run.

  A. Middleton A07502.2.4 -> A07502.2.4.1/.2/.3 (DEEP 5078.08/.09/.10): identity overrides, container audits re-keyed
     to child XPaths, existing node decisions migrated, old seq 16-17 excluded as performance direction.
  B. Alexander A16527.1/.2 -> DEEP 5060.01 Croesus / 5060.02 Darius (official export via official_reconnections.json):
     deep_additions rows, date resolutions (1604 play edition vs 1607 collection issue 5061), identity overrides,
     container audits for the verse chains outside <sp> (read 2026-09-08).
  C. Montague Masque: A01514.1 -> A01514.1.1 (DEEP 5007.01) + residual A01514.1.0 (Posies poems, excluded).
  D. Bushell A17342: deferred 'sonnet' container narrowed to the 24 pillar lines; the 48 lines of 'A Sonnet sung to the
     KING and QVEENE' become include/song node decisions (ChatGPT node_corrections_50.json, hashes verified).
  E. Heywood A03241.23: 'non_dramatic' + false 'handled by frames_attribution' evidence withdrawn; unit becomes
     deferred_to_grace as unattributed performance-frame candidates (620 nodes; supplementary-material policy proposed).
Every node row is verified against out/lines.csv (unit, node_path, text hash).  Nothing is silently overwritten.
"""
import csv, hashlib, json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
REVIEW = os.path.expanduser('~/mnt/corpus_audit/corpus_v1_review')
TODAY = '2026-09-08'
SRC_CG = 'ChatGPT corpus_v1 review 2026-09-07 (corpus_audit/corpus_v1_review); applied by Claude 2026-09-08'
SRC_CL = 'Claude 2026-09-08, corpus_v1 close-out (source read; established performance-language rules)'

def rd(p): return list(csv.DictReader(open(p, encoding='utf-8')))
def wr(p, rows, fields):
    with open(p, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows({k: r.get(k, '') for k in fields} for r in rows)
def sha(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()

# ---------------- lines index for the touched units
TOUCH = {'A07502.2.4.1', 'A07502.2.4.2', 'A07502.2.4.3', 'A01514.1.1', 'A01514.1.0', 'A17342', 'A16527.1', 'A16527.2', 'A03241.23'}
L = {}
for r in csv.DictReader(open(os.path.join(OUT, 'lines.csv'), encoding='utf-8')):
    if r['unit_id'] in TOUCH: L[(r['source_sha256'], r['node_path'])] = r
man = {r['unit_id']: r for r in rd(os.path.join(OUT, 'units_manifest.csv'))}
for u in TOUCH: assert u in man, f'unit {u} not in manifest - re-run extract_units.py first'
def line(sha256, path):
    r = L.get((sha256, path)); assert r, f'node not in lines.csv: {path}'; return r

# ================= 1. manual_overrides.csv
OVF = os.path.join(HERE, 'manual_overrides.csv'); ov = rd(OVF); ovf = list(ov[0].keys())
drop = {'A07502.2.4', 'A01514.1', 'A16527.1', 'A16527.2', 'A03241.23'}
before = {r['unit_id']: r for r in ov if r['unit_id'] in drop}
assert set(before) == drop, set(before)
ov = [r for r in ov if r['unit_id'] not in drop]
have = {r['unit_id'] for r in ov}
new_ov = [
 dict(unit_id='A07502.2.4.1', deep_TCP='A07502.8', claims_primary_identity='yes', identity_status='confirmed_manual', relation='primary', inclusion_status='proposed',
      evidence="Split (extract-2026-09-08.13, children 1-8 of /*/*[2]/*[2]/*[2]/*[9]): head 'The Inuention' + 'At the House of Sir Francis Ihones, L. Maior. For the solemne feast of Easter' - the Four Seasons songs and Flora's speech = Sir Francis Jones's at Easter (DEEP 5078.08, work 376, edition 835). Was A07502.2.4 (mixed three works) in corpus v1. Source: ChatGPT corpus_v1 review source_split_plan.json + Claude source read."),
 dict(unit_id='A07502.2.4.2', deep_TCP='A07502.9', claims_primary_identity='yes', identity_status='confirmed_manual', relation='primary', inclusion_status='proposed',
      evidence="Split (children 9-13): 'Here followes the worthy and Noble Entertainments of the Lords of his Maiesties most Honourable Priuy Councell ... The first Entertainment vpon Thursday in Easter weeke ... 1621' at Sheriff Allen's = Lords of the Council by Sheriff Allen / Flora's Welcome (DEEP 5078.09, work 377, edition 836)."),
 dict(unit_id='A07502.2.4.3', deep_TCP='A07502.10', claims_primary_identity='yes', identity_status='confirmed_manual', relation='primary', inclusion_status='proposed',
      evidence="Split (children 14-30): 'The last Entertainment full as Noble and worthy as the former, vpon the Saturday ensuing, being the 21. of the same month' - Flora, Hyacinth, Adonis dialogue (12 <sp>) = Lords of the Council by Sheriff Ducie / Flora's Servants (DEEP 5078.10, work 378, edition 837)."),
 dict(unit_id='A01514.1.1', deep_TCP='A01514.1', claims_primary_identity='yes', identity_status='confirmed_manual', relation='primary', inclusion_status='proposed',
      evidence="Split (children 35-38 of the 'Flowers' poems div): head 'A deuise of a Maske for the right honorable Viscount Mountacute, written vpon this occasion, when the sayde L. had prepared to solemnize twoo marriages' + the Actor's spoken continuation (36 'the Actor tooke maister Tho. Bro. by the hand ... with these words', 37 'saying thus', 38 'the Actor did make an ende thus') = Montague Masque (DEEP 5007.01, work 62, edition 110, [1575]). ChatGPT located div 35 (346 nodes); Claude added divs 36-38 (30 spoken lines) by function."),
 dict(unit_id='A01514.1.0', deep_TCP='', claims_primary_identity='no', identity_status='confirmed_manual', relation='non_dramatic', inclusion_status='excluded_proposed',
      evidence="Residual of Posies 1575 'Flowers' after the Montague Masque was split off: 43 lyric/occasional poems (Anatomy of a Lover, Lullaby, Deprofundis, Memories, Epitaph on Bourcher, Dan Bartholmew of Bathe, The Reporter...) - heads read 2026-09-08; no spoken/performed text; not a DEEP work."),
 dict(unit_id='A16527.1', deep_TCP='A16527.5', claims_primary_identity='yes', identity_status='confirmed_manual', relation='primary', inclusion_status='proposed',
      evidence="Head 'THE TRAGEDIE of Croesus' = Croesus (DEEP 5060.01, work 209, edition 491, 1604); the 1607 volume A16527 is DEEP 5061 = the 1604 edition 1466 reissued with a cancel title leaf, and 5061 collection_contains links 5060.01/5060.02 (DEEP official export item_data.json sha256 10005117..., accessed 2026-09-07 by ChatGPT: official_reconnections.json). Local deep_min row A16527.1 (a duplicate of the Alexandraean Tragedy) was corrupt; corrected row added as A16527.5 in deep_additions.csv. No 5061.xx child id invented."),
 dict(unit_id='A16527.2', deep_TCP='A16527.6', claims_primary_identity='yes', identity_status='confirmed_manual', relation='primary', inclusion_status='proposed',
      evidence="Head 'THE TRAGEDY OF DARIVS' = Darius (DEEP 5060.02, work 196, edition 446, 1604; TCP sourceDesc: 'The tragedie of Darius retains its original 1604 title page'). Same official-export evidence as A16527.1; corrected row added as A16527.6 in deep_additions.csv."),
 dict(unit_id='A03241.23', deep_TCP='', claims_primary_identity='no', identity_status='confirmed_manual', relation='performance_frames_unattributed', inclusion_status='deferred_to_grace',
      evidence="Heywood, Pleasant Dialogues 1637, 'Sundry Fancies': 620 body candidates = prologues (230), epilogues (170) and presenter speeches (220) written for court, private-house and playhouse performances (Somerset House, Whitehall, Hampton Court, Earl of Dover's, Red Bull Richard III, Cockpit Queen Elizabeth, Cupid and Psyche). Performance language, but printed apart from the plays and NOT attributable to a DEEP edition text by work+witness; the seven frames_attribution rows for A03241 cover only front/back paratext, so the v1 claim 'frames handled by frames_attribution' was FALSE and is withdrawn (ChatGPT heywood_frame_omission.json). Not 'verified non-dramatic'. Proposed policy for Grace: keep as documented supplementary material outside the main corpus; never appended to other editions on a title match."),
]
for r in new_ov:
    assert r['unit_id'] not in have, r['unit_id']; ov.append(r)
wr(OVF, ov, ovf); print('manual_overrides.csv:', len(ov), 'rows (dropped', len(drop), 'added', len(new_ov), ')')

# ================= 2. deep_additions.csv  (official export rows for Croesus / Darius)
DAF = os.path.join(HERE, 'deep_additions.csv'); da = rd(DAF); daf = list(da[0].keys())
rec = json.load(open(os.path.join(REVIEW, 'official_reconnections.json'), encoding='utf-8'))
prov = f"DEEP official export {rec['source_url']} accessed {rec['accessed_on']} sha256 {rec['source_sha256'][:12]} (ChatGPT corpus_v1 review official_reconnections.json); replaces corrupt local rows A16527.1/.2 (duplicates of 5061.01)"
for unit, key in (('A16527.1', 'A16527.5'), ('A16527.2', 'A16527.6')):
    R = [x for x in rec['alexander_reconnections'] if x['unit_id'] == unit][0]['record']
    assert key not in {r['TCP'] for r in da}
    da.append({'TCP': key, 'record_type': 'Play in Collection', 'id': '', 'deep_id': R['deep_id'], 'edition_id': R['edition_id'], 'variant_edition_id': '', 'play_edition': '1', 'book_edition': '',
               'work_id': R['work_id'], 'title_id': '', 'title.1': R['title'], 'author.1': R['author'], 'authors_display': R['author'], 'genre_brit_filter': R['genre_brit_filter'],
               'play_type_filter': R['play_type_filter'], 'in_collection_id': '', 'collection_contains': '', 'total_editions': '', 'year_int': str(R['year_int']), 'date_first_publication': R['year'],
               'greg_full': '', 'in_collection': 'The Monarchic Tragedies (1604; reissued 1607 = DEEP 5061)', 'metadata_repaired': 'True', 'metadata_added_from': prov})
wr(DAF, da, daf); print('deep_additions.csv:', len(da), 'rows')

# ================= 3. date_resolutions.csv
DRF = os.path.join(HERE, 'date_resolutions.csv'); dr = rd(DRF); drf = list(dr[0].keys())
for unit, ed, did, title in (('A16527.1', '491', '5060.01', 'Croesus'), ('A16527.2', '446', '5060.02', 'Darius')):
    assert unit not in {r['unit_id'] for r in dr}
    dr.append({'unit_id': unit, 'edition_id_effective': ed, 'deep_id_effective': did, 'year_effective': '1604', 'year_effective_raw': '1604',
               'resolution': 'play_printing_date_vs_collection_issue_date',
               'basis': f"TCP header 1607 is the date of the cancel general title (DEEP 5061, collection edition 1466 reissued); {title} itself is the 1604 printing (DEEP {did}, edition {ed}); TCP sourceDesc: 'A reissue of the edition of 1604 with cancel general title page; The tragedie of Darius retains its original 1604 title page'. Two levels kept: play edition/year 1604, collection issue 5061/1607.",
               'source': 'ChatGPT corpus_v1 review official_reconnections.json (DEEP official export) + TCP sourceDesc', 'decided_on': TODAY})
wr(DRF, dr, drf); print('date_resolutions.csv:', len(dr), 'rows')

# ================= 4. container_audits.csv
CAF = os.path.join(HERE, 'container_audits.csv'); ca = rd(CAF); caf = list(ca[0].keys())
old_mid = [r for r in ca if r['unit_id'] == 'A07502.2.4']; old_bush = [r for r in ca if r['unit_id'] == 'A17342' and r['div_path_filter'] == 'sonnet']
assert len(old_mid) == 1 and len(old_bush) == 1
ca = [r for r in ca if r not in old_mid + old_bush]
def crow(unit, cpath, flt, dec, role, n, basis, source):
    return {'source_sha256': man[unit]['source_sha256'], 'unit_id': unit, 'container_node_path': cpath, 'div_path_filter': flt, 'decision_default': dec, 'text_role_default': role,
            'expected_candidate_nodes': str(n), 'basis': basis, 'source': source, 'status': 'applied', 'decided_on': TODAY}
MB = "Re-keyed after the Middleton split (was one row on /*/*[2]/*[2]/*[2]/*[9] for A07502.2.4): verse speech outside <sp> "
new_ca = [
 crow('A07502.2.4.1', '/*/*[2]/*[2]/*[2]/*[9]/*[8]', 'entertainment>part', 'include', 'speech', 14, MB + "- Hyacinth/Adonis 'THe goddesse Flora, Empresse of the Spring' (Jones's Easter); lines 13-14 of the lg ('Then fals into the former speech of Flora...') are a performance direction and are excluded by node decision.", SRC_CL),
 crow('A07502.2.4.2', '/*/*[2]/*[2]/*[2]/*[9]/*[12]', 'entertainment>part', 'include', 'speech', 0, MB + "- Flora 'AM I so happy to be blest agen?' (Sheriff Allen).", SRC_CL),
 crow('A07502.2.4.2', '/*/*[2]/*[2]/*[2]/*[9]/*[13]', 'entertainment>part', 'include', 'speech', 0, MB + "- 'The Song of welcome, after which Flora thus Closes the Entertainment' (Sheriff Allen).", SRC_CL),
 crow('A07502.2.4.3', '/*/*[2]/*[2]/*[2]/*[9]/*[29]', 'entertainment>part', 'include', 'speech', 10, MB + "- Flora's closing 'But, the faire Workes concluded, on all parts' (Sheriff Ducie); the 12 <sp> of Flora/Hyacinth/Adonis are kept by rule.", SRC_CL),
 crow('A01514.1.1', '/*/*[2]/*[2]/*[1]/*[2]/*/*[35]', 'poems>poem', 'include', 'dramatic_body', 346, "Montague Masque: the Actor's uninterrupted masque speech ('WHat wonder you my Lords? why gaze you gentlemen?' ... 'Receiue them well my lord'), closing by presenting the masquers; narrative head and inline notes are not candidates.", SRC_CG + ' (function_recommendation in source_split_plan.json)'),
 crow('A01514.1.1', '/*/*[2]/*[2]/*[1]/*[2]/*/*[36]', 'poems>poem', 'include', 'speech', 10, "Head: 'After the maske was done, the Actor tooke maister Tho. Bro. by the hand an brought him to the Venetians, with these words' - spoken presentation ('GVardate Signori my louely Lords behold').", SRC_CL),
 crow('A01514.1.1', '/*/*[2]/*[2]/*[1]/*[2]/*/*[37]', 'poems>poem', 'include', 'speech', 18, "Head: 'Then the Venetians embraced ... he torned to the Bridegroomes and Brides, saying thus' - Thomas Browne's spoken address ('BRother, these noblemen to you nowe haue me sent').", SRC_CL),
 crow('A01514.1.1', '/*/*[2]/*[2]/*[1]/*[2]/*/*[38]', 'poems>poem', 'include', 'speech', 2, "Head: 'Then when they had taken their leaues the Actor did make an ende thus' - two spoken closing lines; the epigraph 'Haud ictus sapio' (author's motto) is not a candidate node.", SRC_CL),
 crow('A17342', '/*/*[2]/*[2]/*[3]', 'sonnet', 'deferred', '', 24, "DEFERRED TO GRACE (narrowed from the whole-unit 'sonnet' row, which also caught the 48 sung lines): 'A Sonnet within the pillar of the Table at the Banquet' - addressed to the King and Queen, but the head places it inside the banquet-table pillar: displayed inscription or sung? Grace to decide.", 'Claude 2026-09-07 (deferred), re-keyed 2026-09-08 after ChatGPT corpus_v1 review'),
]
AB = "INCLUDE: verse lines outside <sp> inside a performance div chain ({}); all lg groups listed and first/last lines read 2026-09-08 - chorus stanzas and characters' stanzaic speeches (Croesus/Darius closet tragedies, same treatment as A16527.3/.4)."
for unit, chains in (('A16527.1', (('tragedy>act>chorus', 60), ('tragedy>act>scene', 126), ('tragedy>act>scene>chorus', 330))),
                     ('A16527.2', (('tragedy>act', 32), ('tragedy>act>chorus', 180), ('tragedy>act>scene', 36), ('tragedy>act>scene>chorus', 250)))):
    for flt, n in chains: new_ca.append(crow(unit, man[unit]['unit_node_path'], flt, 'include', '', n, AB.format(flt), SRC_CL))
keys = Counter((r['source_sha256'], r['container_node_path'], r['div_path_filter']) for r in ca + new_ca)
assert max(keys.values()) == 1, [k for k, v in keys.items() if v > 1]
# expected counts check against lines.csv (nodes outside <sp> under the container with that div_path, minus node decisions is checked later)
for r in new_ca:
    n = sum(1 for k, x in L.items() if x['unit_id'] == r['unit_id'] and (k[1] == r['container_node_path'] or k[1].startswith(r['container_node_path'] + '/')) and x['div_path'] == r['div_path_filter'] and x['in_sp'] == '0')
    print(f"  container {r['unit_id']} {r['container_node_path']} [{r['div_path_filter']}] {r['decision_default']}: {n} candidate nodes outside <sp> (expected {r['expected_candidate_nodes']})")
    if r['expected_candidate_nodes'] == '0': r['expected_candidate_nodes'] = str(n)
    elif r['unit_id'] != 'A07502.2.4.1': assert int(r['expected_candidate_nodes']) == n, (r['unit_id'], r['container_node_path'], n)
    else: assert n == 14, n   # 14 lg lines, of which 2 are excluded by node decision -> 12 speech + 2 songs = 14 kept
ca += new_ca; wr(CAF, ca, caf); print('container_audits.csv:', len(ca), 'rows')

# ================= 5. body_node_decisions.csv
NDF = os.path.join(HERE, 'body_node_decisions.csv'); nd = rd(NDF); ndf = list(nd[0].keys())
have = {(r['source_sha256'], r['node_path']) for r in nd}
# 5a migrate the six Middleton rows to the new unit ids (key unchanged; unit_id, container, seq refreshed; text hash re-verified)
mig = 0
for r in nd:
    if r['unit_id'] == 'A07502.2.4':
        x = L.get((r['source_sha256'], r['node_path'])); assert x and x['unit_id'].startswith('A07502.2.4.'), r['node_path']
        assert sha(x['text']) == r['text_sha256']
        r['unit_id'] = x['unit_id']; r['seq'] = x['seq']; r['container_node_path'] = man[x['unit_id']]['unit_node_path']
        r['source'] += f' | unit_id migrated {TODAY} after the Middleton split (was A07502.2.4)'; mig += 1
print('  migrated node rows:', mig)
# 5b refresh seq of other touched units whose numbering changed (A17342 unchanged; A16527 unchanged) - none expected
# 5c ChatGPT node corrections (50): 2 Middleton exclusions + 48 Bushell song inclusions
nc = json.load(open(os.path.join(REVIEW, 'node_corrections_50.json'), encoding='utf-8')); added = Counter()
for c in nc:
    key = (c['source_sha256'], c['node_path']); assert key not in have, key
    x = line(*key); assert sha(x['text']) == c['text_sha256'], key
    exp_unit = 'A07502.2.4.1' if c['unit_id'] == 'A07502.2.4' else c['unit_id']; assert x['unit_id'] == exp_unit, (x['unit_id'], exp_unit)
    nd.append({'source_sha256': key[0], 'node_path': key[1], 'unit_id': x['unit_id'], 'seq': x['seq'], 'div_path': x['div_path'], 'container_node_path': man[x['unit_id']]['unit_node_path'],
               'text_sha256': c['text_sha256'], 'decision': c['decision'], 'text_role': c['text_role'], 'language': c.get('language', ''), 'exclusion_category': c['exclusion_category'],
               'basis': c['basis'], 'source': SRC_CG + ' (node_corrections_50.json; text hashes verified against out/lines.csv)', 'status': 'applied', 'decided_on': TODAY,
               'decision_basis_type': 'explicit_textual_boundary' if c['decision'] == 'include' else 'editorial_function_assessment', 'historical_performance_status': '', 'xml_language_raw': ''})
    have.add(key); added[(x['unit_id'], c['decision'], c['text_role'])] += 1
print('  added node rows:', dict(added))
wr(NDF, nd, ndf); print('body_node_decisions.csv:', len(nd), 'rows', Counter(r['decision'] for r in nd))
print('done')
