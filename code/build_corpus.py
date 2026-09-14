#!/usr/bin/env python3
"""
build_corpus.py --version <tag> [--line-rule structural|sp_only] [--frames on|off] [--dry-run]

BUILDER_VERSION build_corpus-2026-09-08.v8  (v1-v6 probed by ChatGPT 2026-09-07; v7: explicit 'deferred' fate for material held back for Grace's decision - documented, reversible, never blocking, never counted as verified exclusion; v8 2026-09-08: explicit 'supplementary' fate = material APPROVED to be kept OUTSIDE the main corpus with its provenance (unit inclusion_status 'supplementary', container/node decision 'supplementary') - written to supplementary/ with its own manifest and read-back, never in the three main views, never counted as excluded or deferred; body node decisions may carry relation/translation_of (recorded in kept_nodes.csv and the manifest); frames_decisions.csv may name target_unit_id = explicit editorial attribution of a frame group to ONE built unit (e.g. a prologue shared by two plays))

Materialises the ANALYSIS corpus from the candidate tables under the freeze conditions agreed 2026-09-07.

Included set (hard conditions, per unit)
  inclusion_status == proposed AND identity_status in {confirmed_auto, confirmed_manual}
  AND relation in {primary, component} AND edition_status not CHECK AND edition_id_effective present.
  One representative per effective edition (a second primary of the same work = hard failure unless the
  witness selection table has moved it to alternate).  All units of one edition must come from ONE source
  file (cross-source assembly would need an explicit component order and is a hard failure until then).

Per-node decision precedence (body)
  1. body_node_decisions.csv  (key = source_sha256 + node_path): include / exclude / pending - wins over rules,
     and may set text_role (e.g. Malcontent 'poem' -> prologue, Aminta Venus -> epilogue).
  2. line rule: in_sp -> keep; sp_only -> drop everything else; structural -> innermost performance div keeps,
     any non-dramatic ancestor drops, any poem/poems ancestor WITHOUT a node decision or an applied container audit -> pending, else keep.
  Front/back frames: only groups attributable to exactly one work AND frames_rules.csv / frames_decisions.csv
  say include; unattributed or pending-type groups stay pending.  Collection frames never go to plays.

Assembly = ONE ordered plan per edition: every kept node (body of all its units + attributed frames) sorted by
document order in the source XML (node_path parsed step by step), so a residual unit that surrounds a
component cannot come out A-C-B.  A node claimed twice (same sha256+node_path) or by two editions = hard failure.

Views (same plan, filtered by verified text_role / language)
  texts/                        every kept node (all languages) - the archival performance-language view
  texts_analysis_en/            language == en  (whole-segment foreign-language nodes/units are kept in texts/ with a
                                language tag - body_node_decisions.language or unit_language.csv - never labelled
                                non-dramatic; Grace 2026-09-07)
  texts_no_prologue_epilogue/   texts_analysis_en minus text_role in {prologue, epilogue}; induction is KEPT
Input integrity (hard failures)
  every (source_sha256, node_path) key must be unique across lines.csv + frontback_lines.csv BEFORE any fate is set;
  out/coverage_summary.json (written by coverage_check.py from the XML) must exist, carry the sha256 of exactly these
  two tables, show missing = duplicated = 0, and its XML node count must equal the number of keys seen here;
  every kept body node must carry its owner unit's source sha256, every kept frame node the edition's source sha256.
Node fates: kept | excluded (verified: rule, node decision, verified unit status, frame paratext) | pending
  (unit pending, unit blocked by a hard condition, node decision pending, frame pending, witness not confirmed) |
  deferred (held back for Grace's decision: unit inclusion_status deferred_to_grace, node/container/frame decision
  'deferred' - not in the plan, does NOT block the build, listed in release_checklist.md section E; the opposite of a
  silent default exclusion).
Language resolver (one path for body AND frames; the source is recorded per node)
  1. explicit body_node_decisions.language  2. effective xml:lang of the node from out/node_language.csv (node_language.py,
  nearest ancestor-or-self; 'unk' = no evidence; the table's key set must EQUAL the candidate key set, duplicates refused)  3. unit_language.csv of the owner unit (frames: the edition's head unit)
  4. assumed 'en' (flagged 'assumed').  A unit_language.csv row with overrides_xml_lang=yes (reviewed: the source's xml:lang is wrong for the
     whole unit) ranks between 1 and 2.  Language never decides dramatic status.
Function audit of text outside <sp> (freeze gate)
  Every kept body node with in_sp = 0 that is kept by the structural RULE (no node decision) must lie under a container
  recorded in container_audits.csv (source_sha256 + container XPath prefix, optional div_path_filter = exact div type chain,
  decision_default include/exclude, text_role_default, basis; the most specific matching row wins);
  otherwise its fate is PENDING ('function audit pending') - it is NOT in the plan and blocks a real build.
  Audit-row contract: a row covers nodes only when status starts with 'applied' AND decision_default is exactly
  include or exclude; blank / pending rows cover nothing; any other value is a hard failure; two applicable rows of
  equal specificity with different decisions are a hard failure; a row whose unit_id is not the node's owner is a
  hard failure.  Node decisions override container defaults.
  This is the mechanical form of the performance-language policy (Grace 2026-09-07): rule-kept prose/verse outside <sp>
  is not verified until someone has looked at its container.

Freeze gate (real build only; --dry-run just reports)
  refuses while ANY of these exist: hard failures; pending node decisions; pending frame groups (unattributed
  or pending type); units with inclusion_status pending (identity or relation unresolved); witness selections
  not confirmed; read-back reconciliation mismatch.  Verified exclusions and approved deferrals never block.

Outputs (staging dir, renamed to out_corpus/<version>/ only after read-back passes)
  texts/, texts_analysis_en/, texts_no_prologue_epilogue/ (a view file is written ONLY when it has at least one node),
  corpus_manifest.csv, kept_nodes.csv (output order, view, node key,
  text_role, text sha256), node_fates.csv (EVERY candidate node -> fate), corpus_reconciliation.csv (files
  read back from disk vs plan), release_checklist.md, FREEZE_REPORT.md, inputs_manifest.csv (sha256 of every
  input read), build_args.json, inputs_* copies of all decision tables.
Downstream metadata = *_effective fields only.
"""
import os, re, csv, sys, json, hashlib, argparse, shutil, datetime
from collections import defaultdict, Counter
BUILDER_VERSION='build_corpus-2026-09-08.v8'
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,'out')
csv.field_size_limit(10**9)
ap=argparse.ArgumentParser()
ap.add_argument('--version',required=True); ap.add_argument('--line-rule',choices=['structural','sp_only'],default='structural')
ap.add_argument('--frames',choices=['on','off'],default='on'); ap.add_argument('--dry-run',action='store_true')
A=ap.parse_args()
CDIR=os.path.join(HERE,'out_corpus',A.version); STAGE=CDIR+'.staging'
if not A.dry_run and (os.path.exists(CDIR) or os.path.exists(STAGE)):
    sys.exit(f'output dir exists: {CDIR} (or its .staging) - use a new version tag; frozen corpora are never overwritten')

def sha_file(p): return hashlib.sha256(open(p,'rb').read()).hexdigest()
def sha_text(t): return hashlib.sha256(t.encode('utf-8')).hexdigest()
INPUTS={}  # path -> sha256 of every file actually read
def rd(path):
    INPUTS[path]=sha_file(path); return list(csv.DictReader(open(path,encoding='utf-8')))
def opt(path): return rd(path) if os.path.exists(path) else []
def docorder(p):
    steps=[s for s in p.strip('/').split('/') if s]; out=[]
    for s in steps:
        m=re.search(r'\[(\d+)\]',s); out.append(int(m.group(1)) if m else 1)
    return tuple(out)

NONDRAM_DIVS={'argument','dramatis_personae','dedication','to_the_reader','title_page','colophon','list_of_actors','table_of_contents','encomium','epistle','errata','commendatory_verses','illustration','description','descriptions','inscription','stationer_to_the_reader','imprimatur','license','advertisement'}
DECIDE_DIVS={'poem','poems'}
PERF_DIVS={'prologue','epilogue','chorus','song','induction','act','scene','speech','dumb_show','act_and_scene'}
ROLE_DIVS={'prologue','epilogue','chorus','song','induction','speech','dumb_show','poem'}
NO_PE_VIEW_DROP={'prologue','epilogue'}
VERIFIED_EXCLUDED_UNIT_STATUS={'excluded_proposed','excluded_from_main','deferred_extension'}
DEFERRED_UNIT_STATUS={'deferred_to_grace'}
SUPPLEMENTARY_UNIT_STATUS={'supplementary'}   # approved: kept outside the main corpus, with provenance (supplementary/)

# ---------------- decision tables
node_dec={}
for r in opt(os.path.join(HERE,'body_node_decisions.csv')):
    node_dec[(r['source_sha256'],r['node_path'])]=r
frules={r['innermost_div']:r['default_decision'] for r in opt(os.path.join(HERE,'frames_rules.csv'))}
unit_lang={r['unit_id']:r['language'] for r in opt(os.path.join(HERE,'unit_language.csv')) if r.get('language')}  # whole-unit language (e.g. Pedantius = la)
unit_lang_override={r['unit_id'] for r in opt(os.path.join(HERE,'unit_language.csv')) if r.get('language') and (r.get('overrides_xml_lang') or '').strip().lower()=='yes'}  # reviewed: the source xml:lang is wrong for the whole unit (e.g. Lyndsay tagged eng, text is Scots)
NO_LANG_EVIDENCE={'','unk','und','mul'}
audits=[]; audit_errors=[]   # container audits: (sha, container xpath, decision_default, text_role_default, unit_id, basis, div_path_filter)
for i,r in enumerate(opt(os.path.join(HERE,'container_audits.csv')),start=2):
    dec=(r.get('decision_default') or '').strip().lower(); st=(r.get('status') or '').strip().lower()
    if not st or st.startswith('pending') or dec in ('','pending'): continue          # blank / pending rows cover NOTHING
    if not st.startswith('applied'): audit_errors.append(f'container_audits.csv row {i}: unknown status {st!r}'); continue
    if dec not in ('include','exclude','deferred','supplementary'): audit_errors.append(f'container_audits.csv row {i}: decision_default must be include/exclude/deferred/supplementary, got {dec!r}'); continue
    if not r.get('basis','').strip(): audit_errors.append(f'container_audits.csv row {i}: applied row without a basis'); continue
    audits.append((r['source_sha256'],r['container_node_path'].rstrip('/'),dec,r.get('text_role_default','').strip(),r['unit_id'].strip(),r.get('basis',''),r.get('div_path_filter','').strip()))
def audit_for(key,div_path,owner):
    """most specific applied audit whose container XPath is a prefix of the node (div_path_filter, if any, must equal the node's
    div_path).  Specificity = (path length, has filter).  Equal-specificity rows that disagree, or a row naming another unit, are errors."""
    cands=[a for a in audits if a[0]==key[0] and (key[1]==a[1] or key[1].startswith(a[1]+'/')) and (not a[6] or a[6]==div_path)]
    if not cands: return None
    top=max((len(a[1]),bool(a[6])) for a in cands); best=[a for a in cands if (len(a[1]),bool(a[6]))==top]
    if len({(a[2],a[3],a[4]) for a in best})>1:   # same specificity must agree on decision AND text_role_default AND unit (identical duplicates merge)
        audit_errors.append(f'conflicting container audits of equal specificity for {owner} {key[1]}: {[(a[1],a[6],a[2],a[3],a[4]) for a in best]}'); return 'conflict'
    a=best[0]
    if a[4]!=owner: audit_errors.append(f'container audit row for unit {a[4]} matches a node owned by {owner} ({key[1]})'); return 'conflict'
    return a
fdec={}; frole={}; ftarget={}
for r in opt(os.path.join(HERE,'frames_decisions.csv')):
    if r.get('target_unit_id','').strip(): ftarget[(r['tcp'],r['text_node_path'],r['section'],r['innermost_div'])]=r['target_unit_id'].strip()
    if r.get('decision'): fdec[(r['tcp'],r['text_node_path'],r['section'],r['innermost_div'])]=r['decision'].strip(); frole[(r['tcp'],r['text_node_path'],r['section'],r['innermost_div'])]=(r.get('text_role') or '').strip()

# ---------------- included set
um=rd(os.path.join(OUT,'unit_map.csv')); byuid={r['unit_id']:r for r in um}
umf=os.path.join(OUT,'units_manifest.csv')
gaps={r['unit_id']:r.get('missing_gaps','') for r in opt(umf)}
hard=[]; inc=[]; why=Counter(); blocking=defaultdict(list)
for r in um:
    st=r['inclusion_status']
    if st!='proposed':
        why[f"not proposed ({st})"]+=1
        if st=='pending': blocking['units pending (identity or relation unresolved)'].append(f"{r['unit_id']} [{r['identity_status']}/{r['relation']}] {r['head'][:50]!r}")
        continue
    if r['identity_status'] not in ('confirmed_auto','confirmed_manual'): hard.append(f"{r['unit_id']}: proposed but identity {r['identity_status']}"); continue
    if r['relation'] not in ('primary','component'): hard.append(f"{r['unit_id']}: proposed but relation {r['relation']}"); continue
    if r['edition_status'].startswith('CHECK'): hard.append(f"{r['unit_id']}: proposed but edition CHECK ({r['edition_status'][:80]})"); continue
    if not r['edition_id_effective']: hard.append(f"{r['unit_id']}: no effective edition id"); continue
    if r.get('witness_role','').startswith('representative') and r.get('witness_selection_status','')!='confirmed':
        blocking['witness selection not confirmed'].append(f"{r['unit_id']} edition {r['edition_id_effective']} ({r['title_deep'][:40]}) - {r.get('witness_selection','')[:60]}")
    inc.append(r)
for r in um:
    if r['inclusion_status']=='alternate_witness_same_edition' and r.get('witness_selection_status','')!='confirmed':
        blocking['witness selection not confirmed'].append(f"{r['unit_id']} (alternate) edition {r['edition_id_effective']}")
byed=defaultdict(list)
for r in inc: byed[r['edition_id_effective']].append(r)
bad_ed=set()
for ed,rs in byed.items():
    prim=[r for r in rs if r['relation']=='primary']; works={r['work_key(work_id)'] for r in rs}; srcs={r['source_sha256'] for r in rs}
    if len(prim)>1 and len(works)==1: hard.append(f"edition {ed}: {len(prim)} primary units for one work without a witness selection: {[r['unit_id'] for r in prim]}"); bad_ed.add(ed)
    if len(works)>1: hard.append(f"edition {ed}: units of DIFFERENT works share one edition id: {[(r['unit_id'],r['work_key(work_id)']) for r in rs]}"); bad_ed.add(ed)
    if len(srcs)>1: hard.append(f"edition {ed}: units from more than one source file - cross-source assembly needs an explicit component order (not implemented): {[(r['unit_id'],r['tcp']) for r in rs]}"); bad_ed.add(ed)
inc_ids={r['unit_id']:r['edition_id_effective'] for r in inc if r['edition_id_effective'] not in bad_ed}
oldid2ed={}
for r in inc:
    if r['edition_id_effective'] in bad_ed: continue
    for o in [r['old_id']]+[a for a in r['old_id_aliases'].split(';') if a]:
        if o: oldid2ed.setdefault(o,r['edition_id_effective'])

# ---------------- input integrity: key uniqueness across both tables + binding to the independent XML coverage check
LINES=rd(os.path.join(OUT,'lines.csv')); FBL=rd(os.path.join(OUT,'frontback_lines.csv'))
keycount=Counter((r['source_sha256'],r['node_path']) for r in LINES)
keycount.update((r['source_sha256'],r['node_path']) for r in FBL)
dupkeys=[k for k,c in keycount.items() if c>1]
if dupkeys: hard.append(f"{len(dupkeys)} candidate key(s) appear more than once across lines.csv + frontback_lines.csv (first {dupkeys[0]})")
nl_path=os.path.join(OUT,'node_language.csv'); NLANG={}
if not os.path.exists(nl_path): hard.append('out/node_language.csv missing - run node_language.py first')
else:
    _sh={}; nl_dup=0
    for r in rd(nl_path):
        sh=_sh.setdefault(r['source_sha256'],r['source_sha256']); k=(sh,r['node_path'])
        if k in NLANG: nl_dup+=1; continue
        NLANG[k]=r['xml_lang_effective']
    if nl_dup: hard.append(f'node_language.csv has {nl_dup} duplicate key(s) - rerun node_language.py')
    nl_missing=[k for k in keycount if k not in NLANG]; nl_extra=[k for k in NLANG if k not in keycount]
    if nl_missing or nl_extra: hard.append(f'node_language.csv key set differs from the candidate tables: missing {len(nl_missing)} (first {nl_missing[:1]}), extra {len(nl_extra)} (first {nl_extra[:1]}) - rerun node_language.py')
cov_path=os.path.join(OUT,'coverage_summary.json'); COV=None
if not os.path.exists(cov_path): hard.append('out/coverage_summary.json missing - run coverage_check.py on the current tables first')
else:
    COV=json.load(open(cov_path)); INPUTS[cov_path]=sha_file(cov_path)
    for fn in ('lines.csv','frontback_lines.csv'):
        if COV.get('inputs',{}).get(fn)!=INPUTS[os.path.join(OUT,fn)]: hard.append(f'coverage_summary.json was computed on a different {fn} (sha256 mismatch) - rerun coverage_check.py')
    if COV.get('missing',1) or COV.get('duplicated',1): hard.append(f"coverage check reports missing={COV.get('missing')} duplicated={COV.get('duplicated')}")
    if COV.get('candidate_nodes_in_xml')!=len(keycount): hard.append(f"XML candidate nodes {COV.get('candidate_nodes_in_xml')} != distinct keys in tables {len(keycount)}")

# ---------------- node fates: every candidate node (body + front/back) gets exactly one fate
# fate = ('kept', edition, section, text_role) | ('excluded', reason) | ('pending', reason)
fates={}           # (sha,node_path) -> fate tuple
plan=defaultdict(list)  # edition -> [(docorder, sha, node_path, owner, section, text_role, text)]
dup=[]; multiline=[]
srcmis=[]; lang_sources=Counter()
def resolve_lang(key,ed,owner,decision_lang):
    if decision_lang: return decision_lang,'node decision'
    u0=owner if (owner in byuid or ed is None) else byed[ed][0]['unit_id']
    if u0 in unit_lang_override: return unit_lang[u0],'unit_language.csv (overrides xml:lang)'
    x=NLANG.get(key,'')
    if x not in NO_LANG_EVIDENCE: return x,'xml:lang'
    u=owner if (owner in byuid or ed is None) else byed[ed][0]['unit_id']
    if u in unit_lang: return unit_lang[u],'unit_language.csv'
    return 'en','assumed'
relation_of={}   # key -> (relation, translation_of) from body_node_decisions.csv (e.g. printed English translation of a performed speech)
supp_plan=defaultdict(list); supp_nodes=Counter(); supp_meta={}   # (owner unit, group) -> [(docorder, sha, path, text, role, lang, lsrc)]
def supplement(key,owner,group,level,reason,basis,text,path,role,decision_lang=None):
    """approved supplementary material: kept OUTSIDE the main corpus with provenance; never in the three views"""
    if key in fates: dup.append((key,fates[key],('supplementary',owner,group))); return
    if '\n' in text or '\r' in text: multiline.append(key)
    if owner in byuid and key[0]!=byuid[owner]['source_sha256']: srcmis.append((key,owner,'supplementary')); return
    lang,lsrc=resolve_lang(key,None,owner,decision_lang); lang_sources[(lang,lsrc)]+=1
    fates[key]=('supplementary',reason,owner,group,lang,lsrc,role); supp_plan[(owner,group)].append((docorder(path),key[0],path,text,role,lang,lsrc)); supp_nodes[f'{level} {owner} [{group}]']+=1
    supp_meta.setdefault((owner,group),(level,basis))
def claim(key,ed,owner,section,role,text,path,decision_lang=None):
    if key in fates: dup.append((key,fates[key][1] if fates[key][0]=='kept' else fates[key],ed)); return
    if '\n' in text or '\r' in text: multiline.append(key)
    want=byuid[owner]['source_sha256'] if owner in byuid else byed[ed][0]['source_sha256']
    if key[0]!=want or key[0]!=byed[ed][0]['source_sha256']: srcmis.append((key,owner,ed)); return
    lang,lsrc=resolve_lang(key,ed,owner,decision_lang); lang_sources[(lang,lsrc)]+=1
    fates[key]=('kept',ed,section,role,owner,lang,lsrc); plan[ed].append((docorder(path),key[0],path,owner,section,role,text,lang,lsrc))
def role_of(div_path):
    p=[d for d in div_path.split('>') if d]
    return p[-1] if p and p[-1] in ROLE_DIVS else 'dramatic_body'
pending_nodes=Counter(); excluded=Counter(); dec_applied=Counter(); rule_versions=set(); pending_units_nodes=Counter(); deferred_nodes=Counter()
unaudited=defaultdict(lambda:[0,0]); audited=Counter()   # function audit of rule-kept nodes outside <sp>
ws=defaultdict(lambda:{'n':0,'chars':0,'max':0,'samples':[],'parents':Counter(),'langs':Counter()})   # live worksheet: (unit, div_path) of the pending set
def rule_keep(key,ed,u,L):
    """structural rule would keep this node; outside <sp> it must be covered by a container audit"""
    if L['in_sp']=='1': claim(key,ed,u,'body',role_of(L['div_path']),L['text'],L['node_path']); return
    a=audit_for(key,L['div_path'],u)
    if a is None or a=='conflict':
        setfate(key,('pending','function audit pending (rule-kept text outside <sp>, container not audited)')); pending_units_nodes['function audit pending (outside <sp>, no container audit)']+=1
        unaudited[u][0]+=1; unaudited[u][1]+=int(L['n_chars'])
        w=ws[(u,L['div_path'])]; w['n']+=1; w['chars']+=int(L['n_chars']); w['max']=max(w['max'],int(L['n_chars'])); w['parents'][L['parent']]+=1; w['langs'][resolve_lang(key,ed,u,None)[0]]+=1
        if len(w['samples'])<3: w['samples'].append(L['text'][:100])
        return
    if a[2]=='exclude': setfate(key,('excluded',f'container audit: exclude ({a[3] or "non-performance text"})')); excluded[f'container audit exclude ({a[3] or "non-performance text"})']+=1; audited['exclude']+=1; return
    if a[2]=='deferred': setfate(key,('deferred','container deferred to Grace')); deferred_nodes[f"container {a[4]} {a[6] or a[1]}: {a[5][:80]}"]+=1; audited['deferred']+=1; return
    if a[2]=='supplementary': supplement(key,u,a[6] or a[1],'container',f'container supplementary ({a[6] or a[1]})',a[5],L['text'],L['node_path'],a[3] or role_of(L['div_path'])); audited['supplementary']+=1; return
    claim(key,ed,u,'body',a[3] or role_of(L['div_path']),L['text'],L['node_path']); audited['include']+=1
def setfate(key,fate):
    if key in fates: dup.append((key,fates[key],fate)); return
    fates[key]=fate
for L in LINES:
    key=(L['source_sha256'],L['node_path']); u=L['unit_id']; rule_versions.add(L.get('rule_version',''))
    if u not in inc_ids:
        ur=byuid.get(u,{}); st=ur.get('inclusion_status','?')
        if st in VERIFIED_EXCLUDED_UNIT_STATUS or (st=='alternate_witness_same_edition' and ur.get('witness_selection_status')=='confirmed'):
            setfate(key,('excluded',f'unit not included ({st})')); excluded[f'unit not included ({st})']+=1
        elif st in DEFERRED_UNIT_STATUS:
            setfate(key,('deferred',f'unit deferred to Grace ({u})')); deferred_nodes[f'unit {u} ({ur.get("head","")[:40]})']+=1
        elif st in SUPPLEMENTARY_UNIT_STATUS:
            supplement(key,u,'unit','unit',f'unit supplementary ({u})',ur.get('reason',''),L['text'],L['node_path'],role_of(L['div_path']))
        else:
            why_p='unit blocked by a hard condition' if st=='proposed' else ('alternate witness not confirmed' if st=='alternate_witness_same_edition' else f'unit {st}')
            setfate(key,('pending',why_p)); pending_units_nodes[why_p]+=1
        continue
    ed=inc_ids[u]; d=node_dec.get(key)
    if d is not None:
        if sha_text(L['text'])!=d['text_sha256']: hard.append(f"node decision text hash mismatch {u} {L['node_path']}"); continue
        if d['decision']=='include':
            dec_applied['include']+=1; claim(key,ed,u,'body',d.get('text_role') or role_of(L['div_path']),L['text'],L['node_path'],d.get('language') or None)
            if d.get('relation','').strip(): relation_of[key]=(d['relation'].strip(),d.get('translation_of','').strip())
            continue
        if d['decision']=='supplementary': dec_applied['supplementary']+=1; supplement(key,u,d.get('supplementary_group','').strip() or d.get('container_node_path','') or 'nodes','nodes',f"node decision supplementary",d['basis'],L['text'],L['node_path'],d.get('text_role') or role_of(L['div_path']),d.get('language') or None); continue
        if d['decision']=='exclude': dec_applied['exclude']+=1; setfate(key,('excluded',f"node decision: exclude ({d.get('exclusion_category','')})")); excluded[f"node decision exclude ({d.get('exclusion_category','')})"]+=1; continue
        if d['decision']=='deferred': dec_applied['deferred']+=1; setfate(key,('deferred','node decision deferred to Grace')); deferred_nodes[f"nodes {u} {d.get('container_node_path','')}: {d['basis'][:80]}"]+=1; continue
        setfate(key,('pending','node decision pending')); pending_nodes[(u,d.get('container_node_path',''),d['basis'][:70])]+=1; continue
    if L['in_sp']=='1': rule_keep(key,ed,u,L); continue
    if A.line_rule=='sp_only': setfate(key,('excluded','line rule sp_only')); excluded['line rule sp_only (outside <sp>)']+=1; continue
    p=[x for x in L['div_path'].split('>') if x]
    if p and p[-1] in PERF_DIVS: rule_keep(key,ed,u,L); continue
    if any(x in NONDRAM_DIVS for x in p): setfate(key,('excluded',f'line rule structural: {p[-1]}')); excluded[f'line rule structural dropped ({p[-1]})']+=1; continue
    if any(x in DECIDE_DIVS for x in p):
        if audit_for(key,L['div_path'],u) not in (None,'conflict'): rule_keep(key,ed,u,L); continue   # an applied container audit resolves poem chains too
        setfate(key,('pending','poem div without node decision')); pending_nodes[(u,L['div_path'],'poem/poems div - no node decision yet')]+=1; continue
    rule_keep(key,ed,u,L)

# frames
frames_report=Counter(); frames_pending=[]
fa=rd(os.path.join(OUT,'frames_attribution.csv'))
fl=defaultdict(list)
for r in FBL:
    inner=r['div_path'].split('>')[-1] if r['div_path'] else '(no div)'
    fl[(r['tcp'],r['text_node_path'],r['section'],inner)].append(r)
frame_fate_group={}
for g in fa:
    k=(g['tcp'],g['text_node_path'],g['section'],g['innermost_div'])
    if g['frame_class']!='candidate': frame_fate_group[k]=('excluded',f"frame {g['frame_class']} ({g['scope'][:40]})"); continue
    if A.frames=='off': frame_fate_group[k]=('excluded','frames off'); continue
    oid=g['attributed_work(old_id)']
    dec=fdec.get(k) or frules.get(g['innermost_div'],'pending')
    if dec=='deferred': frame_fate_group[k]=('deferred','frame deferred to Grace'); frames_report[f'{g["innermost_div"]}: deferred to Grace (not built)']+=1; deferred_nodes[f"frame {g['tcp']} {g['section']} {g['innermost_div']} ({g['lines']} lines)"]+=int(g['lines'] or 0); continue
    if dec=='exclude': frame_fate_group[k]=('excluded','frame decision exclude'); frames_report[f'{g["innermost_div"]}: exclude']+=1; continue
    tgt=ftarget.get(k)
    if tgt and dec=='include':   # explicit editorial attribution of this frame group to ONE built unit (frames_decisions.target_unit_id)
        if tgt not in inc_ids: hard.append(f"frames_decisions.csv: target_unit_id {tgt} for {k} is not a built unit"); frame_fate_group[k]=('pending','frame target unit not built'); continue
        if byuid[tgt]['tcp']!=g['tcp']: hard.append(f"frames_decisions.csv: target_unit_id {tgt} belongs to {byuid[tgt]['tcp']}, frame is in {g['tcp']}"); frame_fate_group[k]=('pending','frame target unit in another source'); continue
        frame_fate_group[k]=('kept',inc_ids[tgt],frole.get(k) or g['innermost_div']); frames_report[f'{g["innermost_div"]}: include (explicit target unit {tgt}, edition {inc_ids[tgt]})']+=1; continue
    if not oid: frame_fate_group[k]=('pending','frame unattributed'); frames_report['unattributed (pending, not built)']+=1; frames_pending.append(f"{g['tcp']} {g['section']} {g['innermost_div']} ({g['lines']} lines) - unattributed"); continue
    if dec=='include':
        ed=oldid2ed.get(oid)
        if not ed: frame_fate_group[k]=('excluded',f'frame attributed to a work not built ({oid})'); frames_report[f'{g["innermost_div"]}: attributed to unbuilt work (not built)']+=1; continue
        frame_fate_group[k]=('kept',ed,frole.get(k) or g['innermost_div']); frames_report[f'{g["innermost_div"]}: include' + (f' as {frole[k]}' if frole.get(k) else '')]+=1
    else: frame_fate_group[k]=('pending',f'frame type {g["innermost_div"]} pending'); frames_report[f'{g["innermost_div"]}: pending (not built)']+=1; frames_pending.append(f"{g['tcp']} {g['section']} {g['innermost_div']} ({g['lines']} lines) -> {oid}: type decision pending")
for k,Ls in fl.items():
    f=frame_fate_group.get(k,('excluded','frame group not in frames_attribution'))
    for L in Ls:
        key=(L['source_sha256'],L['node_path'])
        if f[0]=='kept': claim(key,f[1],'(frame)',k[2],f[2],L['text'],L['node_path'])
        else:
            setfate(key,(f[0],f[1]))
            if f[0]=='excluded': excluded[f'front/back: {f[1]}']+=1
            elif f[0]=='deferred': pass
            else: pending_units_nodes[f'front/back: {f[1]}']+=1
if dup: hard.append(f"{len(dup)} node(s) claimed twice (same source sha256 + node_path) - first: {dup[0]}")
if audit_errors: hard.extend(sorted(set(audit_errors))[:20])
if srcmis: hard.append(f"{len(srcmis)} kept node(s) whose source sha256 does not match the owner unit / edition source - first: {srcmis[0]}")
if multiline: hard.append(f"{len(multiline)} kept node text(s) contain a newline - would break the one-line-per-node contract")

# ---------------- assemble views from the ordered plan
VIEWS={'texts':lambda role,lang:True,'texts_analysis_en':lambda role,lang: lang=='en','texts_no_prologue_epilogue':lambda role,lang: lang=='en' and role not in NO_PE_VIEW_DROP}
manifest=[]; kept_rows=[]; files={}  # (view,fname) -> (list of texts, edition)
for ed in sorted(byed, key=lambda e:(len(e),e)):
    if ed in bad_ed: continue
    rs=byed[ed]; items=sorted(plan[ed],key=lambda it:it[0])
    for i in range(1,len(items)):
        if items[i][0]==items[i-1][0]: hard.append(f"edition {ed}: two kept nodes with identical document position {items[i][2]}")
    head=rs[0]; old_ids=sorted({r['old_id'] for r in rs}); fname=f"{ed}__{old_ids[0]}.txt"
    roles=Counter(it[5] for it in items); secs=Counter(it[4] for it in items); langs=Counter(it[7] for it in items); rels=Counter(relation_of[(it[1],it[2])][0] for it in items if (it[1],it[2]) in relation_of)
    row={'edition_id_effective':ed,'file':fname,'work_id':head['work_key(work_id)'],'old_ids':';'.join(old_ids),'unit_ids':';'.join(r['unit_id'] for r in rs),
        'title':head['title_deep'],'author':head['author_deep'],'year_effective':head['year_effective'],'year_effective_raw':head.get('year_effective_raw',head['year_effective']),
        'deep_id_effective':head['deep_id_effective'],'edition_effective_basis':head['edition_effective_basis'],'genre_deep':head['genre_deep'],'play_type_deep':head['play_type_deep'],
        'tcp':head['tcp'],'source_sha256':head['source_sha256'],'witness_role':head.get('witness_role',''),'witness_selection_status':head.get('witness_selection_status',''),
        'n_nodes_total':len(items),'n_chars_total':sum(len(it[6]) for it in items)+max(len(items)-1,0),
        'roles':';'.join(f'{k}={v}' for k,v in sorted(roles.items())),'relations':';'.join(f'{k}={v}' for k,v in sorted(rels.items())),'sections':';'.join(f'{k}={v}' for k,v in sorted(secs.items())),'languages':';'.join(f'{k}={v}' for k,v in sorted(langs.items())),
        'missing_gaps':';'.join(f"{r['unit_id']}={gaps[r['unit_id']]}" for r in rs if gaps.get(r['unit_id']) not in ('',None,'0')),
        'metadata_repaired':head['metadata_repaired'],'metadata_added_from':head.get('metadata_added_from',''),'line_rule':A.line_rule,'frames':A.frames,'corpus_version':A.version,'builder_version':BUILDER_VERSION}
    for view,keep in VIEWS.items():
        sel=[it for it in items if keep(it[5],it[7])]
        if sel: files[(view,fname)]=([it[6] for it in sel],ed)
        row[f'n_nodes[{view}]']=len(sel); row[f'sha256[{view}]']=sha_text('\n'.join(it[6] for it in sel)) if sel else ''
        for idx,it in enumerate(sel):
            kept_rows.append([view,ed,fname,idx,it[1],it[2],it[3],it[4],it[5],it[7],it[8],sha_text(it[6])]+list(relation_of.get((it[1],it[2]),('',''))))
    manifest.append(row)
# supplementary documents: one per (owner unit, group), document order, outside the three views
def slug(s): return re.sub(r'[^A-Za-z0-9]+','_',s).strip('_')[:60] or 'x'
supp_manifest=[]; supp_rows=[]; supp_files={}
for (owner,group),items in sorted(supp_plan.items()):
    items.sort(key=lambda it:it[0])
    for i in range(1,len(items)):
        if items[i][0]==items[i-1][0]: hard.append(f"supplementary {owner} [{group}]: two nodes with identical document position {items[i][2]}")
    fname=f"{owner}__{slug(group)}.txt"
    if fname in supp_files: hard.append(f"supplementary file name collision {fname}")
    ur=byuid.get(owner,{}); level,basis=supp_meta[(owner,group)]
    supp_files[fname]=([it[3] for it in items],(owner,group))
    supp_manifest.append({'file':fname,'unit_id':owner,'group':group,'decision_level':level,'tcp':ur.get('tcp',''),'source_sha256':ur.get('source_sha256',''),'unit_node_path':ur.get('unit_node_path',''),
        'edition_id_effective':ur.get('edition_id_effective','') if owner in inc_ids else '','work_id':ur.get('work_key(work_id)','') if owner in inc_ids else '','title_deep':ur.get('title_deep',''),'head':ur.get('head','')[:120],
        'unit_inclusion_status':ur.get('inclusion_status',''),'unit_relation':ur.get('relation',''),'basis':basis[:400],
        'n_nodes':len(items),'n_chars':sum(len(it[3]) for it in items)+max(len(items)-1,0),'languages':';'.join(f'{k}={v}' for k,v in sorted(Counter(it[5] for it in items).items())),
        'roles':';'.join(f'{k}={v}' for k,v in sorted(Counter(it[4] for it in items).items())),'sha256':sha_text('\n'.join(it[3] for it in items)),'corpus_version':A.version,'builder_version':BUILDER_VERSION})
    for idx,it in enumerate(items): supp_rows.append([fname,owner,group,idx,it[1],it[2],it[4],it[5],it[6],sha_text(it[3])])
# every candidate node accounted for exactly once?
n_cand=len(fates); n_kept=sum(1 for f in fates.values() if f[0]=='kept'); n_exc=sum(1 for f in fates.values() if f[0]=='excluded'); n_pend=sum(1 for f in fates.values() if f[0]=='pending'); n_def=sum(1 for f in fates.values() if f[0]=='deferred'); n_supp=sum(1 for f in fates.values() if f[0]=='supplementary')
if sum(len(v) for v in supp_plan.values())!=n_supp: hard.append(f"supplementary plan holds {sum(len(v) for v in supp_plan.values())} nodes but {n_supp} nodes have fate supplementary")
planned_nodes=sum(len(v) for v in plan.values())
if planned_nodes!=n_kept: hard.append(f"plan holds {planned_nodes} nodes but {n_kept} nodes have fate kept")
if n_cand!=len(keycount): hard.append(f"fates {n_cand} != distinct input keys {len(keycount)}")
if COV and COV.get('candidate_nodes_in_xml')!=n_cand: hard.append(f"fates {n_cand} != XML candidate nodes {COV.get('candidate_nodes_in_xml')} (coverage_check)")
if any(f[0]=='kept' and f[1] in bad_ed for f in fates.values()): hard.append('kept nodes belong to an edition with a hard failure')

# ---------------- blocking list (freeze gate)
if hard: blocking['hard-condition failures']=hard
if unaudited: blocking['function audit pending: rule-kept text outside <sp> without a container audit (nodes NOT in the plan)']=[f"{u}: {n} nodes, {c} chars ({byuid[u]['title_deep'][:40]}; {byuid[u]['play_type_deep'].split(';')[0]})" for u,(n,c) in sorted(unaudited.items(),key=lambda kv:-kv[1][1])]
if pending_nodes: blocking['body node decisions pending']=[f"{u} {c}: {n} nodes - {b}" for (u,c,b),n in pending_nodes.most_common()]
if frames_pending: blocking['frame groups pending']=frames_pending
would_block=bool(blocking)

# ---------------- write to staging, read back, reconcile
recon=[]
if not A.dry_run:
    if would_block: sys.exit('refusing to build: freeze gate not passed -\n'+'\n'.join(f"  {k}: {len(v)}\n"+'\n'.join('    - '+x[:200] for x in v[:5]) for k,v in blocking.items())+'\n(run with --dry-run for the full report)')
    for view in VIEWS: os.makedirs(os.path.join(STAGE,view))
    for (view,fname),(texts,ed) in files.items():
        with open(os.path.join(STAGE,view,fname),'w',encoding='utf-8',newline='\n') as f: f.write('\n'.join(texts))
    os.makedirs(os.path.join(STAGE,'supplementary'))
    for fname,(texts,og) in supp_files.items():
        with open(os.path.join(STAGE,'supplementary',fname),'w',encoding='utf-8',newline='\n') as f: f.write('\n'.join(texts))
    for fname,(texts,og) in supp_files.items():
        raw=open(os.path.join(STAGE,'supplementary',fname),encoding='utf-8',newline='').read(); got=raw.split('\n') if raw!='' else []
        exp_from_fates=sum(1 for f in fates.values() if f[0]=='supplementary' and (f[2],f[3])==og)
        ok=(got==texts) and (len(got)==exp_from_fates)
        recon.append(['supplementary',fname,f'{og[0]} [{og[1]}]',len(texts),len(got),exp_from_fates,sha_text(raw),'ok' if ok else 'MISMATCH'])
    # independent read-back: disk vs plan and vs node_fates
    for (view,fname),(texts,ed) in files.items():
        raw=open(os.path.join(STAGE,view,fname),encoding='utf-8',newline='').read()
        got=raw.split('\n') if raw!='' else []
        exp_from_fates=sum(1 for f in fates.values() if f[0]=='kept' and f[1]==ed and VIEWS[view](f[3],f[5]))
        ok=(got==texts) and (len(got)==exp_from_fates)
        recon.append([view,fname,ed,len(texts),len(got),exp_from_fates,sha_text(raw),'ok' if ok else 'MISMATCH'])
    # editions whose view is empty must have NO file
    for m in manifest:
        for view in VIEWS:
            if m[f'n_nodes[{view}]']==0 and os.path.exists(os.path.join(STAGE,view,m['file'])): recon.append([view,m['file'],m['edition_id_effective'],0,-1,0,'','MISMATCH'])
    bad=[x for x in recon if x[-1]!='ok']
    if bad:
        shutil.rmtree(STAGE); sys.exit(f'read-back reconciliation FAILED for {len(bad)} file(s); staging removed. first: {bad[0]}')

# ---------------- report + checklist
def sec(title,lines): return f"## {title}\n"+('\n'.join(lines) if lines else '- none')+"\n"
rep=[f"# FREEZE REPORT - corpus {A.version}\n", f"builder {BUILDER_VERSION}; line rule {A.line_rule}; frames {A.frames}; dry-run {A.dry_run}; {datetime.datetime.now().isoformat(timespec='seconds')}\n",
 sec('Included set',[f"- units included: **{len(inc)}** (proposed & confirmed & primary/component & no edition CHECK)",f"- editions built: **{len(manifest)}**; works: **{len({m['work_id'] for m in manifest})}**","- units NOT included, by reason:"]+[f"  - {k}: {v}" for k,v in why.most_common()]),
 sec(f'FREEZE GATE: {"BLOCKED" if would_block else "open"}',[f"- {k}: {len(v)}" for k,v in blocking.items()]+["", "Verified exclusions and approved deferrals do not block (see release_checklist.md)."]),
 sec(f'Hard-condition failures ({len(hard)})',['- '+h for h in hard]),
 sec(f'Body node decisions',[f"- applied from body_node_decisions.csv: include {dec_applied['include']}, exclude {dec_applied['exclude']}",f"- pending: {sum(pending_nodes.values())} nodes in {len(pending_nodes)} groups"]+[f"  - {u} {c}: {n} - {b}" for (u,c,b),n in pending_nodes.most_common()]),
 sec('Frames',[f"- {k}: {v}" for k,v in frames_report.most_common()]),
 sec(f'DEFERRED to Grace (not in this build, not blocking, reversible) - {n_def} nodes',[f"- {k}: {v} nodes" for k,v in deferred_nodes.most_common()]),
 sec(f'SUPPLEMENTARY (approved; kept OUTSIDE the main corpus in supplementary/ with provenance; not excluded, not deferred) - {n_supp} nodes in {len(supp_plan)} documents',[f"- {k}: {v} nodes" for k,v in supp_nodes.most_common()]),
 sec('Node accounting (every candidate node exactly one fate; bound to coverage_check.py)',[f"- distinct input keys: {len(keycount)} (duplicate keys: {len(dupkeys)}); XML candidate nodes per coverage_summary.json: {COV.get('candidate_nodes_in_xml') if COV else 'n/a'} (missing {COV.get('missing') if COV else '?'}, duplicated {COV.get('duplicated') if COV else '?'})",f"- fates: kept (passed the structural rule inside <sp>, or a reviewed node/container decision) {n_kept}; excluded (verified) {n_exc}; pending {n_pend}; DEFERRED to Grace {n_def}; SUPPLEMENTARY (approved, outside the main corpus) {n_supp}; total {n_cand}; sum ok: {n_kept+n_exc+n_pend+n_def+n_supp==n_cand}","- pending nodes by reason:"]+[f"  - {k}: {v}" for k,v in pending_units_nodes.most_common()]+[f"  - node decision pending: {sum(pending_nodes.values())}"]),
 sec('Excluded candidate nodes, by reason',[f"- {k}: {v}" for k,v in excluded.most_common()]),
 sec('Text roles in built texts (nodes)',[f"- {k}: {v}" for k,v in Counter(it[5] for ed in plan if ed not in bad_ed for it in plan[ed]).most_common()]),
 sec('Views (files are written only for non-empty documents)',["- texts/: every kept node in document order (all languages)","- texts_analysis_en/: kept nodes with language en","- texts_no_prologue_epilogue/: language en and text_role not prologue/epilogue (induction kept)"]+[f"- {view}: non-empty documents {sum(1 for m in manifest if m[f'n_nodes[{view}]']>0)} / editions {len(manifest)}; works with a non-empty document {len({m['work_id'] for m in manifest if m[f'n_nodes[{view}]']>0})}" for view in VIEWS]+[f"- kept nodes by language: "+', '.join(f'{k}={v}' for k,v in Counter(it[7] for ed in plan if ed not in bad_ed for it in plan[ed]).most_common()),"- language source of kept nodes: "+', '.join(f'{l}/{src}={n}' for (l,src),n in lang_sources.most_common())]
   +[f"- EMPTY in {view}: "+'; '.join(f"{m['edition_id_effective']} {m['title'][:35]} [{'all kept nodes non-en: '+m['languages'] if m['n_nodes_total'] else ('no kept nodes: '+str(unaudited[m['unit_ids'].split(';')[0]][0])+' nodes function-audit pending' if m['unit_ids'].split(';')[0] in unaudited else 'no kept nodes')}]" for m in manifest if m[f'n_nodes[{view}]']==0) for view in VIEWS if any(m[f'n_nodes[{view}]']==0 for m in manifest)]),
 sec('Function audit of rule-kept text outside <sp> (container_audits.csv)',[f"- audited containers applied: include {audited['include']} nodes, exclude {audited['exclude']} nodes",f"- live worksheet of the pending set: out_corpus/FUNCTION_AUDIT_WORKSHEET_{A.version}{'_dryrun' if A.dry_run else ''}.csv ({len(ws)} unit x div-chain rows)",f"- rule-kept nodes outside <sp> with NO applied container audit: {sum(v[0] for v in unaudited.values())} nodes / {sum(v[1] for v in unaudited.values())} chars in {len(unaudited)} units - fate pending, NOT in the plan (blocks a real build)"]+[f"  - {u}: {n} nodes, {c} chars ({byuid[u]['title_deep'][:40]})" for u,(n,c) in sorted(unaudited.items(),key=lambda kv:-kv[1][1])[:40]]+(['  - ...'] if len(unaudited)>40 else [])),
 sec('Read-back reconciliation (real build only)',[f"- files: {len(recon)}; mismatches: {sum(1 for x in recon if x[-1]!='ok')}"] if recon else ['- dry-run: nothing written']),
 sec('Sanity: DEEP play_type of built editions',[f"- {k}: {v}" for k,v in Counter(m['play_type_deep'].split(';')[0] for m in manifest).most_common()])]
report='\n'.join(rep)
chk=[f"# RELEASE CHECKLIST - {A.version}\n","## A. Included (built)",f"- {len(manifest)} editions / {len({m['work_id'] for m in manifest})} works; see corpus_manifest.csv\n","## B. Verified exclusions (do not block)"]
for st in ('excluded_proposed','excluded_from_main','alternate_witness_same_edition'):
    rows=[r for r in um if r['inclusion_status']==st]
    chk.append(f"### {st} ({len(rows)})"); chk+= [f"- {r['unit_id']} [{r['relation']}] {r['title_deep'][:40] or r['head'][:40]!r}: {r['reason'][:100]}" for r in rows]
rows=[r for r in um if r['inclusion_status']=='deferred_extension']
chk.append(f"\n## C. Approved deferrals (scope_decisions.csv; do not block) ({len(rows)})"); chk+=[f"- {r['unit_id']} {r['head'][:50]!r}: {r['reason'][:100]}" for r in rows]
chk.append(f"\n## E. DEFERRED TO GRACE (held out of this build; documented and reversible - NOT verified exclusions) ({len(deferred_nodes)} items, {n_def} nodes)")
for r in um:
    if r['inclusion_status'] in DEFERRED_UNIT_STATUS: chk.append(f"- unit {r['unit_id']} {r['head'][:50]!r}: {r['reason'][:220]}")
for k,v in deferred_nodes.most_common():
    if not k.startswith('unit '): chk.append(f"- {k}: {v} nodes")
chk.append(f"\n## F. SUPPLEMENTARY (approved by policy decision; kept outside the main corpus with provenance - see supplementary_manifest.csv) ({len(supp_manifest)} documents, {n_supp} nodes)")
for m in supp_manifest: chk.append(f"- {m['file']}: {m['decision_level']} {m['unit_id']} [{m['group']}] {m['n_nodes']} nodes, {m['languages']} - {m['basis'][:160]}")
chk.append(f"\n## D. BLOCKING until resolved")
for k,v in blocking.items(): chk.append(f"### {k} ({len(v)})"); chk+=['- '+x for x in v]
if not blocking: chk.append('- none')
checklist='\n'.join(chk)
os.makedirs(os.path.join(HERE,'out_corpus'),exist_ok=True)
tag=f'{A.version}{"_dryrun" if A.dry_run else ""}'
open(os.path.join(HERE,'out_corpus',f'FREEZE_REPORT_{tag}.md'),'w',encoding='utf-8').write(report)
open(os.path.join(HERE,'out_corpus',f'RELEASE_CHECKLIST_{tag}.md'),'w',encoding='utf-8').write(checklist)
# live worksheet of the function-audit pending set (regenerated every run; never reuse an old one)
wsp=os.path.join(HERE,'out_corpus',f'FUNCTION_AUDIT_WORKSHEET_{tag}.csv')
with open(wsp,'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['unit_id','title_deep','play_type_deep','source_sha256','container_node_path','div_path_filter','n_nodes_pending','chars','mean_chars_per_node','max_chars','unit_nodes_in_sp','parents','languages','sample_1','sample_2','sample_3','decision_default','text_role_default','basis','source','status'])
    insp=Counter(L['unit_id'] for L in LINES if L['in_sp']=='1')
    for (u,dp),x in sorted(ws.items(),key=lambda kv:-kv[1]['chars']):
        r=byuid[u]; w.writerow([u,r['title_deep'],r['play_type_deep'].split(';')[0],r['source_sha256'],r['unit_node_path'],dp,x['n'],x['chars'],round(x['chars']/x['n']),x['max'],insp[u],';'.join(f'{k}={v}' for k,v in x['parents'].most_common(3)),';'.join(f'{k}={v}' for k,v in x['langs'].items())]+x['samples']+['']*(3-len(x['samples']))+['','','','',''])
if not A.dry_run:
    def wcsv(name,header,rows):
        with open(os.path.join(STAGE,name),'w',newline='',encoding='utf-8') as f: w=csv.writer(f); w.writerow(header); w.writerows(rows)
    with open(os.path.join(STAGE,'corpus_manifest.csv'),'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(manifest[0].keys())); w.writeheader(); w.writerows(manifest)
    wcsv('kept_nodes.csv',['view','edition_id','file','out_index','source_sha256','node_path','owner_unit','section','text_role','language','language_source','text_sha256','relation','translation_of'],kept_rows)
    if supp_manifest:
        with open(os.path.join(STAGE,'supplementary_manifest.csv'),'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(supp_manifest[0].keys())); w.writeheader(); w.writerows(supp_manifest)
    wcsv('supplementary_nodes.csv',['file','unit_id','group','out_index','source_sha256','node_path','text_role','language','language_source','text_sha256'],supp_rows)
    wcsv('node_fates.csv',['source_sha256','node_path','fate','edition_or_reason','section','text_role','owner','language','language_source'],[[k[0],k[1],f[0],f[1]]+([f[2],f[3],f[4],f[5],f[6]] if f[0]=='kept' else ([f'supplementary:{f[3]}',f[6],f[2],f[4],f[5]] if f[0]=='supplementary' else ['','','','',''])) for k,f in fates.items()])
    wcsv('corpus_reconciliation.csv',['view','file','edition_id','planned_nodes','read_back_lines','expected_from_node_fates','sha256_file','status'],recon)
    wcsv('excluded_nodes_summary.csv',['reason','n_nodes'],excluded.most_common())
    open(os.path.join(STAGE,'FREEZE_REPORT.md'),'w',encoding='utf-8').write(report); open(os.path.join(STAGE,'release_checklist.md'),'w',encoding='utf-8').write(checklist)
    for p in list(INPUTS): shutil.copy(p,os.path.join(STAGE,'inputs_'+os.path.basename(p)))
    for fn in ['manual_overrides.csv','scope_decisions.csv','policy_decisions.csv','date_resolutions.csv','edition_witness_selection.csv','deep_min.csv','deep_additions.csv','edition_corrections_A04632.json','edition_language_check.csv','body_outside_sp_prose_review.csv','container_audits.csv','unit_language.csv']:
        p=os.path.join(HERE,fn)
        if os.path.exists(p): INPUTS[p]=sha_file(p); shutil.copy(p,os.path.join(STAGE,'inputs_'+fn))
    wcsv('inputs_manifest.csv',['file','sha256'],[[os.path.relpath(p,HERE),h] for p,h in sorted(INPUTS.items())])
    json.dump({'builder_version':BUILDER_VERSION,'builder_sha256':sha_file(os.path.abspath(__file__)),'args':vars(A),'built_at':datetime.datetime.now().isoformat(timespec='seconds'),
               'rule_versions':sorted(rule_versions),'map_version':um[0].get('map_version','')},open(os.path.join(STAGE,'build_args.json'),'w'),indent=1)
    os.rename(STAGE,CDIR)
print(report); print(checklist if A.dry_run else f'\nBUILT -> {CDIR}')
if would_block or (recon and any(x[-1]!='ok' for x in recon)): sys.exit(2)
