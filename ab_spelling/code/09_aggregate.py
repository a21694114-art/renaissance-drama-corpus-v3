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
  * genre labels (Grace's rule, 2026-09-22): British Drama (genre_deep, Wiggins & Richardson) is used
    when it is exactly one of MAIN_GENRES; when it is missing or compound (or differs between the
    editions of a work), the Annals of English Drama label (DEEP genre_annals_filter, via --deep)
    is used when IT is a single main genre ('morality' read as 'moral'); otherwise the work
    stays 'other/multi' with its raw labels — never forced. Both raw labels and the source actually
    used are kept per work (genre_assignment.csv: genre_britdrama, genre_annals, genre_main,
    genre_source). Without --deep the Annals step is skipped. play_type_deep is aggregated
    separately (play_type_main = first ';'-separated token);
  * direction: these tables answer "what share of a genre's text falls in topic t" — the opposite
    of topic_sheet's genre_mix_of_topic;
  * statistics: for each selected topic, Kruskal–Wallis across genre_main groups with >= --min-works
    works, Benjamini–Hochberg over the selected topics; descriptive only, no causal reading.
Outputs (in --out, default <runs>/topics_B_s<seed>/aggregate/): edition_topic_share.csv,
work_topic_share.csv, genre_topic_mean.csv, genre_topic_conditional.csv, genre_coverage.csv,
genre_conflicts.csv, kruskal_by_topic.csv (means, medians, works-with-topic, single-work flag),
sensitivity_dominant_work.csv (selected topics in which one work holds >= --sens-threshold of the
topic's words, recomputed without that work: highest genre / ratio / p with and without, verdict),
heatmap_selected_topics.png (sqrt colour scale), heatmap_prevalence.png, aggregate_summary.md.
"""
import argparse, csv, json, math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

MAIN_GENRES = ['comedy', 'tragedy', 'history', 'tragicomedy', 'moral', 'romance', 'pastoral', 'masque', 'interlude']
ANNALS_MAP = {'morality': 'moral'}   # vocabulary alignment only: Annals 'Morality' = British Drama 'moral'
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
    ap.add_argument('--manifest', default='', help='accepted for symmetry with 13_site.py; not needed (chunk_meta edition_id = DEEP edition_id)')
    ap.add_argument('--deep', default='', help='DEEP_data.csv: enables the Annals fallback (genre_annals_filter by edition_id)')
    ap.add_argument('--all-editions', action='store_true', help='include the chunks of non-representative editions (placed after the fit) in the main tables; default: representative editions only when in_fit exists')
    ap.add_argument('--sens-threshold', type=float, default=0.33, help='dominant-work sensitivity check for selected topics in which one work holds at least this share of the topic\'s words')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'
    out = Path(a.out) if a.out else d / 'aggregate'; out.mkdir(parents=True, exist_ok=True)
    use_cats = [x.strip() for x in a.use.split(',') if x.strip()]

    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    wlen = {r['chunk_id']: int(r['len_B_words']) for r in csv.DictReader(open(ch / 'chunk_map.csv', encoding='utf-8'))}
    _dt = list(csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8')))
    labels_all = {r['chunk_id']: int(r['topic']) for r in _dt}
    labels = {r['chunk_id']: int(r['topic']) for r in _dt if r.get('in_fit', '1') == '1'} if not a.all_editions else dict(labels_all)
    representative_only = len(labels) < len(labels_all)   # 03 --dedup-editions: main results on the representative editions only
    sheet = {int(r['topic']): r for r in csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8'))}
    use_of = {t: (r['use_in_genre_analysis'] or 'unclassified') for t, r in sheet.items()}
    name_of = {t: (r['Label'] or r['draft_label'] or f'topic {t}') for t, r in sheet.items()}
    selected = sorted(t for t in sheet if use_of[t] in use_cats)
    cat_of = lambda t: 'outlier_hdbscan' if t == -1 else use_of.get(t, 'unclassified')
    # Annals label per edition (only when manifest + DEEP are given)
    annals_of = {}   # chunk_meta's edition_id is the manifest's edition_id_effective = DEEP's edition_id
    if a.deep and Path(a.deep).exists():
        dg = {r['edition_id']: (r.get('genre_annals_filter') or '').strip().lower() for r in csv.DictReader(open(a.deep, encoding='utf-8-sig'))}
        annals_of = {e: ('' if v in ('', 'n/a') or v.startswith('not in') or v.isdigit() else v) for e, v in dg.items()}

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
        ann = sorted({annals_of.get(x['edition_id'], '') for x in eds} - {''}); ann_raw = ' | '.join(ann)
        if graw in MAIN_GENRES: gmain, gsrc = graw, 'britdrama'
        elif len(ann) == 1 and ANNALS_MAP.get(ann[0], ann[0]) in MAIN_GENRES: gmain, gsrc = ANNALS_MAP.get(ann[0], ann[0]), 'annals'
        else: gmain, gsrc = 'other/multi', 'none'
        r = {'work_id': wid, 'title': eds[0]['title'], 'author': eds[0]['author'], 'n_editions': len(eds), 'editions': '; '.join(x['edition_id'] for x in eds),
             'year_first': min(x['year'] for x in eds), 'genre_deep': graw, 'genre_annals': ann_raw, 'genre_main': gmain, 'genre_source': gsrc,
             'play_type_deep': ptypes[0] if len(ptypes) == 1 else ' | '.join(ptypes), 'play_type_main': ptypes[0].split(';')[0].strip() if ptypes else '',
             'words_mean': round(sum(x['words'] for x in eds) / len(eds))}
        for k in share_cols: r[k] = round(sum(x[k] for x in eds) / len(eds), 5)
        work_rows.append(r)
    work_rows.sort(key=lambda r: (r['genre_main'], r['title']))
    with open(out / 'work_topic_share.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(work_rows[0])); w.writeheader(); w.writerows(work_rows)
    with open(out / 'genre_conflicts.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['work_id', 'title', 'editions', 'genre_deep values']); w.writeheader(); w.writerows(conflicts)
    # what 'other/multi' is made of (works outside the single-genre comparison), by their DEEP genre string
    om = defaultdict(list)
    for r in work_rows:
        if r['genre_main'] == 'other/multi': om[r['genre_deep'] or '(blank)'].append(r)
    om_rows = [{'genre_deep': g, 'n_works': len(rs), 'n_editions': sum(r['n_editions'] for r in rs),
                'reason': ('not in BritDrama (no genre)' if g.lower() == 'not in britdrama' else 'conflicting genres across editions' if g.startswith('CONFLICT') else 'compound or non-main genre label'),
                'annals': '; '.join(f'{k or "(none)"} ×{n}' for k, n in Counter(r['genre_annals'] for r in rs).most_common(3)),
                'examples': '; '.join(f'{r["title"][:60]} ({r["year_first"]})' for r in sorted(rs, key=lambda r: r['year_first'])[:3])}
               for g, rs in sorted(om.items(), key=lambda kv: -len(kv[1]))]
    with open(out / 'other_multi_works.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['genre_deep', 'n_works', 'n_editions', 'reason', 'annals', 'examples']); w.writeheader(); w.writerows(om_rows)
    # every work with both raw labels and the label actually used
    with open(out / 'genre_assignment.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['work_id', 'title', 'author', 'year_first', 'n_editions', 'genre_britdrama', 'genre_annals', 'genre_main', 'genre_source']); w.writeheader()
        for r in work_rows: w.writerow({'work_id': r['work_id'], 'title': r['title'], 'author': r['author'], 'year_first': r['year_first'], 'n_editions': r['n_editions'],
                                        'genre_britdrama': r['genre_deep'], 'genre_annals': r['genre_annals'], 'genre_main': r['genre_main'], 'genre_source': r['genre_source']})
    src_counts = Counter(r['genre_source'] for r in work_rows)
    genre_rule = ('British Drama single label → else Annals single label → else other/multi' if annals_of else 'British Drama single label → else other/multi (no DEEP given: Annals step skipped)')

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

    # sensitivity to the dominant work: for every selected topic in which one work holds >= --sens-threshold of
    # the topic's words, redo the genre aggregation WITHOUT that work (clusters fixed; only the work-level
    # averaging changes). It records whether the highest-mean genre changes and by how much the means move; an
    # unchanged ranking is not a small effect, so the absolute means, their change and the supporting works are
    # written alongside. The threshold is an operational rule, not a statistical criterion, and it does not cover
    # several works of one author or one story that together dominate a topic.
    sens_rows = []
    for t in selected:
        contrib = {r['work_id']: r[f't{t}'] * r['words_mean'] for r in work_rows}
        tot = sum(contrib.values())
        if tot <= 0: continue
        dom_w = max(contrib, key=contrib.get); dom_share = contrib[dom_w] / tot
        if dom_share < a.sens_threshold: continue
        dr = next(r for r in work_rows if r['work_id'] == dom_w); g_dom = dr['genre_main']
        before = next(r for r in kw_rows if r['topic'] == t); hi1 = before['highest']
        pct = lambda v: f'{100 * v:.2f} %'
        row = {'topic': t, 'label': name_of[t], 'dominant_work': dr['title'], 'dominant_work_genre': g_dom, 'dominant_share_of_topic_words': round(dom_share, 3),
               'highest_with': hi1, 'mean_highest_with': before['mean ' + hi1], 'second_with': before['second'], 'mean_second_with': before['mean ' + before['second']], 'p_with': before['kruskal_p']}
        if g_dom not in tested:
            row.update({'highest_without': '', 'mean_original_highest_without': '', 'second_without': '', 'mean_second_without': '', 'p_without': '',
                        'its_genre_mean_with': '', 'its_genre_mean_without': '', 'its_genre_works_with_topic_with': '', 'its_genre_works_with_topic_without': '', 'its_genre_n_works_with': '', 'its_genre_n_works_without': '',
                        'verdict': f'not applicable — the dominant work is in {g_dom}, outside the tested genres, so omitting it changes nothing here'})
        else:
            samples1 = {g: [r[f't{t}'] for r in groups[g]] for g in tested}
            samples2 = {g: [r[f't{t}'] for r in groups[g] if r['work_id'] != dom_w] for g in tested}
            means2 = {g: (float(np.mean(s)) if s else 0.0) for g, s in samples2.items()}
            ranked2 = sorted(tested, key=lambda g: -means2[g]); hi2 = ranked2[0]; se2 = ranked2[1] if len(ranked2) > 1 else hi2
            p2 = float('nan')
            if kruskal is not None and any(any(v > 0 for v in s) for s in samples2.values()):
                try: p2 = float(kruskal(*samples2.values()).pvalue)
                except ValueError: pass
            m1_hi = float(before['mean ' + hi1]); m2_hi1 = means2[hi1]
            drop = (m2_hi1 - m1_hi) / m1_hi if m1_hi > 0 else 0.0
            if hi2 == hi1:
                verdict = f'highest genre unchanged ({hi1}: {pct(m1_hi)} → {pct(m2_hi1)}, {100 * drop:+.0f} %)'
            else:
                verdict = f'highest genre changes: {hi1} → {hi2} ({hi1}: {pct(m1_hi)} → {pct(m2_hi1)}; {hi2}: {pct(means2[hi2])})'
            row.update({'highest_without': hi2, 'mean_original_highest_without': round(m2_hi1, 5), 'second_without': se2, 'mean_second_without': round(means2[se2], 5),
                        'p_without': ('<1e-5' if p2 < 1e-5 else round(p2, 5)) if not math.isnan(p2) else '',
                        'its_genre_mean_with': round(float(np.mean(samples1[g_dom])), 5), 'its_genre_mean_without': round(means2[g_dom], 5),
                        'its_genre_works_with_topic_with': sum(1 for v in samples1[g_dom] if v > 0), 'its_genre_works_with_topic_without': sum(1 for v in samples2[g_dom] if v > 0),
                        'its_genre_n_works_with': len(samples1[g_dom]), 'its_genre_n_works_without': len(samples2[g_dom]), 'verdict': verdict})
        sens_rows.append(row)
    with open(out / 'sensitivity_dominant_work.csv', 'w', newline='', encoding='utf-8') as f:
        cols = list(sens_rows[0]) if sens_rows else ['topic']
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(sens_rows)

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
            fig, ax = plt.subplots(figsize=(1.05 * len(tested) + 5.5, fig_h))
            im = ax.imshow(mat, cmap='Blues', aspect='auto', norm=norm) if norm is not None else ax.imshow(mat, cmap='Blues', aspect='auto', vmin=0, vmax=max(mat.max(), 0.01))
            ax.set_xticks(range(len(tested))); ax.set_xticklabels([f'{g}\n(n={len(groups[g])})' for g in tested], fontsize=11)
            ax.set_yticks(range(len(selected))); ax.set_yticklabels(ylab, fontsize=10)
            thresh = norm.inverse(0.6) if norm is not None else 0.6 * mat.max()
            for i in range(mat.shape[0]):
                for j in range(mat.shape[1]):
                    if mat[i, j] >= 0.05:
                        ax.text(j, i, fmt(mat[i, j]), ha='center', va='center', fontsize=8.5, color='#1a1a1a' if mat[i, j] < thresh else 'white')
            for sp in ('top', 'right', 'left', 'bottom'): ax.spines[sp].set_visible(False)
            ax.tick_params(length=0)
            cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02); cb.set_label(cblabel, fontsize=9.5); cb.ax.tick_params(labelsize=8.5); cb.outline.set_visible(False)
            ax.set_title(title, fontsize=11, loc='left')
            fig.tight_layout(); fig.savefig(out / fname, dpi=160); plt.close(fig)
        heat(M, 'heatmap_selected_topics.png',
             f'Selected topics by genre — mean share of a work\'s words, %\n(seed {a.seed}; works equal-weighted, editions averaged, all chunks in the denominator; square-root colour scale)',
             'mean share of a work\'s words (%)', lambda v: f'{v:.1f}', norm=PowerNorm(gamma=0.5, vmin=0, vmax=max(M.max(), 0.01)))
        heat(P, 'heatmap_prevalence.png',
             f'Selected topics by genre — share of works in which the topic occurs at all, % (seed {a.seed})',
             '% of the genre\'s works with the topic', lambda v: f'{v:.0f}')

    json.dump({'seed': a.seed, 'use': use_cats, 'selected_topics': selected, 'n_selected': len(selected), 'min_works': a.min_works, 'genres_tested': tested,
               'n_works': len(work_rows), 'n_other_multi': len(groups.get('other/multi', [])),
               'genre_rule': genre_rule, 'n_by_genre_source': dict(src_counts), 'annals_map': ANNALS_MAP,
               'representative_only': representative_only, 'n_chunks_used': len(labels), 'n_chunks_placed_excluded': len(labels_all) - len(labels),
               'n_editions_used': len(ed_words), 'sens_threshold': a.sens_threshold, 'sensitivity_topics': [r['topic'] for r in sens_rows]}, open(out / 'config.json', 'w'), indent=1)
    # summary
    n_om = len(groups.get('other/multi', []))
    md = [f'# Aggregation summary — seed {a.seed}', '',
          f'Selected categories: {", ".join(use_cats)} → {len(selected)} topics. Works: {len(work_rows)} ({sum(r["n_editions"] for r in work_rows)} editions). '
          f'Genre conflicts inside a work: {len(conflicts)} (listed in genre_conflicts.csv).' + (f' Representative editions only: {len(labels):,} chunks of {len(ed_words)} editions; the {len(labels_all) - len(labels):,} chunks of the other editions were placed after the fit and are excluded from these tables.' if representative_only else ''), '',
          f'Genre assignment rule: {genre_rule}. Works by source: ' + ', '.join(f'{k} {v}' for k, v in src_counts.most_common()) + '. Both raw labels and the source used are in genre_assignment.csv.', '']
    ann_rows = [r for r in work_rows if r['genre_source'] == 'annals']
    if ann_rows:
        md += [f'Works placed by Annals ({len(ann_rows)}; British Drama label compound or missing):', '', '| work | year | British Drama | Annals | placed in |', '|---|---:|---|---|---|']
        md += [f'| {r["title"][:60]} | {r["year_first"]} | {r["genre_deep"]} | {r["genre_annals"]} | {r["genre_main"]} |' for r in sorted(ann_rows, key=lambda r: (r['genre_main'], r['title']))]
    md += ['',
          f'Coverage (mean share of a work\'s words). "selected" = the {len(selected)} topics of the categories above; the other columns are the categories NOT in the comparison, so every row sums to 100 %.', '',
          '| genre_main | works | editions | selected | ' + ' | '.join(c for c in CATS if c not in use_cats) + ' |', '|---|---:|---:|---:|' + '---:|' * len([c for c in CATS if c not in use_cats])]
    for g, cr in zip(genre_order, cov_rows):
        md.append(f'| {g} | {cr["n_works"]} | {sum(r["n_editions"] for r in groups[g])} | {cr["selected topics mean share of words"]:.1%} | '
                  + ' | '.join(f'{cr[f"{c} mean share of words"]:.1%}' for c in CATS if c not in use_cats) + ' |')
    if om_rows:
        md += ['', f'other/multi = {n_om} works ({100 * n_om / len(work_rows):.1f} % of {len(work_rows)}) kept out of the single-genre comparison; described, not tested:', '',
               '| genre_deep | works | editions | reason |', '|---|---:|---:|---|'] + [f'| {r["genre_deep"]} | {r["n_works"]} | {r["n_editions"]} | {r["reason"]} |' for r in om_rows[:12]]
        if len(om_rows) > 12: md += ['', f'({len(om_rows) - 12} smaller groups omitted here; the full list with example titles is other_multi_works.csv)']
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
    if sens_rows:
        md += ['', f'Dominant-work check: selected topics in which one work holds >= {a.sens_threshold:.0%} of the topic\'s words, aggregated again without that work (sensitivity_dominant_work.csv; clusters unchanged). '
                   'It records whether the highest-mean genre changes and how far the means move; an unchanged ranking does not mean a small effect. '
                   'The threshold is an operational rule, not a statistical criterion, and it does not cover several works of one author or one story that together dominate a topic. p = Kruskal–Wallis across all tested genres, exploratory.', '',
               '| topic | dominant work (genre; share of topic) | its genre: mean with → without (works with topic / works) | highest genre: with → without | original highest genre\'s mean: with → without | p: with → without |', '|---|---|---|---|---|---:|']
        for r in sens_rows:
            if r['highest_without'] == '':
                md.append(f'| T{r["topic"]} {r["label"][:36]} | {r["dominant_work"][:38]} ({r["dominant_work_genre"]}; {r["dominant_share_of_topic_words"]:.0%}) | — | {r["highest_with"]} (not applicable: the dominant work is outside the tested genres) | — | — |')
            else:
                md.append(f'| T{r["topic"]} {r["label"][:36]} | {r["dominant_work"][:38]} ({r["dominant_work_genre"]}; {r["dominant_share_of_topic_words"]:.0%}) | '
                          f'{r["its_genre_mean_with"]:.2%} → {r["its_genre_mean_without"]:.2%} ({r["its_genre_works_with_topic_with"]}/{r["its_genre_n_works_with"]} → {r["its_genre_works_with_topic_without"]}/{r["its_genre_n_works_without"]}) | '
                          f'{r["highest_with"]} → {r["highest_without"]} | {float(r["mean_highest_with"]):.2%} → {r["mean_original_highest_without"]:.2%} | {r["p_with"]} → {r["p_without"]} |')
    md += ['', 'Reading: shares are of a work\'s words, averaged over its editions and then over the works of a genre; the remaining words of every work sit in the '
                'contextual_only / pending / unclassified / outlier columns, so the selected topics never describe the whole genre.']
    (out / 'aggregate_summary.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md[:14])); print(f'... written to {out}')


if __name__ == '__main__':
    main()
