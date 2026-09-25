#!/usr/bin/env python3
"""14_genre_figures.py — "which topics does each genre contain": the figures of the old project's
11_genre_visualization (stacked bar per genre, top-N topics; one horizontal bar chart per genre with
the topic labels beside the bars), redrawn from the B pipeline's tables.

    python 14_genre_figures.py --chunks <chunks_w500> --runs <runs_dir> --seed 42
        [--weight works|chunks] [--use included,candidate | all] [--top 20]
        [--genres comedy,tragedy,history | all] [--min-works 10] [--out <dir>]

Two ways of measuring "how much of a genre is topic k":
  works  (default) — the 09_aggregate.py measure: a work's share of WORDS in topic k, editions of a work
           averaged, works of a genre averaged with equal weight; every chunk stays in the denominator,
           so the bar also shows the words in topics outside the selection and the unassigned words.
  chunks — the old project's measure: topic-assigned CHUNKS counted per genre, % within the genre,
           unassigned chunks left out of the denominator. Big plays and multi-edition works count more.

--use picks the topics eligible for the top-N (use_in_genre_analysis categories of topic_sheet.csv;
'all' = every topic, as in the old figures). Labels come from the sheet's Label column, else draft_label.
Colours are fixed per topic id across every figure (topic_color_map.csv), 'other' greys are fixed too.

Outputs in <out> (default <runs>/topics_B_s<seed>/aggregate/):
  genre_stacked_top{N}_{weight}.png       one stacked bar per genre, topic list on the right
  genre_{genre}_top{N}_{weight}.png       horizontal bars, one file per genre
  genre_panels_top{N}_{weight}.png        the same bars as one small-multiples figure
  genre_topic_top{N}_{weight}.csv         the numbers behind the figures (long table)
  topic_color_map.csv                     topic id → colour
"""
import argparse, csv, collections, math
from pathlib import Path

MAIN_GENRES = ['comedy', 'tragedy', 'history', 'tragicomedy', 'moral', 'romance', 'pastoral', 'masque', 'interlude']
GREY_OTHER_SEL, GREY_NOT_SEL, GREY_UNASSIGNED = '#9a9a9a', '#c4c4c4', '#e6e6e6'


def palette(n):
    """Qualitative colours in a fixed order (the old project's Dark2 + Set1 + Accent + Paired + tab20…)."""
    import matplotlib, colorsys
    from matplotlib.colors import to_hex, to_rgb
    cols = []
    for name, k in (('Dark2', 8), ('Set1', 9), ('Accent', 8), ('Paired', 12), ('tab20', 20), ('tab20b', 20), ('tab20c', 20)):
        cs = [to_hex(matplotlib.colormaps[name](i)) for i in range(k)]
        if name.startswith(('Paired', 'tab20')): cs = cs[::2] + cs[1::2]   # separate light/dark neighbours
        cols += cs
    cols = [c for c in cols if colorsys.rgb_to_hls(*to_rgb(c))[2] > 0.25]   # greys are reserved for the remainder
    while len(cols) < n: cols += [to_hex(matplotlib.colormaps['hsv'](i / max(1, n - len(cols)))) for i in range(n - len(cols))]
    return cols[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--weight', choices=['works', 'chunks'], default='works')
    ap.add_argument('--use', default='included,candidate', help="topic categories eligible for the top-N, or 'all'")
    ap.add_argument('--top', type=int, default=20)
    ap.add_argument('--genres', default='', help="comma list, 'all' (adds other/multi), or empty = main genres with >= --min-works works")
    ap.add_argument('--min-works', type=int, default=10)
    ap.add_argument('--legend-cols', type=int, default=2, help='columns of the topic list beside the stacked bars (2 = wide figure that fits a screen; 1 = tall, larger type when printed)')
    ap.add_argument('--panel-cols', type=int, default=0, help='columns of the small-multiples panel (0 = automatic: 4 for 7+ genres, 3 for 4-6)')
    ap.add_argument('--renorm', action='store_true', help='works mode: rescale so the selected topics sum to 100 %% (like the old chunk figures); coverage is printed instead')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'
    out = Path(a.out) if a.out else d / 'aggregate'; out.mkdir(parents=True, exist_ok=True)
    sheet = {int(r['topic']): r for r in csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8'))}
    topics_all = sorted(sheet)
    use = None if a.use.strip().lower() == 'all' else {u.strip() for u in a.use.split(',') if u.strip()}
    selected = [t for t in topics_all if use is None or sheet[t].get('use_in_genre_analysis', '') in use]
    label = {t: (sheet[t].get('Label') or sheet[t].get('draft_label') or f'topic {t}').strip() for t in topics_all}

    # ---- shares per genre: {genre: {topic: value}} plus the remainder categories ----
    n_units = {}
    if a.weight == 'works':
        rows = list(csv.DictReader(open(d / 'aggregate' / 'work_topic_share.csv', encoding='utf-8')))
        by_g = collections.defaultdict(list)
        for r in rows: by_g[r['genre_main']].append(r)
        share, rest = {}, {}
        for g, rs in by_g.items():
            n_units[g] = len(rs)
            share[g] = {t: sum(float(r[f't{t}']) for r in rs) / len(rs) for t in topics_all}
            rest[g] = {'unassigned': sum(float(r['cat:outlier_hdbscan']) for r in rs) / len(rs)}
        unit, measure = 'works', "mean share of a work's words (%)"
        if a.renorm:
            for g in share:
                tot = sum(share[g][t] for t in topics_all if use is None or sheet[t].get('use_in_genre_analysis', '') in use) or 1
                rest[g]['coverage'] = tot
                share[g] = {t: share[g][t] / tot for t in topics_all}
            measure = f'% of the words in the {len(selected)} selected topics (all of them, not only the top {a.top})'
    else:
        meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
        gwork = {}   # the aggregate's genre assignment per work (British Drama → Annals rule), when 09 has run
        if (d / 'aggregate' / 'genre_assignment.csv').exists():
            gwork = {r['work_id']: r['genre_main'] for r in csv.DictReader(open(d / 'aggregate' / 'genre_assignment.csv', encoding='utf-8'))}
        cnt = collections.defaultdict(collections.Counter); tot_all = collections.Counter(); eds = collections.defaultdict(set)
        for r in csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8')):
            if r.get('in_fit', '1') != '1': continue   # representative editions only
            m = meta[r['chunk_id']]; graw = m['genre_deep'].strip().lower()
            g = gwork.get(m['work_id']) or (graw if graw in MAIN_GENRES else 'other/multi')
            t = int(r['topic']); tot_all[g] += 1; eds[g].add(m['edition_id'])
            if t != -1: cnt[g][t] += 1
        share, rest = {}, {}
        for g in tot_all:
            n_units[g] = len(eds[g]); n_assigned = sum(cnt[g].values()) or 1
            share[g] = {t: cnt[g][t] / n_assigned for t in topics_all}
            rest[g] = {'unassigned': 1 - n_assigned / tot_all[g]}   # reported, not in the denominator
        unit, measure = 'editions', '% of topic-assigned chunks'

    if a.genres.strip().lower() == 'all':
        genres = [g for g in MAIN_GENRES if g in share] + (['other/multi'] if 'other/multi' in share else [])
    elif a.genres.strip():
        genres = [g.strip().lower() for g in a.genres.split(',') if g.strip().lower() in share]
    else:
        genres = [g for g in MAIN_GENRES if g in share and n_units[g] >= a.min_works]
    if not genres: raise SystemExit('no genre passes the filter')

    # ---- top-N per genre, fixed colours ----
    cols = palette(len(topics_all)); color = {t: cols[i] for i, t in enumerate(topics_all)}
    with open(out / 'topic_color_map.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['topic', 'label', 'color']); [w.writerow([t, label[t], color[t]]) for t in topics_all]
    top = {g: sorted(selected, key=lambda t: -share[g][t])[:a.top] for g in genres}
    top = {g: [t for t in ts if share[g][t] > 0] for g, ts in top.items()}
    sfx = f'top{a.top}_{a.weight}' + ('_renorm' if a.renorm else '')
    with open(out / f'genre_topic_{sfx}.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['genre', 'n_' + unit, 'rank', 'topic', 'label', 'use', 'value', 'measure'])
        for g in genres:
            for i, t in enumerate(top[g], 1):
                w.writerow([g, n_units[g], i, t, label[t], sheet[t].get('use_in_genre_analysis', ''), f'{100 * share[g][t]:.3f}', measure])
            other_sel = sum(share[g][t] for t in selected if t not in top[g])
            not_sel = sum(share[g][t] for t in topics_all if t not in selected)
            w.writerow([g, n_units[g], '', 'other selected topics', '', '', f'{100 * other_sel:.3f}', measure])
            if a.renorm: w.writerow([g, n_units[g], '', 'coverage of the selected topics', '', '', f'{100 * rest[g]["coverage"]:.3f}', "mean share of a work's words"])
            elif use is not None: w.writerow([g, n_units[g], '', 'topics outside the selection', '', '', f'{100 * not_sel:.3f}', measure])
            if not a.renorm: w.writerow([g, n_units[g], '', 'unassigned', '', '', f'{100 * rest[g]["unassigned"]:.3f}', 'share of all words' if a.weight == 'works' else 'share of all chunks (not in the denominator)'])

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                         'grid.color': '#e4e4e4', 'grid.linewidth': 0.6, 'axes.axisbelow': True})

    # ---- (1) stacked bars ----
    used = []
    for g in genres:
        for t in top[g]:
            if t not in used: used.append(t)
    LC = max(1, a.legend_cols); maxlab = max([len(label[t][:48]) for t in used] + [20]); fig_w = 0.9 * len(genres) + 1.9 + LC * 0.105 * maxlab   # 10.5 pt DejaVu ≈ 0.1 in per character
    fig = plt.figure(figsize=(fig_w, max(7, 0.3 * math.ceil((len(used) + 3) / LC) + 2.2)))
    axw = (0.9 * len(genres)) / fig_w; ax = fig.add_axes([0.07, 0.1, axw, 0.84])
    for i, g in enumerate(genres):
        base = 0.0
        for t in top[g]:
            v = 100 * share[g][t]
            ax.bar(i, v, 0.62, bottom=base, color=color[t], edgecolor='white', linewidth=0.8)
            if v >= 2.6: ax.text(i, base + v / 2, f'T{t}', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
            base += v
        other_sel = 100 * sum(share[g][t] for t in selected if t not in top[g])
        ax.bar(i, other_sel, 0.62, bottom=base, color=GREY_OTHER_SEL, edgecolor='white', linewidth=0.8); base += other_sel
        if use is not None and not a.renorm:
            not_sel = 100 * sum(share[g][t] for t in topics_all if t not in selected)
            ax.bar(i, not_sel, 0.62, bottom=base, color=GREY_NOT_SEL, edgecolor='white', linewidth=0.8); base += not_sel
        if a.weight == 'works' and not a.renorm:
            un = 100 * rest[g]['unassigned']
            ax.bar(i, un, 0.62, bottom=base, color=GREY_UNASSIGNED, edgecolor='white', linewidth=0.8, hatch='////'); base += un
        ntxt = f'n={n_units[g]}' + (f'\ncov. {100 * rest[g]["coverage"]:.0f} %' if a.renorm else '')
        ax.text(i, 101, ntxt, ha='center', va='bottom', fontsize=8.5, color='#555')
    ax.set_xticks(range(len(genres))); ax.set_xticklabels([g.capitalize() for g in genres], fontsize=11)
    ax.set_ylim(0, 112 if a.renorm else 106); ax.set_ylabel(measure, fontsize=11); ax.tick_params(axis='y', labelsize=10); ax.grid(axis='x', visible=False)
    # topic list (legend) on the right, two columns, in topic-id order
    handles = [Patch(color=color[t], label=f'T{t}: {label[t][:48]}' + ('…' if len(label[t]) > 48 else '')) for t in sorted(used)]
    handles.append(Patch(color=GREY_OTHER_SEL, label='other selected topics'))
    if use is not None and not a.renorm: handles.append(Patch(color=GREY_NOT_SEL, label='topics outside the selection'))
    if a.weight == 'works' and not a.renorm: handles.append(Patch(facecolor=GREY_UNASSIGNED, hatch='////', label='unassigned words'))
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(0.07 + axw + 0.05, 0.96), ncol=LC, fontsize=10.5, frameon=False,
               handlelength=1.1, handleheight=1.1, columnspacing=1.2, labelspacing=0.42)
    fig.text(0.06, 0.02, f'{a.weight}: {measure}; top {a.top} of {len(selected)} eligible topics ({a.use}); n = {unit}' + ('; cov. = share of the genre\'s words that the selected topics cover' if a.renorm else '') + f'; seed {a.seed}', fontsize=8.5, color='#666')
    fig.savefig(out / f'genre_stacked_{sfx}.png', dpi=200); plt.close(fig)

    # ---- (2) one horizontal bar chart per genre ----
    for g in genres:
        ts = list(reversed(top[g]))
        if not ts: continue
        fig, ax = plt.subplots(figsize=(9.5, 0.34 * len(ts) + 1.5), dpi=200)
        vals = [100 * share[g][t] for t in ts]
        ax.barh(range(len(ts)), vals, color=[color[t] for t in ts], height=0.66, edgecolor='white', linewidth=0.5)
        xmax = max(vals) * 1.05
        for i, (t, v) in enumerate(zip(ts, vals)):
            ax.text(v + xmax * 0.012, i, f'{label[t]}  ({v:.1f} %)', va='center', ha='left', fontsize=9.5, color='#222')
        ax.set_yticks(range(len(ts))); ax.set_yticklabels([f'T{t}' for t in ts], fontsize=9.5)
        ax.set_xlim(0, xmax * 2.1); ax.set_xlabel(measure, fontsize=10); ax.tick_params(axis='x', labelsize=9); ax.grid(axis='y', visible=False)
        note = f'{g.capitalize()} — {n_units[g]} {unit}; ' + (f'unassigned {100 * rest[g]["unassigned"]:.0f} % of words' if a.weight == 'works' else f'{100 * rest[g]["unassigned"]:.0f} % of chunks unassigned (excluded)')
        ax.set_title(note, fontsize=11, loc='left')
        fig.tight_layout(); fig.savefig(out / f'genre_{g.replace("/", "_")}_{sfx}.png'); plt.close(fig)

    # ---- (3) small multiples of (2) ----
    ncol = a.panel_cols or (4 if len(genres) >= 7 else 3 if len(genres) >= 4 else len(genres)); nrow = math.ceil(len(genres) / ncol)   # landscape: fits a screen
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.6 * ncol, (0.3 * a.top + 1.3) * nrow), dpi=200, squeeze=False)
    for k, g in enumerate(genres):
        ax = axes[k // ncol][k % ncol]; ts = list(reversed(top[g])); vals = [100 * share[g][t] for t in ts]
        ax.barh(range(len(ts)), vals, color=[color[t] for t in ts], height=0.66, edgecolor='white', linewidth=0.5)
        xm = (max(vals) if vals else 1) * 1.05
        for i, (t, v) in enumerate(zip(ts, vals)):
            ax.text(v + xm * 0.012, i, f'{label[t][:44]}  ({v:.1f})', va='center', ha='left', fontsize=8.5, color='#222')
        ax.set_yticks(range(len(ts))); ax.set_yticklabels([f'T{t}' for t in ts], fontsize=8.5)
        ax.set_xlim(0, xm * 2.25); ax.grid(axis='y', visible=False); ax.tick_params(axis='x', labelsize=8)
        ax.set_title(f'{g.capitalize()} (n={n_units[g]} {unit})', fontsize=11, loc='left')
    for k in range(len(genres), nrow * ncol): axes[k // ncol][k % ncol].axis('off')
    fig.supxlabel(measure, fontsize=10.5); fig.tight_layout(); fig.savefig(out / f'genre_panels_{sfx}.png'); plt.close(fig)
    print(f'genre figures ({a.weight}, top {a.top}, {len(selected)} eligible topics, genres {", ".join(genres)}) → {out}')


if __name__ == '__main__':
    main()
