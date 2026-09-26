#!/usr/bin/env python3
"""18_shakespeare.py — Shakespeare against the rest of the corpus, within genre, on 09's work-level topic shares.

    python 18_shakespeare.py --agg <topics_B_s42/aggregate> --sheet <topics_B_s42/topic_sheet.csv>
                             [--use included] [--min-shak 3] [--min-other 10] [--boot 1000] [--perm 1000] [--seed 42] [--out <dir>]

Same measure as the Genre page: the share of a work's words in each topic (representative editions, every chunk
in the denominator, works equal-weighted). Inside every genre group in which Shakespeare has >= --min-shak works
and the others >= --min-other, two groups are compared: his works and everyone else's. Two variants are reported —
'attributed' (any work whose author field names Shakespeare, collaborations and adaptations included) and 'sole'
(author field = Shakespeare alone) — and the collaborative works are listed so the reader can see what moves.

Per genre the script writes (all in --out, default <agg>/shakespeare/):
  shakespeare_works.csv     the works on each side, with the collaboration flag
  topic_by_genre.csv        per topic: mean share on each side, works with the topic, ratio, difference; and the
                            COMPOSITION — which plays supply each side's total (top play and its share of that
                            side's total, top three), so a difference can be read as broad or as one play's
  shared_inventory.csv      the share of each side's words sitting in topics BOTH sides use (of all words and of
                            the words in the compared topics), with and without a >= 1 % floor; exclusive shares
  jsd.csv                   ONE summary per genre: Jensen–Shannon divergence (bits) between the two sides' mean
                            profiles, conditional on the compared topics and with the rest of the words as one extra
                            bin; work-level bootstrap 95 % interval; permutation p (labels shuffled among the
                            genre's works); size-matched median (larger side subsampled to the smaller)
  genre_pairs_jsd.csv       the same divergence between genre groups (all works), with bootstrap intervals
  genre_shared_inventory.csv  share of each genre's words in topics that occur in all of comedy / tragedy / history
  shakespeare_<genre>.png   dumbbell chart of the largest differences, annotated with the top play when one play
                            supplies half of a side
  shakespeare_summary.md    the tables in prose order
Descriptive throughout: the composition columns are the reading, the divergence is one number beside them.
"""
import argparse, csv, json, math, random, re
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

BLUE, ORANGE, GREY, INK, MUTED = '#2a78d6', '#eb6834', '#c9c9c4', '#0b0b0b', '#52514e'


def split_authors(v):
    return [p.strip() for p in re.split(r';\s*|(?<=[a-z])(?=[A-Z][a-z]+, )', v or '') if p.strip()]


def is_attributed(author): return 'shakespeare' in (author or '').lower()
def is_sole(author): return (author or '').strip().lower() == 'shakespeare, william'


def jsd(p, q):
    p = np.asarray(p, float); q = np.asarray(q, float); m = (p + q) / 2
    def kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def profile(ws, topics, mode):
    """Mean over works of the topic-share vector. 'cond' = renormalised to the compared topics; 'rest' = the words
    outside them appended as one bin (the vector then sums to 1 by construction)."""
    M = np.array([[w[f't{t}'] for t in topics] for w in ws], float)
    v = M.mean(axis=0)
    if mode == 'cond':
        s = v.sum(); return v / s if s > 0 else v
    return np.append(v, max(0.0, 1.0 - v.sum()))


def div_with_ci(S, N, topics, mode, rng, boot):
    obs = jsd(profile(S, topics, mode), profile(N, topics, mode))
    bs = []
    for _ in range(boot):
        s = [S[i] for i in rng.integers(0, len(S), len(S))]; n = [N[i] for i in rng.integers(0, len(N), len(N))]
        bs.append(jsd(profile(s, topics, mode), profile(n, topics, mode)))
    return obs, float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agg', required=True); ap.add_argument('--sheet', required=True)
    ap.add_argument('--use', default='', help='categories compared; default from config.json (included)')
    ap.add_argument('--min-shak', type=int, default=3); ap.add_argument('--min-other', type=int, default=10)
    ap.add_argument('--boot', type=int, default=1000); ap.add_argument('--perm', type=int, default=1000); ap.add_argument('--sub', type=int, default=300)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--floor', type=float, default=0.01, help='mean share that counts as "used" in the floored inventory')
    ap.add_argument('--top', type=int, default=15); ap.add_argument('--out', default='')
    a = ap.parse_args()
    agg = Path(a.agg); out = Path(a.out) if a.out else agg / 'shakespeare'; out.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(agg / 'config.json')) if (agg / 'config.json').exists() else {}
    use = [u.strip() for u in a.use.split(',') if u.strip()] or cfg.get('use') or ['included']
    sheet = {int(r['topic']): r for r in csv.DictReader(open(a.sheet, encoding='utf-8'))}
    topics = sorted(t for t, r in sheet.items() if (r.get('use_in_genre_analysis') or '') in use)
    name = {t: (sheet[t].get('Label') or sheet[t].get('draft_label') or f'topic {t}') for t in topics}
    works = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8')))
    for w in works:
        for t in topics: w[f't{t}'] = float(w[f't{t}'])
        w['words_mean'] = float(w['words_mean'])
    rng = np.random.default_rng(a.seed); pyrng = random.Random(a.seed)
    tested = cfg.get('genres_tested') or sorted({w['genre_main'] for w in works if w['genre_main'] != 'other/multi'})

    # ---- the works on each side
    wrows = []
    for w in sorted(works, key=lambda w: (w['genre_main'], not is_attributed(w['author']), w['title'])):
        if is_attributed(w['author']):
            wrows.append({'genre_main': w['genre_main'], 'work_id': w['work_id'], 'title': w['title'], 'author': ' / '.join(split_authors(w['author'])), 'year_first': w['year_first'],
                          'side': 'Shakespeare', 'attribution': 'sole' if is_sole(w['author']) else 'collaborative / adapted', 'words_mean': round(w['words_mean'])})
    with open(out / 'shakespeare_works.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(wrows[0])); wr.writeheader(); wr.writerows(wrows)

    try:
        from scipy.stats import mannwhitneyu
    except ImportError:
        mannwhitneyu = None

    genres = [g for g in tested if sum(1 for w in works if w['genre_main'] == g and is_attributed(w['author'])) >= a.min_shak
              and sum(1 for w in works if w['genre_main'] == g and not is_attributed(w['author'])) >= a.min_other]
    topic_rows, inv_rows, jsd_rows = [], [], []
    md = [f'# Shakespeare against the rest, within genre — {agg.parent.name}', '',
          f'Measure: share of a work\'s words in each topic (representative editions, every chunk in the denominator, works equal-weighted) — the same as the Genre page. Compared topics: {len(topics)} ({", ".join(use)}). '
          f'Genres with at least {a.min_shak} Shakespeare works and {a.min_other} others: {", ".join(genres)}. Two variants: "attributed" = every work whose author field names Shakespeare (collaborations and adaptations included), "sole" = author field is Shakespeare alone.', '']
    md += ['## The works', '', '| genre | work | authors (field) | year | attribution |', '|---|---|---|---:|---|'] + [f'| {r["genre_main"]} | {r["title"][:52]} | {r["author"][:40]} | {r["year_first"]} | {r["attribution"]} |' for r in wrows] + ['']

    for g in genres:
        G = [w for w in works if w['genre_main'] == g]
        for variant, pick in (('attributed', is_attributed), ('sole', is_sole)):
            S = [w for w in G if pick(w['author'])]; N = [w for w in G if not is_attributed(w['author'])]   # 'others' never contain a Shakespeare-attributed work
            if len(S) < a.min_shak: continue
            # ---- per-topic table with composition
            for t in topics:
                sS = np.array([w[f't{t}'] for w in S]); sN = np.array([w[f't{t}'] for w in N])
                mS, mN = float(sS.mean()), float(sN.mean())
                def comp(ws, vals):
                    tot = vals.sum()
                    if tot <= 0: return [], ''
                    order = np.argsort(-vals)
                    parts = [(ws[i], vals[i] / tot) for i in order[:3] if vals[i] > 0]
                    return parts, ''
                cS, _ = comp(S, sS); cN, _ = comp(N, sN)
                auth = Counter()
                for w, v in zip(N, sN):
                    for au in split_authors(w['author']) or ['?']: auth[au] += v / max(sN.sum(), 1e-12)
                p = ''
                if mannwhitneyu is not None and (sS.sum() > 0 or sN.sum() > 0):
                    try: p = round(float(mannwhitneyu(sS, sN, alternative='two-sided').pvalue), 4)
                    except ValueError: p = ''
                topic_rows.append({'genre': g, 'variant': variant, 'topic': t, 'label': name[t],
                                   'mean_shakespeare': round(mS, 5), 'mean_others': round(mN, 5), 'diff_pp': round(100 * (mS - mN), 2), 'ratio': round(mS / mN, 2) if mN > 0 else ('' if mS == 0 else 'inf'),
                                   'works_with_topic_shakespeare': f'{int((sS > 0).sum())}/{len(S)}', 'works_with_topic_others': f'{int((sN > 0).sum())}/{len(N)}',
                                   'shakespeare_top_play': cS[0][0]['title'] if cS else '', 'shakespeare_top_play_share_of_side': round(cS[0][1], 2) if cS else '',
                                   'shakespeare_top3': '; '.join(f'{w["title"][:34]} {100 * v:.0f} %' for w, v in cS),
                                   'others_top_play': cN[0][0]['title'] if cN else '', 'others_top_play_author': ' / '.join(split_authors(cN[0][0]['author'])) if cN else '', 'others_top_play_share_of_side': round(cN[0][1], 2) if cN else '',
                                   'others_top_author': (auth.most_common(1)[0][0] if (auth and sN.sum() > 0) else ''), 'others_top_author_share_of_side': round(auth.most_common(1)[0][1], 2) if (auth and sN.sum() > 0) else '',
                                   'one_play_shakespeare': 'YES' if cS and cS[0][1] >= 0.5 else '', 'one_play_others': 'YES' if cN and cN[0][1] >= 0.5 else '',
                                   'mannwhitney_p_exploratory': p})
            # ---- shared inventory
            used_S = {t for t in topics if any(w[f't{t}'] > 0 for w in S)}; used_N = {t for t in topics if any(w[f't{t}'] > 0 for w in N)}
            both = used_S & used_N
            fl_S = {t for t in topics if np.mean([w[f't{t}'] for w in S]) >= a.floor}; fl_N = {t for t in topics if np.mean([w[f't{t}'] for w in N]) >= a.floor}
            both_fl = fl_S & fl_N
            def share(ws, ts): return float(np.mean([sum(w[f't{t}'] for t in ts) for w in ws])) if ts else 0.0
            allS, allN = share(S, topics), share(N, topics)
            inv_rows.append({'genre': g, 'variant': variant, 'n_shakespeare': len(S), 'n_others': len(N), 'topics_used_shakespeare': len(used_S), 'topics_used_others': len(used_N), 'topics_used_by_both': len(both),
                             'shakespeare_words_in_shared_topics_of_all': round(share(S, both), 4), 'shakespeare_words_in_shared_topics_of_compared': round(share(S, both) / allS, 4) if allS else '',
                             'others_words_in_shared_topics_of_all': round(share(N, both), 4), 'others_words_in_shared_topics_of_compared': round(share(N, both) / allN, 4) if allN else '',
                             'shakespeare_words_in_exclusive_topics_of_all': round(share(S, used_S - used_N), 4), 'others_words_in_exclusive_topics_of_all': round(share(N, used_N - used_S), 4),
                             f'topics_ge{int(100 * a.floor)}pct_shakespeare': len(fl_S), f'topics_ge{int(100 * a.floor)}pct_others': len(fl_N), f'topics_ge{int(100 * a.floor)}pct_both': len(both_fl),
                             f'shakespeare_words_in_both_ge{int(100 * a.floor)}pct_of_compared': round(share(S, both_fl) / allS, 4) if allS else '', f'others_words_in_both_ge{int(100 * a.floor)}pct_of_compared': round(share(N, both_fl) / allN, 4) if allN else '',
                             'compared_topics_share_shakespeare': round(allS, 4), 'compared_topics_share_others': round(allN, 4)})
            # ---- divergence: one summary
            for mode in ('cond', 'rest'):
                obs, lo, hi = div_with_ci(S, N, topics, mode, rng, a.boot)
                pool = S + N; k = len(S); null = []
                for _ in range(a.perm):
                    pyrng.shuffle(pool); null.append(jsd(profile(pool[:k], topics, mode), profile(pool[k:], topics, mode)))
                pperm = (sum(1 for v in null if v >= obs) + 1) / (a.perm + 1)
                subs = [jsd(profile(S, topics, mode), profile([N[i] for i in rng.choice(len(N), len(S), replace=False)], topics, mode)) for _ in range(a.sub)] if len(N) > len(S) else [obs]
                jsd_rows.append({'genre': g, 'variant': variant, 'profile': 'conditional on the compared topics' if mode == 'cond' else 'compared topics + the rest as one bin',
                                 'n_shakespeare': len(S), 'n_others': len(N), 'jsd_bits': round(obs, 4), 'boot_ci_low': round(lo, 4), 'boot_ci_high': round(hi, 4),
                                 'permutation_p': round(pperm, 4), 'permutation_null_median': round(float(np.median(null)), 4), 'size_matched_median': round(float(np.median(subs)), 4), 'size_matched_iqr': f'{np.percentile(subs, 25):.4f}–{np.percentile(subs, 75):.4f}'})

    with open(out / 'topic_by_genre.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(topic_rows[0])); wr.writeheader(); wr.writerows(topic_rows)
    with open(out / 'shared_inventory.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(inv_rows[0])); wr.writeheader(); wr.writerows(inv_rows)
    with open(out / 'jsd.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(jsd_rows[0])); wr.writeheader(); wr.writerows(jsd_rows)

    # ---- genre pairs (all works) and the genre-level shared inventory
    gp = []
    for i, g1 in enumerate(tested):
        for g2 in tested[i + 1:]:
            A = [w for w in works if w['genre_main'] == g1]; B = [w for w in works if w['genre_main'] == g2]
            obs, lo, hi = div_with_ci(A, B, topics, 'cond', rng, max(200, a.boot // 5))
            gp.append({'genre_a': g1, 'genre_b': g2, 'n_a': len(A), 'n_b': len(B), 'jsd_bits_conditional': round(obs, 4), 'boot_ci_low': round(lo, 4), 'boot_ci_high': round(hi, 4)})
    with open(out / 'genre_pairs_jsd.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(gp[0])); wr.writeheader(); wr.writerows(gp)
    core = [g for g in ('comedy', 'tragedy', 'history') if g in tested]
    gi = []
    if len(core) == 3:
        used = {g: {t for t in topics if any(w[f't{t}'] > 0 for w in works if w['genre_main'] == g)} for g in core}
        fl = {g: {t for t in topics if np.mean([w[f't{t}'] for w in works if w['genre_main'] == g]) >= a.floor} for g in core}
        in_all = used[core[0]] & used[core[1]] & used[core[2]]; in_all_fl = fl[core[0]] & fl[core[1]] & fl[core[2]]
        for g in tested:
            ws = [w for w in works if w['genre_main'] == g]
            tot = float(np.mean([sum(w[f't{t}'] for t in topics) for w in ws]))
            excl = used.get(g, set()) - set().union(*(used[h] for h in core if h != g)) if g in core else set()
            gi.append({'genre': g, 'n_works': len(ws), 'compared_topics_share_of_words': round(tot, 4),
                       'words_in_topics_present_in_all_three_core_genres_of_compared': round(float(np.mean([sum(w[f't{t}'] for t in in_all) for w in ws])) / tot, 4) if tot else '',
                       f'words_in_topics_ge{int(100 * a.floor)}pct_in_all_three_of_compared': round(float(np.mean([sum(w[f't{t}'] for t in in_all_fl) for w in ws])) / tot, 4) if tot else '',
                       'words_in_topics_exclusive_to_this_genre_among_core_of_compared': round(float(np.mean([sum(w[f't{t}'] for t in excl) for w in ws])) / tot, 4) if (tot and g in core) else '',
                       'n_topics_in_all_three': len(in_all), f'n_topics_ge{int(100 * a.floor)}pct_in_all_three': len(in_all_fl)})
        with open(out / 'genre_shared_inventory.csv', 'w', newline='', encoding='utf-8') as f:
            wr = csv.DictWriter(f, fieldnames=list(gi[0])); wr.writeheader(); wr.writerows(gi)

    # ---- figures: dumbbell of the largest differences per genre (attributed variant)
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        plt.rcParams.update({'font.size': 10.5, 'font.family': 'sans-serif'})
        for g in genres:
            rows = [r for r in topic_rows if r['genre'] == g and r['variant'] == 'attributed' and max(r['mean_shakespeare'], r['mean_others']) >= 0.005]
            rows = sorted(rows, key=lambda r: -abs(r['diff_pp']))[:a.top][::-1]
            if not rows: continue
            nS = next(r for r in inv_rows if r['genre'] == g and r['variant'] == 'attributed')
            fig, ax = plt.subplots(figsize=(11, 0.42 * len(rows) + 1.8))
            y = np.arange(len(rows)); xs = [100 * r['mean_shakespeare'] for r in rows]; xo = [100 * r['mean_others'] for r in rows]
            for i in range(len(rows)): ax.plot([xo[i], xs[i]], [y[i], y[i]], color=GREY, lw=2, zorder=1, solid_capstyle='round')
            ax.scatter(xo, y, s=64, color=ORANGE, zorder=3, label=f'others ({nS["n_others"]} works)', edgecolor='white', linewidth=1.5)
            ax.scatter(xs, y, s=64, color=BLUE, zorder=3, label=f'Shakespeare ({nS["n_shakespeare"]} works)', edgecolor='white', linewidth=1.5)
            xmax = max(max(xs), max(xo))
            for i, r in enumerate(rows):
                lab = f'{xs[i]:.1f} vs {xo[i]:.1f}'; x0 = max(xs[i], xo[i]) + 0.02 * xmax
                ax.text(x0, y[i], lab, va='center', fontsize=8.5, color=MUTED)
                x1 = x0 + (len(lab) + 2) * 0.0135 * xmax          # after the value label (≈ one character = 0.0135 of the largest value at this width)
                if r['one_play_shakespeare']: ax.text(x1, y[i], f'{100 * r["shakespeare_top_play_share_of_side"]:.0f} % of his side = {r["shakespeare_top_play"].split(" (")[0][:30]}', va='center', fontsize=8, color=BLUE)
                elif r['one_play_others']: ax.text(x1, y[i], f'{100 * r["others_top_play_share_of_side"]:.0f} % of the others = {r["others_top_play"].split(" (")[0][:30]}', va='center', fontsize=8, color=ORANGE)
            ax.set_yticks(y); ax.set_yticklabels([f'T{r["topic"]}  {r["label"][:46]}' for r in rows])
            ax.set_xlim(0, xmax * 1.75); ax.set_xlabel('mean share of a work\'s words (%)')
            ax.set_title(f'{g}: the {len(rows)} topics that differ most between Shakespeare and the others\n(mean share of a work\'s words, works equal-weighted; note = one play gives ≥ half of a side)', loc='left', fontsize=10.5)
            for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
            ax.grid(axis='x', color='#eeeeea'); ax.set_axisbelow(True); ax.legend(loc='lower right', frameon=False)
            fig.tight_layout(); fig.savefig(out / f'shakespeare_{g}.png', dpi=160); plt.close(fig)
    except ImportError:
        print('matplotlib not installed: figures skipped')

    # ---- summary
    md += ['## Divergence (one summary per genre)', '', 'Jensen–Shannon divergence in bits between the two sides\' mean profiles; bootstrap = works resampled within each side; permutation = Shakespeare labels reassigned at random among the genre\'s works; size-matched = the larger side subsampled to the smaller side\'s size. A divergence says how far two weightings differ, not what differs — read the composition tables for that.', '',
           'Reading the columns: the bootstrap interval is biased upward for a side of ten-odd works (resampling duplicates works and roughens the profile), so it should be read as a spread, not as a range that must contain the observed value; the permutation null median is the divergence a random set of the same size shows against the rest, and the size-matched median is the divergence of Shakespeare\'s set against equally small random sets of the others — the two numbers to compare the observed value with.', '',
           '| genre | variant | profile | n (S / others) | JSD | 95 % bootstrap | permutation null median | permutation p | size-matched median |', '|---|---|---|---:|---:|---|---:|---:|---:|']
    md += [f'| {r["genre"]} | {r["variant"]} | {r["profile"]} | {r["n_shakespeare"]} / {r["n_others"]} | {r["jsd_bits"]} | {r["boot_ci_low"]}–{r["boot_ci_high"]} | {r["permutation_null_median"]} | {r["permutation_p"]} | {r["size_matched_median"]} |' for r in jsd_rows]
    md += ['', '## Shared inventory', '', f'Of each side\'s words in the compared topics, the share sitting in topics that BOTH sides use (any work), and in topics that reach a mean of {100 * a.floor:.0f} % on both sides.', '',
           f'| genre | variant | topics used S / others / both | S words in shared topics | others\' words in shared topics | S in both ≥{100 * a.floor:.0f} % | others in both ≥{100 * a.floor:.0f} % | S exclusive (of all words) | others exclusive |', '|---|---|---|---:|---:|---:|---:|---:|---:|']
    fk = f'ge{int(100 * a.floor)}pct'
    md += [f'| {r["genre"]} | {r["variant"]} | {r["topics_used_shakespeare"]} / {r["topics_used_others"]} / {r["topics_used_by_both"]} | {100 * float(r["shakespeare_words_in_shared_topics_of_compared"]):.1f} % | {100 * float(r["others_words_in_shared_topics_of_compared"]):.1f} % | '
           f'{100 * float(r[f"shakespeare_words_in_both_{fk}_of_compared"]):.1f} % | {100 * float(r[f"others_words_in_both_{fk}_of_compared"]):.1f} % | {100 * float(r["shakespeare_words_in_exclusive_topics_of_all"]):.2f} % | {100 * float(r["others_words_in_exclusive_topics_of_all"]):.2f} % |' for r in inv_rows]
    if gi:
        md += ['', '### Genres (all works)', '', '| genre | works | words in topics present in all three core genres (of compared) | in topics ≥ floor in all three | exclusive to this genre among the core |', '|---|---:|---:|---:|---:|']
        for r in gi:
            ex = r['words_in_topics_exclusive_to_this_genre_among_core_of_compared']
            md.append(f'| {r["genre"]} | {r["n_works"]} | {100 * float(r["words_in_topics_present_in_all_three_core_genres_of_compared"] or 0):.1f} % | {100 * float(r[f"words_in_topics_{fk}_in_all_three_of_compared"] or 0):.1f} % | ' + (f'{100 * float(ex):.1f} %' if ex != '' else '—') + ' |')
    for g in genres:
        for variant in ('attributed', 'sole'):
            rows = [r for r in topic_rows if r['genre'] == g and r['variant'] == variant]
            if not rows: continue
            rows = sorted([r for r in rows if max(r['mean_shakespeare'], r['mean_others']) >= 0.005], key=lambda r: -abs(r['diff_pp']))[:12]
            md += ['', f'## {g} — {variant}: the twelve largest differences', '', '| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |', '|---|---:|---:|---:|---|---|']
            for r in rows:
                theirs = (f'{r["others_top_play"][:36]} ({r["others_top_play_author"][:22]}) {100 * float(r["others_top_play_share_of_side"]):.0f} %; top author {r["others_top_author"][:24]} {100 * float(r["others_top_author_share_of_side"]):.0f} %' + (' **one play**' if r['one_play_others'] else '')) if r['others_top_play'] else '—'
                his = (r['shakespeare_top3'] + (' **one play**' if r['one_play_shakespeare'] else '')) if r['shakespeare_top3'] else '—'
                md.append(f'| T{r["topic"]} {r["label"][:40]} | {100 * r["mean_shakespeare"]:.2f} % ({r["works_with_topic_shakespeare"]}) | {100 * r["mean_others"]:.2f} % ({r["works_with_topic_others"]}) | {r["diff_pp"]:+.2f} | {his} | {theirs} |')
    md += ['', 'Reading: a difference carried by one play is a fact about that play, not about the author; a difference spread over many works on both sides is the kind that supports a claim. Nothing here removes, merges or subsets topics.']
    (out / 'shakespeare_summary.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md[:6])); print(f'→ {out}')


if __name__ == '__main__':
    main()
