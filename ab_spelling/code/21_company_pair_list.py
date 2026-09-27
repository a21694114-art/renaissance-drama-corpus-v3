#!/usr/bin/env python3
"""
21_company_pair_list.py — the work list for one company-pair comparison within one genre
(preparation only: no topic comparison, no tests).

Reads company_fields_by_work.csv (made by 20_company_coverage.py) and lists
  * group A / group B: works whose company value in the chosen source (default British Drama
    first-performance company) is exactly the named company with status 'clear' and whose
    genre_main is the chosen genre;
  * candidates: other works of that genre that any source links to either company (uncertain
    '(?)' values, multiple values, the other first-performance source, the title page, or a
    spelling variant) — listed for the attribution decision, not counted in A or B.
For every work: both first-performance companies and the title-page company, the attribution
divergences between them, both sources' dates with limits and flags, publication year, authors
(individuals; collaboration flagged), share of words in the included topics, outlier share.

Common period: for each source the point years of A and of B give a range; their overlap is
the window of that source; the proposal is the intersection of the sources' windows (strict)
— nothing is assigned by a single year. Each work is then placed relative to the strict window:
  core                         every point year inside and every bracketed limit inside
  boundary — limits            point years inside, but a limit extends beyond the window
  boundary — sources disagree  one source's point year inside, the other's outside
  outside                      all point years outside (whether limits reach the window is noted)
The extended band is the hull of the strict window and the intervals of the boundary works.

Outputs (--out, default <company dir>/pair_<A>_vs_<B>_<genre>/): pair_works.csv, pair_summary.md
"""
import argparse, csv, collections, re, statistics
from pathlib import Path


def slug(s):
    return re.sub(r'[^A-Za-z0-9]+', '_', s).strip('_')


def norm(s):
    return (s or '').replace('’', "'").replace('‘', "'")


def tokens(s):
    return frozenset(t for t in re.findall(r'[a-z0-9]+', norm(s).lower().replace("'s", 's')) if t not in ('of', 'the'))


def interval(r, tag):
    y = r[f'date_{tag}_year']
    if y == '': return None
    y = int(y); lo = int(r[f'date_{tag}_low']) if r[f'date_{tag}_low'] != '' else y; hi = int(r[f'date_{tag}_high']) if r[f'date_{tag}_high'] != '' else y
    return y, min(lo, y), max(hi, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--company-dir', required=True, help='aggregate/company/ of the run (company_fields_by_work.csv)')
    ap.add_argument('--a', required=True); ap.add_argument('--b', required=True)
    ap.add_argument('--genre', required=True)
    ap.add_argument('--source', default='britdrama', choices=['britdrama', 'annals'])
    ap.add_argument('--related', action='append', default=[], help='"A:Name" or "B:Name" — a predecessor / successor name (see company_lineage_notes.csv) whose works of the genre are listed separately, not counted')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    cdir = Path(a.company_dir); out = Path(a.out) if a.out else cdir / f'pair_{slug(a.a)}_vs_{slug(a.b)}_{a.genre}'; out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(cdir / 'company_fields_by_work.csv', encoding='utf-8')))
    col = {'britdrama': 'company_brit', 'annals': 'company_annals'}[a.source]
    other = {'britdrama': 'company_annals', 'annals': 'company_brit'}[a.source]
    names = {'A': a.a, 'B': a.b}; tk = {k: tokens(v) for k, v in names.items()}

    def mentions(r, key):
        """where a company name (or a spelling variant of it) appears in the three sources of a work"""
        hits = []
        for lab, c in (('britdrama', 'company_brit'), ('annals', 'company_annals'), ('title page', 'company_titlepage')):
            raw = r[c + '_raw']; base = r[c + '_base']; comps = r[c + '_components'].split(' | ') if r[c + '_components'] else []
            parts = comps if comps else ([base] if base else [])
            for p in parts:
                if p == names[key] or (tk[key] and (tk[key] <= tokens(p) or tokens(p) <= tk[key])):
                    hits.append(f'{lab}: {raw}')
                    break
        return hits

    def attribution_note(r, key):
        """how the other first-performance source and the title page relate to the group's company"""
        notes = []
        o_raw, o_st, o_base = r[other + '_raw'], r[other + '_status'], r[other + '_base']
        olab = 'Annals' if other == 'company_annals' else 'British Drama'
        if o_st == 'clear' and o_base == names[key]: notes.append(f'{olab}: same')
        elif o_st == 'uncertain' and o_base == names[key]: notes.append(f'{olab}: same name with (?)')
        elif o_st.startswith('multiple'): notes.append(f'{olab}: multiple — {o_raw}')
        elif o_st in ('clear', 'uncertain'): notes.append(f'{olab}: DIFFERS — {o_raw}')
        else: notes.append(f'{olab}: {o_raw}')
        t_raw, t_st, t_base = r['company_titlepage_raw'], r['company_titlepage_status'], r['company_titlepage_base']
        if t_st == 'clear' and t_base == names[key]: notes.append('title page: same')
        elif t_st.startswith('multiple'): notes.append(f'title page: multiple — {t_raw}')
        elif t_st == 'clear': notes.append(f'title page: DIFFERS — {t_raw}')
        else: notes.append(f'title page: {t_raw}')
        return '; '.join(notes)

    # ---- groups and candidates --------------------------------------------------------------
    listed = []
    for r in rows:
        if r['genre_main'] != a.genre: continue
        grp = ''
        for key in ('A', 'B'):
            if r[col + '_base'] == names[key] and r[col + '_status'] == 'clear': grp = key
        if grp:
            listed.append((grp, r, attribution_note(r, grp), '')); continue
        links = {key: mentions(r, key) for key in ('A', 'B')}
        if links['A'] or links['B']:
            link = '; '.join(f'{names[k]} ← ' + ' | '.join(v) for k, v in links.items() if v)
            listed.append(('candidate', r, f"{a.source}: {r[col + '_raw']} ({r[col + '_status']})", link))

    # ---- common period ----------------------------------------------------------------------
    yrs = {src: {k: sorted(int(r[f'date_{src}_year']) for g, r, _, _ in listed if g == k and r[f'date_{src}_year'] != '') for k in ('A', 'B')} for src in ('brit', 'annals')}
    win = {}
    for src in ('brit', 'annals'):
        if yrs[src]['A'] and yrs[src]['B']:
            lo = max(min(yrs[src]['A']), min(yrs[src]['B'])); hi = min(max(yrs[src]['A']), max(yrs[src]['B']))
            win[src] = (lo, hi)
    strict = (max(w[0] for w in win.values()), min(w[1] for w in win.values())) if win else None

    def place(r):
        if not strict: return '', ''
        lo, hi = strict; ivs = {s: interval(r, s) for s in ('brit', 'annals')}; ivs = {s: v for s, v in ivs.items() if v}
        if not ivs: return 'no date', ''
        inside = {s: lo <= v[0] <= hi for s, v in ivs.items()}
        lim_out = [f'{s} limits {v[1]}–{v[2]}' for s, v in ivs.items() if v[1] < lo or v[2] > hi]
        if all(inside.values()):
            return ('core', '') if not lim_out else ('boundary — limits', '; '.join(lim_out))
        if any(inside.values()):
            return 'boundary — sources disagree', '; '.join(f'{s} {v[0]}' + (' (in)' if inside[s] else ' (out)') for s, v in ivs.items())
        reach = [s for s, v in ivs.items() if v[1] <= hi and v[2] >= lo]
        return 'outside', ('limits reach the window: ' + ', '.join(reach)) if reach else ''

    recs = []
    for g, r, note, link in listed:
        tier, why = place(r)
        recs.append({'group': {'A': 'A: ' + names['A'], 'B': 'B: ' + names['B'], 'candidate': 'candidate (not in A or B)'}[g],
                     'work_id': r['work_id'], 'title': r['title'], 'author': r['author'], 'n_individual_authors': len(r['author'].split(' / ')),
                     'collaboration': 'Y' if ' / ' in r['author'] else '',
                     f'company_{a.source}_raw': r[col + '_raw'], f'company_{a.source}_status': r[col + '_status'],
                     f'company_{"annals" if a.source == "britdrama" else "britdrama"}_raw': r[other + '_raw'], 'company_titlepage_raw': r['company_titlepage_raw'],
                     'attribution_note': note, 'candidate_link': link,
                     'date_brit_raw': r['date_brit_raw'], 'date_brit_year': r['date_brit_year'], 'date_brit_low': r['date_brit_low'], 'date_brit_high': r['date_brit_high'], 'date_brit_flags': r['date_brit_flags'],
                     'date_annals_raw': r['date_annals_raw'], 'date_annals_year': r['date_annals_year'], 'date_annals_low': r['date_annals_low'], 'date_annals_high': r['date_annals_high'], 'date_annals_flags': r['date_annals_flags'],
                     'date_annals_vs_brit': r['date_annals_vs_brit'], 'date_publication': r['date_publication_raw'], 'play_type_raw': r['play_type_raw'],
                     'included_share': r['included_share'], 'outlier_share': r['outlier_share'], 'words_mean': r['words_mean'],
                     'window_strict': f'{strict[0]}–{strict[1]}' if strict else '', 'window_placement': tier, 'window_note': why})
    order = {'A': 0, 'B': 1, 'c': 2}
    recs.sort(key=lambda d: (order[d['group'][0]], int(d['date_brit_year'] or d['date_annals_year'] or 0), d['title']))
    with open(out / 'pair_works.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(recs[0].keys())); wr.writeheader(); wr.writerows(recs)

    # ---- summary ---------------------------------------------------------------------------
    def fmt(v): return f'{float(v):.2f}' if v not in ('', None) else ''
    A = [d for d in recs if d['group'].startswith('A')]; B = [d for d in recs if d['group'].startswith('B')]; C = [d for d in recs if d['group'].startswith('c')]
    md = [f'# {names["A"]} vs {names["B"]} — {a.genre}: work list and common period', '',
          f'Groups by the {a.source} first-performance company, status clear, genre_main = {a.genre}: A {len(A)} works, B {len(B)} works; {len(C)} further {a.genre} works are linked to one of the two names by some source or status (candidates, not counted).', '',
          'Attribution divergences are marked DIFFERS in the attribution_note column; dates are given for both sources with their bracketed limits; nothing is merged or assigned by a single year. '
          'The title-page company is that of the representative edition (the earliest edition under the selection policy) and can name a later company than the first performance.', '']
    for lab, grp in (('A', A), ('B', B)):
        md += [f'## {lab}: {names[lab]} ({len(grp)} works)', '', '| work | author | Annals company | title page | British Drama date | Annals date | publ. | included share | placement |', '|---|---|---|---|---|---|---|---:|---|']
        for d in grp:
            md.append(f'| {d["title"][:45]} ({d["work_id"]}) | {d["author"][:40]} | {d["company_annals_raw"] if a.source == "britdrama" else d["company_britdrama_raw"]} | {d["company_titlepage_raw"]} | {d["date_brit_raw"]} | {d["date_annals_raw"]} | {d["date_publication"]} | {fmt(d["included_share"])} | {d["window_placement"]}{(" (" + d["window_note"] + ")") if d["window_note"] else ""} |')
        inc = [float(d['included_share']) for d in grp]
        ind = collections.Counter(p for d in grp for p in d['author'].split(' / '))
        md += ['', f'Authors: {len(ind)} individuals ({", ".join(f"{k} {v}" for k, v in ind.most_common(4))}); collaborations {sum(1 for d in grp if d["collaboration"])}. '
               f'Included-topic share: mean {statistics.mean(inc):.3f}, range {min(inc):.2f}–{max(inc):.2f}. '
               f'British Drama years: {", ".join(str(y) for y in yrs["brit"][lab])}. Annals years: {", ".join(str(y) for y in yrs["annals"][lab])}.', '']
    md += ['## Attribution divergences inside A and B', '']
    div = [d for d in A + B if 'DIFFERS' in d['attribution_note'] or 'multiple' in d['attribution_note'] or '(?)' in d['attribution_note']]
    md += [f'- {d["title"][:45]} ({d["work_id"]}, {d["group"][0]}): {d["attribution_note"]}' for d in div] or ['- none']
    md += ['', f'## Candidates linked to either name but not in A or B ({len(C)})', '']
    md += [f'- {d["title"][:45]} ({d["work_id"]}): {a.source} = {d[f"company_{a.source}_raw"]} [{d[f"company_{a.source}_status"]}]; {d["candidate_link"]}; dates {d["date_brit_raw"]} / {d["date_annals_raw"]}' for d in C] or ['- none']
    rel = []
    for spec in a.related:
        key, _, nm = spec.partition(':'); key = key.strip().upper(); nm = nm.strip()
        for r in rows:
            if r['genre_main'] != a.genre or any(r['work_id'] == d['work_id'] for d in recs): continue
            hits = [f'{lab}: {r[c + "_raw"]}' for lab, c in (('britdrama', 'company_brit'), ('annals', 'company_annals'), ('title page', 'company_titlepage'))
                    if r[c + '_base'] == nm or (r[c + '_components'] and nm in r[c + '_components'].split(' | '))]
            if hits: rel.append((key, nm, r, ' | '.join(hits)))
    if a.related:
        md += ['', '## Works under a related name (lineage note; listed only, not counted)', '']
        md += [f'- [{k}: {nm}] {r["title"][:45]} ({r["work_id"]}), {r["author"][:30]}: {hits}; dates {r["date_brit_raw"]} / {r["date_annals_raw"]}; included share {fmt(r["included_share"])}' for k, nm, r, hits in rel] or ['- none']
        with open(out / 'pair_related_names.csv', 'w', newline='', encoding='utf-8') as f:
            wr = csv.writer(f); wr.writerow(['group', 'related_name', 'work_id', 'title', 'author', 'where_named', 'date_brit_raw', 'date_annals_raw', 'date_publication', 'included_share'])
            wr.writerows([[k, nm, r['work_id'], r['title'], r['author'], hits, r['date_brit_raw'], r['date_annals_raw'], r['date_publication_raw'], r['included_share']] for k, nm, r, hits in rel])
    md += ['', '## Common period', '']
    for src, w in win.items():
        md.append(f'- {src}: A {min(yrs[src]["A"])}–{max(yrs[src]["A"])}, B {min(yrs[src]["B"])}–{max(yrs[src]["B"])} → overlap of point years {w[0]}–{w[1]}')
    if strict:
        bw = [d for d in A + B if d['window_placement'].startswith('boundary')]
        ext_lo, ext_hi = strict
        for d in bw:
            for s in ('brit', 'annals'):
                if d[f'date_{s}_year'] != '':
                    lo = int(d[f'date_{s}_low'] or d[f'date_{s}_year']); hi = int(d[f'date_{s}_high'] or d[f'date_{s}_year']); ext_lo = min(ext_lo, lo); ext_hi = max(ext_hi, hi)
        def n(tiers, g): return sum(1 for d in A + B if d['window_placement'] in tiers and d['group'][0] == g)
        md += [f'- strict window (intersection of the sources): **{strict[0]}–{strict[1]}**; extended band including the boundary works\' limits: {ext_lo}–{ext_hi}',
               f'- sizes if the window is applied at different tolerances (for the decision, not a recommendation): core only A {n(["core"], "A")} / B {n(["core"], "B")}; '
               f'core + boundary by limits A {n(["core", "boundary — limits"], "A")} / B {n(["core", "boundary — limits"], "B")}; '
               f'+ sources disagree A {n(["core", "boundary — limits", "boundary — sources disagree"], "A")} / B {n(["core", "boundary — limits", "boundary — sources disagree"], "B")}; all A {len(A)} / B {len(B)}', '']
        for tier in ('core', 'boundary — limits', 'boundary — sources disagree', 'outside'):
            ws = [d for d in A + B if d['window_placement'] == tier]
            md.append(f'### {tier} ({len(ws)}: A {sum(1 for d in ws if d["group"][0] == "A")}, B {sum(1 for d in ws if d["group"][0] == "B")})')
            md += [f'- {d["title"][:45]} ({d["group"][0]}) — BritDrama {d["date_brit_raw"]}; Annals {d["date_annals_raw"]}' + (f' — {d["window_note"]}' if d['window_note'] else '') for d in ws] or ['- none']
            md.append('')
    md += ['Placement is relative to the strict window and is descriptive: a boundary work is one whose dating (limits or the two sources) does not settle whether it belongs to the common period; the decision is left open.', '']
    (out / 'pair_summary.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
