#!/usr/bin/env python3
"""
24_window_check.py — common time-window sensitivity check for the Shakespeare-vs-rest comparison.

Question answered: do the within-genre differences between Shakespeare's plays and the other plays of the genre
persist when both groups are restricted to plays whose estimated first-performance / composition year falls in
one common window (default 1590–1613, the span of Shakespeare's own dated works in the three genres)?

What it does NOT do: it does not re-embed, re-cluster, re-review or change any measure; it does not control for
date (a common window is not a matched date distribution); it does not show that any difference is caused by
period; it does not reuse the full-period random reference (the random groups were drawn from the full genre).
It re-aggregates the existing work-level topic shares (aggregate/work_topic_share.csv) with the existing dates
(aggregate/chronology/dates_by_work.csv, 23_chronology.py: British Drama first, Annals fallback) under one rule
applied identically to both sides, and reports counts, coverage, topic means, differences and a descriptive JSD
for the full period and for the window side by side. Works whose bracketed date limits cross a window edge are
listed, and the same tables are repeated with those works placed by their lower limit and by their upper limit
(membership sensitivity); the window itself is fixed in advance and is not changed after seeing results.

Inputs (all existing files):  --agg <aggregate dir> (work_topic_share.csv, config.json, chronology/dates_by_work.csv,
shakespeare/topic_by_genre.csv + jsd.csv for the cross-check)  --sheet topic_sheet.csv
Outputs (--out, default <agg>/window_check/): window_works.csv, window_counts.csv, window_topic_means.csv,
window_top10.csv, window_jsd.csv, excluded_by_decade.csv, summary.md, methods.md, checks.json, provenance.json.
"""
import argparse, csv, datetime, hashlib, json, platform, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

SHAKES = 'Shakespeare, William'


def split_authors(v):   # as in 18 / 22
    return [p.strip() for p in re.split(r';\s*|(?<=[a-z])(?=[A-Z][a-z]+, )', v or '') if p.strip()]


def jsd(p, q):
    p = np.asarray(p, float); q = np.asarray(q, float); m = (p + q) / 2
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def profile(ws, topics, mode):
    M = np.array([[w[f't{t}'] for t in topics] for w in ws], float)
    v = M.mean(axis=0)
    if mode == 'cond':
        s = v.sum(); return v / s if s > 0 else v
    return np.append(v, max(0.0, 1.0 - v.sum()))


def both(A, B, topics):
    if not A or not B: return None, None
    pa, pb = profile(A, topics, 'cond'), profile(B, topics, 'cond')
    cond = None if pa.sum() == 0 or pb.sum() == 0 else jsd(pa, pb)
    return cond, jsd(profile(A, topics, 'rest'), profile(B, topics, 'rest'))


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def fint(v):
    try: return int(float(v))
    except (TypeError, ValueError): return None


def r4(x): return None if x is None else round(x, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agg', required=True); ap.add_argument('--sheet', required=True)
    ap.add_argument('--chronology', default=''); ap.add_argument('--shakespeare', default='')
    ap.add_argument('--window', default='1590,1613', help='inclusive year window, "lo,hi"')
    ap.add_argument('--genres', default='comedy,tragedy,history'); ap.add_argument('--use', default='included')
    ap.add_argument('--top', type=int, default=10); ap.add_argument('--out', default='')
    a = ap.parse_args()
    agg = Path(a.agg); chron = Path(a.chronology) if a.chronology else agg / 'chronology'; shk = Path(a.shakespeare) if a.shakespeare else agg / 'shakespeare'
    out = Path(a.out) if a.out else agg / 'window_check'; out.mkdir(parents=True, exist_ok=True)
    lo, hi = [int(x) for x in a.window.split(',')]
    genres = [g.strip() for g in a.genres.split(',') if g.strip()]
    uses = set(u.strip() for u in a.use.split(','))
    # ---- inputs -------------------------------------------------------------------------------------------------
    sheet = list(csv.DictReader(open(a.sheet, encoding='utf-8')))
    topics = sorted(int(r['topic']) for r in sheet if r.get('use_in_genre_analysis', '') in uses)
    label = {int(r['topic']): (r.get('Label') or r.get('draft_label') or '') for r in sheet}
    works_all = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8')))
    dates = {r['work_id']: r for r in csv.DictReader(open(chron / 'dates_by_work.csv', encoding='utf-8'))}
    for w in works_all:
        for t in topics: w[f't{t}'] = fnum(w.get(f't{t}')) or 0.0
        w['cat:included'] = fnum(w.get('cat:included')) or 0.0
    works = [w for w in works_all if w['genre_main'] in genres]
    for w in works:
        w['side'] = 'Shakespeare' if SHAKES in split_authors(w['author']) else 'other'
        d = dates.get(w['work_id'], {})
        w['adopted'] = fint(d.get('adopted_year')); w['lower'] = fint(d.get('lower_limit')); w['upper'] = fint(d.get('upper_limit'))
        w['date_kind'] = d.get('date_kind', ''); w['source_used'] = d.get('source_used', ''); w['flags'] = d.get('flags', '')
        yl = w['lower'] if w['lower'] is not None else w['adopted']; yu = w['upper'] if w['upper'] is not None else w['adopted']
        w['in_adopted'] = w['adopted'] is not None and lo <= w['adopted'] <= hi
        w['in_lower'] = yl is not None and lo <= yl <= hi
        w['in_upper'] = yu is not None and lo <= yu <= hi
        w['boundary'] = len({w['in_adopted'], w['in_lower'], w['in_upper']}) > 1
        w['undated'] = w['adopted'] is None
    variants = {'full': lambda w: True, 'window': lambda w: w['in_adopted'], 'window_by_lower_limit': lambda w: w['in_lower'], 'window_by_upper_limit': lambda w: w['in_upper']}
    # ---- per-genre tables ----------------------------------------------------------------------------------------
    counts_rows, means_rows, jsd_rows, top_rows, excl_rows = [], [], [], [], []
    checks = {'window': [lo, hi], 'topics': len(topics), 'genres': {}}
    ref_tbg = {}
    p = shk / 'topic_by_genre.csv'
    if p.exists():
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r['variant'] == 'attributed': ref_tbg[(r['genre'], int(r['topic']))] = r
    ref_jsd = {}
    p = shk / 'jsd.csv'
    if p.exists():
        for r in csv.DictReader(open(p, encoding='utf-8')):
            if r['variant'] == 'attributed' and r['profile'].startswith('conditional'): ref_jsd[r['genre']] = r
    summary = {}
    for g in genres:
        G = [w for w in works if w['genre_main'] == g]
        by = {}
        for vname, keep in variants.items():
            S = [w for w in G if w['side'] == 'Shakespeare' and keep(w)]; O = [w for w in G if w['side'] == 'other' and keep(w)]
            by[vname] = (S, O)
            cj, rj = both(S, O, topics)
            yS = [w['adopted'] for w in S if w['adopted'] is not None]; yO = [w['adopted'] for w in O if w['adopted'] is not None]
            counts_rows.append({'genre': g, 'variant': vname, 'n_shakespeare': len(S), 'n_other': len(O),
                                'coverage_shakespeare': r4(float(np.mean([w['cat:included'] for w in S])) if S else None), 'coverage_other': r4(float(np.mean([w['cat:included'] for w in O])) if O else None),
                                'median_year_shakespeare': int(np.median(yS)) if yS else None, 'median_year_other': int(np.median(yO)) if yO else None,
                                'iqr_year_shakespeare': f'{int(np.percentile(yS, 25))}–{int(np.percentile(yS, 75))}' if yS else '', 'iqr_year_other': f'{int(np.percentile(yO, 25))}–{int(np.percentile(yO, 75))}' if yO else ''})
            jsd_rows.append({'genre': g, 'variant': vname, 'n_shakespeare': len(S), 'n_other': len(O), 'jsd_cond_bits': r4(cj), 'jsd_rest_bits': r4(rj),
                             'note': 'descriptive; the full-period random reference does not apply to the window groups'})
        Sf, Of = by['full']; Sw, Ow = by['window']; Sl, Ol = by['window_by_lower_limit']; Su, Ou = by['window_by_upper_limit']
        checks['genres'][g] = {'n_full': [len(Sf), len(Of)], 'n_window': [len(Sw), len(Ow)], 'n_by_lower': [len(Sl), len(Ol)], 'n_by_upper': [len(Su), len(Ou)],
                               'shakespeare_outside_window': [w['title'] for w in Sf if not w['in_adopted']], 'undated': [w['title'] for w in G if w['undated']],
                               'boundary_works': [w['title'] for w in G if w['boundary']]}
        # full-period cross-check against 18's table
        if ref_tbg:
            errs = []
            for t in topics:
                r = ref_tbg.get((g, t))
                if not r: continue
                mS = float(np.mean([w[f't{t}'] for w in Sf])); mO = float(np.mean([w[f't{t}'] for w in Of]))
                if abs(mS - float(r['mean_shakespeare'])) > 1e-4 or abs(mO - float(r['mean_others'])) > 1e-4: errs.append(t)
            checks['genres'][g]['full_period_means_match_topic_by_genre'] = (not errs); checks['genres'][g]['mismatching_topics'] = errs
            rr = ref_tbg.get((g, topics[0]))
            if rr: checks['genres'][g]['full_period_counts_match_18'] = (rr['works_with_topic_shakespeare'].split('/')[1] == str(len(Sf)) and rr['works_with_topic_others'].split('/')[1] == str(len(Of)))
        if ref_jsd.get(g):
            cj, _ = both(Sf, Of, topics)
            checks['genres'][g]['full_period_jsd_matches_18'] = abs((cj or 0) - float(ref_jsd[g]['jsd_bits'])) < 5e-4
        # topic means
        def mean_of(ws, t): return float(np.mean([w[f't{t}'] for w in ws])) if ws else None
        def nwith(ws, t): return sum(1 for w in ws if w[f't{t}'] > 0)
        per_topic = {}
        for t in topics:
            row = {'genre': g, 'topic': t, 'label': label[t]}
            for vname, (S, O) in by.items():
                mS, mO = mean_of(S, t), mean_of(O, t)
                key = {'full': 'full', 'window': 'win', 'window_by_lower_limit': 'lower', 'window_by_upper_limit': 'upper'}[vname]
                row[f'mean_S_{key}_pct'] = r4(100 * mS) if mS is not None else None; row[f'mean_O_{key}_pct'] = r4(100 * mO) if mO is not None else None
                row[f'diff_{key}_pp'] = r4(100 * (mS - mO)) if (mS is not None and mO is not None) else None
                row[f'works_with_topic_S_{key}'] = f'{nwith(S, t)}/{len(S)}'; row[f'works_with_topic_O_{key}'] = f'{nwith(O, t)}/{len(O)}'
            row['change_in_diff_pp'] = r4(row['diff_win_pp'] - row['diff_full_pp']) if (row['diff_win_pp'] is not None and row['diff_full_pp'] is not None) else None
            row['sign_change'] = 'yes' if (row['diff_win_pp'] is not None and row['diff_full_pp'] is not None and row['diff_win_pp'] * row['diff_full_pp'] < 0 and abs(row['diff_full_pp']) >= 0.05) else ''
            means_rows.append(row); per_topic[t] = row
        # the paper's top-10 (full-period rule: simple average of the two group means) and the window's own top-10
        top_full = sorted(topics, key=lambda t: -(per_topic[t]['mean_S_full_pct'] + per_topic[t]['mean_O_full_pct']) / 2)[:a.top]
        top_win = sorted(topics, key=lambda t: -((per_topic[t]['mean_S_win_pct'] or 0) + (per_topic[t]['mean_O_win_pct'] or 0)) / 2)[:a.top]
        for rank, t in enumerate(top_full, 1):
            r = per_topic[t]
            top_rows.append({'genre': g, 'rank_full': rank, 'topic': t, 'label': label[t], 'mean_S_full_pct': r['mean_S_full_pct'], 'mean_O_full_pct': r['mean_O_full_pct'], 'diff_full_pp': r['diff_full_pp'],
                             'mean_S_win_pct': r['mean_S_win_pct'], 'mean_O_win_pct': r['mean_O_win_pct'], 'diff_win_pp': r['diff_win_pp'], 'change_in_diff_pp': r['change_in_diff_pp'],
                             'works_with_topic_S_win': r['works_with_topic_S_win'], 'works_with_topic_O_win': r['works_with_topic_O_win'],
                             'in_window_top10': 'yes' if t in top_win else 'no', 'rank_in_window_top10': (top_win.index(t) + 1) if t in top_win else ''})
        # what the window removes
        dec = Counter(); au = Counter()
        for w in Of:
            if not w['in_adopted']:
                dec[(w['adopted'] // 10 * 10) if w['adopted'] is not None else 'undated'] += 1
                for x in split_authors(w['author']): au[x] += 1
        for k, n in sorted(dec.items(), key=lambda kv: (str(kv[0]))):
            excl_rows.append({'genre': g, 'side': 'other', 'decade': k, 'n_excluded': n})
        summary[g] = {'n': (len(Sf), len(Of), len(Sw), len(Ow)), 'top_full': top_full, 'top_win': top_win, 'per_topic': per_topic,
                      'excluded_authors': au.most_common(6), 'excluded_decades': dict(dec), 'cov': (counts_rows[-4], counts_rows[-3]),
                      'jsd': (jsd_rows[-4], jsd_rows[-3])}
    # ---- write --------------------------------------------------------------------------------------------------
    def wcsv(name, rows, fields=None):
        if not rows: return
        fields = fields or list(rows[0].keys())
        with open(out / name, 'w', newline='', encoding='utf-8') as f:
            wr = csv.DictWriter(f, fieldnames=fields); wr.writeheader(); wr.writerows(rows)
    wrows = []
    for w in sorted(works, key=lambda w: (genres.index(w['genre_main']), w['side'] != 'Shakespeare', w['adopted'] or 0, w['title'])):
        wrows.append({'genre': w['genre_main'], 'side': w['side'], 'work_id': w['work_id'], 'title': w['title'], 'author_field': w['author'], 'adopted_year': w['adopted'], 'lower_limit': w['lower'], 'upper_limit': w['upper'],
                      'date_kind': w['date_kind'], 'source_used': w['source_used'], 'flags': w['flags'], 'in_window': 'yes' if w['in_adopted'] else 'no', 'in_window_by_lower_limit': 'yes' if w['in_lower'] else 'no',
                      'in_window_by_upper_limit': 'yes' if w['in_upper'] else 'no', 'boundary_work': 'yes' if w['boundary'] else '', 'undated': 'yes' if w['undated'] else '', 'included_share': r4(w['cat:included'])})
    wcsv('window_works.csv', wrows); wcsv('window_counts.csv', counts_rows); wcsv('window_topic_means.csv', means_rows); wcsv('window_top10.csv', top_rows); wcsv('window_jsd.csv', jsd_rows); wcsv('excluded_by_decade.csv', excl_rows)
    # summary
    L = [f'# Common time-window check ({lo}–{hi})', '',
         f'This is a **time-window sensitivity check**, not a comparison in which date has been controlled. Both groups (Shakespeare\'s plays; all other plays of the genre) are restricted by the same rule — estimated first-performance / composition year (British Drama first, Annals fallback, as on the Chronology page) between {lo} and {hi} inclusive — and the existing work-level topic shares are re-aggregated with the measure unchanged (one representative edition per work, works equal-weighted, share of all words, {len(topics)} {a.use} topics). Nothing is re-embedded, re-clustered or re-reviewed; the full-period results are not replaced. The window is the span of Shakespeare\'s own dated works in these genres and was fixed before the results were seen. The full-period random reference does not apply to the window groups and is not reused. A difference that persists in the window is not thereby shown to be independent of date, and a difference that shrinks is not thereby shown to be caused by date; the check only says what remains when the earliest and latest plays are set aside.', '']
    for g in genres:
        s = summary[g]; nSf, nOf, nSw, nOw = s['n']
        c_full, c_win = s['cov']; j_full, j_win = s['jsd']
        L += [f'## {g.capitalize()}', '',
              f'Works: Shakespeare {nSf} → {nSw} in the window; others {nOf} → {nOw}. Mean included-topic coverage: Shakespeare {100 * (c_full["coverage_shakespeare"] or 0):.1f} % → {100 * (c_win["coverage_shakespeare"] or 0):.1f} %; others {100 * (c_full["coverage_other"] or 0):.1f} % → {100 * (c_win["coverage_other"] or 0):.1f} %. '
              f'JSD on the selected topics (descriptive): {j_full["jsd_cond_bits"]} → {j_win["jsd_cond_bits"]} bits; with the rest bin {j_full["jsd_rest_bits"]} → {j_win["jsd_rest_bits"]}. '
              f'Dates inside the window are still not matched: median adopted year Shakespeare {c_win["median_year_shakespeare"]} (IQR {c_win["iqr_year_shakespeare"]}) vs others {c_win["median_year_other"]} (IQR {c_win["iqr_year_other"]}).',
              'Other plays set aside by decade: ' + (', '.join(f'{k}s: {n}' if k != 'undated' else f'undated: {n}' for k, n in sorted(s['excluded_decades'].items(), key=lambda kv: str(kv[0]))) or 'none') + '. Authors most represented among them: ' + (', '.join(f'{x} ({n})' for x, n in s['excluded_authors']) or 'none') + '.', '',
              '| topic | Shakespeare full → window (%) | others full → window (%) | difference full → window (pp) | works with topic, window (S / others) |', '|---|---|---|---|---|']
        for t in s['top_full']:
            r = s['per_topic'][t]
            L.append(f'| T{t} {label[t]} | {r["mean_S_full_pct"]:.2f} → {r["mean_S_win_pct"]:.2f} | {r["mean_O_full_pct"]:.2f} → {r["mean_O_win_pct"]:.2f} | {r["diff_full_pp"]:+.2f} → {r["diff_win_pp"]:+.2f} | {r["works_with_topic_S_win"]} / {r["works_with_topic_O_win"]} |')
        big = sorted([r for r in s['per_topic'].values() if r['change_in_diff_pp'] is not None and (abs(r['change_in_diff_pp']) >= 1.0 or r['sign_change'])], key=lambda r: -abs(r['change_in_diff_pp']))
        L += ['', 'Topics whose difference of means moves by ≥ 1 pp or changes sign (all selected topics): ' + (', '.join(f'T{r["topic"]} {label[r["topic"]]} ({r["diff_full_pp"]:+.2f} → {r["diff_win_pp"]:+.2f}{", sign change" if r["sign_change"] else ""})' for r in big) or 'none') + '.',
              'The paper\'s ten topics (full-period rule) that leave the window\'s own top ten: ' + (', '.join(f'T{t}' for t in s['top_full'] if t not in s['top_win']) or 'none') + '; entering: ' + (', '.join(f'T{t}' for t in s['top_win'] if t not in s['top_full']) or 'none') + '.', '']
    L += ['## Membership sensitivity', '', 'window_topic_means.csv and window_counts.csv repeat every value with the works whose bracketed date limits cross a window edge placed by their lower limit and by their upper limit (boundary works listed in checks.json). These are boundary cases for the membership rule, not alternative datings, and the window itself is not changed.', '']
    (out / 'summary.md').write_text('\n'.join(L), encoding='utf-8')
    (out / 'methods.md').write_text(__doc__.strip() + f'\n\nRun {datetime.date.today().isoformat()}: window {lo}–{hi}; genres {", ".join(genres)}; {len(topics)} topics ({a.use}).\n', encoding='utf-8')
    json.dump(checks, open(out / 'checks.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    prov = {'script': Path(__file__).name, 'date': datetime.datetime.now().isoformat(timespec='seconds'), 'python': platform.python_version(), 'numpy': np.__version__, 'args': vars(a),
            'inputs': {str(p): sha256(p) for p in [agg / 'work_topic_share.csv', chron / 'dates_by_work.csv', Path(a.sheet)] + ([shk / 'topic_by_genre.csv'] if (shk / 'topic_by_genre.csv').exists() else [])}}
    json.dump(prov, open(out / 'provenance.json', 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print(f'window check → {out}'); print(json.dumps({g: {k: v for k, v in c.items() if k in ('n_full', 'n_window', 'full_period_means_match_topic_by_genre', 'full_period_jsd_matches_18', 'full_period_counts_match_18')} for g, c in checks['genres'].items()}, indent=1))


if __name__ == '__main__':
    main()
