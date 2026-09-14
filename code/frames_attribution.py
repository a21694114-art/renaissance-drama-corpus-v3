#!/usr/bin/env python3
"""
frames_attribution.py — attribute <front>/<back> candidate lines to works.

Each front/back line carries the xpath of the <text> element it belongs to. If that <text>
is the text of exactly one mapped unit (single playbook, or one inner text of a <group>),
its performance frames (prologue / epilogue / induction / chorus / song / speech) are
candidates FOR THAT WORK.  If the <text> is a collection-level wrapper whose body holds
several works (the Folio), its front/back is paratext of the volume and is never copied to
any play.  Nothing is included here; this produces the candidate table for review.
Writes out/frames_attribution.csv (one row per (tcp, text, section, innermost div type)).
"""
import os, csv
from collections import defaultdict
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=os.path.join(HERE,'out')
csv.field_size_limit(10**9)
PERF={'prologue','epilogue','induction','chorus','song','speech','dumb_show','argument_in_verse'}
umap=list(csv.DictReader(open(os.path.join(OUT,'unit_map.csv'),encoding='utf-8')))
# text xpath -> units under it (unit_node_path starts with text path + '/')
by_text=defaultdict(list)
for r in umap:
    p=r['unit_node_path']
    # the <text> element is the ancestor path ending before '/*[2]' (body) — derive by walking up until a path that is a prefix of a frontback text path; simpler: collect all and test prefix
    by_text[r['tcp']].append(r)
agg=defaultdict(lambda:{'lines':0,'chars':0,'in_sp':0})
for r in csv.DictReader(open(os.path.join(OUT,'frontback_lines.csv'),encoding='utf-8')):
    inner=r['div_path'].split('>')[-1] if r['div_path'] else '(no div)'
    k=(r['tcp'],r['text_node_path'],r['section'],inner)
    a=agg[k]; a['lines']+=1; a['chars']+=int(r['n_chars']); a['in_sp']+=int(r['in_sp'])
rows=[]
for (tcp,tpath,section,inner),a in sorted(agg.items()):
    units=[u for u in by_text[tcp] if u['unit_node_path'].startswith(tpath+'/') or u['unit_node_path']==tpath]
    works=sorted({u['old_id'] for u in units if u['old_id'] and u['relation'] in ('primary','component')})
    if len(works)==1: attr=works[0]; scope='single work'
    elif len(works)==0: attr=''; scope='no mapped work under this <text>'
    else: attr=''; scope=f'collection-level ({len(works)} works) - volume paratext, never copied to plays'
    cand='candidate' if (inner in PERF or a['in_sp']) else 'paratext'
    if cand=='candidate': incl='pending' if attr else 'pending_unattributed'      # never auto-exclude performance text
    else: incl='excluded_proposed'
    role=inner if inner in PERF else ('paratext' if cand=='paratext' else 'performance_other')
    rows.append({'tcp':tcp,'text_node_path':tpath,'section':section,'innermost_div':inner,'text_role':role,'lines':a['lines'],'chars':a['chars'],'lines_in_sp':a['in_sp'],
                 'attributed_work(old_id)':attr,'scope':scope,'frame_class':cand,'inclusion_status':incl,
                 'note':'' if attr or cand!='candidate' else ('attribution pending: parent text has no mapped work yet' if not works else 'shared/volume-level frame: verify which work it addresses; never copied to several plays')})
with open(os.path.join(OUT,'frames_attribution.csv'),'w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
from collections import Counter
c=Counter((r['frame_class'],r['scope'].split(' (')[0],r['inclusion_status']) for r in rows)
print('front/back groups:',len(rows)); [print('  ',k,v) for k,v in c.most_common()]
one=[r for r in rows if r['inclusion_status']=='pending']; una=[r for r in rows if r['inclusion_status']=='pending_unattributed']
print('performance-frame candidates attributable to ONE work:',len(one),'groups;',sum(r['chars'] for r in one),'chars; by div:',Counter(r['innermost_div'] for r in one).most_common(8))
print('performance-frame candidates NOT yet attributable (pending_unattributed, never excluded):',len(una),'groups;',sum(r['chars'] for r in una),'chars')
