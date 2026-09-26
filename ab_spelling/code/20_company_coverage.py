#!/usr/bin/env python3
"""
20_company_coverage.py — coverage of playing-company, theatre and date metadata for the
works of the frozen run (step 1 of the company exploration; no comparison, no interpretation).

Inputs (all existing files; nothing is recomputed):
  * aggregate/work_topic_share.csv   — the works of the run (one representative edition each,
                                        genre_main, cat:included share); made by 09_aggregate.py
  * chunk_meta.csv                   — edition_id → deep_id of the representative edition
  * DEEP_data.csv                    — the DEEP export (company, theatre, play type, dates)

DEEP row selection. DEEP has several rows for some editions (playbook / play-in-collection
records). For each work the row whose deep_id equals the deep_id recorded in chunk_meta for
the representative edition is used; the other rows of that edition are only inspected to
report whether their company / date / play-type fields differ (column deep_alt_rows_differ).
69 rows of the export carry one extra field (an unquoted comma in a collection link); they are
realigned by anchoring title_id == id, and flagged (deep_row_realigned = Y).

Sources are kept apart and never mixed: the British Drama first-performance company
(company_first_performance_brit_display), the Annals first-performance company
(company_first_performance_annals_display) and the title-page company
(title_page_company_display) each get their own columns and their own coverage rows.
Raw strings are kept verbatim; base_name only removes '(?)', '(by 1594)'-type qualifiers,
'(on tour)/(in London)' and curly apostrophes, so that variants can be seen — nothing is
merged, and historical renamings (Chamberlain's → King's, …) are listed in
company_lineage_notes.csv as reference notes only, used in no count.

Status of a company value: clear | uncertain ('(?)' on a single name) | multiple (';', ' and ',
' or ', ', then ') | unacted | unknown | not in BritDrama | missing (blank / n/a / None).

Dates: Annals date_first_performance (always a year; brackets give limits, 'c.', '(?)',
months, 'licensed', 'revised' are kept as flags) and British Drama
date_first_performance_brit_display (year + limits; 'not in BritDrama' = missing) are parsed
separately; date_first_publication is a separate column and is never substituted for a
performance date. For closet / unacted works the Annals date is a composition date by that
source's convention; play_type_display is kept beside it so the reader can tell.

Outputs (--out, default <agg>/company/):
  company_fields_by_work.csv     one row per work: raw fields, statuses, parsed dates
  company_coverage.csv           one row per (source, raw company value): n works, genre
                                 composition, authors, date ranges of the corpus records,
                                 missing / uncertain / multiple counts, mean included share
  company_name_notes.csv         raw spellings grouped by base_name (variants to check)
  company_lineage_notes.csv      reference notes on renamings / successions (not applied)
  company_source_agreement.csv   per work: do the three company sources agree?
  theatre_coverage.csv           venue / performance-context tokens → works, companies
  deep_row_selection.csv         which DEEP row was used per work and why
  company_coverage_summary.md    totals, status counts, largest companies
"""
import argparse, csv, collections, json, re, statistics
from pathlib import Path

GENRES = ['comedy', 'tragedy', 'history', 'tragicomedy', 'moral', 'masque', 'pastoral', 'romance', 'interlude', 'other/multi']
DEEP_FIELDS = ['company_first_performance_brit_display', 'company_first_performance_brit_filter',
               'company_first_performance_annals_display', 'company_first_performance_annals_filter',
               'title_page_company_display', 'title_page_company_filter',
               'play_type_display', 'play_type_filter', 'theater', 'theater_type',
               'date_first_performance', 'date_first_performance_filter',
               'date_first_performance_brit_display', 'date_first_performance_brit_filter',
               'date_first_publication', 'date_first_publication_display',
               'genre_brit_display', 'genre_annals_display', 'record_type', 'year']
COMPARE_FIELDS = ['company_first_performance_brit_display', 'company_first_performance_annals_display',
                  'title_page_company_display', 'play_type_display', 'theater',
                  'date_first_performance', 'date_first_performance_brit_display', 'date_first_publication']
MONTHS = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*'
SEASONS = r'spring|summer|autumn|winter|Christmas|Lent|Shrovetide|New Year|early|late'
REVISION = r'revis|adapt|re-licensed|interpolat|prologue|Act \d|poss\. written|written'


def read_deep(path):
    """DEEP export with realignment of rows that carry an extra field (unquoted comma)."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f); hdr = next(rd); n = len(hdr); ti = hdr.index('title_id')
        rows = []
        for row in rd:
            k = len(row) - n; realigned = False
            if k > 0:
                js = [j for j in range(ti, ti + k + 1) if row[j] == row[0]]
                if not js or js[-1] - ti != k:
                    raise SystemExit(f'DEEP row {row[:2]} has {k} extra field(s) and cannot be realigned')
                s = js[-1] - ti
                row = row[:ti] + row[ti + s:ti + s + (n - ti)]; realigned = True
            elif k < 0:
                row = row + [''] * (-k)
            d = dict(zip(hdr, row)); d['_realigned'] = realigned; rows.append(d)
    return rows


def authors_of(v):
    return [p.strip() for p in re.split(r';\s*|(?<=[a-z])(?=[A-Z][a-z]+, )', v or '') if p.strip()]


def norm_apos(s):
    return s.replace('’', "'").replace('‘', "'")


def company_status(raw):
    """(status, base_name, qualifiers, components) for one raw company string."""
    s = norm_apos(raw or '').strip()
    s = re.sub(r'\s*\(and ([^)]*?)\s*\[\?\]\)', r'; \1 (?)', s)
    if s == '':
        return 'missing (blank)', '', '', []
    if s.lower() == 'n/a':
        return 'missing (n/a)', '', '', []
    if s == 'None':
        return 'missing (None)', '', '', []
    if s == 'not in BritDrama':
        return 'not in BritDrama', '', '', []
    if re.match(r'^Unknown', s):
        return 'unknown', 'Unknown', s[len('Unknown'):].strip(), []
    if re.match(r'^Unacted', s):
        return 'unacted', 'Unacted', '(?)' if '(?)' in s else '', []
    quals = re.findall(r'\((?:\?|by \d{4}|on tour|in London)\)|\[\?\]', s)
    base = re.sub(r'\s*\((?:\?|by \d{4}|on tour|in London)\)', '', s)
    base = re.sub(r'\s*\[\?\]', '', base)
    base = re.sub(r'\)\(', ') (', base)
    base = re.sub(r'\s+', ' ', base).strip()
    parts = [p.strip() for p in re.split(r';|\band\b|\bor\b|,\s*then\b', base) if p.strip()]
    kinds = []
    if ';' in base: kinds.append(';')
    if re.search(r'\band\b', base): kinds.append('and')
    if re.search(r'\bor\b', base): kinds.append('or')
    if re.search(r',\s*then\b', base): kinds.append('then')
    if len(parts) > 1 or kinds:
        return 'multiple (' + '/'.join(kinds) + ')', base, ' '.join(quals), parts
    if '(?)' in s or '[?]' in s:
        return 'uncertain', base, ' '.join(quals), parts
    return 'clear', base, ' '.join(quals), parts


def tokens(base):
    return frozenset(t for t in re.findall(r'[a-z0-9]+', norm_apos(base).lower().replace("'s", 's')) if t not in ('of', 'the'))


def parse_date(raw, source):
    """Year point, limits and qualifier flags of an Annals or British Drama date string."""
    s = norm_apos(raw or '').strip()
    out = {'raw': s, 'year': '', 'low': '', 'high': '', 'flags': '', 'missing': ''}
    if s == '' or s.lower() in ('n/a', 'nan', 'none') or s == 'not in BritDrama':
        out['missing'] = s if s else 'blank'; return out
    m = re.search(r'\d{4}', s)
    if not m:
        out['missing'] = 'no year: ' + s; return out
    out['year'] = int(m.group())
    flags = []
    if re.match(r'^c\.\s*\d{4}', s): flags.append('circa')
    head = s.split('[')[0]
    if '?' in head: flags.append('queried')
    brs = re.findall(r'\[([^\]]*)\]', s)
    lows, highs = [], []
    for b in brs:
        if 'incorrect' in b: flags.append('marked-incorrect')
        for seg in re.split(r';', b):
            revision = re.search(REVISION, seg, re.I) is not None
            rngs = re.findall(r'(c\.)?\s*(\d{4})\s*(\(\?\))?\s*-\s*(c\.)?\s*(\d{4})\s*(\(\?\))?', seg)
            if rngs and revision:
                flags.append('secondary-dates-ignored')
            elif rngs:
                for r in rngs:
                    lows.append(int(r[1])); highs.append(int(r[4]))
                    if r[0] or r[3]: flags.append('circa-limit')
                    if r[2] or r[5]: flags.append('queried-limit')
                if len(rngs) > 1 or re.search(r'\bor\b', seg): flags.append('alternative-limits')
        if re.search(r'\b' + MONTHS + r'\b', b): flags.append('month')
        if re.search(r'\b(' + SEASONS + r')\b', b, re.I): flags.append('season')
        if 'licensed' in b: flags.append('licensed')
        if re.search(r'revis|adapt', b): flags.append('revised')
        if 'payment' in b: flags.append('payment')
        if re.search(r'\d{4}s', b): flags.append('decade')
        if '?' in b and not re.search(r'\d{4}\s*\(\?\)', b): flags.append('queried-bracket')
    if lows:
        out['low'] = min(lows); out['high'] = max(highs)
    seen = []
    for f in flags:
        if f not in seen: seen.append(f)
    out['flags'] = ' '.join(seen)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agg', required=True, help='aggregate/ directory of the run (work_topic_share.csv)')
    ap.add_argument('--chunk-meta', required=True)
    ap.add_argument('--deep', required=True, help='DEEP_data.csv')
    ap.add_argument('--out', default='', help='default <agg>/company')
    a = ap.parse_args()
    agg = Path(a.agg); out = Path(a.out) if a.out else agg / 'company'; out.mkdir(parents=True, exist_ok=True)

    works = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8-sig')))
    cm = {}
    for r in csv.DictReader(open(a.chunk_meta, encoding='utf-8-sig')):
        cm.setdefault(r['edition_id'], r)
    deep = read_deep(a.deep)
    by_ed = collections.defaultdict(list)
    for r in deep: by_ed[r['edition_id']].append(r)

    # ---- per-work rows -------------------------------------------------------------------
    rows, sel_rows = [], []
    for w in works:
        eid = w['editions']; meta = cm[eid]; did = meta['deep_id']
        cands = by_ed.get(eid, [])
        chosen = next((x for x in cands if x['deep_id'] == did), None)
        basis = 'deep_id match'
        if chosen is None and cands:
            chosen = cands[0]; basis = 'no deep_id match — first DEEP row of the edition'
        if chosen is None:
            chosen = {k: '' for k in DEEP_FIELDS}; chosen['_realigned'] = False; basis = 'no DEEP row for this edition'
        alt = [x for x in cands if x is not chosen]
        differ = [f for f in COMPARE_FIELDS if any(norm_apos(x.get(f, '')) != norm_apos(chosen.get(f, '')) for x in alt)]
        sel_rows.append({'work_id': w['work_id'], 'title': w['title'], 'edition_id': eid, 'deep_id_chunk_meta': did,
                         'deep_rows_for_edition': len(cands), 'deep_id_used': chosen.get('deep_id', ''),
                         'record_type_used': chosen.get('record_type', ''), 'basis': basis,
                         'deep_row_realigned': 'Y' if chosen.get('_realigned') else '',
                         'alt_deep_ids': '; '.join(x['deep_id'] for x in alt),
                         'alt_rows_differ_in': '; '.join(differ)})
        st_b, base_b, q_b, parts_b = company_status(chosen['company_first_performance_brit_display'])
        st_a, base_a, q_a, parts_a = company_status(chosen['company_first_performance_annals_display'])
        st_t, base_t, q_t, parts_t = company_status(chosen['title_page_company_display'])
        da = parse_date(chosen['date_first_performance'], 'annals')
        db = parse_date(chosen['date_first_performance_brit_display'], 'brit')
        pub = chosen['date_first_publication'].strip()
        ptype = chosen['play_type_display']
        pt_flag = 'closet/unacted (per play_type)' if re.search(r'Closet|Unacted', ptype) else ''
        r = {'work_id': w['work_id'], 'title': w['title'], 'author': ' / '.join(authors_of(w['author'])), 'genre_main': w['genre_main'],
             'genre_source': w['genre_source'], 'genre_britdrama': w['genre_deep'], 'genre_annals': w['genre_annals'],
             'edition_id': eid, 'edition_year': meta['year'], 'deep_id': chosen.get('deep_id', ''), 'deep_row_basis': basis,
             'deep_row_realigned': 'Y' if chosen.get('_realigned') else '', 'deep_alt_rows_differ': '; '.join(differ),
             'company_brit_raw': chosen['company_first_performance_brit_display'], 'company_brit_status': st_b,
             'company_brit_base': base_b, 'company_brit_qualifiers': q_b, 'company_brit_components': ' | '.join(parts_b) if len(parts_b) > 1 else '',
             'company_annals_raw': chosen['company_first_performance_annals_display'], 'company_annals_status': st_a,
             'company_annals_base': base_a, 'company_annals_qualifiers': q_a, 'company_annals_components': ' | '.join(parts_a) if len(parts_a) > 1 else '',
             'company_titlepage_raw': chosen['title_page_company_display'], 'company_titlepage_status': st_t,
             'company_titlepage_base': base_t, 'company_titlepage_components': ' | '.join(parts_t) if len(parts_t) > 1 else '',
             'play_type_raw': ptype, 'play_type_main': w['play_type_main'], 'closet_or_unacted_flag': pt_flag,
             'theater_raw': chosen['theater'], 'theater_type_raw': chosen['theater_type'],
             'date_annals_raw': da['raw'], 'date_annals_year': da['year'], 'date_annals_low': da['low'], 'date_annals_high': da['high'],
             'date_annals_flags': da['flags'], 'date_annals_missing': da['missing'],
             'date_brit_raw': db['raw'], 'date_brit_year': db['year'], 'date_brit_low': db['low'], 'date_brit_high': db['high'],
             'date_brit_flags': db['flags'], 'date_brit_missing': db['missing'],
             'date_annals_vs_brit': ('' if da['year'] == '' or db['year'] == '' else ('same year' if da['year'] == db['year'] else f'differ by {abs(da["year"] - db["year"])}')),
             'date_publication_raw': pub, 'date_publication_display_raw': chosen['date_first_publication_display'],
             'year_first_in_run': w['year_first'], 'words_mean': w['words_mean'], 'included_share': w['cat:included'],
             'outlier_share': w.get('cat:outlier_hdbscan', '')}
        rows.append(r)
    with open(out / 'company_fields_by_work.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    with open(out / 'deep_row_selection.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(sel_rows[0].keys())); wr.writeheader(); wr.writerows(sel_rows)

    # ---- coverage per (source, raw value) ---------------------------------------------------
    def fmt_comp(counter, order=None):
        items = sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        return '; '.join(f'{k} {v}' for k, v in items)

    def yr_stats(vals):
        vals = [v for v in vals if v != '']
        return (min(vals), max(vals)) if vals else ('', '')

    sources = [('britdrama', 'company_brit'), ('annals', 'company_annals'), ('title_page', 'company_titlepage')]
    cov = []
    mentions = {s: collections.defaultdict(set) for s, _ in sources}   # base component → works mentioned in multiples
    for src, col in sources:
        for r in rows:
            if r[col + '_components']:
                for p in r[col + '_components'].split(' | '):
                    mentions[src][p].add(r['work_id'])
    for src, col in sources:
        groups = collections.defaultdict(list)
        for r in rows: groups[r[col + '_raw']].append(r)
        for raw, rs in groups.items():
            st = rs[0][col + '_status']; base = rs[0][col + '_base']
            gc = collections.Counter(r['genre_main'] for r in rs)
            ac = collections.Counter(r['author'] for r in rs)
            top_a, top_n = ac.most_common(1)[0]
            ay = [r['date_annals_year'] for r in rs]; by = [r['date_brit_year'] for r in rs]
            alow = [r['date_annals_low'] if r['date_annals_low'] != '' else r['date_annals_year'] for r in rs]
            ahigh = [r['date_annals_high'] if r['date_annals_high'] != '' else r['date_annals_year'] for r in rs]
            blow = [r['date_brit_low'] if r['date_brit_low'] != '' else r['date_brit_year'] for r in rs]
            bhigh = [r['date_brit_high'] if r['date_brit_high'] != '' else r['date_brit_year'] for r in rs]
            py = [int(r['date_publication_raw']) for r in rs if re.fullmatch(r'\d{4}', r['date_publication_raw'])]
            inc = [float(r['included_share']) for r in rs]
            d = {'source': src, 'company_raw': raw, 'status': st, 'base_name': base, 'n_works': len(rs)}
            for g in GENRES: d['n_' + g] = gc.get(g, 0)
            d.update({'genre_composition': fmt_comp(gc), 'n_authors': len(ac), 'top_author': top_a, 'top_author_n_works': top_n,
                      'top_author_share': round(top_n / len(rs), 3),
                      'play_type_composition': fmt_comp(collections.Counter(r['play_type_raw'] for r in rs)),
                      'n_closet_or_unacted_playtype': sum(1 for r in rs if r['closet_or_unacted_flag']),
                      'annals_year_min': yr_stats(ay)[0], 'annals_year_max': yr_stats(ay)[1],
                      'annals_limits_min': yr_stats(alow)[0], 'annals_limits_max': yr_stats(ahigh)[1],
                      'annals_year_median': (statistics.median([v for v in ay if v != '']) if any(v != '' for v in ay) else ''),
                      'n_annals_date_missing': sum(1 for r in rs if r['date_annals_missing']),
                      'n_annals_with_limits': sum(1 for r in rs if r['date_annals_low'] != ''),
                      'n_annals_circa_or_queried': sum(1 for r in rs if re.search(r'circa|queried', r['date_annals_flags'])),
                      'n_annals_licensed_or_revised': sum(1 for r in rs if re.search(r'licensed|revised', r['date_annals_flags'])),
                      'brit_year_min': yr_stats(by)[0], 'brit_year_max': yr_stats(by)[1],
                      'brit_limits_min': yr_stats(blow)[0], 'brit_limits_max': yr_stats(bhigh)[1],
                      'n_brit_date_missing': sum(1 for r in rs if r['date_brit_missing']),
                      'n_brit_with_limits': sum(1 for r in rs if r['date_brit_low'] != ''),
                      'n_brit_circa_or_queried': sum(1 for r in rs if re.search(r'circa|queried', r['date_brit_flags'])),
                      'n_dates_annals_brit_differ': sum(1 for r in rs if r['date_annals_vs_brit'].startswith('differ')),
                      'publication_year_min': min(py) if py else '', 'publication_year_max': max(py) if py else '',
                      'mean_included_share': round(sum(inc) / len(inc), 4), 'min_included_share': round(min(inc), 4), 'max_included_share': round(max(inc), 4),
                      'n_works_mentioned_in_multiple_values': len(mentions[src].get(base, set())) if base and not st.startswith('multiple') else '',
                      'works': '; '.join(sorted(r['title'][:40] + ' (' + r['work_id'] + ')' for r in rs)) if len(rs) <= 12 else ''})
            for s2, c2 in sources:
                d[f'n_same_raw_in_{s2}'] = '' if s2 == src else sum(1 for r in rs if r[c2 + '_raw'] == raw)
                d[f'n_same_base_in_{s2}'] = '' if s2 == src else sum(1 for r in rs if base and r[c2 + '_base'] == base)
            cov.append(d)
    order = {'clear': 0, 'uncertain': 1, 'multiple': 2, 'unacted': 3, 'unknown': 4, 'not in BritDrama': 5, 'missing': 6}
    cov.sort(key=lambda d: (['britdrama', 'annals', 'title_page'].index(d['source']), order.get(d['status'].split(' ')[0], 9), -d['n_works'], d['company_raw']))
    with open(out / 'company_coverage.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(cov[0].keys())); wr.writeheader(); wr.writerows(cov)

    # ---- name notes: raw spellings per base name and loose key --------------------------------
    notes = collections.defaultdict(lambda: {'raw': collections.Counter(), 'sources': set()})
    for src, col in sources:
        for r in rows:
            if r[col + '_base'] and r[col + '_status'] in ('clear', 'uncertain'):
                notes[r[col + '_base']]['raw'][(src, r[col + '_raw'])] += 1; notes[r[col + '_base']]['sources'].add(src)
            for p in (r[col + '_components'].split(' | ') if r[col + '_components'] else []):
                notes[p]['raw'][(src, '[in multiple] ' + r[col + '_raw'])] += 1; notes[p]['sources'].add(src)
    toks = {b: tokens(b) for b in notes}
    note_rows = []
    for b, v in sorted(notes.items()):
        sib = [x for x in notes if x != b and (toks[x] <= toks[b] or toks[b] <= toks[x])]
        singles = sorted({raw for (_, raw) in v['raw'] if not raw.startswith('[in multiple]')})
        note_rows.append({'base_name': b, 'raw_single_forms': ' | '.join(singles), 'n_raw_single_forms': len(singles),
                          'raw_values (source: value ×n)': ' || '.join(f'{s}: {raw} ×{n}' for (s, raw), n in sorted(v['raw'].items())),
                          'possible_same_name_other_spelling': ' | '.join(sib),
                          'n_works_single_britdrama': sum(1 for r in rows if r['company_brit_base'] == b and not r['company_brit_status'].startswith('multiple')),
                          'n_works_single_annals': sum(1 for r in rows if r['company_annals_base'] == b and not r['company_annals_status'].startswith('multiple')),
                          'n_works_single_title_page': sum(1 for r in rows if r['company_titlepage_base'] == b and not r['company_titlepage_status'].startswith('multiple')),
                          'n_works_in_multiple_britdrama': len(mentions['britdrama'].get(b, set())),
                          'n_works_in_multiple_annals': len(mentions['annals'].get(b, set())),
                          'n_works_in_multiple_title_page': len(mentions['title_page'].get(b, set()))})
    with open(out / 'company_name_notes.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(note_rows[0].keys())); wr.writeheader(); wr.writerows(note_rows)

    # ---- lineage notes (reference only; not applied anywhere) --------------------------------
    lineage = [
        ("Lord Chamberlain's (Hunsdon's) Men", "King's Men", 'renamed 1603 (royal patent); same company', ''),
        ("Admiral's (Nottingham's) Men", "Prince Henry's Men", 'renamed 1603/4; same company', ''),
        ("Prince Henry's Men", "Prince Palatine's (Palsgrave's) Men", 'renamed 1613 after Prince Henry\'s death; same company', ''),
        ("Derby's (Strange's) Men", "Lord Chamberlain's (Hunsdon's) Men", "Strange's Men (Derby's from 1593) dispersed 1594; several players went to the new Chamberlain's Men — not a renaming", 'a later, separate Derby\'s Men (6th earl) also existed'),
        ("Worcester's Men", "Queen Anne's Men", 'renamed 1603/4; same company', ''),
        ("Queen Anne's Men", 'Red Bull (Revels) Company (first)', "after Queen Anne's death (1619) part of the company continued at the Red Bull as the Revels company — continuation, not a clean renaming", ''),
        ('Children of the Chapel (second)', "Children of the Queen's Revels", 'renamed 1604 (patent); same Blackfriars boys company', ''),
        ("Children of the Queen's Revels", "Lady Elizabeth's Men", "Queen's Revels boys (at Whitefriars from 1609) merged into Lady Elizabeth's Men in 1613", 'DEEP also writes "Children of the Queens Revels (Children of the Whitefriars)"'),
        ("Lady Elizabeth's Men", "Queen Henrietta Maria's Men", "Queen Henrietta Maria's Men (1625, Cockpit) were formed partly from Lady Elizabeth's players — successor, not a renaming", ''),
        ("Children of Paul's (first)", "Children of Paul's (second)", 'same institution, two separate phases of playing (c.1575–1590 and 1599–1606/8)', ''),
        ("Children of the Chapel (first) (Oxford's Boys)", 'Children of the Chapel (second)', 'same institution, two separate phases (1580s; 1600–1604)', ''),
        ("Children of the King's Revels", "King's Revels Company", "different companies: boys at Whitefriars 1607–9 vs the adult King's Revels of the 1630s (Salisbury Court) — do not merge", ''),
        ("Prince Charles's Men (first)", "Prince Charles's Men (second)", 'different companies (1608/10–1625 vs 1631–1642, the second for the future Charles II)', ''),
        ("Queen Henrietta Maria's Men", "Beeston's Boys", "Beeston's Boys (King and Queen's Young Company, 1637) succeeded Queen Henrietta Maria's Men at the Cockpit under the same manager — successor, not a renaming", ''),
        ('Red Bull (Revels) Company (first)', 'Red Bull Company (second)', 'DEEP distinguishes two Red Bull companies; relation to be checked in the literature', ''),
    ]
    with open(out / 'company_lineage_notes.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f); wr.writerow(['from_name', 'to_name', 'relation (reference note; not applied in any table)', 'remark'])
        wr.writerows(lineage)

    # ---- source agreement per work -------------------------------------------------------------
    agree = []
    for r in rows:
        b, an, t = r['company_brit_raw'], r['company_annals_raw'], r['company_titlepage_raw']
        sb, sa, st = r['company_brit_status'], r['company_annals_status'], r['company_titlepage_status']
        def has(s): return not (s.startswith('missing') or s == 'not in BritDrama')
        if has(sb) and has(sa):
            ba = 'identical' if norm_apos(b) == norm_apos(an) else ('same base name' if r['company_brit_base'] == r['company_annals_base'] and r['company_brit_base'] else 'differ')
        elif has(sb) or has(sa):
            ba = 'only britdrama' if has(sb) else 'only annals'
        else:
            ba = 'neither'
        tp = ''
        if has(st):
            ref = r['company_brit_base'] or r['company_annals_base']
            tp = 'title page = first-performance source' if ref and r['company_titlepage_base'] == ref else ('title page differs' if ref else 'title page only')
        agree.append({'work_id': r['work_id'], 'title': r['title'], 'genre_main': r['genre_main'], 'company_brit_raw': b, 'company_annals_raw': an,
                      'company_titlepage_raw': t, 'britdrama_vs_annals': ba, 'title_page_vs_first_performance': tp})
    with open(out / 'company_source_agreement.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(agree[0].keys())); wr.writeheader(); wr.writerows(agree)

    # ---- theatre coverage ----------------------------------------------------------------------
    th = collections.defaultdict(list)
    for r in rows:
        toks = [t.strip() for t in r['theater_raw'].split(';') if t.strip()] if r['theater_raw'] not in ('', 'None') else ['(no theatre recorded)']
        for t in toks: th[t].append(r)
    th_rows = []
    for t, rs in sorted(th.items(), key=lambda kv: -len(kv[1])):
        kind = 'performance type' if t.endswith('Professional') else ('context' if t.startswith(('before the', 'at ')) else ('none' if t.startswith('(') else 'venue'))
        th_rows.append({'theater_token': t, 'kind': kind, 'n_works': len(rs),
                        'genre_composition': fmt_comp(collections.Counter(r['genre_main'] for r in rs)),
                        'companies_britdrama': fmt_comp(collections.Counter(r['company_brit_raw'] for r in rs)),
                        'companies_annals': fmt_comp(collections.Counter(r['company_annals_raw'] for r in rs)),
                        'annals_year_min': yr_stats([r['date_annals_year'] for r in rs])[0], 'annals_year_max': yr_stats([r['date_annals_year'] for r in rs])[1]})
    with open(out / 'theatre_coverage.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(th_rows[0].keys())); wr.writeheader(); wr.writerows(th_rows)

    # ---- summary ---------------------------------------------------------------------------------
    n = len(rows)
    md = ['# Company metadata coverage — works of the frozen run', '',
          f'Works: {n} (one representative edition each; genre_main from the run). DEEP rows: {sum(1 for s in sel_rows if s["basis"] == "deep_id match")} chosen by deep_id match, '
          f'{sum(1 for s in sel_rows if s["basis"].startswith("no deep_id"))} by fallback, {sum(1 for s in sel_rows if s["basis"].startswith("no DEEP"))} without a DEEP row; '
          f'{sum(1 for s in sel_rows if s["deep_row_realigned"])} rows realigned (extra field in the export); '
          f'{sum(1 for s in sel_rows if s["alt_rows_differ_in"])} works whose other DEEP rows differ in a company/date/play-type field (see deep_row_selection.csv).', '']
    for src, col in sources:
        sc = collections.Counter(r[col + '_status'] for r in rows)
        md += [f'## {src}: status of the company value', '', '| status | works |', '|---|---:|'] + [f'| {k} | {v} |' for k, v in sorted(sc.items(), key=lambda kv: (order.get(kv[0].split(" ")[0], 9), -kv[1]))] + ['']
    def named(st): return st in ('clear', 'uncertain') or st.startswith('multiple')
    md += ['## Availability of a first-performance company (British Drama field) by genre and play type', '',
           f'Named (clear, uncertain or multiple) in British Drama: {sum(1 for r in rows if named(r["company_brit_status"]))}; in Annals: {sum(1 for r in rows if named(r["company_annals_status"]))}; '
           f'in at least one of the two: {sum(1 for r in rows if named(r["company_brit_status"]) or named(r["company_annals_status"]))}; in both: {sum(1 for r in rows if named(r["company_brit_status"]) and named(r["company_annals_status"]))}. '
           f'Clear single name in British Drama: {sum(1 for r in rows if r["company_brit_status"] == "clear")}.', '']
    for key, label in (('genre_main', 'genre_main'), ('play_type_main', 'play_type_main (first token of the DEEP play type)')):
        ct = collections.defaultdict(collections.Counter)
        for r in rows: ct[r[key]]['named' if named(r['company_brit_status']) else r['company_brit_status']] += 1
        cats = ['named', 'unknown', 'unacted', 'not in BritDrama', 'missing (n/a)']
        md += [f'| {label} | works | ' + ' | '.join(cats) + ' |', '|---|---:|' + '---:|' * len(cats)]
        for g, c in sorted(ct.items(), key=lambda kv: -sum(kv[1].values())):
            md.append(f'| {g} | {sum(c.values())} | ' + ' | '.join(str(c.get(k, 0)) for k in cats) + ' |')
        md.append('')
    md += ['## British Drama vs Annals first-performance company', '', '| relation | works |', '|---|---:|']
    md += [f'| {k} | {v} |' for k, v in collections.Counter(x['britdrama_vs_annals'] for x in agree).most_common()] + ['']
    md += ['## Dates', '',
           f'Annals date_first_performance: {sum(1 for r in rows if r["date_annals_missing"])} missing; {sum(1 for r in rows if r["date_annals_low"] != "")} with limits in brackets; '
           f'{sum(1 for r in rows if re.search("circa|queried", r["date_annals_flags"]))} circa/queried; {sum(1 for r in rows if "licensed" in r["date_annals_flags"])} licensed; '
           f'{sum(1 for r in rows if r["closet_or_unacted_flag"])} works whose play_type says closet/unacted (date = composition by convention).',
           f'British Drama date: {sum(1 for r in rows if r["date_brit_missing"])} missing (not in BritDrama), {sum(1 for r in rows if r["date_brit_low"] != "")} with limits. '
           f'Annals and British Drama years differ for {sum(1 for r in rows if r["date_annals_vs_brit"].startswith("differ"))} works (same year for {sum(1 for r in rows if r["date_annals_vs_brit"] == "same year")}).',
           'Publication year is kept in its own column and is never used as a performance date.', '']
    for src, col in sources[:2]:
        md += [f'## Largest companies — {src} (clear values only; uncertain and multiple listed separately in company_coverage.csv)', '',
               '| company (raw) | works (clear) | same name uncertain | named in multiple values | genres | authors (top) | Annals years (records in this corpus) | Annals limits | mean included share |', '|---|---:|---:|---:|---|---|---|---|---:|']
        for d in [d for d in cov if d['source'] == src and d['status'] == 'clear'][:15]:
            unc = sum(1 for r in rows if r[col + '_base'] == d['base_name'] and r[col + '_status'] == 'uncertain')
            md.append(f'| {d["company_raw"]} | {d["n_works"]} | {unc} | {d["n_works_mentioned_in_multiple_values"]} | {d["genre_composition"]} | {d["n_authors"]} ({d["top_author"]} {d["top_author_n_works"]}) | {d["annals_year_min"]}–{d["annals_year_max"]} | {d["annals_limits_min"]}–{d["annals_limits_max"]} | {d["mean_included_share"]:.3f} |')
        md.append('')
    md += ['Year ranges are those of the works in this corpus that carry the value, not the company\'s period of activity. '
           'Names are raw DEEP strings; renamings and successions are listed in company_lineage_notes.csv for reference and are not applied.', '']
    (out / 'company_coverage_summary.md').write_text('\n'.join(md), encoding='utf-8')
    json.dump({'n_works': n, 'deep': str(a.deep), 'agg': str(agg), 'sources': [s for s, _ in sources],
               'status_rule': 'clear | uncertain (?) | multiple (; and or then) | unacted | unknown | not in BritDrama | missing (blank/n/a/None)',
               'no_merging': True}, open(out / 'company_config.json', 'w'), indent=1)
    print('\n'.join(md))


if __name__ == '__main__':
    main()
