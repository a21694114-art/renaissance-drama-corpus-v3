#!/usr/bin/env python3
"""19_play_distances.py — reading single plays distributionally (the WSC "Handout 3" analysis on the new model).

    python 19_play_distances.py --agg <topics_B_s42/aggregate> --sheet <topics_B_s42/topic_sheet.csv> [--use included] [--out <dir>]

For every work, its topic profile (share of the work's words in each compared topic, representative edition,
renormalised over the compared topics) is compared with the mean profile of every genre group — the work's own
genre profile computed WITHOUT the work (leave-one-out). Distance = Jensen–Shannon divergence (bits). For each
work the table gives its distance to every genre, the nearest genre, and the "comedy lean" = distance to comedy
minus distance to the work's own genre (negative = its material sits closer to the comedy profile than to its own
genre's). A percentile places each Shakespeare play among all works of its genre group, so "closest to comedy of
his tragedies" can be read against "closest to comedy of all tragedies".
Decomposition: for each Shakespeare play, the topics that pull it towards comedy — those in which the play's share
exceeds its own genre's mean and the comedy mean exceeds it too — with the three shares side by side.
Outputs (in --out, default <agg>/shakespeare/): play_distances.csv (all works), shakespeare_play_distances.csv,
shakespeare_play_pull.csv (per play, the pulling topics), othello_panel.png (his tragedies' comedy lean + one
play's distances in full), play_distances_summary.md.
"""
import argparse, csv, json
from collections import defaultdict
from pathlib import Path
import numpy as np

BLUE, ORANGE, GREY, MUTED, RED = '#2a78d6', '#eb6834', '#c9c9c4', '#52514e', '#e34948'
SNYDER = ('Romeo and Juliet', 'Hamlet, Prince of Denmark', 'Othello, the Moor of Venice', 'King Lear')


def ordinal(n):
    n = int(round(n)); return f'{n}{"th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")}'


def jsd(p, q):
    p = np.asarray(p, float); q = np.asarray(q, float); m = (p + q) / 2
    def kl(a, b):
        mask = a > 0; return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agg', required=True); ap.add_argument('--sheet', required=True); ap.add_argument('--use', default='')
    ap.add_argument('--focus', default='Othello, the Moor of Venice'); ap.add_argument('--out', default='')
    a = ap.parse_args()
    agg = Path(a.agg); out = Path(a.out) if a.out else agg / 'shakespeare'; out.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(agg / 'config.json')) if (agg / 'config.json').exists() else {}
    use = [u.strip() for u in a.use.split(',') if u.strip()] or cfg.get('use') or ['included']
    sheet = {int(r['topic']): r for r in csv.DictReader(open(a.sheet, encoding='utf-8'))}
    topics = sorted(t for t, r in sheet.items() if (r.get('use_in_genre_analysis') or '') in use)
    name = {t: (sheet[t].get('Label') or sheet[t].get('draft_label') or f'topic {t}') for t in topics}
    works = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8')))
    genres = cfg.get('genres_tested') or sorted({w['genre_main'] for w in works if w['genre_main'] != 'other/multi'})
    V = {w['work_id']: np.array([float(w[f't{t}']) for t in topics]) for w in works}
    cover = {k: v.sum() for k, v in V.items()}
    P = {k: (v / v.sum() if v.sum() > 0 else v) for k, v in V.items()}                    # conditional profile
    by_g = defaultdict(list)
    for w in works: by_g[w['genre_main']].append(w['work_id'])
    PR = {k: np.append(v, max(0.0, 1.0 - v.sum())) for k, v in V.items()}               # profile with the rest of the words as one bin
    def genre_profile(g, exclude=None, rest=False):
        ids = [k for k in by_g[g] if k != exclude]
        m = np.mean([V[k] for k in ids], axis=0)
        if rest: return np.append(m, max(0.0, 1.0 - m.sum())), len(ids)
        return m / m.sum() if m.sum() > 0 else m, len(ids)
    rows = []
    for w in works:
        k = w['work_id']; g = w['genre_main']
        if cover[k] <= 0: continue
        d = {}; dr = {}
        for h in genres:
            prof, n = genre_profile(h, exclude=k if h == g else None); d[h] = jsd(P[k], prof)
            profr, _ = genre_profile(h, exclude=k if h == g else None, rest=True); dr[h] = jsd(PR[k], profr)
        nearest = min(d, key=d.get)
        r = {'work_id': k, 'title': w['title'], 'author': w['author'], 'year_first': w['year_first'], 'genre_main': g, 'shakespeare': 'yes' if 'shakespeare' in w['author'].lower() else '',
             'compared_topics_share_of_words': round(cover[k], 4), 'nearest_genre': nearest, 'own_genre_tested': 'yes' if g in genres else ''}
        for h in genres: r[f'd_{h}'] = round(d[h], 4)
        r['comedy_lean'] = round(d['comedy'] - d[g], 4) if (g in d and 'comedy' in d and g != 'comedy') else ''
        r['comedy_lean_with_rest_bin'] = round(dr['comedy'] - dr[g], 4) if (g in dr and 'comedy' in dr and g != 'comedy') else ''
        rows.append(r)
    # percentile of the comedy lean within the genre (lower = closer to comedy than most of the genre)
    for g in genres:
        vals = sorted(float(r['comedy_lean']) for r in rows if r['genre_main'] == g and r['comedy_lean'] != '')
        for r in rows:
            if r['genre_main'] == g and r['comedy_lean'] != '':
                r['comedy_lean_percentile_in_genre'] = round(100 * sum(1 for v in vals if v < float(r['comedy_lean'])) / len(vals), 1)
    rows.sort(key=lambda r: (r['genre_main'], r['title']))
    cols = list(rows[0]) + (['comedy_lean_percentile_in_genre'] if 'comedy_lean_percentile_in_genre' not in rows[0] else [])
    with open(out / 'play_distances.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(rows)
    shak = [r for r in rows if r['shakespeare']]
    with open(out / 'shakespeare_play_distances.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(shak)

    # ---- what pulls a play towards comedy: topics where play > own genre and comedy > own genre
    pull = []
    for r in shak:
        k = r['work_id']; g = r['genre_main']
        if g not in genres or g == 'comedy': continue
        own, _ = genre_profile(g, exclude=k); com, _ = genre_profile('comedy')
        own_raw = np.mean([V[x] for x in by_g[g] if x != k], axis=0); com_raw = np.mean([V[x] for x in by_g['comedy']], axis=0)
        for i, t in enumerate(topics):
            if V[k][i] > own_raw[i] and com_raw[i] > own_raw[i]:
                pull.append({'work_id': k, 'title': r['title'], 'genre_main': g, 'topic': t, 'label': name[t], 'play_share': round(100 * V[k][i], 2),
                             'own_genre_mean_without_play': round(100 * own_raw[i], 2), 'comedy_mean': round(100 * com_raw[i], 2), 'excess_over_own_genre_pp': round(100 * (V[k][i] - own_raw[i]), 2)})
    pull.sort(key=lambda r: (r['title'], -r['excess_over_own_genre_pp']))
    with open(out / 'shakespeare_play_pull.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(pull[0]) if pull else ['work_id']); wr.writeheader(); wr.writerows(pull)

    # ---- figure: his tragedies' comedy lean + the focus play's distances in full
    trag = sorted([r for r in shak if r['genre_main'] == 'tragedy' and r['comedy_lean'] != ''], key=lambda r: float(r['comedy_lean']))
    focus = next((r for r in rows if r['title'] == a.focus), None)
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size': 10.5})
        n_trag = sum(1 for r in rows if r['genre_main'] == 'tragedy')
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 0.42 * len(trag) + 3.0), gridspec_kw={'width_ratios': [1.7, 1]})
        y = np.arange(len(trag)); vals = [float(r['comedy_lean']) for r in trag]
        cols_ = [RED if r['title'] == a.focus else (BLUE if r['title'] in SNYDER else GREY) for r in trag]
        ax1.barh(y, vals, color=cols_, height=0.62); ax1.invert_yaxis()          # most comedy-leaning at the top
        ax1.axvline(0, color=MUTED, lw=1)
        for i, r in enumerate(trag):
            ax1.text(max(vals[i], 0) + 0.006, y[i], f'{vals[i]:+.3f}   {ordinal(r["comedy_lean_percentile_in_genre"])} percentile of the {n_trag} tragedies', va='center', ha='left', fontsize=8.5, color=MUTED)
        ax1.set_yticks(y); ax1.set_yticklabels([r['title'].split(' (')[0][:30] + (' *' if r['title'] in SNYDER else '') + f'  ({100 * float(r["compared_topics_share_of_words"]):.0f} %)' for r in trag])
        ax1.set_xlabel('d(comedy profile) − d(tragedy profile), bits;  negative = closer to comedy')
        ax1.set_title('Shakespeare\'s tragedies: lean towards the comedy profile', loc='left', fontsize=11)
        lim = max(abs(v) for v in vals); ax1.set_xlim(-lim * 1.25, lim * 2.3)
        for sp in ('top', 'right'): ax1.spines[sp].set_visible(False)
        ax1.grid(axis='x', color='#eeeeea'); ax1.set_axisbelow(True)
        if focus:
            ds = sorted(((h, float(focus[f'd_{h}'])) for h in genres), key=lambda kv: kv[1])
            y2 = np.arange(len(ds))
            ax2.barh(y2, [v for _, v in ds], color=[RED if h == focus['genre_main'] else BLUE for h, _ in ds], height=0.62)
            for i, (h, v) in enumerate(ds): ax2.text(v + 0.008, y2[i], f'{v:.3f}', va='center', fontsize=8.5, color=MUTED)
            ax2.set_yticks(y2); ax2.set_yticklabels([h for h, _ in ds]); ax2.invert_yaxis()
            ax2.set_xlabel('JSD to the genre profile (bits)'); ax2.set_title(f'{focus["title"].split(" (")[0].split(",")[0]}: distance to each genre profile', loc='left', fontsize=11)
            ax2.set_xlim(0, max(v for _, v in ds) * 1.3)
            for sp in ('top', 'right'): ax2.spines[sp].set_visible(False)
            ax2.grid(axis='x', color='#eeeeea'); ax2.set_axisbelow(True)
        fig.text(0.01, 0.005, '* Snyder\'s Comic Matrix four · red = the focus play / its own genre · each play is left out of its own genre\'s profile · in brackets: share of the play\'s words in the compared topics · profiles over the compared topics only', fontsize=8.5, color=MUTED)
        fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(out / 'othello_panel.png', dpi=160); plt.close(fig)
    except ImportError:
        print('matplotlib missing: figure skipped')

    # ---- summary
    md = [f'# Reading single plays distributionally — {agg.parent.name}', '',
          f'Each work\'s profile = its shares of the {len(topics)} compared topics, renormalised; genre profiles = equal-weighted means over the genre\'s works, the work itself left out of its own genre. Distance = Jensen–Shannon divergence (bits). Comedy lean = d(comedy) − d(own genre); the percentile places the work among all works of its genre group (0 = closest to comedy of them all).', '',
          '## Shakespeare\'s plays', '', '| genre | play | nearest genre | d(own genre) | d(comedy) | comedy lean | percentile in genre | compared-topic share of words |', '|---|---|---|---:|---:|---:|---:|---:|']
    for r in shak:
        g = r['genre_main']
        md.append(f'| {g} | {r["title"][:40]}{" *" if r["title"] in SNYDER else ""} | {r["nearest_genre"]} | {r.get(f"d_{g}", "—")} | {r.get("d_comedy", "—")} | {r["comedy_lean"] if r["comedy_lean"] != "" else "—"} | {r.get("comedy_lean_percentile_in_genre", "—")} | {100 * float(r["compared_topics_share_of_words"]):.0f} % |')
    md += ['', '\\* Snyder\'s Comic Matrix four.', '']
    if trag:
        md += ['## His tragedies ordered by comedy lean (most comedy-leaning first)', '', '| play | comedy lean | with the rest bin | percentile among all tragedies | topics pulling it towards comedy (play % / tragedy mean % / comedy mean %) |', '|---|---:|---:|---:|---|']
        for r in trag:
            ps = [p for p in pull if p['work_id'] == r['work_id']][:4]
            md.append(f'| {r["title"][:40]}{" *" if r["title"] in SNYDER else ""} | {float(r["comedy_lean"]):+.3f} | {float(r["comedy_lean_with_rest_bin"]):+.3f} | {r["comedy_lean_percentile_in_genre"]} | ' + '; '.join(f'T{p["topic"]} {p["label"][:28]} ({p["play_share"]} / {p["own_genre_mean_without_play"]} / {p["comedy_mean"]})' for p in ps) + ' |')
    # the same ordering for every genre with tested profiles: which tragedies of anyone lean most to comedy
    md += ['', '## For comparison: the ten tragedies of the whole corpus that lean most towards comedy', '', '| play | author | year | comedy lean |', '|---|---|---:|---:|']
    allt = sorted([r for r in rows if r['genre_main'] == 'tragedy' and r['comedy_lean'] != ''], key=lambda r: float(r['comedy_lean']))[:10]
    md += [f'| {r["title"][:44]} | {r["author"][:30]} | {r["year_first"]} | {float(r["comedy_lean"]):+.3f} |' for r in allt]
    md += ['', 'Illustrative, not a test: profiles are over the compared topics only (the unassigned rest of each play is not in them), and a play with a small compared-topic share has a rough profile.']
    (out / 'play_distances_summary.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md[:40])); print(f'→ {out}')


if __name__ == '__main__':
    main()
