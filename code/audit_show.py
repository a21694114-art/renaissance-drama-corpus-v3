#!/usr/bin/env python3
"""audit_show.py UNIT [UNIT...] [--all] [--chain CHAIN] [--head N] [--tail N]
Prints the function-audit PENDING nodes of a unit (rule-kept, outside <sp>, no node decision, no applied container audit),
grouped by div chain, with seq, parent element, language, xpath tail, head/tail of the text.  Verse (parent lg) rows are
summarised with 3 samples unless --all."""
import csv,sys,os,argparse
csv.field_size_limit(10**9)
ap=argparse.ArgumentParser(); ap.add_argument('units',nargs='+'); ap.add_argument('--all',action='store_true'); ap.add_argument('--chain',default=None); ap.add_argument('--head',type=int,default=150); ap.add_argument('--tail',type=int,default=60)
A=ap.parse_args()
HERE=os.path.dirname(os.path.abspath(__file__))
nd={(r['source_sha256'],r['node_path']) for r in csv.DictReader(open(os.path.join(HERE,'body_node_decisions.csv'),encoding='utf-8'))}
aud=[r for r in csv.DictReader(open(os.path.join(HERE,'container_audits.csv'),encoding='utf-8')) if r['status'].startswith('applied') and r['decision_default'] in ('include','exclude')] if os.path.exists(os.path.join(HERE,'container_audits.csv')) else []
nl={}
NON={'argument','dramatis_personae','dedication','to_the_reader','title_page','colophon','list_of_actors','table_of_contents','encomium','epistle','errata','commendatory_verses','illustration','description','descriptions','inscription','stationer_to_the_reader','imprimatur','license','advertisement'}
units=set(A.units)
for r in csv.DictReader(open(os.path.join(HERE,'out','node_language.csv'),encoding='utf-8')):
    if r['xml_lang_effective'] not in ('','en','unk'): nl[(r['source_sha256'],r['node_path'])]=r['xml_lang_effective']
from collections import defaultdict
groups=defaultdict(list)
for L in csv.DictReader(open(os.path.join(HERE,'out','lines.csv'),encoding='utf-8')):
    if L['unit_id'] not in units or L['in_sp']=='1': continue
    k=(L['source_sha256'],L['node_path'])
    if k in nd: continue
    p=[x for x in L['div_path'].split('>') if x]
    if any(x in NON for x in p) or any(x in ('poem','poems') for x in p): continue
    if any(a['unit_id']==L['unit_id'] and L['node_path'].startswith(a['container_node_path']) and (not a['div_path_filter'] or a['div_path_filter']==L['div_path']) for a in aud): continue
    if A.chain is not None and L['div_path']!=A.chain: continue
    groups[(L['unit_id'],L['div_path'])].append(L)
for (u,dp),Ls in sorted(groups.items()):
    print(f"===== {u} [{dp}] {len(Ls)} nodes {sum(int(x['n_chars']) for x in Ls)} chars")
    verse=[x for x in Ls if x['parent']=='lg']; other=[x for x in Ls if x['parent']!='lg']
    if verse and not A.all:
        print(f"  (verse lg: {len(verse)} nodes, seq {verse[0]['seq']}-{verse[-1]['seq']}) "+' | '.join(x['text'][:70] for x in verse[:3]))
        other=other
    for x in (Ls if A.all else other):
        t=x['text']; lang=nl.get((x['source_sha256'],x['node_path']),'')
        body=t if len(t)<=A.head+A.tail+10 else t[:A.head]+' ... '+t[-A.tail:]
        print(f"  s{x['seq']} {x['parent']}{'/'+lang if lang else ''} {len(t)}c {x['node_path'].split('/')[-1]}: {body}")
