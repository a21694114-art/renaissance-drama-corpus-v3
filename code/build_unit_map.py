#!/usr/bin/env python3
"""
build_unit_map.py  v2  (2026-09-06)  —  DRAFT mapping of candidate units to DEEP records.

Changes from v1 (after the 2026-09-06 review):
  * numbers are IDENTITY: ordinals (first/second/...), roman numerals (II/III), regnal numbers
    and part numbers are extracted as a numeric signature and MUST agree; they are no longer
    stopwords and are no longer dropped for being short.
  * a score is a bounded similarity in [0,1] (each target token counted once).
  * ties / near-ties (top two within 0.05) are NEVER auto-assigned: identity_status = pending,
    both candidates are listed.
  * duplicate DEEP rows for one work inside one collection become ALIASES of the matched unit
    (old_id_aliases); they do not consume candidate units.
  * status is split: identity_status / edition_status / inclusion_status; `relation` says how a
    unit relates to the work it is mapped to (primary / component / appendix /
    alternative_version / separate_work / unresolved).
  * work_key = DEEP work_id (WORK level); witness_key = DEEP edition_id (EDITION level);
    unit_id = SOURCE level.  Nothing is merged here.
  * regression tests: the five mis-matches found in the v1 draft must map correctly.
  * evidence columns for review: xpath, first/last 160 chars of candidate text, act heads.
Reads   out/units_manifest.csv, out/lines.csv, deep_min.csv (repaired), ../tcp_drama/*.xml
Writes  out/unit_map.csv, out/unit_map_review.csv, out/deep_records_without_unit.csv,
        out/review_cases.md (evidence per pending case, grouped by source volume)
"""
import os, re, csv, glob, difflib, sys
from collections import defaultdict, Counter
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,'out'); SRC=os.path.join(HERE,'..','tcp_drama')
csv.field_size_limit(10**9)
MAP_VERSION='unit_map-2026-09-08.v16'
PERF_DIVS={'prologue','epilogue','chorus','song','induction','speech','dumb_show'}
DRAMATIC_TYPES={'dialogue','play','tragedy','comedy','masque','maque','interlude','entertainment','pageant','part'}

NONDRAM_KINDS={'poem','poems','book','letters','treatise','sonnet','sonnet_sequence','epigrams','colophon','commentary',
 'addendum','elegies_and_epitaphs','epithalamiums','to_the_reader','title_page','illustration','chapter','fable','sermon',
 'canto','version','complaint','verse_letter','translation','elegy','epistle','dedication','table_of_contents','epigraph',
 'stationer_to_the_reader','encomium','list_of_actors'}
APPENDIX_WORDS={'sermon','preface','epistle','poems','poem','elegy','elegies','epigram','epigrams','underwoods','discoveries','panegyre','desire to goe to church'}

ORD={'first':1,'second':2,'third':3,'fourth':4,'fifth':5,'fift':5,'sixth':6,'sixt':6,'seventh':7,'eighth':8,'eight':8,'ninth':9,'tenth':10,
     'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'nine':9,'ten':10}
ROMAN={'ii':2,'iii':3,'iiii':4,'iv':4,'v':5,'vi':6,'vii':7,'viii':8,'ix':9,'x':10}
STOP={'the','a','an','of','and','or','in','at','to','his','her','with','by','as','it','was','is','for','on','vpon','upon',
 'tragedie','tragedy','comedie','comedy','historie','history','famous','life','death','true','chronicle','most','lamentable',
 'pleasant','conceited','excellent','new','play','acted','maske','masque','entertainment','entertainement','presented','court',
 'before','their','from','this','that','which','containing','sirnamed','surnamed'}
def basic(s):
    s=str(s).lower().replace('ſ','s').replace('vv','w').replace('æ','ae').replace('œ','oe')
    return re.sub(r'[^a-z0-9 ]+',' ',s).split()
def numsig(s):
    out=[]
    for t in basic(s):
        t=re.sub(r'e$','',t) if t in ('firste','seconde','thirde','fourthe','fifte','sixte','seuenth','eyghth','ninthe','tenthe') else t
        t={'seuenth':'seventh','eyghth':'eighth','ninth':'ninth','sixt':'sixth','fift':'fifth','thyrd':'third','fovrth':'fourth'}.get(t,t)
        if t.isdigit(): out.append(int(t))
        elif t in ORD: out.append(ORD[t])
        elif t in ROMAN: out.append(ROMAN[t])
    return out
def toks(s):
    out=[]
    for t in basic(s):
        if t in STOP or t.isdigit() or t in ORD or t in ROMAN: continue
        t=t.replace('v','u').replace('j','i').replace('y','i'); t=re.sub(r'ie$','i',t); t=re.sub(r'(.)\1+',r'\1',t)
        if len(t)>2: out.append(t)
    return out
def score(head,title,tail=''):
    A=list(dict.fromkeys(toks(head))); B=list(dict.fromkeys(toks(title)))
    if not A or not B: return 0.0
    usedA=set(); hit=0
    for y in B:
        for i,x in enumerate(A):
            if i in usedA: continue
            if x==y or difflib.SequenceMatcher(None,x,y).ratio()>=0.82: usedA.add(i); hit+=1; break
    recall=hit/len(B); prec=hit/len(A)
    seq=difflib.SequenceMatcher(None,' '.join(A),' '.join(B)).ratio()
    s=0.5*recall+0.25*prec+0.25*seq
    nh,nt=numsig(head),numsig(title)
    if not nh and tail:                                       # e.g. "The ende of the first part." or TEI @n="1"
        m=re.search(r'(first|second|third|1|2|3)\s+part',tail.lower().replace('ſ','s'))
        if m: nh=numsig(m.group(0))
        else:
            m2=re.search(r'@n=(\d+)',tail)
            if m2: nh=[int(m2.group(1))]
    if nh and nt and not set(nt)<=set(nh): s*=0.3
    if nt and not nh: s*=0.85
    return round(min(s,1.0),3)

def tcp_header_date(tcp):
    """(editionStmt date raw, year) - and the sourceDesc publication date is kept separately in SRC_DATE"""
    p=os.path.join(SRC,tcp+'.xml')
    if not os.path.exists(p): return '',''
    raw=open(p,encoding='utf-8',errors='replace').read(60000)
    m=re.search(r'<editionStmt>.*?<date>(.*?)</date>',raw,re.S)
    raw_date=m.group(1).strip() if m else ''
    y=re.search(r'1[456]\d\d',raw_date)
    s=re.search(r'<sourceDesc>.*?<publicationStmt>.*?<date>(.*?)</date>',raw,re.S)
    SRC_DATE[tcp]=re.sub(r'\s+',' ',s.group(1)).strip() if s else ''
    return raw_date,(y.group(0) if y else '')
SRC_DATE={}
def load_text_evidence():
    first={}; last={}
    for r in csv.DictReader(open(os.path.join(OUT,'lines.csv'),encoding='utf-8')):
        u=r['unit_id']
        if u not in first: first[u]=r['text'][:160]
        last[u]=r['text'][-160:]
    return first,last
def act_heads():
    sys.path.insert(0,HERE); import importlib
    x=importlib.import_module('extract_units')
    from lxml import etree
    coll={r['TCP'] for r in csv.DictReader(open(os.path.join(HERE,'deep_min.csv'),encoding='utf-8')) if r['record_type']=='Collection'}
    out={}
    for path in sorted(glob.glob(os.path.join(SRC,'*.xml'))):
        tcp=os.path.basename(path)[:-4]
        root=etree.parse(path,etree.XMLParser(recover=True,huge_tree=True)).getroot()
        text=root.find('t:text',x.NS)
        if text is None: continue
        for un in [s for u in x.units_from_text(text,tcp,tcp in coll) for s in x.subsplit(u)]:
            uid,body,excl=un['uid'],un['node'],un['exclude']
            hs=[]
            for d in body.iter('{%s}div'%x.TEI):
                if any(a is e for a in d.iterancestors() for e in excl): continue
                if (d.get('type') or '') in ('act','scene','part','prologue','epilogue','induction','chorus'):
                    h=d.find('t:head',x.NS)
                    if h is not None:
                        t=re.sub(r'\s+',' ',''.join(h.itertext())).strip()
                        if t: hs.append(f"{d.get('type')}:{t[:40]}")
                if len(hs)>=4: break
            out[uid]=' | '.join(hs)
    return out

man=list(csv.DictReader(open(os.path.join(OUT,'units_manifest.csv'),encoding='utf-8')))
deep=list(csv.DictReader(open(os.path.join(HERE,'deep_min.csv'),encoding='utf-8')))
if os.path.exists(os.path.join(HERE,'deep_additions.csv')):
    add=list(csv.DictReader(open(os.path.join(HERE,'deep_additions.csv'),encoding='utf-8')))
    have={d['TCP'] for d in deep}
    for a in add:
        if a['TCP'] not in have: deep.append({k:a.get(k,'') for k in deep[0].keys()}|{'metadata_added_from':a.get('metadata_added_from','')}); print('metadata row added from official export:',a['TCP'],a['title.1'][:50])
SCOPE=list(csv.DictReader(open(os.path.join(HERE,'scope_decisions.csv'),encoding='utf-8'))) if os.path.exists(os.path.join(HERE,'scope_decisions.csv')) else []
def scope_decision(u):
    for s in SCOPE:
        if s['tcp']==u['tcp'] and (not s['div_type'] or s['div_type']==u['div_type']): return s
    return None
# DEEP sub-ids are two-digit decimals (5076.01 ... 5076.27); Excel turned .10/.20 into .1/.2 - restore as strings
for d in deep:
    v=d.get('deep_id','')
    if d['record_type']=='Play in Collection' and re.fullmatch(r'\d+\.\d',v): d['deep_id']=v+'0'
    elif re.fullmatch(r'\d+\.0',v): d['deep_id']=v[:-2]
by_tcp=defaultdict(list)
for d in deep: by_tcp[d['TCP'].split('.')[0]].append(d)
COLL={d['TCP'] for d in deep if d['record_type']=='Collection'}
hdr={t:tcp_header_date(t) for t in by_tcp}
FIRST,LAST=load_text_evidence(); AH=act_heads()
def base(u): return u.split('.')[0]
def has_frames(u): return bool(set(u.get('div_paths_present','').split(';')) & PERF_DIVS)
def nchars(u): return int(u['chars_in_sp'])+int(u['chars_outside_sp_unclassified'])

rows=[]; consumed=set()
OV={}
ov_path=os.path.join(HERE,'manual_overrides.csv')
if os.path.exists(ov_path):
    for o in csv.DictReader(open(ov_path,encoding='utf-8')): OV[o['unit_id']]=o
OV_DEEP={o['deep_TCP'] for o in OV.values() if o['deep_TCP'] and o.get('claims_primary_identity','no')=='yes'}   # association != claiming the primary text
def edition_status(tcp,d):
    raw,y=hdr.get(tcp,('',''))
    dy=(d or {}).get('year_int','')
    if not d or not y or not dy: return 'n.a.',raw
    if y==dy: return 'ok',raw
    if abs(int(y)-int(dy))<=1: return f'minor: header {y} vs DEEP {dy} - not verified',raw
    return f'CHECK: header {y} vs DEEP {dy} - DEEP row may describe another edition',raw
def relation_guess(u,group_units,d):
    if len(group_units)<=1: return 'primary'
    h=str(u['head']).lower(); ah=AH.get(u['unit_id'],'').lower()
    if any(w in h for w in APPENDIX_WORDS) or u['div_type'] in NONDRAM_KINDS: return 'appendix'
    first_act=next((h for h in ah.split(' | ') if h.startswith('act:')),'')
    m=re.search(r'\b(?:actus|act)\.?\s*([ivx]+|\d+|[a-z]+)\b',first_act[4:])
    if m:
        v=m.group(1); n=ROMAN.get(v) or ORD.get(v) or {'primus':1,'secundus':2,'tertius':3,'quartus':4,'quintus':5}.get(v) or (int(v) if v.isdigit() else None)
        if n and n>=2: return 'alternative_version'
    if re.search(r'(first|second|third|1|2|3)\s+part|part\s+(i|ii|iii|1|2|3)\b',h): return 'component'
    return 'unresolved'
def mkrow(u,d,method,sc,identity,reason,cands='',aliases='',relation='primary',inclusion=None):
    es,raw=edition_status(u['tcp'],d)
    if inclusion is None: inclusion='proposed' if (d and identity=='confirmed_auto' and nchars(u)>0) else 'pending'
    return {'map_version':MAP_VERSION,'unit_id':u['unit_id'],'tcp':u['tcp'],'source_sha256':u['source_sha256'],'unit_node_path':u['unit_node_path'],
     'parent_unit':u.get('parent_unit',''),'kind':u['kind'],'div_type':u['div_type'],'div_paths_present':u.get('div_paths_present',''),'head':u['head'],'n_sp':u['n_sp'],'n_chars_candidate':nchars(u),
     'trailer_text':u.get('trailer_text',''),'act_heads':AH.get(u['unit_id'],''),'text_first160':FIRST.get(u['unit_id'],''),'text_last160':LAST.get(u['unit_id'],''),
     'old_id':(d or {}).get('TCP',''),'old_id_aliases':aliases,'deep_id':(d or {}).get('deep_id',''),
     'work_key(work_id)':(d or {}).get('work_id',''),'witness_key(edition_id)':(d or {}).get('edition_id',''),
     'title_deep':(d or {}).get('title.1',''),'author_deep':(d or {}).get('author.1',''),'genre_deep':(d or {}).get('genre_brit_filter',''),
     'play_type_deep':(d or {}).get('play_type_filter',''),'year_deep':(d or {}).get('year_int',''),'metadata_repaired':(d or {}).get('metadata_repaired',''),
     'edition_id_corrected':'','deep_id_corrected':'','year_corrected':'','edition_correction_source':'','edition_record_states':'',
     'edition_id_effective':(d or {}).get('edition_id',''),'deep_id_effective':(d or {}).get('deep_id',''),'year_effective':(d or {}).get('year_int',''),'edition_effective_basis':'original DEEP row' if d else '',
     'metadata_added_from':(d or {}).get('metadata_added_from',''),
     'tcp_header_date_raw':raw,'tcp_source_publication_date_raw':SRC_DATE.get(u['tcp'],''),'edition_status':es,
     'match_method':method,'match_score':sc,'candidates':cands,'identity_status':identity,'relation':relation,
     'inclusion_status':inclusion,'witness_role':'','witness_selection':'','witness_selection_status':'','year_effective_raw':'','reason':reason}

def title_lead(t):
    b=basic(t); return int(b[0]) if b and b[0].isdigit() else None
def ordinal_unique(u,d,cands):
    nh=numsig(u['head']); nt=numsig(d['title.1'])
    if not nh and u.get('div_n','').isdigit():
        # TEI @n on the division vs the leading part number of DEEP titles ("1 Edward the Fourth")
        n=int(u['div_n']); lead=title_lead(d['title.1'])
        return lead==n and sum(1 for c in cands if title_lead(c['title.1'])==n)==1
    if not nh or not nt or set(nt)-set(nh): return False
    return sum(1 for c in cands if numsig(c['title.1']) and set(numsig(c['title.1']))<=set(nh))==1

def assign(units,cands,allow_order):
    """greedy title assignment with tie protection; returns au{uid:(deepTCP,score,tie)} and order set"""
    pairs=sorted(((score(u['head'],d['title.1'],u.get('trailer_text','')+' '+LAST.get(u['unit_id'],'')+(f" @n={u['div_n']}" if u.get('div_n','').isdigit() else '')),u['unit_id'],d['TCP']) for u in units for d in cands),reverse=True)
    au={}; ad={}
    for sc,uid,dt in pairs:
        if sc<0.3 or uid in au or dt in ad: continue
        rival=[p for p in pairs if p[1]==uid and p[2]!=dt and p[2] not in ad]
        if rival and rival[0][0]>=sc-0.05:
            au[uid]=(dt,sc,'TIE:'+';'.join(f'{p[2]}={p[0]}' for p in [(sc,uid,dt)]+rival[:2])); continue
        au[uid]=(dt,sc,''); ad[dt]=uid
    order=set()
    if allow_order:
        unmatched=[u for u in units if u['unit_id'] not in au]; freed=[d for d in cands if d['TCP'] not in ad]
        if unmatched and len(unmatched)==len(freed)<=3:
            for u,d in zip(unmatched,freed): au[u['unit_id']]=(d['TCP'],0.0,''); ad[d['TCP']]=u['unit_id']; order.add(u['unit_id'])
    return au,order

residuals=[u for u in man if u['kind']=='residual']
man=[u for u in man if u['kind']!='residual']
groups=defaultdict(list)
for u in man: groups[base(u['unit_id'])].append(u)
for tcp,units in groups.items():
    cands=[d for d in by_tcp.get(tcp,[]) if d['record_type']!='Collection']
    dmap={d['TCP']:d for d in cands}
    if not cands:
        for u in units: rows.append(mkrow(u,None,'none',0,'pending','metadata row missing: no DEEP record for this TCP id'))
        continue
    bywork=defaultdict(list)
    for d in cands: bywork[d['work_id']].append(d)
    alias_of={}
    for wid,ds in bywork.items():
        if len(ds)>1:
            for extra in ds[1:]: alias_of[extra['TCP']]=ds[0]['TCP']
    prim=[d for d in cands if d['TCP'] not in alias_of and d['TCP'] not in OV_DEEP]
    def aliases_for(dt): return ';'.join(a for a,p in alias_of.items() if p==dt)
    def consume(d):
        consumed.add(id(d))
        for a,p in alias_of.items():
            if p==d['TCP']: consumed.add(id(dmap[a]))
    textual=[u for u in units if u['div_type'] not in NONDRAM_KINDS and nchars(u)>0 and u['unit_id'] not in OV]
    units=[u for u in units if u['unit_id'] not in OV]          # overridden units are emitted in the override pass
    if not units: continue
    if len(prim)==1:
        d=prim[0]; consume(d); al=aliases_for(d['TCP'])
        for u in units:
            if u['div_type'] in NONDRAM_KINDS and has_frames(u): rows.append(mkrow(u,None,'none',0,'pending','non-dramatic division that CONTAINS performance frames (prologue/epilogue/speech) - attribute each frame to its work, do not exclude wholesale',inclusion='pending')); continue
            if u['div_type'] in NONDRAM_KINDS: rows.append(mkrow(u,None,'none',0,'confirmed_auto','non-dramatic division (structure)',inclusion='excluded_proposed')); continue
            if nchars(u)==0: rows.append(mkrow(u,None,'none',0,'pending','no candidate text in source division (zero output is NOT evidence of absence)')); continue
            if len(textual)==1:
                rows.append(mkrow(u,d,'tcp_1to1',1.0,'confirmed_auto','',aliases=al)); continue
            rel=relation_guess(u,textual,d)
            rows.append(mkrow(u,d,'tcp_prefix' if tcp not in COLL else 'single_work_collection',0.9,
                'confirmed_auto' if rel in ('primary','component') else 'pending',
                f'ONE DEEP work, {len(textual)} text-bearing units; relation={rel} - merge only components; appendices excluded; alternative versions kept apart',
                aliases=al,relation=rel,inclusion='pending'))
        continue
    au,order=assign(textual,prim,allow_order=True)
    for u in units:
        if u['div_type'] in NONDRAM_KINDS and has_frames(u): rows.append(mkrow(u,None,'none',0,'pending','non-dramatic division that CONTAINS performance frames (prologue/epilogue/speech) - attribute each frame to its work, do not exclude wholesale',inclusion='pending')); continue
        if u['div_type'] in NONDRAM_KINDS: rows.append(mkrow(u,None,'none',0,'confirmed_auto','non-dramatic division (structure)',inclusion='excluded_proposed')); continue
        if nchars(u)==0: rows.append(mkrow(u,None,'none',0,'pending','no candidate text in source division (empty or narrative-only) - NOT evidence of absence')); continue
        if u['unit_id'] in au:
            dt,sc,tie=au[u['unit_id']]
            if tie: rows.append(mkrow(u,None,'title',sc,'pending','TIE between candidates - decide from source',cands=tie)); continue
            d=dmap[dt]; consume(d); al=aliases_for(dt)
            if u['unit_id'] in order:
                if ordinal_unique(u,d,prim): rows.append(mkrow(u,d,'order+@n',0.0,'confirmed_auto','assigned by document order; TEI @n / ordinal of this division equals the DEEP title number and is unique',aliases=al))
                else: rows.append(mkrow(u,d,'order',0.0,'pending','assigned by document order (counts agree) - verify',aliases=al))
            elif sc>=0.6: rows.append(mkrow(u,d,'title',sc,'confirmed_auto','',aliases=al))
            elif ordinal_unique(u,d,prim): rows.append(mkrow(u,d,'title+ordinal',sc,'confirmed_auto','ordinal in source head equals the DEEP title ordinal and is unique in this collection',aliases=al))
            else: rows.append(mkrow(u,d,'title',sc,'pending','weak title match - verify',aliases=al))
        else:
            freed=[d for d in prim if id(d) not in consumed]
            sd=scope_decision(u)
            if sd:
                rows.append(mkrow(u,None,'none',0,'pending',f"SCOPE DECISION ({sd['decided_by']}, {sd['decided_on']}): {sd['reason']}",cands=';'.join(d['TCP'] for d in freed[:6]),inclusion=sd['inclusion_status']))
            else:
                rows.append(mkrow(u,None,'none',0,'pending','UNMATCHED: no DEEP row matched this division - identity pending (could be a missing metadata row, a weak title, or a non-DEEP text); decide from source',cands=';'.join(d['TCP'] for d in freed[:6])))

rm_tmp={r['unit_id']:r for r in rows}
for u in residuals:
    if u['unit_id'] in OV: continue
    par=rm_tmp.get(u['parent_unit'])
    # parent may itself have been split: inherit from the first mapped sibling's work if the parent has no row
    d=None
    if par and par['old_id']: d={x['TCP']:x for x in deep}.get(par['old_id'])
    sib=[r for r in rows if r['parent_unit']==u['parent_unit'] and r['old_id']]
    pm={x['unit_id']:x for x in man}.get(u['parent_unit'])
    if pm and pm['kind']=='work_div' and pm['div_type'] in ('masque','maque','entertainment','pageant','play','tragedy','comedy','interlude','dialogue') and par and par['old_id']:
        rows.append(mkrow(u,d,'residual',0,'pending',f"residual of work div {u['parent_unit']} after a nested work was split off = the parent work's own text (verify)",relation='primary',inclusion='pending')); continue
    note=f"residual of {u['parent_unit']}: frames/leftovers outside the work divisions ({u.get('div_paths_present','')}) - attribute per work or exclude; never merged automatically"
    rows.append(mkrow(u,d,'residual',0,'pending',note,cands=';'.join(sorted({r['old_id'] for r in sib})[:6]),relation='residual',inclusion='pending'))
# ---------------- manual overrides (evidence-based, human-editable: manual_overrides.csv)
ov_path=os.path.join(HERE,'manual_overrides.csv'); n_ov=0
if os.path.exists(ov_path):
    dmap_all={d['TCP']:d for d in deep}
    allu={x['unit_id']:x for x in man+residuals}
    rows=[r for r in rows if r['unit_id'] not in OV]
    for o in OV.values():
        u=allu.get(o['unit_id'])
        if u is None: print('override for unknown unit',o['unit_id']); continue
        d=dmap_all.get(o['deep_TCP']) if o['deep_TCP'] else None
        rows.append(mkrow(u,d,'manual',1.0 if d else 0,o['identity_status'],'OVERRIDE: '+o['evidence'],relation=o['relation'],inclusion=o['inclusion_status']))
        if d: consumed.add(id(d))
        n_ov+=1
    print('manual overrides applied:',n_ov)
PAGES_MISSING={'A04632.21':'Oberon','A04632.22':'Love Freed','A04632.23':'Love Restored','A04632.24':'Challenge at Tilt','A04632.25':'Irish Masque'}
# ---------------- edition-level corrections (DEEP official export; see edition_corrections_*.json)
import json as _json
for ecf in sorted(glob.glob(os.path.join(HERE,'edition_corrections_*.json'))):
    ec=_json.load(open(ecf,encoding='utf-8')); src=ec.get('provenance',{}).get('official_export_url','')+' @ '+ec.get('provenance',{}).get('retrieved_utc','')
    by_alias={c['old_tcp_alias']:c for c in ec['corrections']}; n=0
    for r in rows:
        c=by_alias.get(r['old_id'])
        if not c: continue
        r['edition_id_corrected']=str(c['new_edition_id']); r['deep_id_corrected']=str(c['edition_reference_deep_id']); r['year_corrected']=str(c['new_year'])
        r['edition_correction_source']=os.path.basename(ecf)+' <- '+src
        r['edition_record_states']=f"{len(c.get('possible_record_deep_ids',[]))} record state(s): {';'.join(map(str,c.get('possible_record_deep_ids',[])))} - {c.get('exact_record_state_status','')}"
        r['edition_id_effective']=str(c['new_edition_id']); r['deep_id_effective']=str(c['edition_reference_deep_id']); r['year_effective']=str(c['new_year'])
        r['edition_effective_basis']='corrected from DEEP official export (edition-representative record; title-page state unverified)'
        y=hdr.get(r['tcp'],('',''))[1]
        r['edition_status']=('ok (corrected to DEEP %s, edition %s, %s)'%(c['edition_reference_deep_id'],c['new_edition_id'],c['new_year'])) if y==str(c['new_year']) else r['edition_status']+' | correction applied but header year differs'
        n+=1
    print('edition corrections applied from',os.path.basename(ecf),':',n)
# ---------------- reviewed date resolutions (date_resolutions.csv: same edition, different dating)
dr_path=os.path.join(HERE,'date_resolutions.csv')
if os.path.exists(dr_path):
    n=0
    for dres in csv.DictReader(open(dr_path,encoding='utf-8')):
        for r in rows:
            if r['unit_id']==dres['unit_id'] and r['old_id']:
                r['edition_id_effective']=dres['edition_id_effective']; r['deep_id_effective']=dres['deep_id_effective']; r['year_effective']=dres['year_effective']; r['year_effective_raw']=dres['year_effective_raw']
                r['edition_effective_basis']=f"reviewed date resolution ({dres['resolution']}); raw {dres['year_effective_raw']}; header {r['tcp_header_date_raw']!r}, sourceDesc {r['tcp_source_publication_date_raw']!r}"
                r['edition_status']=f"resolved: {dres['resolution']} - {dres['basis'][:120]}"; n+=1
    print('date resolutions applied:',n)
# ---------------- same-edition full-text witnesses (edition_witness_selection.csv)
ws_path=os.path.join(HERE,'edition_witness_selection.csv')
if os.path.exists(ws_path):
    n=0
    for wsel in csv.DictReader(open(ws_path,encoding='utf-8')):
        for r in rows:
            if r['unit_id']==wsel['unit_id']:
                r['witness_role']=wsel['role_proposed']; r['witness_selection']=f"{wsel['status']}: {wsel['selection_rule'] or wsel['reason']}"; r['witness_selection_status']='confirmed' if wsel['status'].lower().startswith('confirmed') else 'proposed'
                if wsel['role_proposed']=='alternate_witness_same_edition': r['inclusion_status']='alternate_witness_same_edition'
                n+=1
    print('witness selections applied:',n)
for r in rows:
    r.setdefault('witness_role','sole_witness' if r['inclusion_status']=='proposed' else ''); r.setdefault('witness_selection',''); r.setdefault('witness_selection_status','')
    if not r.get('year_effective_raw'): r['year_effective_raw']=r.get('year_effective','')
KNOWN={'A68278.2':'source XML holds Part 1 only (text ends "The ende of the first part"); Part 2 named only in the bibliographic note',
 'A04643.3':'source XML holds 2 of the 3 masques (Haddington masque absent)',
 'A19811.1':'source XML (Daniel 1623) contains The Civil Wars only - no plays','A19811.2':'same as A19811.1','A19811.3':'same as A19811.1','A19811.4':'same as A19811.1','A19811.5':'same as A19811.1'}
aliased={a for r in rows for a in r['old_id_aliases'].split(';') if a}
missing=[]
for d in deep:
    if d['record_type']=='Collection' or id(d) in consumed: continue
    if d['TCP'] in aliased: cat='duplicate metadata row (alias of a matched unit)'
    elif d['TCP'] in KNOWN: cat='confirmed absent from source XML: '+KNOWN[d['TCP']]
    elif d['TCP'] in PAGES_MISSING: cat=f"source pages missing in TCP copy (A04632.14.7-.9 hold only <gap reason=missing>, 25 pages): {PAGES_MISSING[d['TCP']]} not transcribed"
    else:
        tc=base(d['TCP']); pend=[r['unit_id'] for r in rows if r['tcp']==tc and r['identity_status']=='pending' and r['n_chars_candidate']>0]
        cat=('candidate units exist, identity pending: '+';'.join(pend[:8])) if pend else 'no candidate unit in source XML - verify against the XML before calling it absent'
    eff={'deep_id_effective':d['deep_id'],'edition_id_effective':d['edition_id'],'year_effective':d['year_int'],'edition_effective_basis':'original DEEP row'}
    for ecf in glob.glob(os.path.join(HERE,'edition_corrections_*.json')):
        for c in _json.load(open(ecf,encoding='utf-8'))['corrections']:
            if c['old_tcp_alias']==d['TCP']: eff={'deep_id_effective':str(c['edition_reference_deep_id']),'edition_id_effective':str(c['new_edition_id']),'year_effective':str(c['new_year']),'edition_effective_basis':'corrected from DEEP official export'}
    missing.append({'deep_TCP_(old_id)':d['TCP'],'deep_id_original':d['deep_id'],'edition_id_original':d['edition_id'],'year_original':d['year_int'],**eff,'work_id':d['work_id'],'title':d['title.1'],'author':d['author.1'],'play_type':d['play_type_filter'],'category':cat})

REG_REL={'A03224.1.1':('1 Edward the Fourth','primary'),'A03224.1.2':('2 Edward the Fourth','primary'),'A03224.1.0':('1 Edward the Fourth','paratext_in_body'),'A21246.1.0':('The Royal Entertainment at Rycote','primary')}
REG={'A11954.16':'Richard the Second','A11954.23':'Richard the Third','A11954.17':'1 Henry the Fourth','A11954.18':'2 Henry the Fourth','A68278.1':'1 The Troublesome Reign of King John','A11954.34':'Othello','A11954.33':'King Lear','A11954.3':'Merry Wives','A11909.10':'Hercules Oetaeus','A11909.3':'Thebais','A15045.1.2':'2 Promos'}
rm={r['unit_id']:r for r in rows}
print('REGRESSION:'); ok=True
for uid,exp in REG.items():
    got=rm[uid]['title_deep']; st=rm[uid]['identity_status']; good=got.startswith(exp) or exp in got
    ok&=good; print(f"  {'PASS' if good else 'FAIL'}  {uid:<12} -> {got!r:<45} [{st}, {rm[uid]['match_score']}] {rm[uid]['candidates']}")
for uid,(exp,rel) in REG_REL.items():
    r=rm[uid]; good=(exp in r['title_deep']) and r['relation']==rel
    ok&=good; print(f"  {'PASS' if good else 'FAIL'}  {uid:<12} -> {r['title_deep'][:40]!r} rel={r['relation']} [{r['identity_status']}]")
if not ok:
    print('  !! regression failed - map NOT trustworthy; nothing written'); sys.exit(1)

def key(r): return [int(p) if p.isdigit() else p for p in re.split(r'[.]',r['unit_id'][1:])]
rows.sort(key=key)
fn=list(rows[0].keys())
with open(os.path.join(OUT,'unit_map.csv'),'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fn); w.writeheader(); w.writerows(rows)
rev=[r for r in rows if r['identity_status'] not in ('confirmed_auto','confirmed_manual') or r['edition_status'].startswith('CHECK') or r['relation'] not in ('primary','component') or r['inclusion_status']=='deferred_extension']
with open(os.path.join(OUT,'unit_map_review.csv'),'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=fn); w.writeheader(); w.writerows(rev)
with open(os.path.join(OUT,'deep_records_without_unit.csv'),'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(missing[0].keys())); w.writeheader(); w.writerows(missing)
with open(os.path.join(OUT,'review_cases.md'),'w',encoding='utf-8') as f:
    f.write(f'# Review cases - {MAP_VERSION}\n\nOnly units whose identity, edition or relation is not settled automatically. confirmed_auto rows are in unit_map.csv and are NOT human-verified.\n\n')
    for tcp in sorted({r['tcp'] for r in rev}):
        rs=[r for r in rev if r['tcp']==tcp]
        f.write(f'## {tcp}  ({len(rs)} units)  TCP header date: {hdr.get(tcp,("",""))[0]!r}\n\n')
        for r in rs:
            f.write(f"### {r['unit_id']}  - {r['kind']}/{r['div_type']}  `{r['unit_node_path']}`\n")
            f.write(f"- head: **{r['head']}**\n- trailer: {r['trailer_text']}\n- act heads: {r['act_heads']}\n- text begins: _{r['text_first160']}_\n- text ends: _{r['text_last160']}_\n- chars: {r['n_chars_candidate']}, sp: {r['n_sp']}\n")
            f.write(f"- proposed: {r['title_deep'] or '-'} (old_id {r['old_id'] or '-'}, work_id {r['work_key(work_id)'] or '-'})\n- effective edition: id {r['edition_id_effective'] or '-'}, DEEP {r['deep_id_effective'] or '-'}, year {r['year_effective'] or '-'} [{r['edition_effective_basis']}]; original row: id {r['witness_key(edition_id)'] or '-'}, DEEP {r['deep_id'] or '-'}, year {r['year_deep'] or '-'}\n")
            if r['candidates']: f.write(f"- candidates: {r['candidates']}\n")
            f.write(f"- identity: {r['identity_status']} | edition: {r['edition_status']} | relation: {r['relation']} | inclusion: {r['inclusion_status']}\n- **question:** {r['reason'] or 'confirm the proposed identity'}\n\n")
print('units:',len(rows),'| identity:',Counter(r['identity_status'] for r in rows),'| relation:',Counter(r['relation'] for r in rows))
print('match_method:',Counter(r['match_method'] for r in rows))
print('edition CHECK:',sum(1 for r in rows if r['edition_status'].startswith('CHECK')),'| review rows:',len(rev))
print('DEEP records without unit:',len(missing),'|',Counter(m['category'].split(':')[0] for m in missing))
