#!/usr/bin/env python3
"""
23_chronology.py — topic shares by conjectured first-performance / composition decade (descriptive).

    python 23_chronology.py --agg <topics_B_s42/aggregate> --sheet <topics_B_s42/topic_sheet.csv>
                        --chunk-meta <chunks_w500/chunk_meta.csv> --deep <DEEP_data.csv>
                        [--company-dir <agg>/company] [--genres comedy,tragedy,history] [--use included] [--out <dir>]

Two layers: (1) all works of the run — date availability, decade distribution, genre composition per decade;
(2) inside comedy, tragedy and history — topic shares per decade.  Measure unchanged: share of a work's words in
each topic (representative edition, every chunk in the denominator: outliers, pending and contextual-only topics
included; the selected topics are NOT renormalised), works equal-weighted.

Date rule.  Main source: British Drama (date_first_performance_brit_display); Annals (date_first_performance)
only when British Drama is absent or has no usable year, with the reason recorded.  Per work: both raw strings,
the source used, the adopted point year, its lower / upper limit (the bracketed limits of the SAME source),
the date kind — 'first performance' (play type names a performance setting), 'composition' (play type is
closet / unacted only), 'kind unclear' (both, or neither, or queried), 'other event only' (no leading year,
only a licence / revision / publication date) — the flags circa / queried / licensed / revised / marked
incorrect, whether the two sources differ, and whether the work enters the period analysis and why.
Never: publication years as substitutes, averages of the two sources, guessed years for range-only strings
(a range-only string is kept as 'range only' and grouped only when the whole range lies in one decade).
'licensed' / 'revised' in a bracket do not disqualify the leading year: the leading year is the date, the
bracket is an accompanying event; a revision range never widens the limits.  'Translation' alone does not
make a work unacted.  A date whose meaning cannot be settled (e.g. the only source is marked incorrect)
is set aside as 'pending', not guessed.

Decades: floor(year / 10) × 10, fixed, covering the adopted years.  Each work is counted in exactly one
decade of a grouping.  Display rule for genre × decade cells: < 5 works — heatmap cell left blank, marked
insufficient; 5–9 — shown but marked sparse; ≥ 10 — shown (no reliability claim).  No decades are merged.

Sensitivity (limited): works whose own-source limits cross a decade boundary are regrouped by their lower
limit and, separately, by their upper limit; all other works keep their main decade; circa years without
limits keep their point decade (flagged).  Reported as two descriptive alternatives beside the main grouping.

Outputs (--out, default <agg>/chronology/): dates_by_work.csv, coverage.csv, genre_composition.csv,
included_coverage.csv, topic_stats.csv, topic_top_works.csv, author_composition.csv, boundary_works.csv,
sensitivity_counts.csv, topic_stats_sensitivity.csv, range_only_works.csv, sources_differ.csv,
fig1_corpus_composition.{png,svg}, fig2_sample_and_coverage.{png,svg}, fig3_topic_decade_heatmap_<genre>.{png,svg},
methods.md, checks.json, provenance.json.
"""
import argparse, csv, hashlib, importlib.util, json, platform, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED, GREY, INK, MUTED = '#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948', '#c9c9c4', '#0b0b0b', '#52514e'
GENRE_COLOUR = {'comedy': BLUE, 'tragedy': ORANGE, 'history': AQUA, 'tragicomedy': YELLOW, 'masque': MAGENTA, 'moral': GREEN, 'romance': VIOLET, 'pastoral': RED}
PERF = ('Adult Professional', 'Boys Professional', 'Professional', 'Occasional', 'Interlude', 'University', 'Inns of Court', 'Private',
        'Nonprofessional', 'Boys Nonprofessional/School', 'University (Nonprofessional)', 'Private (Nonprofessional)', 'Adult', 'Boys')


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('.py', ''), HERE / name); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def date_kind(play_type):
    """first performance / composition / kind unclear, from the DEEP play type (a translation is not thereby unacted)."""
    toks = [x.strip() for t in re.split(r';', play_type or '') for x in re.split(r'/', t) if x.strip()]
    closet = [t for t in toks if re.match(r'^(Closet|Unacted)', t)]
    perf = [t for t in toks if any(re.match(r'^' + re.escape(p) + r'(\b|\s*\(|$)', t) for p in PERF) or re.match(r'^(Adult|Boys) \(\?\)', t)]
    if closet and not perf:
        return 'composition' if not all('(?)' in t for t in closet) else 'kind unclear'
    if perf and not closet:
        return 'first performance'
    return 'kind unclear'


def parse(raw):
    """leading year, own limits (revision / secondary ranges excluded), flags. Returns None when no leading year."""
    s = (raw or '').replace('’', "'").strip()
    if not s or s == 'not in BritDrama': return None
    m = re.match(r'^(c\.\s*)?(\d{4})(\s*\(\?\))?', s)
    out = {'year': None, 'low': None, 'high': None, 'flags': set(), 'event_only': False, 'range_only': False}
    if not m:
        r = re.search(r'(\d{4})\s*-\s*(\d{4})', s)
        if r: out.update(low=int(r.group(1)), high=int(r.group(2)), range_only=True)
        else: out['event_only'] = True
        return out
    out['year'] = int(m.group(2))
    if m.group(1): out['flags'].add('circa')
    if m.group(3) or '?' in s.split('[')[0]: out['flags'].add('queried')
    for b in re.findall(r'\[([^\]]*)\]', s):
        if 'incorrect' in b: out['flags'].add('marked incorrect')
        for seg in b.split(';'):
            secondary = re.search(r'revis|adapt|re-licensed|interpolat|prologue|Act \d|written', seg, re.I)
            rngs = re.findall(r'(c\.)?\s*(\d{4})\s*(\(\?\))?\s*-\s*(c\.)?\s*(\d{4})\s*(\(\?\))?', seg)
            if rngs and not secondary:
                lo = min(int(r[1]) for r in rngs); hi = max(int(r[4]) for r in rngs)
                out['low'] = lo if out['low'] is None else min(out['low'], lo); out['high'] = hi if out['high'] is None else max(out['high'], hi)
                if any(r[0] or r[3] for r in rngs): out['flags'].add('circa limit')
                if any(r[2] or r[5] for r in rngs): out['flags'].add('queried limit')
                if len(rngs) > 1 or re.search(r'\bor\b', seg): out['flags'].add('alternative limits')
            elif rngs and secondary: out['flags'].add('later revision dates ignored')
        if 'licensed' in b: out['flags'].add('licensed (accompanying event)')
        if re.search(r'revis|adapt', b): out['flags'].add('revised (accompanying event)')
        if re.search(r'\?', b) and 'queried limit' not in out['flags']: out['flags'].add('queried detail')
    if out['low'] is not None:
        out['low'] = min(out['low'], out['year']); out['high'] = max(out['high'], out['year'])
    return out


def decade(y): return (y // 10) * 10
def dlabel(d): return f'{d}–{d + 9}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agg', required=True); ap.add_argument('--sheet', required=True)
    ap.add_argument('--chunk-meta', required=True); ap.add_argument('--deep', default='')
    ap.add_argument('--company-dir', default=''); ap.add_argument('--genres', default='comedy,tragedy,history')
    ap.add_argument('--expect', default='comedy:151,tragedy:111,history:34'); ap.add_argument('--use', default='')
    ap.add_argument('--top-works', type=int, default=3); ap.add_argument('--heat-topics', type=int, default=25); ap.add_argument('--out', default='')
    a = ap.parse_args()
    agg = Path(a.agg); out = Path(a.out) if a.out else agg / 'chronology'; out.mkdir(parents=True, exist_ok=True)
    cdir = Path(a.company_dir) if a.company_dir else agg / 'company'
    cfg = json.load(open(agg / 'config.json')) if (agg / 'config.json').exists() else {}
    use = [u.strip() for u in a.use.split(',') if u.strip()] or cfg.get('use') or ['included']
    sheet = {int(r['topic']): r for r in csv.DictReader(open(a.sheet, encoding='utf-8'))}
    topics = sorted(t for t, r in sheet.items() if (r.get('use_in_genre_analysis') or '') in use)
    label = {t: (sheet[t].get('Label') or sheet[t].get('draft_label') or f'topic {t}') for t in topics}
    works = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8')))
    cats = [c for c in works[0] if c.startswith('cat:')]
    for w in works:
        for c in list(w):
            if re.fullmatch(r't\d+', c) or c in cats or c == 'words_mean': w[c] = float(w[c])
    genres = [g.strip() for g in a.genres.split(',') if g.strip()]
    expect = {k: int(v) for k, v in (x.split(':') for x in a.expect.split(',') if ':' in x)}
    cf = {r['work_id']: r for r in csv.DictReader(open(cdir / 'company_fields_by_work.csv', encoding='utf-8'))}
    m22 = load('22_author_by_genre.py'); split_authors, read_deep = m22.split_authors, m22.read_deep

    # ---- author names (re-split against DEEP) and roles, as in 22 ----------------------------------
    deep_display = {}
    if a.deep and Path(a.deep).exists():
        cm = {}
        for r in csv.DictReader(open(a.chunk_meta, encoding='utf-8-sig')): cm.setdefault(r['edition_id'], r['deep_id'])
        by_ed = defaultdict(list)
        for r in read_deep(a.deep): by_ed[r['edition_id']].append(r)
        for w in works:
            row = next((x for x in by_ed.get(w['editions'], []) if x['deep_id'] == cm.get(w['editions'], '')), None)
            deep_display[w['work_id']] = row['authors_display'] if row else ''
    def deep_names(disp): return [re.sub(r',\s*(trans|rev|ed|adapt)\.?$', '', x.replace('(?)', '').strip()).strip() for x in disp.split(';') if x.strip()]
    all_names = sorted({nm for d in deep_display.values() for nm in deep_names(d)}, key=len, reverse=True)
    for w in works:
        disp = deep_display.get(w['work_id'], ''); own = sorted(deep_names(disp), key=len, reverse=True)
        rest = w['author'] or ''; got = []
        while rest:
            hit = next((nm for nm in own if rest.startswith(nm)), None) or next((nm for nm in all_names if rest.startswith(nm)), None)
            if not hit: break
            got.append(hit); rest = rest[len(hit):]
        w['names'] = got + (split_authors(rest) if rest else []) or split_authors(w['author'])
        tags = {}
        for e in [x.strip() for x in disp.split(';') if x.strip()]:
            nm = e.replace('(?)', '').strip(); m = re.search(r',\s*(trans|rev|ed|adapt)\.?$', nm)
            tags[nm[:m.start()].strip() if m else nm] = m.group(1) if m else 'author'
        w['translators'] = [nm for nm in w['names'] if tags.get(nm) == 'trans']

    # ---- dates ---------------------------------------------------------------------------------------
    drows = []; checks_parse = []
    for w in works:
        c = cf[w['work_id']]; braw, araw = c['date_brit_raw'], c['date_annals_raw']
        pb, pa = parse(braw), parse(araw)
        kind = date_kind(c['play_type_raw'])
        src, why, p = '', '', None
        if pb and (pb['year'] is not None or pb['range_only']):
            src, p = 'British Drama', pb
        elif pa and (pa['year'] is not None or pa['range_only']):
            src, p = 'Annals', pa
            why = 'not in British Drama' if braw == 'not in BritDrama' or not braw else ('British Drama has no usable year: ' + braw)
        else:
            why = 'no usable year in either source'
        year = p['year'] if p else None; low = p['low'] if p else None; high = p['high'] if p else None
        flags = sorted(p['flags']) if p else []
        include, reason = True, ''
        if p is None: include, reason = False, 'no usable date'
        elif p['event_only']: include, reason = False, 'other event only (licence / revision / publication) — pending'
        elif src == 'Annals' and 'marked incorrect' in flags: include, reason = False, 'only source is marked incorrect in DEEP — pending'
        elif p['range_only']:
            if decade(low) == decade(high): reason = 'range only, whole range in one decade'
            else: include, reason = False, 'range only, spans decades — cannot be placed'
        grp = decade(year) if (include and year is not None) else (decade(low) if include and low is not None else None)
        other = pa if src == 'British Drama' else pb
        oy = other['year'] if other and other['year'] is not None else None
        differ = '' if year is None or oy is None else ('same year' if oy == year else f'differ by {abs(oy - year)} ({"same decade" if decade(oy) == decade(year) else "different decade"})')
        cross = bool(include and low is not None and high is not None and decade(low) != decade(high))
        # cross-check against the 20_company_coverage parse of the same string
        for tag, pp in (('brit', pb), ('annals', pa)):
            y20 = c[f'date_{tag}_year']; lo20 = c[f'date_{tag}_low']; hi20 = c[f'date_{tag}_high']
            if pp and pp['year'] is not None and (str(pp['year']) != y20 or (lo20 and pp['low'] is not None and str(pp['low']) != lo20) or (hi20 and pp['high'] is not None and str(pp['high']) != hi20)):
                checks_parse.append({'work_id': w['work_id'], 'title': w['title'], 'source': tag, 'raw': c[f'date_{tag}_raw'], '20_year_low_high': f'{y20}/{lo20}/{hi20}', '23_year_low_high': f'{pp["year"]}/{pp["low"]}/{pp["high"]}'})
        d = {'work_id': w['work_id'], 'title': w['title'], 'author_field': ' / '.join(w['names']), 'genre_main': w['genre_main'], 'play_type_raw': c['play_type_raw'],
             'date_brit_raw': braw, 'date_annals_raw': araw, 'source_used': src, 'fallback_reason': why,
             'adopted_year': year if year is not None else '', 'lower_limit': low if low is not None else '', 'upper_limit': high if high is not None else '',
             'date_kind': kind if include else '', 'flags': '; '.join(flags), 'sources_differ': differ,
             'decade_main': dlabel(grp) if grp is not None else '', 'crosses_decade_boundary': 'Y' if cross else '',
             'decade_by_lower_limit': dlabel(decade(low)) if cross else '', 'decade_by_upper_limit': dlabel(decade(high)) if cross else '',
             'in_period_analysis': 'Y' if include else '', 'reason': reason, 'date_publication_raw_not_used': c['date_publication_raw'],
             'included_share': round(w['cat:included'], 4)}
        w.update(_year=year, _grp=grp, _low=low, _high=high, _inc=include, _cross=cross, _kind=kind if include else '', _src=src, _flags=flags, _differ=differ)
        drows.append(d)
    with open(out / 'dates_by_work.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(drows[0])); wr.writeheader(); wr.writerows(drows)

    # ---- coverage ------------------------------------------------------------------------------------
    inc = [w for w in works if w['_inc']]
    decades = list(range(min(w['_grp'] for w in inc), max(w['_grp'] for w in inc) + 10, 10))   # every decade of the range, empty ones included
    scopes = [('all', works)] + [(g, [w for w in works if w['genre_main'] == g]) for g in genres]
    cov_rows = []
    for name, ws in scopes:
        wi = [w for w in ws if w['_inc']]
        r = {'scope': name, 'n_works': len(ws), 'n_in_period_analysis': len(wi), 'n_not_usable': len(ws) - len(wi),
             'n_british_drama': sum(1 for w in wi if w['_src'] == 'British Drama'), 'n_annals_fallback': sum(1 for w in wi if w['_src'] == 'Annals'),
             'n_first_performance': sum(1 for w in wi if w['_kind'] == 'first performance'), 'n_composition': sum(1 for w in wi if w['_kind'] == 'composition'),
             'n_kind_unclear': sum(1 for w in wi if w['_kind'] == 'kind unclear'),
             'n_circa_or_queried': sum(1 for w in wi if any(f.startswith(('circa', 'queried')) for f in w['_flags'])),
             'n_with_limits': sum(1 for w in wi if w['_low'] is not None), 'n_crossing_decade_boundary': sum(1 for w in wi if w['_cross']),
             'n_sources_differ': sum(1 for w in wi if w['_differ'].startswith('differ')), 'n_sources_differ_decade': sum(1 for w in wi if 'different decade' in w['_differ']),
             'n_licensed_or_revised_note': sum(1 for w in wi if any('accompanying' in f for f in w['_flags'])),
             'not_usable_reasons': '; '.join(f'{k} {v}' for k, v in Counter(d['reason'] for d in drows if d['work_id'] in {w['work_id'] for w in ws} and not d['in_period_analysis']).items())}
        for dd in decades: r[f'n_{dlabel(dd)}'] = sum(1 for w in wi if w['_grp'] == dd)
        cov_rows.append(r)
    with open(out / 'coverage.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(cov_rows[0])); wr.writeheader(); wr.writerows(cov_rows)
    all_genres = [g for g, _ in Counter(w['genre_main'] for w in works).most_common()]
    gc_rows = []
    for dd in decades:
        ws = [w for w in inc if w['_grp'] == dd]; c = Counter(w['genre_main'] for w in ws)
        r = {'decade': dlabel(dd), 'n_works': len(ws)}
        for g in all_genres: r[f'n_{g}'] = c.get(g, 0)
        r['composition_by_works'] = '; '.join(f'{g} {n}' for g, n in c.most_common())
        r['n_first_performance'] = sum(1 for w in ws if w['_kind'] == 'first performance'); r['n_composition'] = sum(1 for w in ws if w['_kind'] == 'composition'); r['n_kind_unclear'] = sum(1 for w in ws if w['_kind'] == 'kind unclear')
        gc_rows.append(r)
    with open(out / 'genre_composition.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(gc_rows[0])); wr.writeheader(); wr.writerows(gc_rows)

    def status(n): return 'insufficient (< 5)' if n < 5 else ('sparse (5–9)' if n < 10 else 'shown (≥ 10)')
    ic_rows = []
    for g in genres:
        for dd in decades:
            ws = [w for w in inc if w['genre_main'] == g and w['_grp'] == dd]
            r = {'genre': g, 'decade': dlabel(dd), 'n_works': len(ws), 'display_status': status(len(ws))}
            for c in cats: r['mean_' + c.replace('cat:', '')] = round(float(np.mean([w[c] for w in ws])), 4) if ws else ''
            r['sum_of_means'] = round(sum(float(np.mean([w[c] for w in ws])) for c in cats), 4) if ws else ''
            ic_rows.append(r)
    with open(out / 'included_coverage.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(ic_rows[0])); wr.writeheader(); wr.writerows(ic_rows)

    # ---- topic stats per genre × decade ---------------------------------------------------------------
    ts_rows, tw_rows, au_rows = [], [], []
    for g in genres:
        for dd in decades:
            ws = [w for w in inc if w['genre_main'] == g and w['_grp'] == dd]
            if not ws: continue
            M = np.array([[w[f't{t}'] for t in topics] for w in ws])
            for j, t in enumerate(topics):
                col = M[:, j]; tot = col.sum()
                ts_rows.append({'genre': g, 'decade': dlabel(dd), 'n_works': len(ws), 'display_status': status(len(ws)), 'topic': t, 'label': label[t],
                                'mean_share_pct': round(col.mean() * 100, 3), 'median_share_pct': round(float(np.median(col)) * 100, 3),
                                'works_with_topic': int((col > 0).sum()),
                                'top_works': '; '.join(f'{ws[k]["title"][:40]} ({col[k] / len(ws) * 100:.2f} pp of the mean, {col[k] / tot:.0%} of the group total)' for k in np.argsort(-col)[:a.top_works] if col[k] > 0)})
                for k in np.argsort(-col)[:a.top_works]:
                    if col[k] > 0:
                        tw_rows.append({'genre': g, 'decade': dlabel(dd), 'topic': t, 'label': label[t], 'n_works': len(ws), 'work_id': ws[k]['work_id'], 'title': ws[k]['title'],
                                        'author_field': ' / '.join(ws[k]['names']), 'adopted_year': ws[k]['_year'], 'share_in_work_pct': round(col[k] * 100, 3),
                                        'contribution_to_group_mean_pp': round(col[k] / len(ws) * 100, 3), 'share_of_group_total': round(col[k] / tot, 3)})
            names = Counter(nm for w in ws for nm in w['names'] if nm != 'Anonymous' and nm not in w['translators'])
            trans = Counter(nm for w in ws for nm in w['translators'])
            au_rows.append({'genre': g, 'decade': dlabel(dd), 'n_works': len(ws), 'n_distinct_authors': len(names),
                            'top_authors_works_involved': '; '.join(f'{k} {v}' for k, v in names.most_common(4)),
                            'top_author_share_of_works': round(names.most_common(1)[0][1] / len(ws), 3) if names else '',
                            'n_collaborative_works': sum(1 for w in ws if len(w['names']) > 1), 'n_anonymous_works': sum(1 for w in ws if 'Anonymous' in w['names']),
                            'translators_works_involved': '; '.join(f'{k} {v}' for k, v in trans.most_common()),
                            'counting_rule': 'works involved per name (a collaborative work counts once for each of its authors; the counts are not exclusive and do not add up to n_works)'})
    for name, rows in (('topic_stats.csv', ts_rows), ('topic_top_works.csv', tw_rows), ('author_composition.csv', au_rows)):
        with open(out / name, 'w', newline='', encoding='utf-8') as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

    # ---- sensitivity: boundary works by lower / upper limit ---------------------------------------------
    bw = [w for w in inc if w['_cross']]
    with open(out / 'boundary_works.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f); wr.writerow(['work_id', 'title', 'genre_main', 'source_used', 'date_raw_used', 'adopted_year', 'lower_limit', 'upper_limit', 'decade_main', 'decade_by_lower_limit', 'decade_by_upper_limit', 'flags'])
        for w in sorted(bw, key=lambda w: (w['genre_main'], w['_year'])):
            wr.writerow([w['work_id'], w['title'], w['genre_main'], w['_src'], cf[w['work_id']]['date_brit_raw' if w['_src'] == 'British Drama' else 'date_annals_raw'], w['_year'], w['_low'], w['_high'], dlabel(w['_grp']), dlabel(decade(w['_low'])), dlabel(decade(w['_high'])), '; '.join(w['_flags'])])
    variants = {'main': lambda w: w['_grp'], 'lower limit': lambda w: decade(w['_low']) if w['_cross'] else w['_grp'], 'upper limit': lambda w: decade(w['_high']) if w['_cross'] else w['_grp']}
    all_dec = decades
    sc_rows, st_rows = [], []
    for name, wsg in [('all', inc)] + [(g, [w for w in inc if w['genre_main'] == g]) for g in genres]:
        for vname, fn in variants.items():
            r = {'scope': name, 'grouping': vname, 'n_moved': sum(1 for w in wsg if fn(w) != w['_grp'])}
            for dd in all_dec: r[f'n_{dlabel(dd)}'] = sum(1 for w in wsg if fn(w) == dd)
            sc_rows.append(r)
    for g in genres:
        for vname, fn in variants.items():
            for dd in all_dec:
                ws = [w for w in inc if w['genre_main'] == g and fn(w) == dd]
                if not ws: continue
                M = np.array([[w[f't{t}'] for t in topics] for w in ws]).mean(axis=0)
                for j, t in enumerate(topics):
                    st_rows.append({'genre': g, 'grouping': vname, 'decade': dlabel(dd), 'n_works': len(ws), 'display_status': status(len(ws)), 'topic': t, 'label': label[t], 'mean_share_pct': round(M[j] * 100, 3)})
    for name, rows in (('sensitivity_counts.csv', sc_rows), ('topic_stats_sensitivity.csv', st_rows)):
        with open(out / name, 'w', newline='', encoding='utf-8') as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)

    # ---- range-only works (none expected) and the two-source disagreement list ------------------------------
    ro = [d for d in drows if d['reason'].startswith('range only')]
    with open(out / 'range_only_works.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f); wr.writerow(['work_id', 'title', 'genre_main', 'source_used', 'lower_limit', 'upper_limit', 'main_grouping', 'decade_under_lower_limit', 'decade_under_upper_limit', 'note'])
        for d in ro:
            wr.writerow([d['work_id'], d['title'], d['genre_main'], d['source_used'], d['lower_limit'], d['upper_limit'], d['decade_main'] or 'not placed',
                         dlabel(decade(int(d['lower_limit']))), dlabel(decade(int(d['upper_limit']))), 'a range-only work that the main grouping cannot place ADDS to the sample under the limit groupings; it is not a moved work'])
    sd = [d for d in drows if d['sources_differ'].startswith('differ')]
    with open(out / 'sources_differ.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=['work_id', 'title', 'genre_main', 'source_used', 'date_brit_raw', 'date_annals_raw', 'adopted_year', 'sources_differ', 'decade_main', 'note'])
        wr.writeheader()
        for d in sd:
            wr.writerow({k: d[k] for k in ['work_id', 'title', 'genre_main', 'source_used', 'date_brit_raw', 'date_annals_raw', 'adopted_year', 'sources_differ', 'decade_main']} | {'note': 'kept as listed; no further dating research this round'})
    n_rev_ignored = sum(1 for d in drows if 'later revision dates ignored' in d['flags'])

    # ---- checks ----------------------------------------------------------------------------------------
    checks = {'genre_counts': {g: sum(1 for w in works if w['genre_main'] == g) for g in genres}, 'genre_counts_expected': expect,
              'n_works': len(works), 'n_in_period_analysis': len(inc), 'n_not_usable': len(works) - len(inc),
              'each_included_work_in_exactly_one_decade': all(sum(1 for dd in decades if w['_grp'] == dd) == 1 for w in inc),
              'decade_counts_sum_to_included': sum(r['n_works'] for r in gc_rows) == len(inc),
              'sensitivity_counts_preserve_total': all(sum(v for k, v in r.items() if k.startswith('n_1')) == (len(inc) if r['scope'] == 'all' else sum(1 for w in inc if w['genre_main'] == r['scope'])) for r in sc_rows),
              'max_abs_dev_category_means_sum_minus_1': max(abs(r['sum_of_means'] - 1) for r in ic_rows if r['sum_of_means'] != ''),
              'inclusion_accounting': {'n_works': len(works), 'in_analysis': len(inc), 'pending': sum(1 for d in drows if 'pending' in d['reason']), 'excluded_other': sum(1 for d in drows if not d['in_period_analysis'] and 'pending' not in d['reason']),
                                       'sums_to_n_works': len(inc) + sum(1 for d in drows if not d['in_period_analysis']) == len(works)},
              'no_duplicates_in_any_grouping': all(len({w['work_id'] for w in inc}) == len(inc) for _ in variants),
              'n_adopted_years_taken_from_publication': 0, 'n_works_with_revision_ranges_ignored_for_limits': n_rev_ignored,
              'n_range_only_works': len(ro), 'n_sources_differ_listed': len(sd),
              'publication_year_used': False, 'sources_averaged': False,
              'parse_differences_vs_20_company_coverage': checks_parse, 'n_selected_topics': len(topics)}
    json.dump(checks, open(out / 'checks.json', 'w'), indent=1, default=str)

    # ---- figures ---------------------------------------------------------------------------------------
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Patch
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': GREY, 'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': INK, 'svg.fonttype': 'none'})
    note = f'Representative editions · works equal-weighted · decade = adopted year (British Drama; Annals only as fallback) · {len(topics)} {"/".join(use)} topics as share of all words (not renormalised)'
    # counts figure: stacked genre composition per decade + date-kind strip
    series = [g for g in ['comedy', 'tragedy', 'history', 'tragicomedy', 'masque', 'moral', 'romance', 'pastoral'] if g in all_genres]
    other = [g for g in all_genres if g not in series]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    x = np.arange(len(decades)); bottom = np.zeros(len(decades))
    for g in series + (['other'] if other else []):
        vals = np.array([sum(1 for w in inc if w['_grp'] == dd and ((w['genre_main'] == g) if g != 'other' else (w['genre_main'] in other))) for dd in decades], float)
        ax.bar(x, vals, 0.72, bottom=bottom, color=GENRE_COLOUR.get(g, GREY), edgecolor='white', linewidth=1.5, label=(g if g != 'other' else f'other ({", ".join(other)})'))
        bottom += vals
    for i, dd in enumerate(decades):
        ax.text(i, bottom[i] + 1.2, str(int(bottom[i])), ha='center', va='bottom', fontsize=8, color=MUTED)
    ax.set_xticks(x); ax.set_xticklabels([dlabel(dd) for dd in decades], rotation=45, ha='right')
    ax.set_ylabel('works (representative editions)'); ax.set_ylim(0, bottom.max() * 1.15)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
    ax.grid(axis='y', color='#eeeeea', lw=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc='upper left')
    nu = len(works) - len(inc)
    ax.set_title(f'Composition of this corpus by decade of the adopted date — {len(inc)} of {len(works)} works placed ({nu} not usable); not a count of plays written or staged', loc='left', fontsize=10.5, color=INK)
    fig.text(0.01, 0.03, 'Representative editions · works equal-weighted · decade = adopted year (British Drama; Annals only as fallback) · genre_main from the run', ha='left', fontsize=7.5, color=MUTED)
    fig.text(0.01, 0.005, 'Empty decades are kept; the one work without a usable date (Albertus Wallenstein, Annals date marked incorrect, not in British Drama) is set aside.' if nu == 1 else f'{nu} works without a usable date are set aside.', ha='left', fontsize=7.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 1)); fig.savefig(out / 'fig1_corpus_composition.png', dpi=200); fig.savefig(out / 'fig1_corpus_composition.svg'); plt.close(fig)
    # fig 2: per genre, works per decade and mean included coverage — two facet rows, one y-scale per row, no dual axis
    fig, axes = plt.subplots(2, len(genres), figsize=(3.4 * len(genres) + 0.6, 5.6), sharex=True, squeeze=False)
    gdec = decades
    for j, g in enumerate(genres):
        n = [sum(1 for w in inc if w['genre_main'] == g and w['_grp'] == dd) for dd in gdec]
        cv = [np.mean([w['cat:included'] for w in inc if w['genre_main'] == g and w['_grp'] == dd]) if nn else np.nan for dd, nn in zip(gdec, n)]
        ax = axes[0, j]; x = np.arange(len(gdec))
        ax.bar(x, n, 0.7, color=GENRE_COLOUR.get(g, BLUE), edgecolor='white')
        for i, nn in enumerate(n):
            if nn: ax.text(i, nn + 0.6, str(nn), ha='center', va='bottom', fontsize=7, color=MUTED)
        ax.axhline(10, color=GREY, lw=0.8, ls=(0, (3, 3))); ax.axhline(5, color=GREY, lw=0.8, ls=(0, (1, 2)))
        ax.set_title(f'{g.capitalize()} — {sum(n)} works', loc='left', fontsize=10, color=INK)
        if j == 0: ax.set_ylabel('works')
        ax2 = axes[1, j]
        ok = [i for i, nn in enumerate(n) if nn >= 5]
        for i in ok: ax2.plot(x[i], cv[i], color=GENRE_COLOUR.get(g, BLUE), marker='o', ms=6, mec='white', ls='none')
        for i0, i1 in zip(ok, ok[1:]):
            if i1 == i0 + 1: ax2.plot([x[i0], x[i1]], [cv[i0], cv[i1]], color=GENRE_COLOUR.get(g, BLUE), lw=2)   # line only between adjacent decades that both have >= 5 works
        for i, nn in enumerate(n):
            if 0 < nn < 5: ax2.plot(x[i], cv[i], marker='o', ms=6, mfc='white', mec=GENRE_COLOUR.get(g, BLUE), ls='none')
        ax2.set_ylim(0, 1); ax2.set_xticks(x); ax2.set_xticklabels([dlabel(dd) for dd in gdec], rotation=60, ha='right', fontsize=7)
        if j == 0: ax2.set_ylabel('mean included share')
        for a_ in (ax, ax2):
            for sp in ('top', 'right'): a_.spines[sp].set_visible(False)
            a_.grid(axis='y', color='#eeeeea', lw=0.8); a_.set_axisbelow(True)
    ymax = max(sum(1 for w in inc if w['genre_main'] == g and w['_grp'] == dd) for g in genres for dd in gdec)
    for j in range(len(genres)): axes[0, j].set_ylim(0, ymax * 1.18)
    fig.suptitle('Sample size and included-topic coverage by decade, three genres', x=0.01, ha='left', fontsize=11, color=INK)
    fig.text(0.01, 0.905, 'Top: works per decade (dashed lines at 5 and 10 = display thresholds). Bottom: equal-weighted mean of the work-level share of words in the 53 included topics; hollow marker = fewer than 5 works; lines join only adjacent decades that both have ≥ 5 works. Same y-scale in each row; no dual axis.', ha='left', fontsize=7.5, color=MUTED, wrap=True)
    fig.tight_layout(rect=(0, 0.02, 1, 0.88)); fig.savefig(out / 'fig2_sample_and_coverage.png', dpi=200); fig.savefig(out / 'fig2_sample_and_coverage.svg'); plt.close(fig)

    # fig 3: heatmaps per genre, decades × topics (mean share of all words, %), one colour scale for the three genres
    cmap = LinearSegmentedColormap.from_list('seq', ['#f4f7fc', '#9dc0ee', BLUE, '#123c78'])
    sel = {}
    for g in genres:
        cols = [dd for dd in decades if any(w['genre_main'] == g and w['_grp'] == dd for w in inc)]
        n = {dd: sum(1 for w in inc if w['genre_main'] == g and w['_grp'] == dd) for dd in cols}
        M = np.full((len(topics), len(cols)), np.nan)
        for j, dd in enumerate(cols):
            if n[dd] >= 5:
                ws = [w for w in inc if w['genre_main'] == g and w['_grp'] == dd]
                M[:, j] = np.array([[w[f't{t}'] for t in topics] for w in ws]).mean(axis=0) * 100
        big = [j for j, dd in enumerate(cols) if n[dd] >= 10]
        if len(big) >= 2:
            score = np.nanmax(M[:, big], axis=1) - np.nanmin(M[:, big], axis=1); rule = f'max − min of the decade means across the {len(big)} decades with ≥ 10 works'
        else:
            allg = [w for w in works if w['genre_main'] == g]
            score = np.array([[w[f't{t}'] for t in topics] for w in allg]).mean(axis=0) * 100; rule = f'overall mean share in {g} (fewer than two decades with ≥ 10 works, so no "largest change" selection)'
        order = np.argsort(-score)[:15]
        sel[g] = (cols, n, M[order], [topics[i] for i in order], rule)
    vmax = max(np.nanmax(M) for _, _, M, _, _ in sel.values() if not np.all(np.isnan(M)))
    for g, (cols, n, Ms, ts, rule) in sel.items():
        fig, ax = plt.subplots(figsize=(2.6 + 0.95 * len(cols), 2.6 + 0.32 * len(ts)))
        im = ax.imshow(np.where(np.isnan(Ms), 0, Ms), cmap=cmap, vmin=0, vmax=vmax, aspect='auto')
        for i in range(len(ts)):
            for j in range(len(cols)):
                v = Ms[i, j]
                if np.isnan(v): ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, facecolor='white', hatch='///', edgecolor='#dddcd6', lw=0))
                else: ax.text(j, i, f'{v:.1f}', ha='center', va='center', fontsize=7.5, color='white' if v > vmax * 0.6 else INK)
        ax.set_xticks(range(len(cols)))
        ax.set_xticklabels([f'{dlabel(dd)}\nn = {n[dd]}' + ('\ninsufficient' if n[dd] < 5 else ('\nsparse' if n[dd] < 10 else '')) for dd in cols], fontsize=7.5)
        ax.set_yticks(range(len(ts))); ax.set_yticklabels([f'T{t}  {label[t][:54]}' for t in ts], fontsize=8)
        ax.set_xticks(np.arange(-.5, len(cols), 1), minor=True); ax.set_yticks(np.arange(-.5, len(ts), 1), minor=True)
        ax.grid(which='minor', color='white', lw=2); ax.tick_params(which='minor', length=0)
        for sp in ax.spines.values(): sp.set_visible(False)
        cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02); cb.set_label('mean share of the work\'s words (%), same scale for the three genres', fontsize=8); cb.outline.set_visible(False)
        ax.set_title(f'{g.capitalize()}: mean topic share by decade ({sum(n.values())} works with a usable date)', loc='left', fontsize=10, color=INK)
        fig.text(0.01, 0.01, f'Exploratory display. Topics shown: {len(ts)} of {len(topics)}, chosen by {rule}; full statistics in topic_stats.csv. Raw percentages, no per-row scaling. Hatched = fewer than 5 works (not shown); "sparse" = 5–9 works, descriptive only. A difference between decades is not a tested change. ' + note,
                 ha='left', fontsize=7, color=MUTED, wrap=True)
        fig.tight_layout(rect=(0, 0.09, 1, 1)); fig.savefig(out / f'fig3_topic_decade_heatmap_{g}.png', dpi=200); fig.savefig(out / f'fig3_topic_decade_heatmap_{g}.svg'); plt.close(fig)

    # ---- methods, provenance --------------------------------------------------------------------------------
    inputs = {'work_topic_share.csv': str(agg / 'work_topic_share.csv'), 'config.json': str(agg / 'config.json'), 'topic_sheet.csv': a.sheet, 'chunk_meta.csv': a.chunk_meta,
              'company_fields_by_work.csv': str(cdir / 'company_fields_by_work.csv')}
    if a.deep: inputs['DEEP_data.csv'] = a.deep
    json.dump({'command': ' '.join(sys.argv), 'python': platform.python_version(), 'numpy': np.__version__, 'matplotlib': matplotlib.__version__,
               'params': {'genres': genres, 'use': use, 'n_topics': len(topics), 'top_works': a.top_works, 'heat_topics_max': 15, 'heat_topic_rule': 'max-min of decade means across decades with >=10 works, else overall genre mean', 'decade_rule': 'floor(year/10)*10', 'display_rule': '<5 blank, 5-9 sparse, >=10 shown'},
               'inputs_sha256': {k: (sha256(v) if Path(v).exists() else 'missing') for k, v in inputs.items()}, 'run': agg.parent.name}, open(out / 'provenance.json', 'w'), indent=1)
    md = ['# Topic shares by decade — methods and coverage', '',
          f'Run {agg.parent.name}; {len(topics)} topics ({", ".join(use)}); genre counts ' + ', '.join(f'{g} {checks["genre_counts"][g]} (expected {expect.get(g, "?")})' for g in genres) + '.', '',
          'Date rule: British Drama first-performance date first; Annals only when British Drama is absent or has no usable year (reason recorded per work). The leading year of the string is the date; bracketed limits of the same source are the lower / upper limit; licence and revision notes are accompanying events and do not disqualify the date; later revision ranges never widen the limits; publication years are never used; the two sources are never averaged. Date kind from the DEEP play type: first performance (a performance setting is named), composition (closet / unacted only), kind unclear (both or neither, or queried). A range without a point year would be kept as "range only" and grouped only if it lies within one decade (none in this corpus). Dates whose meaning cannot be settled are pending, not guessed.',
          'Decades: floor(year / 10) × 10 on the adopted point year; each work in exactly one decade; no merging. Display: < 5 works blank, 5–9 sparse, ≥ 10 shown — a display rule, not a reliability claim.',
          'Measure: share of a work\'s words per topic (all words in the denominator, selected topics not renormalised), works equal-weighted; composition counts are by works; coverage means are equal-weighted means of work-level shares. Top works per cell: contribution = share / n (works equal-weighted) and share of the group total.',
          'Sensitivity: works whose own-source limits cross a decade boundary are regrouped by lower limit and, separately, by upper limit; other works keep their decade; circa or queried years without limits get no ± years. The two groupings are boundary cases for the grouping\'s sensitivity, not two claims about the real dates, and do not exhaust the dating uncertainty; a range-only work (none here) would ADD to the sample under the limit groupings rather than move. Works whose two sources differ are listed (sources_differ.csv) without further dating research.',
          'Figures: fig1 = composition of this corpus by decade (stacked by genre_main, totals) — not a count of plays written or staged; fig2 = per genre, works per decade and mean included coverage in two facet rows (no dual axis); fig3 = per-genre heatmap, at most 15 topics chosen by max − min of the decade means across decades with ≥ 10 works (or by overall genre mean when fewer than two such decades), raw percentages on one colour scale for the three genres; cells with < 5 works blank, 5–9 marked sparse. No sensitivity figures (tables only).', '',
          '## Coverage', '', '| scope | works | placed | not usable | British Drama | Annals fallback | first perf. | composition | kind unclear | circa/queried | with limits | cross boundary | sources differ (diff. decade) |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in cov_rows:
        md.append(f'| {r["scope"]} | {r["n_works"]} | {r["n_in_period_analysis"]} | {r["n_not_usable"]} | {r["n_british_drama"]} | {r["n_annals_fallback"]} | {r["n_first_performance"]} | {r["n_composition"]} | {r["n_kind_unclear"]} | {r["n_circa_or_queried"]} | {r["n_with_limits"]} | {r["n_crossing_decade_boundary"]} | {r["n_sources_differ"]} ({r["n_sources_differ_decade"]}) |')
    md += ['', 'Not usable: ' + '; '.join(f'{d["title"][:40]} — {d["reason"]}' for d in drows if not d['in_period_analysis']), '',
           '## Works per decade (all placed works) and genre composition', '', '| decade | works | composition (by works) | first perf. | composition | unclear |', '|---|---:|---|---:|---:|---:|']
    md += [f'| {r["decade"]} | {r["n_works"]} | {r["composition_by_works"]} | {r["n_first_performance"]} | {r["n_composition"]} | {r["n_kind_unclear"]} |' for r in gc_rows]
    md += ['', '## Genre × decade: works and mean included coverage', '', '| genre | decade | works | status | mean included | outlier | pending | contextual only | candidate | unclassified |', '|---|---|---:|---|---:|---:|---:|---:|---:|---:|']
    md += [f'| {r["genre"]} | {r["decade"]} | {r["n_works"]} | {r["display_status"]} | {r["mean_included"]} | {r["mean_outlier_hdbscan"]} | {r["mean_pending"]} | {r["mean_contextual_only"]} | {r["mean_candidate"]} | {r["mean_unclassified"]} |' for r in ic_rows if r['n_works']]
    md += ['', '## Sensitivity: works per decade under the three groupings', '', '| scope | grouping | moved | ' + ' | '.join(dlabel(dd) for dd in all_dec) + ' |', '|---|---|---:|' + '---:|' * len(all_dec)]
    md += [f'| {r["scope"]} | {r["grouping"]} | {r["n_moved"]} | ' + ' | '.join(str(r[f"n_{dlabel(dd)}"]) for dd in all_dec) + ' |' for r in sc_rows]
    (out / 'methods.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
