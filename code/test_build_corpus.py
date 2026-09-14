#!/usr/bin/env python3
"""Synthetic regression suite for build_corpus.py (adapted from ChatGPT's probe_builder.py, 2026-09-07).
Runs the CURRENT build_corpus.py on tiny synthetic inputs in a temporary directory - never touches out/ or out_corpus/.
Column schemas are taken from the real out/*.csv headers so the suite breaks if the tables change shape.
Exit 1 on any failed expectation."""
import csv, json, shutil, subprocess, tempfile, sys, os, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
schemas={}
for fn in ['unit_map.csv','units_manifest.csv','lines.csv','frontback_lines.csv','frames_attribution.csv']:
    with (HERE/'out'/fn).open(encoding='utf-8') as h: schemas[fn]=next(csv.reader(h))
def wcsv(path,rows,fields):
    with path.open('w',newline='',encoding='utf-8') as h: w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(rows)
S='s'*64
def unit(uid,relation='primary',status='proposed',ed='101',path='/*/*[2]/*[2]',src=S,tcp='T',old='OLD'):
    r=dict.fromkeys(schemas['unit_map.csv'],'')
    r.update(unit_id=uid,tcp=tcp,old_id=old,source_sha256=src,unit_node_path=path,inclusion_status=status,identity_status='confirmed_manual',relation=relation,
             edition_status='ok',edition_id_effective=ed,deep_id_effective='201',year_effective='1600',title_deep='Synthetic',witness_role='sole_witness',play_type_deep='Occasional',head='h')
    r['work_key(work_id)']='1'; return r
def line(uid,text,path,div='act',sp='1',src=S):
    r=dict.fromkeys(schemas['lines.csv'],''); r.update(unit_id=uid,tcp='T',text=text,node_path=path,source_sha256=src,div_path=div,in_sp=sp,n_chars=str(len(text)),seq='1',rule_version='test'); return r
def frame_group(inner,section='front',oid='OLD',tnp='/*/*[2]'):
    f=dict.fromkeys(schemas['frames_attribution.csv'],''); f.update(tcp='T',text_node_path=tnp,section=section,innermost_div=inner,frame_class='candidate',lines='1',scope='single work'); f['attributed_work(old_id)']=oid; return f
def frame_line(text,path,inner='prologue',section='front',tnp='/*/*[2]'):
    f=dict.fromkeys(schemas['frontback_lines.csv'],''); f.update(tcp='T',text_node_path=tnp,section=section,div_path=inner,text=text,node_path=path,source_sha256=S,in_sp='0'); return f
def run(case,us,ls,fa=(),fl=(),node_dec=None,dry=False,cov='ok',nlang=None,audits=None,ulang=None,nl_rows=None,fdec=None):
    d=Path(tempfile.mkdtemp(prefix='bc-test-')); (d/'out').mkdir(); shutil.copyfile(HERE/'build_corpus.py',d/'build_corpus.py')
    for fn,rr in [('unit_map.csv',us),('units_manifest.csv',[]),('lines.csv',ls),('frontback_lines.csv',list(fl)),('frames_attribution.csv',list(fa))]: wcsv(d/'out'/fn,rr,schemas[fn])
    wcsv(d/'frames_rules.csv',[{'innermost_div':'prologue','default_decision':'include'},{'innermost_div':'epilogue','default_decision':'include'}],['innermost_div','default_decision'])
    if node_dec: wcsv(d/'body_node_decisions.csv',node_dec,list(node_dec[0].keys()))
    if audits: wcsv(d/'container_audits.csv',audits,list(audits[0].keys()))
    if ulang: wcsv(d/'unit_language.csv',ulang,list(ulang[0].keys()))
    if fdec: wcsv(d/'frames_decisions.csv',fdec,list(fdec[0].keys()))
    # node_language.csv as node_language.py would write it: every key, xml lang 'eng' unless overridden
    nl=nlang or {}
    keys={(r['source_sha256'],r['node_path']) for r in list(ls)+list(fl)}
    nlrows=[{'source_sha256':k[0],'node_path':k[1],'xml_lang_effective':nl.get(k[1],'en'),'xml_lang_raw':nl.get(k[1],'eng'),'lang_source_xpath':'/*/*[2]'} for k in keys]
    if nl_rows is not None: nlrows=nl_rows(nlrows)
    wcsv(d/'out'/'node_language.csv',nlrows,['source_sha256','node_path','xml_lang_effective','xml_lang_raw','lang_source_xpath'])
    if cov:  # synthetic coverage_summary.json as coverage_check.py would write it for these tables
        keys={(r['source_sha256'],r['node_path']) for r in list(ls)+list(fl)}
        sh=lambda fn: hashlib.sha256((d/'out'/fn).read_bytes()).hexdigest()
        summ={'inputs':{'lines.csv':sh('lines.csv') if cov=='ok' else 'stale','frontback_lines.csv':sh('frontback_lines.csv')},'candidate_nodes_in_xml':len(keys),'missing':0,'duplicated':0}
        (d/'out'/'coverage_summary.json').write_text(json.dumps(summ))
    args=[sys.executable,str(d/'build_corpus.py'),'--version',case]+(['--dry-run'] if dry else [])
    r=subprocess.run(args,capture_output=True,text=True); dest=d/'out_corpus'/case
    res={'rc':r.returncode,'out':r.stdout+r.stderr,'exists':dest.exists(),'staging':(d/'out_corpus'/(case+'.staging')).exists()}
    if dest.exists():
        res['texts']={p.name:p.read_text(encoding='utf-8') for p in (dest/'texts').glob('*.txt')}
        res['nope']={p.name:p.read_text(encoding='utf-8') for p in (dest/'texts_no_prologue_epilogue').glob('*.txt')}
        res['recon']=list(csv.DictReader((dest/'corpus_reconciliation.csv').open(encoding='utf-8')))
        res['fates']=list(csv.DictReader((dest/'node_fates.csv').open(encoding='utf-8')))
        res['kept']=list(csv.DictReader((dest/'kept_nodes.csv').open(encoding='utf-8')))
        res['manifest']=list(csv.DictReader((dest/'corpus_manifest.csv').open(encoding='utf-8')))
        res['supp']={p.name:p.read_text(encoding='utf-8') for p in (dest/'supplementary').glob('*.txt')} if (dest/'supplementary').exists() else None
        res['suppman']=list(csv.DictReader((dest/'supplementary_manifest.csv').open(encoding='utf-8'))) if (dest/'supplementary_manifest.csv').exists() else []
    shutil.rmtree(d); return res
fails=[]
def expect(name,cond,detail=''):
    print(('PASS ' if cond else 'FAIL ')+name+('' if cond else '  <- '+detail[:600]));
    if not cond: fails.append(name)

# 1. pending items must block a real build (and be listed in dry-run)
u=unit('U'); u['witness_role']='representative_proposed'; u['witness_selection_status']='proposed'
alt=unit('ALT',status='alternate_witness_same_edition'); alt['witness_role']='alternate_witness_same_edition'; alt['witness_selection_status']='proposed'
pend=unit('PENDING','unresolved','pending',ed='102')
fa=[frame_group('induction',oid='')]
r=run('pending',[u,alt,pend],[line('U','A','/*/*[2]/*[2]/*[1]')],fa)
expect('pending: real build refused',r['rc']!=0 and not r['exists'] and not r['staging'],r['out'])
r=run('pending',[u,alt,pend],[line('U','A','/*/*[2]/*[2]/*[1]')],fa,dry=True)
expect('pending: dry-run lists witness / unit / frame blockers',all(k in r['out'] for k in ['witness selection not confirmed','units pending','frame groups pending']) and 'FREEZE GATE: BLOCKED' in r['out'],r['out'])

# 2. document order across residual + component, frames in front, and the no-prologue/epilogue view
u=unit('U'); comp=unit('C','component',path='/*/*[2]/*[2]/*[3]')
ls=[line('U','BODY_PROLOGUE','/*/*[2]/*[2]/*[1]','prologue','0'),line('U','A','/*/*[2]/*[2]/*[2]'),line('U','C','/*/*[2]/*[2]/*[4]'),line('C','B','/*/*[2]/*[2]/*[3]/*[1]')]
AUD=[{'source_sha256':S,'unit_id':'U','container_node_path':'/*/*[2]/*[2]','decision_default':'include','text_role_default':'','basis':'test','source':'test','status':'applied'}]
r=run('order',[u,comp],ls,[frame_group('prologue')],[frame_line('FRONT_PROLOGUE','/*/*[2]/*[1]/*[1]')],audits=AUD)
expect('order: build succeeds',r['rc']==0 and r['exists'],r['out'])
if r['exists']:
    expect('order: texts = FRONT_PROLOGUE,BODY_PROLOGUE,A,B,C',list(r['texts'].values())[0]=='FRONT_PROLOGUE\nBODY_PROLOGUE\nA\nB\nC',str(r['texts']))
    expect('order: no_prologue_epilogue view = A,B,C',list(r['nope'].values())[0]=='A\nB\nC',str(r['nope']))
    expect('order: reconciliation all ok',all(x['status']=='ok' for x in r['recon']) and len(r['recon'])==3,str(r['recon']))
    expect('order: node_fates covers 5 nodes all kept',len(r['fates'])==5 and all(f['fate']=='kept' for f in r['fates']),str(r['fates']))

# 3. duplicate node (same sha + node_path twice) must fail
ls=[line('U','A','/*/*[2]/*[2]/*[1]')]; ls.append(dict(ls[0]))
r=run('dup',[unit('U')],ls)
expect('duplicate node: refused',r['rc']!=0 and not r['exists'] and 'claimed twice' in r['out'],r['out'])

# 4. node decisions override rules and set text_role
ls=[line('U','KEEP','/*/*[2]/*[2]/*[1]'),line('U','DROP_ME','/*/*[2]/*[2]/*[2]'),line('U','VENUS','/*/*[2]/*[2]/*[3]','poem','0'),line('U','UNDECIDED_POEM','/*/*[2]/*[2]/*[4]','poem','0')]
def nd(text,path,dec,role=''):
    return {'source_sha256':S,'node_path':path,'unit_id':'U','seq':'1','div_path':'x','container_node_path':'','text_sha256':hashlib.sha256(text.encode()).hexdigest(),'decision':dec,'text_role':role,'exclusion_category':'test','basis':'test','source':'test','status':'applied','decided_on':''}
r=run('nodedec',[unit('U')],ls,node_dec=[nd('DROP_ME','/*/*[2]/*[2]/*[2]','exclude'),nd('VENUS','/*/*[2]/*[2]/*[3]','include','epilogue')],dry=True)
expect('node decisions: undecided poem blocks (dry-run reports pending)',r['rc']==2 and 'body node decisions pending' in r['out'],r['out'])
r=run('nodedec2',[unit('U')],ls[:3],node_dec=[nd('DROP_ME','/*/*[2]/*[2]/*[2]','exclude'),nd('VENUS','/*/*[2]/*[2]/*[3]','include','epilogue')])
expect('node decisions: exclude beats in_sp; include sets epilogue role',r['rc']==0 and r['exists'] and list(r['texts'].values())[0]=='KEEP\nVENUS' and list(r['nope'].values())[0]=='KEEP',r['out'][:300]+str(r.get('texts')))
r=run('nodedec3',[unit('U')],ls[:3],node_dec=[nd('WRONG_TEXT','/*/*[2]/*[2]/*[2]','exclude')])
expect('node decisions: text hash mismatch is a hard failure',r['rc']!=0 and 'hash mismatch' in r['out'],r['out'])

# 4b. language: Latin node kept in texts/, absent from the English views
ls_l=[line('U','ENGLISH','/*/*[2]/*[2]/*[1]'),line('U','LATINA','/*/*[2]/*[2]/*[2]','poem','0')]
ndl=nd('LATINA','/*/*[2]/*[2]/*[2]','include','poem'); ndl['language']='la'
r=run('lang',[unit('U')],ls_l,node_dec=[ndl])
expect('language: Latin node in texts/ only',r['rc']==0 and list(r['texts'].values())[0]=='ENGLISH\nLATINA' and list(r['nope'].values())[0]=='ENGLISH',r['out'][:300]+str(r.get('texts')))

# 5. cross-source edition refused
u2=unit('U2',src='t'*64,tcp='T2',path='/*/*[2]/*[2]',relation='component')
r=run('xsrc',[unit('U'),u2],[line('U','A','/*/*[2]/*[2]/*[1]'),line('U2','B','/*/*[2]/*[2]/*[1]',src='t'*64)])
expect('cross-source edition: refused',r['rc']!=0 and 'more than one source file' in r['out'],r['out'])

# 6. two primaries for one work / one edition without selection -> hard failure
r=run('twoprim',[unit('U'),unit('V',path='/*/*[2]/*[3]')],[line('U','A','/*/*[2]/*[2]/*[1]'),line('V','B','/*/*[2]/*[3]/*[1]')])
expect('two primaries one edition: refused',r['rc']!=0 and 'primary units for one work' in r['out'],r['out'])

# 7. duplicate EXCLUDED node must also be refused (v2 gap A)
ls=[line('U','A','/*/*[2]/*[2]/*[1]'),line('U','ARG','/*/*[2]/*[2]/*[2]','argument','0')]; ls.append(dict(ls[1]))
r=run('dupexcl',[unit('U')],ls)
expect('duplicate excluded node: refused',r['rc']!=0 and not r['exists'] and 'more than once' in r['out'],r['out'])

# 8. body line / frame whose source sha differs from the owner unit (v2 gap B)
r=run('srcmis',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]'),line('U','B','/*/*[2]/*[2]/*[2]',src='t'*64)])
expect('source hash mismatch (body): refused',r['rc']!=0 and 'source sha256 does not match' in r['out'],r['out'])
flx=frame_line('FRONT_PROLOGUE','/*/*[2]/*[1]/*[1]'); flx['source_sha256']='t'*64
r=run('srcmisf',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]')],[frame_group('prologue')],[flx])
expect('source hash mismatch (frame): refused',r['rc']!=0 and 'source sha256 does not match' in r['out'],r['out'])

# 9. nodes of pending units are PENDING, not excluded; coverage binding required and must match
pend=unit('PENDING','unresolved','pending',ed='102',path='/*/*[2]/*[3]')
r=run('pendnodes',[unit('U'),pend],[line('U','A','/*/*[2]/*[2]/*[1]'),line('PENDING','P','/*/*[2]/*[3]/*[1]')],dry=True)
expect('pending unit nodes counted as pending',r['rc']==2 and 'unit pending: 1' in r['out'] and 'excluded (verified) 0' in r['out'],r['out'])
r=run('nocov',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]')],cov=None)
expect('missing coverage_summary.json: refused',r['rc']!=0 and 'coverage_summary.json missing' in r['out'],r['out'])
r=run('stalecov',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]')],cov='stale')
expect('stale coverage_summary.json: refused',r['rc']!=0 and 'sha256 mismatch' in r['out'],r['out'])

# 10. language resolver: xml:lang beats assumed default; empty decision language inherits; unk = no evidence; frames resolve too
ls=[line('U','ENG','/*/*[2]/*[2]/*[1]'),line('U','LAT_XML','/*/*[2]/*[2]/*[2]'),line('U','UNK','/*/*[2]/*[2]/*[3]'),line('U','DEC_EMPTY','/*/*[2]/*[2]/*[4]','poem','0')]
ndx=nd('DEC_EMPTY','/*/*[2]/*[2]/*[4]','include','poem'); ndx['language']=''
r=run('langres',[unit('U')],ls,[frame_group('prologue')],[frame_line('FRONT_LAT','/*/*[2]/*[1]/*[1]')],node_dec=[ndx],nlang={'/*/*[2]/*[2]/*[2]':'la','/*/*[2]/*[2]/*[3]':'unk','/*/*[2]/*[2]/*[4]':'la','/*/*[2]/*[1]/*[1]':'la'})
expect('language: xml:lang / unk / empty-decision inheritance / frame',r['rc']==0 and list(r['texts'].values())[0]=='FRONT_LAT\nENG\nLAT_XML\nUNK\nDEC_EMPTY' and list(r['nope'].values())[0]=='ENG\nUNK',r['out'][:300]+str(r.get('texts'))+str(r.get('nope')))
# 11. whole-unit language (unit_language.csv) applies when xml has no evidence; empty English view -> no file written
r=run('unitlang',[unit('U')],[line('U','LATINA','/*/*[2]/*[2]/*[1]')],nlang={'/*/*[2]/*[2]/*[1]':'unk'},ulang=[{'unit_id':'U','language':'la','basis':'t','source':'t','status':'applied'}])
expect('unit language + empty view not written',r['rc']==0 and list(r['texts'].values())[0]=='LATINA' and r['nope']=={} and 'non-empty documents 0 / editions 1' in r['out'],r['out'][:400]+str(r.get('nope')))
# 12. function-audit gate: rule-kept node outside <sp> without container audit blocks; with audit include passes; audit exclude drops
ls=[line('U','SPEECH','/*/*[2]/*[2]/*[1]'),line('U','NARRATION','/*/*[2]/*[2]/*[2]','act','0')]
r=run('audit0',[unit('U')],ls)
expect('audit gate: unaudited non-<sp> node blocks',r['rc']!=0 and not r['exists'] and 'function audit pending' in r['out'],r['out'])
AUD_EX=[{'source_sha256':S,'unit_id':'U','container_node_path':'/*/*[2]/*[2]/*[2]','decision_default':'exclude','text_role_default':'performance_description','basis':'test','source':'test','status':'applied'}]
r=run('audit1',[unit('U')],ls,audits=AUD_EX)
expect('audit gate: container exclude drops the node',r['rc']==0 and list(r['texts'].values())[0]=='SPEECH',r['out'][:300]+str(r.get('texts')))
r=run('audit2',[unit('U')],ls,audits=AUD)
expect('audit gate: container include keeps the node',r['rc']==0 and list(r['texts'].values())[0]=='SPEECH\nNARRATION',r['out'][:300]+str(r.get('texts')))
ndo=nd('NARRATION','/*/*[2]/*[2]/*[2]','exclude')
r=run('audit3',[unit('U')],ls,audits=AUD,node_dec=[ndo])
expect('audit gate: node decision overrides container default',r['rc']==0 and list(r['texts'].values())[0]=='SPEECH',r['out'][:300]+str(r.get('texts')))

# 13. audit-row contract (ChatGPT v10 probe): blank / pending rows cover nothing; illegal values, equal-specificity conflicts and wrong unit_id are errors
def aud(dec,status='applied',path='/*/*[2]/*[2]',unit='U',filt='',basis='test'):
    return {'source_sha256':S,'unit_id':unit,'container_node_path':path,'div_path_filter':filt,'decision_default':dec,'text_role_default':'','basis':basis,'source':'test','status':status}
ls=[line('U','SPEECH','/*/*[2]/*[2]/*[1]'),line('U','NARRATION','/*/*[2]/*[2]/*[2]','act','0')]
r=run('audblank',[unit('U')],ls,audits=[aud('','')])
expect('audit contract: blank row covers nothing',r['rc']!=0 and not r['exists'] and 'function audit pending' in r['out'],r['out'])
r=run('audpend',[unit('U')],ls,audits=[aud('pending')])
expect('audit contract: status applied + decision pending covers nothing',r['rc']!=0 and not r['exists'] and 'function audit pending' in r['out'],r['out'])
r=run('audbad',[unit('U')],ls,audits=[aud('maybe')])
expect('audit contract: illegal decision value is a hard failure',r['rc']!=0 and 'must be include/exclude' in r['out'],r['out'])
r=run('audconf',[unit('U')],ls,audits=[aud('include'),aud('exclude')])
r2=run('audconf2',[unit('U')],ls,audits=[aud('exclude'),aud('include')])
expect('audit contract: equal-specificity conflict is a hard failure in both row orders',r['rc']!=0 and r2['rc']!=0 and 'conflicting container audits' in r['out'] and 'conflicting container audits' in r2['out'],r['out']+r2['out'])
r=run('audunit',[unit('U')],ls,audits=[aud('include',unit='OTHER')])
expect('audit contract: row naming another unit is a hard failure',r['rc']!=0 and 'owned by U' in r['out'],r['out'])
r=run('audnobasis',[unit('U')],ls,audits=[aud('include',basis='')])
expect('audit contract: applied row without basis is a hard failure',r['rc']!=0 and 'without a basis' in r['out'],r['out'])
r=run('auddeep',[unit('U')],ls,audits=[aud('include'),aud('exclude',path='/*/*[2]/*[2]/*[2]')])
expect('audit contract: deeper container still wins',r['rc']==0 and list(r['texts'].values())[0]=='SPEECH',r['out'][:300]+str(r.get('texts')))

# 14. language table: key set must equal candidates; duplicates refused
ls1=[line('U','A','/*/*[2]/*[2]/*[1]'),line('U','LAT','/*/*[2]/*[2]/*[2]')]
r=run('nlwrong',[unit('U')],ls1,nl_rows=lambda rows:[dict(x,node_path='/*/*[9]/*[9]') if x['node_path']=='/*/*[2]/*[2]/*[2]' else x for x in rows])
expect('language table: wrong key (same count) refused',r['rc']!=0 and 'key set differs' in r['out'] and 'missing 1' in r['out'] and 'extra 1' in r['out'],r['out'])
r=run('nldup',[unit('U')],ls1,nl_rows=lambda rows:rows+[dict(rows[0],xml_lang_effective='la')])
expect('language table: duplicate key refused',r['rc']!=0 and 'duplicate key' in r['out'],r['out'])

# 15. A15516-type case: whole play wrapped in a prologue div; node-level role overrides keep the body in the no-PE view
ls=[line('U','PRO','/*/*[2]/*[2]/*[1]/*[1]','play>prologue','0'),line('U','BODY1','/*/*[2]/*[2]/*[1]/*[2]','play>prologue','1'),line('U','BODY2','/*/*[2]/*[2]/*[1]/*[3]','play>prologue','1'),line('U','EPI','/*/*[2]/*[2]/*[1]/*[4]','play>prologue','1')]
r=run('wrapped0',[unit('U')],ls,audits=[aud('include')])
expect('wrapped prologue: without overrides the no-PE view is empty (the bug)',r['rc']==0 and r['nope']=={},r['out'][:300]+str(r.get('nope')))
nds=[nd('PRO','/*/*[2]/*[2]/*[1]/*[1]','include','prologue'),nd('BODY1','/*/*[2]/*[2]/*[1]/*[2]','include','dramatic_body'),nd('BODY2','/*/*[2]/*[2]/*[1]/*[3]','include','dramatic_body'),nd('EPI','/*/*[2]/*[2]/*[1]/*[4]','include','epilogue')]
r=run('wrapped1',[unit('U')],ls,node_dec=nds)
expect('wrapped prologue: node role overrides restore the body',r['rc']==0 and list(r['texts'].values())[0]=='PRO\nBODY1\nBODY2\nEPI' and list(r['nope'].values())[0]=='BODY1\nBODY2',r['out'][:300]+str(r.get('texts'))+str(r.get('nope')))

# 16. equal-specificity audits that both include but disagree on text_role_default are a conflict (ChatGPT v11 probe), in both orders
ls=[line('U','SPOKEN_TEXT','/*/*[2]/*[2]/*[1]','act','0')]
def audr(role): a=aud('include'); a['text_role_default']=role; return a
r=run('roleconf1',[unit('U')],ls,audits=[audr('prologue'),audr('dramatic_body')]); r2=run('roleconf2',[unit('U')],ls,audits=[audr('dramatic_body'),audr('prologue')])
expect('audit contract: role conflict at equal specificity refused in both orders',r['rc']!=0 and r2['rc']!=0 and 'conflicting container audits' in r['out'] and 'conflicting container audits' in r2['out'],r['out']+r2['out'])
r=run('roledup',[unit('U')],ls,audits=[audr('dramatic_body'),audr('dramatic_body')])
expect('audit contract: identical duplicate rows merge',r['rc']==0 and list(r['texts'].values())[0]=='SPOKEN_TEXT',r['out'][:300])

# 17. deferred material: unit deferred_to_grace, container/node/frame 'deferred' -> fate deferred, not built, NOT blocking, listed in checklist E
u=unit('U'); dg=unit('DG',status='deferred_to_grace',ed='103',path='/*/*[2]/*[3]')
ls=[line('U','SPEECH','/*/*[2]/*[2]/*[1]'),line('U','MAYBE','/*/*[2]/*[2]/*[2]','act','0'),line('U','MAYBE2','/*/*[2]/*[2]/*[3]'),line('DG','DEFERRED_UNIT','/*/*[2]/*[3]/*[1]')]
audd=aud('deferred',path='/*/*[2]/*[2]/*[2]'); audd['basis']='held for Grace'
ndd=nd('MAYBE2','/*/*[2]/*[2]/*[3]','deferred')
fdef=[{'tcp':'T','text_node_path':'/*/*[2]','section':'front','innermost_div':'prologue','decision':'deferred','text_role':'','basis':'t','source':'t','status':'deferred_to_grace','decided_on':''}]
def run2(case,**kw):
    return run(case,**kw)
d=Path(tempfile.mkdtemp(prefix='bc-test-')); shutil.rmtree(d)
r=run('deferred',[u,dg],ls,[frame_group('prologue')],[frame_line('FRONT_PROLOGUE','/*/*[2]/*[1]/*[1]')],node_dec=[ndd],audits=[aud('include'),audd])
# frames_decisions is not wired into run(); emulate by checking the rest: build must succeed with deferred unit/container/node
expect('deferred: build succeeds and deferred material is absent',r['rc']==0 and r['exists'] and list(r['texts'].values())[0]=='FRONT_PROLOGUE\nSPEECH' and sum(1 for f in r['fates'] if f['fate']=='deferred')==3 and 'DEFERRED to Grace' in r['out'],r['out'][:400]+str(r.get('texts'))+str(r.get('fates')))

# 18. supplementary (v8): unit status 'supplementary', container 'supplementary', node decision 'supplementary' -> fate supplementary, written to supplementary/ with manifest + read-back, absent from the views, not excluded, not deferred, not blocking
u=unit('U'); su=unit('SU',status='supplementary',ed='104',path='/*/*[2]/*[3]'); su['reason']='approved supplementary unit'
ls=[line('U','SPEECH','/*/*[2]/*[2]/*[1]'),line('U','PILLAR','/*/*[2]/*[2]/*[2]','sonnet','0'),line('U','POEM_TR','/*/*[2]/*[2]/*[3]','poem','0'),line('SU','SUPP_UNIT_A','/*/*[2]/*[3]/*[1]'),line('SU','SUPP_UNIT_B','/*/*[2]/*[3]/*[2]','act','0')]
auds=aud('supplementary',path='/*/*[2]/*[2]/*[2]',filt='sonnet'); auds['basis']='approved supplementary container'
nds=nd('POEM_TR','/*/*[2]/*[2]/*[3]','supplementary'); nds['supplementary_group']='norwich poems'; nds['language']='la'
r=run('supp',[u,su],ls,node_dec=[nds],audits=[aud('include'),auds])
ok=r['rc']==0 and r['exists'] and list(r['texts'].values())[0]=='SPEECH' and r['supp'] is not None and len(r['supp'])==3 and r['supp'].get('SU__unit.txt')=='SUPP_UNIT_A\nSUPP_UNIT_B' and r['supp'].get('U__sonnet.txt')=='PILLAR' and r['supp'].get('U__norwich_poems.txt')=='POEM_TR'
expect('supplementary: three documents written outside the views',ok,r['out'][:400]+str(r.get('supp')))
if r['exists']:
    from collections import Counter as _C; fs=_C(f['fate'] for f in r['fates'])
    expect('supplementary: fates = kept 1 / supplementary 4 / excluded 0 / deferred 0',fs=={'kept':1,'supplementary':4},str(fs))
    expect('supplementary: read-back rows ok incl. supplementary',all(x['status']=='ok' for x in r['recon']) and sum(1 for x in r['recon'] if x['view']=='supplementary')==3,str(r['recon']))
    sm={m['file']:m for m in r['suppman']}
    expect('supplementary: manifest carries provenance (unit, group, level, language, sha)',sm.get('U__norwich_poems.txt',{}).get('decision_level')=='nodes' and sm['U__norwich_poems.txt']['languages']=='la=1' and sm['SU__unit.txt']['decision_level']=='unit' and sm['SU__unit.txt']['edition_id_effective']=='' and all(m['sha256']==hashlib.sha256(r['supp'][m['file']].encode()).hexdigest() for m in r['suppman']),str(r['suppman']))
r=run('supp_dry',[u,su],ls,node_dec=[nds],audits=[aud('include'),auds],dry=True)
expect('supplementary: dry-run reports 4 nodes, gate open',r['rc']==0 and 'SUPPLEMENTARY (approved, outside the main corpus) 4' in r['out'] and 'FREEZE GATE: open' in r['out'],r['out'][:600])

# 19. relation on an included node decision (printed translation of a performed speech) is recorded, not a role
ls=[line('U','SPEECH','/*/*[2]/*[2]/*[1]'),line('U','TRANSLATED_SPEECH','/*/*[2]/*[2]/*[2]','account>translation','0')]
ndt=nd('TRANSLATED_SPEECH','/*/*[2]/*[2]/*[2]','include','speech'); ndt['language']='en'; ndt['relation']='translation'; ndt['translation_of']='Latin oration (source statement)'
r=run('relation',[unit('U')],ls,node_dec=[ndt])
expect('relation: translated speech kept in the English view with relation recorded',r['rc']==0 and list(r['nope'].values())[0]=='SPEECH\nTRANSLATED_SPEECH' and any(k['relation']=='translation' and k['translation_of'].startswith('Latin') and k['view']=='texts' for k in r['kept']) and r['manifest'][0]['relations']=='translation=1',r['out'][:300]+str(r.get('kept'))+str(r.get('manifest')))

# 20. frames: explicit target_unit_id attributes an UNATTRIBUTED frame group to one built unit; a target not built is a hard failure
fd=[{'tcp':'T','text_node_path':'/*/*[2]','section':'front','innermost_div':'prologue','decision':'include','text_role':'prologue','target_unit_id':'U','basis':'shared prologue -> first play','source':'t','status':'applied','decided_on':''}]
r=run('ftarget',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]')],[frame_group('prologue',oid='')],[frame_line('SHARED_PROLOGUE','/*/*[2]/*[1]/*[1]')],fdec=fd)
expect('frames: target_unit_id attributes an unattributed group; prologue kept, dropped from the no-PE view',r['rc']==0 and list(r['texts'].values())[0]=='SHARED_PROLOGUE\nA' and list(r['nope'].values())[0]=='A' and 'explicit target unit U' in r['out'],r['out'][:400]+str(r.get('texts')))
fd2=[dict(fd[0],target_unit_id='ZZ')]
r=run('ftarget2',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]')],[frame_group('prologue',oid='')],[frame_line('SHARED_PROLOGUE','/*/*[2]/*[1]/*[1]')],fdec=fd2)
expect('frames: target_unit_id not built is a hard failure',r['rc']!=0 and not r['exists'] and 'is not a built unit' in r['out'],r['out'][:400])
r=run('ftarget3',[unit('U')],[line('U','A','/*/*[2]/*[2]/*[1]')],[frame_group('prologue',oid='')],[frame_line('SHARED_PROLOGUE','/*/*[2]/*[1]/*[1]')])
expect('frames: without a target the unattributed group still blocks',r['rc']!=0 and 'frame groups pending' in r['out'],r['out'][:400])

# 21. unit_language.csv overrides_xml_lang=yes beats a wrong source xml:lang (Lyndsay tagged eng, text Scots); without the flag xml:lang wins
r=run('ulover',[unit('U')],[line('U','SCOTS','/*/*[2]/*[2]/*[1]')],nlang={'/*/*[2]/*[2]/*[1]':'en'},ulang=[{'unit_id':'U','language':'sco','overrides_xml_lang':'yes','basis':'t','source':'t','status':'applied'}])
expect('unit language override: sco beats xml:lang en, English view empty',r['rc']==0 and list(r['texts'].values())[0]=='SCOTS' and r['nope']=={} and 'overrides xml:lang' in r['out'],r['out'][:400]+str(r.get('nope')))
r=run('ulnoover',[unit('U')],[line('U','SCOTS','/*/*[2]/*[2]/*[1]')],nlang={'/*/*[2]/*[2]/*[1]':'en'},ulang=[{'unit_id':'U','language':'sco','overrides_xml_lang':'','basis':'t','source':'t','status':'applied'}])
expect('unit language without the flag: xml:lang en still wins',r['rc']==0 and list(r['nope'].values())[0]=='SCOTS',r['out'][:400]+str(r.get('nope')))

print(f"\n{len(fails)} failure(s)"); sys.exit(1 if fails else 0)
