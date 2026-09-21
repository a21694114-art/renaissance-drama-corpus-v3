#!/usr/bin/env python3
"""08b_apply_review.py — carry Grace's decisions from topic_sheet.xlsx into the files the pipeline reads.

    python 08b_apply_review.py --runs <runs dir> --seed 42 [--xlsx <topic_sheet.xlsx>] [--drafts <csv>]

Everything downstream (09_aggregate, 11_figures, 12_map, 13_site, 14_genre_figures) reads
topics_B_s<seed>/topic_sheet.csv, not the workbook.  This script reads the 'topics' sheet of the
workbook, takes the review columns — Label, Notes, use_in_genre_analysis, pattern_basis, basis,
review_status, chunks_read, draft_label — and

  1. writes them into topic_sheet.csv (all other columns untouched);
  2. writes them into ab_spelling/drafts/topic_drafts_B_s<seed>.csv, so that re-running
     `run_b.sh sheet` later rebuilds the workbook WITH the decisions instead of the AI drafts.

A row counts as reviewed by Grace when its Label is filled or its use_in_genre_analysis differs from
the draft file; its review_status then becomes user_confirmed unless she set another value herself.
Values of use_in_genre_analysis are checked against {included, candidate, contextual_only, pending}.
"""
import argparse, csv, shutil
from pathlib import Path

USE_VALUES = {'included', 'candidate', 'contextual_only', 'pending'}
REVIEW_COLS = ['draft_label', 'pattern_basis', 'use_in_genre_analysis', 'basis', 'review_status', 'chunks_read', 'Label', 'Notes']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--runs', required=True); ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--xlsx', default=''); ap.add_argument('--drafts', default='')
    a = ap.parse_args()
    d = Path(a.runs) / f'topics_{a.variant}_s{a.seed}'
    xlsx = Path(a.xlsx) if a.xlsx else d / 'topic_sheet.xlsx'
    dpath = Path(a.drafts) if a.drafts else Path(__file__).resolve().parent.parent / 'drafts' / f'topic_drafts_{a.variant}_s{a.seed}.csv'

    import openpyxl
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb['topics'] if 'topics' in wb.sheetnames else wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True); header = [str(h).strip() if h is not None else '' for h in next(it)]
    col = {h: i for i, h in enumerate(header)}
    missing = [c for c in ['topic'] + REVIEW_COLS if c not in col]
    if missing: raise SystemExit(f'workbook lacks columns {missing}')
    edited = {}
    for row in it:
        if row is None or row[col['topic']] in (None, ''): continue
        t = int(row[col['topic']])
        edited[t] = {c: ('' if row[col[c]] is None else str(row[col[c]]).strip()) for c in REVIEW_COLS}

    old_drafts = {}
    if dpath.exists():
        old_drafts = {int(r['topic']): r for r in csv.DictReader(open(dpath, encoding='utf-8'))}

    bad = {t: e['use_in_genre_analysis'] for t, e in edited.items() if e['use_in_genre_analysis'] and e['use_in_genre_analysis'] not in USE_VALUES}
    if bad: raise SystemExit(f'use_in_genre_analysis must be one of {sorted(USE_VALUES)}; found {bad}')

    n_conf = 0
    for t, e in edited.items():
        draft_use = old_drafts.get(t, {}).get('use_in_genre_analysis', '')
        reviewed = bool(e['Label']) or (e['use_in_genre_analysis'] and e['use_in_genre_analysis'] != draft_use)
        if reviewed and e['review_status'] in ('', 'draft_ai', 'checked_ai'):
            e['review_status'] = 'user_confirmed'
        if e['review_status'] == 'user_confirmed': n_conf += 1

    # 1. topic_sheet.csv
    sp = d / 'topic_sheet.csv'; shutil.copy(sp, sp.with_suffix('.csv.bak'))
    rows = list(csv.DictReader(open(sp, encoding='utf-8'))); fields = list(rows[0].keys())
    for r in rows:
        e = edited.get(int(r['topic']))
        if e:
            for c in REVIEW_COLS:
                if c in r: r[c] = e[c]
    with open(sp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    # 2. drafts file (now carrying the decisions)
    dpath.parent.mkdir(parents=True, exist_ok=True)
    if dpath.exists(): shutil.copy(dpath, dpath.with_suffix('.csv.bak'))
    with open(dpath, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['topic'] + REVIEW_COLS)
        for t in sorted(edited): w.writerow([t] + [edited[t][c] for c in REVIEW_COLS])

    from collections import Counter
    uses = Counter(e['use_in_genre_analysis'] or 'unclassified' for e in edited.values())
    print(f'{len(edited)} topics read from {xlsx.name}; {n_conf} user_confirmed; labels filled: {sum(1 for e in edited.values() if e["Label"])}')
    print('use_in_genre_analysis:', ', '.join(f'{k} {v}' for k, v in uses.most_common()))
    print(f'→ {sp}\n→ {dpath}  (backups *.csv.bak)')


if __name__ == '__main__':
    main()
