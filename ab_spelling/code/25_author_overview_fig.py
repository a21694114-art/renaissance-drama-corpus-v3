#!/usr/bin/env python3
"""
25_author_overview_fig.py — the simplified author-divergence overview (dot + grey reference line).

Reads ONLY aggregate/author_by_genre/author_jsd.csv (22_author_by_genre.py) and draws, for each genre, one row per
author group: a dot at the observed Jensen–Shannon divergence between the author's plays and the rest of the genre
(jsd_cond_bits: the relative distribution within the selected topics, works equal-weighted, signature rule of 22)
and a light grey line from the 2.5th to the 97.5th percentile of the 1,000 random same-size groups
(random_cond_p2_5 … random_cond_p97_5). Nothing is recomputed; no author set, ordering basis or value is changed.
Rows are sorted by the observed value within each genre (as in fig1); the "original author of translated works"
group (Seneca) is drawn at the bottom of its genre, separated by a thin rule, with the same values.
Outputs <out>/<name>.png (300 dpi), <out>/<name>.svg and <out>/<name>_data.csv (the plotted values, for checking).
"""
import argparse, csv, datetime, json, textwrap
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BLUE = '#2a78d6'; DARK = '#4a4a46'; BAND = '#dcdbd5'; INK = '#1b1b22'; MUTED = '#5f5f6b'; FAINT = '#8b8b95'; RULE = '#e6e6df'
SHAKES = 'Shakespeare, William'
TRANSLATED = 'original author of translated works'


def fnum(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ab', required=True, help='aggregate/author_by_genre directory (author_jsd.csv)')
    ap.add_argument('--genres', default='comedy,tragedy,history'); ap.add_argument('--out', default='')
    ap.add_argument('--name', default='fig0_author_jsd_overview'); ap.add_argument('--width', type=float, default=7.0)
    a = ap.parse_args()
    ab = Path(a.ab); out = Path(a.out) if a.out else ab; out.mkdir(parents=True, exist_ok=True)
    genres = [g.strip() for g in a.genres.split(',') if g.strip()]
    rows = list(csv.DictReader(open(ab / 'author_jsd.csv', encoding='utf-8')))
    # ---- data per genre: sorted by observed value, translated-original group last ----------------------------------
    panels = []
    for g in genres:
        R = [r for r in rows if r['genre'] == g]
        if not R: continue
        main_rows = sorted([r for r in R if r['group_kind'] != TRANSLATED], key=lambda r: -fnum(r['jsd_cond_bits']))
        apart = sorted([r for r in R if r['group_kind'] == TRANSLATED], key=lambda r: -fnum(r['jsd_cond_bits']))
        items = []
        for r in main_rows + apart:
            n = int(r['n_A']); sur = r['author'].split(',')[0]
            lab = f'{sur} in English translation · {n} plays' if r['group_kind'] == TRANSLATED else f'{sur} · {n} plays'
            items.append({'genre': g, 'author': r['author'], 'label': lab, 'n_plays': n, 'n_rest': int(r['n_B']), 'jsd': fnum(r['jsd_cond_bits']),
                          'lo': fnum(r['random_cond_p2_5']), 'hi': fnum(r['random_cond_p97_5']), 'shakespeare': r['author'] == SHAKES, 'apart': r['group_kind'] == TRANSLATED,
                          'percentile': fnum(r['observed_cond_percentile'])})
        n_genre = int(main_rows[0]['n_A']) + int(main_rows[0]['n_B']) if main_rows else None
        panels.append((g, n_genre, items))
    xmax = max(max(i['jsd'], i['hi']) for _, _, it in panels for i in it)
    xmax = (int(xmax * 10) + 1) / 10
    # ---- figure ---------------------------------------------------------------------------------------------------
    plt.rcParams.update({'font.family': ['Helvetica Neue', 'Helvetica', 'Arial', 'DejaVu Sans'], 'font.size': 9.5, 'svg.fonttype': 'none'})
    row_h = 0.34; gaps = 0.62; top_in = 1.42; bottom_in = 1.05; margin_in = 0.28; label_col_in = 2.75
    heights = [len(it) * row_h + (0.18 if any(i['apart'] for i in it) else 0) for _, _, it in panels]
    fig_h = top_in + bottom_in + sum(heights) + gaps * (len(panels) - 1)
    fig = plt.figure(figsize=(a.width, fig_h))
    left, right = (margin_in + label_col_in) / a.width, 1 - 0.62 / a.width; ml = margin_in / a.width
    y = 1 - top_in / fig_h
    axes = []
    for (g, n_genre, items), h in zip(panels, heights):
        ax = fig.add_axes([left, y - h / fig_h, right - left, h / fig_h]); axes.append(ax)
        ys = list(range(len(items)))[::-1]
        if any(i['apart'] for i in items):
            k = next(j for j, i in enumerate(items) if i['apart']); ys = [yy + (0.55 if j < k else 0) for j, yy in enumerate(ys)]
            ax.axhline(ys[k] + 0.5 + 0.275, color=FAINT, lw=0.6, xmin=-(label_col_in / (a.width * (right - left))), xmax=1, clip_on=False)
        for i, yy in zip(items, ys):
            ax.plot([i['lo'], i['hi']], [yy, yy], color=BAND, lw=5.5, solid_capstyle='butt', zorder=1)
            ax.plot([i['jsd']], [yy], marker='o', ms=7.2, color=BLUE if i['shakespeare'] else DARK, mec='white', mew=0.9, zorder=3, ls='none')
            ax.text(xmax + 0.012, yy, f'{i["jsd"]:.2f}', va='center', ha='left', fontsize=8.6, color=INK, clip_on=False)
        ax.set_yticks(ys); ax.set_yticklabels([i['label'] for i in items], fontsize=9.2, ha='left')
        ax.tick_params(axis='y', pad=label_col_in * 72)
        for lab, i in zip(ax.get_yticklabels(), items):
            lab.set_color(BLUE if i['shakespeare'] else INK); lab.set_fontweight('bold' if i['shakespeare'] else 'normal')
        ax.set_xlim(0, xmax); ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)
        ax.text(-(label_col_in / (a.width * (right - left))), 1.0 + 0.06 / (h if h else 1), f'{g.capitalize()} — {n_genre} plays', transform=ax.transAxes, fontsize=10, fontweight='bold', color=INK, va='bottom', ha='left')
        ax.grid(axis='x', color=RULE, lw=0.6); ax.set_axisbelow(True)
        for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
        ax.spines['bottom'].set_color(RULE); ax.tick_params(axis='y', length=0, pad=label_col_in * 72); ax.tick_params(axis='x', colors=MUTED, labelsize=8.4, length=3, color=RULE)
        if ax is not axes[-1] or True:
            ax.set_xticks([x / 10 for x in range(0, int(xmax * 10) + 1)])
        y -= (h + gaps) / fig_h
    axes[-1].set_xlabel('Difference in topic distribution (JSD)   →  larger difference', color=INK, fontsize=9.4, labelpad=6)
    # titles and legend
    fig.text(ml, 1 - 0.26 / fig_h, 'Authors and the rest of their genre', fontsize=13, fontweight='bold', color=INK, va='top')
    fig.text(ml, 1 - 0.55 / fig_h, 'How different is each author\'s topic distribution?', fontsize=10.5, color=MUTED, va='top')
    handles = [Line2D([], [], marker='o', ms=7, color=DARK, mec='white', ls='none'), Line2D([], [], color=BAND, lw=5.5)]
    fig.legend(handles, ['Dot: observed difference', 'Grey line: reference range for random groups with the same number of plays'],
               loc='upper left', bbox_to_anchor=(ml, 1 - 0.80 / fig_h), ncol=1, frameon=False, fontsize=8.8, handlelength=1.6, labelspacing=0.35, borderaxespad=0)
    note = ('Each row compares one author\'s plays with the rest of the same genre. The grey line is the middle 95 % of 1,000 random groups with the same number of plays, '
            'drawn from the same genre — a reference for the group size, not a confidence interval. Shakespeare in blue.')
    fig.text(ml, 0.16 / fig_h, textwrap.fill(note, width=int(118 * a.width / 7.0)), fontsize=7.8, color=MUTED, va='bottom', linespacing=1.45)
    fig.savefig(out / f'{a.name}.png', dpi=300, facecolor='white'); fig.savefig(out / f'{a.name}.svg', facecolor='white')
    with open(out / f'{a.name}_data.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=['genre', 'row', 'author', 'label', 'n_plays', 'n_rest', 'jsd', 'lo', 'hi', 'shakespeare', 'apart', 'percentile']); wr.writeheader()
        for g, _, items in panels:
            for k, i in enumerate(items, 1): wr.writerow({'row': k, **{x: i[x] for x in wr.fieldnames if x != 'row'}})
    print(f'{a.name}: {sum(len(it) for _, _, it in panels)} rows in {len(panels)} panels → {out}  ({datetime.date.today().isoformat()})')


if __name__ == '__main__':
    main()
