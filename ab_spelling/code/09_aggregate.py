#!/usr/bin/env python3
"""09_aggregate.py — chunk → edition → work → genre aggregation of one topic run.

  python 09_aggregate.py --chunks <chunks dir> --runs <runs dir> --seed 42 \
        [--use included,candidate] [--min-works 10] [--out <dir>]

Rules (agreed 2026-09-21):
  * unit hierarchy chunk → edition → work → genre; chunks are never treated as independent works;
  * length weighting: share of topic t in edition e = words of e's chunks in t / words of ALL e's
    chunks (len_B_words).  Every chunk stays in the denominator: the shares of the use-categories
    (included / candidate / contextual_only / pending / unclassified / outlier_hdbscan, from
    topic_sheet.csv column use_in_genre_analysis) are reported next to the topic shares, so nothing
    is silently dropped.  A conditional composition (denominator = words in the selected topics
    only) is written to a separate file and labelled as such;
  * editions of one work_id are averaged with equal weight; works enter their genre with equal
    weight (multi-edition works are not double counted);
  * genre labels: the raw genre_deep string is kept; genre_main is set only when the raw string is
    exactly one of MAIN_GENRES, otherwise 'other/multi'; conflicting genre_deep values inside one
    work_id are listed in genre_conflicts.csv and the work is put in 'other/multi'; play_type_deep
    is aggregated separately (play_type_main = first ';'-separated token);
  * direction: these tables answer "what share of a genre's text falls in topic t" — the opposite
    of topic_sheet's genre_mix_of_topic;
  * statistics: for each selected topic, Kruskal–Wallis across genre_main groups with >= --min-works
    works, Benjamini–Hochberg over the selected topics; descriptive only, no causal reading.
Outputs (in --out, default <runs>/topics_B_s<seed>/aggregate/): edition_topic_share.csv,
work_topic_share.csv, genre_topic_mean.csv, genre_topic_conditional.csv, genre_coverage.csv,
genre_conflicts.csv, kruskal_by_topic.csv (means, medians, works-with-topic, single-work flag),
heatmap_selected_topics.png (sqrt colour scale), heatmap_prevalence.png, aggregate_summary.md.
"""
import argparse, csv, json, math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

MAIN_GENRES = ['comedy', 'tragedy', 'history', 'tragicomedy', 'moral', 'romance', 'pastoral', 'masque', 'interlude']
CATS = ['included', 'candidate', 'contextual_only', 'pending', 'unclassified', 'outlier_hdbscan']


def bh(pvals):
    n = len(pvals); order = sorted(range(n), key=lambda i: pvals[i]); q = [0.0] * n; prev = 1.0
    for rank, i in reversed(list(enumerate(order, 1))):
        prev = min(prev, pvals[i] * n / rank); q[i] = prev
    return q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--use', default='included,candidate', help='use_in_genre_analysis categories that form the main comparison')
    ap.add_argument('--min-works', type=int, default=10, help='genre groups with fewer works are shown but not tested')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'
    out = Path(a.out) if a.out else d / 'aggregate'; out.mkdir(parents=True, exist_ok=True)
    use_cats = [x.strip() for x in a.use.split(',') if x.strip()]

    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    wlen = {r['chunk_id']: int(r['len_B_words']) for r in csv.DictReader(open(ch / 'chunk_map.csv', encoding='utf-8'))}
    labels = {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8'))}
    sheet = {int(r['topic']): r for r in csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8'))}
    use_of = {t: (r['use_in_genre_analysis'] or 'unclassified') for t, r in sheet.items()}
    name_of = {t: (r['Label'] or r['draft_label'] or f'topic {t}') for t, r in sheet.items()}
    selected = sorted(t for t in sheet if use_of[t] in use_cats)
    cat_of = lambda t: 'outlier_hdbscan' if t == -1 else use_of.get(t, 'unclassified')

    # edition level
    ed_words = Counter(); ed_topic = defaultdict(Counter); ed_cat = defaultdict(Counter); ed_info = {}
    for c, t in labels.items():
        m = meta[c]; e = m['edition_id']; w = wlen[c]
        ed_words[e] += w; ed_topic[e][t] += w; ed_cat[e][cat_of(t)] += w
        ed_info.setdefault(e, {'edition_id': e, 'work_id': m['work_id'], 'title': m['title'], 'author': m['author'], 'year': m['year'],
                               'genre_deep': m['genre_deep'], 'play_type_deep': m['play_type_deep']})
    topics_all = sorted(t for t in sheet)
    ed_rows = []
    for e in sorted(ed_words, key=lambda x: int(x)):
        r = dict(ed_info[e]); r['words'] = ed_words[e]; r['n_chunks'] = sum(1 for c in labels if meta[c]['edition_id'] == e)
        for cat in CATS: r[f'cat:{cat}'] = round(ed_cat[e][cat] / ed_words[e], 5)
        for t in topics_all: r[f't{t}'] = round(ed_topic[e][t] / ed_words[e], 5)
        ed_rows.append(r)
    with open(out / 'edition_topic_share.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(ed_rows[0])); w.writeheader(); w.writerows(ed_rows)

    # work level: equal-weight mean over editions
    by_work = defaultdict(list)
    for r in ed_rows: by_work[r['work_id']].append(r)
    conflicts = []; work_rows = []
    share_cols = [k for k in ed_rows[0] if k.startswith('cat:') or k.startswith('t')]
    share_cols = [k for k in share_cols if k.startswith('cat:') or k[1:].isdigit()]
    for wid, eds in by_work.items():
        genres = sorted({x['genre_deep'] for x in eds}); ptypes = sorted({x['play_type_deep'] for x in eds})
        if len(genres) > 1:
            conflicts.append({'work_id': wid, 'title': eds[0]['title'], 'editions': '; '.join(x['edition_id'] for x in eds), 'genre_deep values': ' | '.join(genres)})
        graw = genres[0] if len(genres) == 1 else 'CONFLICT: ' + ' | '.join(genres)
        gmain = graw if graw in MAIN_GENRES else 'other/multi'
        r = {'work_id': wid, 'title': eds[0]['title'], 'author': eds[0]['author'], 'n_editions': len(eds), 'editions': '; '.join(x['edition_id'] for x in eds),
             'year_first': min(x['year'] for x in eds), 'genre_deep': graw, 'genre_main': gmain,
             'play_type_deep': ptypes[0] if len(ptypes) == 1 else ' | '.join(ptypes), 'play_type_main': ptypes[0].split(';')[0].strip() if ptypes else '',
             'words_mean': round(sum(x['words'] for x in eds) / len(eds))}
        for k in share_cols: r[k] = round(sum(x[k] for x in eds) / len(eds), 5)
        work_rows.append(r)
    work_rows.sort(key=lambda r: (r['genre_main'], r['title']))
    with open(out / 'work_topic_share.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(work_rows[0])); w.writeheader(); w.writerows(work_rows)
    with open(out / 'genre_conflicts.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['work_id', 'title', 'editions', 'genre_deep values']); w.writeheader(); w.writerows(conflicts)

    # genre level: works equal weight
    groups = defaultdict(list)
    for r in work_rows: groups[r['genre_main']].append(r)
    genre_order = [g for g in MAIN_GENRES if g in groups] + (['other/multi'] if 'other/multi' in groups else [])
    gen_rows = []; cov_rows = []
    for g in genre_order:
        rs = groups[g]; n = len(rs)
        row = {'genre_main': g, 'n_works': n, 'n_editions': sum(r['n_editions'] for r in rs)}
        for t in topics_all:
            vals = [r[f't{t}'] for r in rs]
            row[f't{t} mean'] = round(float(np.mean(vals)), 5); row[f't{t} median'] = round(float(np.median(vals)), 5)
            row[f't{t} works>0'] = sum(1 for v in vals if v > 0)
        gen_rows.append(row)
        cr = {'genre_main': g, 'n_works': n}
        for cat in CATS: cr[f'{cat} mean share of words'] = round(float(np.mean([r[f'cat:{cat}'] for r in rs])), 4)
        cr['selected topics mean share of words'] = round(float(np.mean([sum(r[f't{t}'] for t in selected) for r in rs])), 4)
        cov_rows.append(cr)
    with open(out / 'genre_topic_mean.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(gen_rows[0])); w.writeheader(); w.writerows(gen_rows)
    with open(out / 'genre_coverage.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(cov_rows[0])); w.writeheader(); w.writerows(cov_rows)

    # conditional composition within selected topics (denominator = words in selected topics of the work)
    cond_rows = []
    for g in genre_order:
        rs = groups[g]; row = {'genre_main': g, 'n_works': len(rs), 'n_works_with_selected_text': 0}
        comp = defaultdict(list)
        for r in rs:
            tot = sum(r[f't{t}'] for t in selected)
            if tot <= 0: continue
            row['n_works_with_selected_text'] += 1
            for t in selected: comp[t].append(r[f't{t}'] / tot)
        for t in selected: row[f't{t} cond. mean'] = round(float(np.mean(comp[t])), 5) if comp[t] else ''
        cond_rows.append(row)
    with open(out / 'genre_topic_conditional.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(cond_rows[0])); w.writeheader(); w.writerows(cond_rows)

    # Kruskal–Wallis per selected topic over genres with >= min_works works
    tested = [g for g in genre_order if g != 'other/multi' and len(groups[g]) >= a.min_works]
    kw_rows = []
    try:
        from scipy.stats import kruskal
    except ImportError:
        kruskal = None
    pv = []
    for t in selected:
        samples = [[r[f't{t}'] for r in groups[g]] for g in tested]
        means = {g: float(np.mean(s)) for g, s in zip(tested, samples)}
        medians = {g: float(np.median(s)) for g, s in zip(tested, samples)}
        prev = {g: sum(1 for v in s if v > 0) for g, s in zip(tested, samples)}          # works in which the topic occurs
        dom = {g: (max(s) / sum(s) if sum(s) > 0 else 0.0) for g, s in zip(tested, samples)}   # share of the genre's total held by its top work
        ranked = sorted(tested, key=lambda g: -means[g])
        hi, second, lo = ranked[0], (ranked[1] if len(ranked) > 1 else ranked[0]), ranked[-1]
        p = float('nan')
        if kruskal is not None and len(tested) >= 2 and any(any(v > 0 for v in s) for s in samples):
            try: p = float(kruskal(*samples).pvalue)
            except ValueError: p = float('nan')
        pv.append(p)
        kw_rows.append({'topic': t, 'label': name_of[t], 'use': use_of[t], 'genres_tested': ', '.join(tested),
                        **{f'mean {g}': round(means[g], 5) for g in tested}, **{f'median {g}': round(medians[g], 5) for g in tested},
                        **{f'works_with_topic {g}': f'{prev[g]}/{len(groups[g])}' for g in tested},
                        'highest': hi, 'highest_works_with_topic': f'{prev[hi]}/{len(groups[hi])}', 'highest_top_work_share': round(dom[hi], 2),
                        'single_work_driven': 'YES' if dom[hi] >= 0.5 else '',
                        'second': second, 'ratio_high_second': round(means[hi] / means[second], 2) if means[second] > 0 else '',
                        'lowest': lo, 'kruskal_p': ('<1e-5' if p < 1e-5 else round(p, 5)) if not math.isnan(p) else ''})
    valid = [i for i, p in enumerate(pv) if not math.isnan(p)]
    if valid:
        q = bh([pv[i] for i in valid])
        for i, qi in zip(valid, q): kw_rows[i]['bh_q'] = '<1e-5' if qi < 1e-5 else round(qi, 5)
    with open(out / 'kruskal_by_topic.csv', 'w', newline='', encoding='utf-8') as f:
        cols = (list(kw_rows[0]) + (['bh_q'] if valid and 'bh_q' not in kw_rows[0] else [])) if kw_rows else ['topic']
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(kw_rows)

    # heatmap: selected topics × tested genres, mean share of words (one hue, light → dark)
    try:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None
        print('matplotlib not installed: heatmap skipped (pip install matplotlib), tables are complete')
    if selected and tested and plt is not None:
        from matplotlib.colors import PowerNorm
        M = np.array([[float(np.mean([r[f't{t}'] for r in groups[g]])) * 100 for g in tested] for t in selected])
        P = np.array([[100 * sum(1 for r in groups[g] if r[f't{t}'] > 0) / len(groups[g]) for g in tested] for t in selected])
        order = np.argsort(-M.max(axis=1))
        M = M[order]; P = P[order]; ylab = [f'T{selected[i]}  {name_of[selected[i]][:42]}' for i in order]
        def heat(mat, fname, title, cblabel, fmt, norm=None):
            fig_h = max(4, 0.32 * len(selected) + 1.5)
            fig, ax = plt.subplots(figsize=(1.3 * len(tested) + 6, fig_h))
            im = ax.imshow(mat, cmap='Blues', aspect='auto', norm=norm) if norm is not None else ax.imshow(mat, cmap='Blues', aspect='auto', vmin=0, vmax=max(mat.max(), 0.01))
            ax.set_xticks(range(len(tested))); ax.set_xticklabels([f'{g}\n(n={len(groups[g])})' for g in tested], fontsize=9)
            ax.set_yticks(range(len(selected))); ax.set_yticklabels(ylab, fontsize=8)
            thresh = norm.inverse(0.6) if norm is not None else 0.6 * mat.max()
            for i in range(mat.shape[0]):
                for j in range(mat.shape[1]):
                    if mat[i, j] >= 0.05:
                        ax.text(j, i, fmt(mat[i, j]), ha='center', va='center', fontsize=7, color='#1a1a1a' if mat[i, j] < thresh else 'white')
            for sp in ('top', 'right', 'left', 'bottom'): ax.spines[sp].set_visible(False)
            ax.tick_params(length=0)
            cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label(cblabel, fontsize=8); cb.outline.set_visible(False)
            ax.set_title(title, fontsize=9, loc='left')
            fig.tight_layout(); fig.savefig(out / fname, dpi=160); plt.close(fig)
        heat(M, 'heatmap_selected_topics.png',
             f'Selected topics by genre — mean share of a work\'s words, % (seed {a.seed}; works equal-weighted; editions averaged; all chunks in the denominator; square-root colour scale)',
             'mean share of a work\'s words (%)', lambda v: f'{v:.1f}', norm=PowerNorm(gamma=0.5, vmin=0, vmax=max(M.max(), 0.01)))
        heat(P, 'heatmap_prevalence.png',
             f'Selected topics by genre — share of works in which the topic occurs at all, % (seed {a.seed})',
             '% of the genre\'s works with the topic', lambda v: f'{v:.0f}')

    # summary
    md = [f'# Aggregation summary — seed {a.seed}', '',
          f'Selected categories: {", ".join(use_cats)} → {len(selected)} topics. Works: {len(work_rows)} ({sum(r["n_editions"] for r in work_rows)} editions). '
          f'Genre conflicts inside a work: {len(conflicts)} (listed in genre_conflicts.csv, placed in other/multi).', '',
          '| genre_main | works | editions | selected-topic share of words | contextual_only | pending | unclassified | outlier |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for g, cr in zip(genre_order, cov_rows):
        md.append(f'| {g} | {cr["n_works"]} | {sum(r["n_editions"] for r in groups[g])} | {cr["selected topics mean share of words"]:.1%} | '
                  f'{cr["contextual_only mean share of words"]:.1%} | {cr["pending mean share of words"]:.1%} | {cr["unclassified mean share of words"]:.1%} | {cr["outlier_hdbscan mean share of words"]:.1%} |')
    md += ['', f'Genres tested (>= {a.min_works} works): {", ".join(tested)}. Kruskal–Wallis + BH over {len(selected)} topics; descriptive. '
               '"works" = works of the highest genre in which the topic occurs at all; "one-work" = YES when a single work holds >= 50 % of that genre\'s total share (the mean is then that work, not the genre).', '',
           '| topic | label | highest genre (mean; works) | one-work | second (mean) | ratio | p | q |', '|---|---|---|---|---|---:|---:|---:|']
    def qkey(r):
        q = r.get('bh_q', '')
        return -1 if q == '<1e-5' else (float(q) if q != '' else 1)
    for r in sorted(kw_rows, key=qkey):
        hi_m = r['mean ' + r['highest']]; se_m = r['mean ' + r['second']]
        md.append(f'| T{r["topic"]} | {r["label"][:45]} | {r["highest"]} ({hi_m:.2%}; {r["highest_works_with_topic"]}) | {r["single_work_driven"]} | '
                  f'{r["second"]} ({se_m:.2%}) | {r["ratio_high_second"]} | {r["kruskal_p"]} | {r.get("bh_q", "")} |')
    md += ['', 'Reading: shares are of a work\'s words, averaged over its editions and then over the works of a genre; the remaining words of every work sit in the '
                'contextual_only / pending / unclassified / outlier columns, so the selected topics never describe the whole genre.']
    (out / 'aggregate_summary.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md[:14])); print(f'... written to {out}')


if __name__ == '__main__':
    main()
