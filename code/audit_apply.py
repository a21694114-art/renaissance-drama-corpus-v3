#!/usr/bin/env python3
"""audit_apply.py decisions.json
Appends container audits and node decisions from a compact JSON:
{"source": "...", "containers": [{"unit": "A123", "chain": "play>act", "decision": "include|exclude", "role": "", "basis": "..."}],
 "nodes": [{"unit": "A123", "seqs": [1,2], "decision": "include|exclude", "role": "", "category": "", "basis": "...", "language": ""}]}
Containers use the unit's unit_node_path + exact div_path_filter.  Node seqs are resolved to (source_sha256, node_path) via lines.csv
and text_sha256 is recorded.  Refuses duplicate keys.  Prints what it added."""
import csv,json,sys,os,hashlib,datetime
csv.field_size_limit(10**9)
HERE=os.path.dirname(os.path.abspath(__file__)); D=json.load(open(sys.argv[1],encoding='utf-8'))
today=datetime.date.today().isoformat(); src=D.get('source','Claude content audit '+today+' (performance-language policy, Grace 2026-09-07)')
um={r['unit_id']:r for r in csv.DictReader(open(os.path.join(HERE,'out','unit_map.csv'),encoding='utf-8'))}
# containers
cp=os.path.join(HERE,'container_audits.csv'); crows=list(csv.DictReader(open(cp,encoding='utf-8'))); cf=list(crows[0].keys())
have={(r['source_sha256'],r['container_node_path'],r['div_path_filter']) for r in crows}; nc=0
for c in D.get('containers',[]):
    u=um[c['unit']]; k=(u['source_sha256'],u['unit_node_path'],c['chain'])
    if k in have: print('SKIP existing container',c['unit'],c['chain']); continue
    crows.append({'source_sha256':u['source_sha256'],'unit_id':c['unit'],'container_node_path':u['unit_node_path'],'div_path_filter':c['chain'],'decision_default':c['decision'],
      'text_role_default':c.get('role',''),'expected_candidate_nodes':c.get('n',''),'basis':c['basis'],'source':c.get('source',src),'status':'applied','decided_on':today}); have.add(k); nc+=1
with open(cp,'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=cf); w.writeheader(); w.writerows(crows)
# nodes
np_=os.path.join(HERE,'body_node_decisions.csv'); nrows=list(csv.DictReader(open(np_,encoding='utf-8'))); nf=list(nrows[0].keys())
nhave={(r['source_sha256'],r['node_path']) for r in nrows}
want={}; ranges=[]
for n in D.get('nodes',[]):
    for s in n.get('seqs',[]): want[(n['unit'],str(s))]=n
    if 'seq_range' in n: ranges.append(n)
found={}
if want or ranges:
    for L in csv.DictReader(open(os.path.join(HERE,'out','lines.csv'),encoding='utf-8')):
        k=(L['unit_id'],L['seq'])
        for n in ranges:   # selector: unit + seq range + optional parent / parent_not
            if L['unit_id']==n['unit'] and n['seq_range'][0]<=int(L['seq'])<=n['seq_range'][1] and (not n.get('parent') or L['parent']==n['parent']) and (not n.get('parent_not') or L['parent']!=n['parent_not']):
                want.setdefault(k,n)
        if k in want: found[k]=L
nn=0
for k,n in want.items():
    if k not in found: print('!! seq not found',k); continue
    L=found[k]; key=(L['source_sha256'],L['node_path'])
    if key in nhave: print('SKIP existing node',k); continue
    nrows.append({'source_sha256':L['source_sha256'],'node_path':L['node_path'],'unit_id':L['unit_id'],'seq':L['seq'],'div_path':L['div_path'],'container_node_path':um[L['unit_id']]['unit_node_path'],
      'text_sha256':hashlib.sha256(L['text'].encode()).hexdigest(),'decision':n['decision'],'text_role':n.get('role','') if n['decision']=='include' else '','language':n.get('language',''),
      'exclusion_category':n.get('category','') if n['decision']=='exclude' else '','basis':n['basis']+f" [text: {L['text'][:60]!r}]",'source':n.get('source',src),'status':'applied','decided_on':today,
      'decision_basis_type':'editorial_function_assessment','historical_performance_status':'','xml_language_raw':''}); nhave.add(key); nn+=1
with open(np_,'w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=nf); w.writeheader(); w.writerows(nrows)
print(f'added containers {nc}, node decisions {nn}')
