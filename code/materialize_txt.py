#!/usr/bin/env python3
"""
materialize_txt.py --rule {structural,sp_only}

Turns out/lines.csv into out/units_<rule>/<unit_id>.txt so the D3 decision ("what counts as
dialogue") is an explicit switch, not something buried in extraction.

  sp_only     : only lines inside <sp>
  structural  : keep if inside <sp>; else decide by the INNERMOST div type first:
                  performance frame (prologue, epilogue, chorus, song, induction, act, scene,
                  speech, dumb_show)                          -> keep
                  otherwise any non-dialogue div type on the path (argument, dramatis_personae,
                  dedication, title_page, colophon, poems...)  -> drop
                  otherwise                                    -> keep
Both are CANDIDATE rules.  Writes out/rule_report_<rule>.csv (chars kept/dropped per unit).
"""
import os, csv, argparse
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
NONDRAM_DIVS = {'argument', 'dramatis_personae', 'dedication', 'to_the_reader', 'title_page', 'colophon', 'list_of_actors',
                'table_of_contents', 'encomium', 'epistle', 'errata', 'commendatory_verses', 'illustration', 'description',
                'descriptions', 'inscription', 'stationer_to_the_reader', 'imprimatur', 'license', 'advertisement', 'poems', 'poem'}
PERF_DIVS = {'prologue', 'epilogue', 'chorus', 'song', 'induction', 'act', 'scene', 'speech', 'dumb_show', 'act_and_scene'}
ap = argparse.ArgumentParser(); ap.add_argument('--rule', choices=['structural', 'sp_only'], default='structural')
rule = ap.parse_args().rule
def keep(r):
    if r['in_sp'] == '1': return True
    if rule == 'sp_only': return False
    path = [d for d in r['div_path'].split('>') if d]
    if path and path[-1] in PERF_DIVS: return True
    if any(d in NONDRAM_DIVS for d in path): return False
    return True
udir = os.path.join(OUT, f'units_{rule}'); os.makedirs(udir, exist_ok=True)
kept = defaultdict(list); stats = defaultdict(lambda: [0, 0])
csv.field_size_limit(10**9)
with open(os.path.join(OUT, 'lines.csv'), newline='', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        if keep(r): kept[r['unit_id']].append(r['text']); stats[r['unit_id']][0] += int(r['n_chars'])
        else: stats[r['unit_id']][1] += int(r['n_chars'])
for uid, lines in kept.items():
    with open(os.path.join(udir, uid + '.txt'), 'w', encoding='utf-8') as f: f.write('\n'.join(lines))
with open(os.path.join(OUT, f'rule_report_{rule}.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['unit_id', 'chars_kept', 'chars_dropped'])
    for uid in sorted(stats): w.writerow([uid, *stats[uid]])
tk = sum(v[0] for v in stats.values()); td = sum(v[1] for v in stats.values())
print(f'rule={rule}: {len(kept)} non-empty units; kept {tk:,} chars, dropped {td:,} chars -> {udir}')
