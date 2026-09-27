#!/usr/bin/env python3
"""
22_author_by_genre.py — author topic profiles against the rest of the same genre (exploratory).

    python 22_author_by_genre.py --agg <topics_B_s42/aggregate> --sheet <topics_B_s42/topic_sheet.csv>
                                 --chunk-meta <chunks_w500/chunk_meta.csv> --deep <DEEP_data.csv>
                                 [--genres comedy,tragedy,history] [--min-author 5] [--min-rest 10]
                                 [--draws 1000] [--seed 42] [--use included] [--out <dir>]

Question: within one genre, which authors' mean topic profiles differ most from the rest of the genre,
and in which topics and works does the difference sit?  Nothing here is a measure of literary value.

Measure (unchanged from 09 / the Genre page / 18): share of a work's words in each topic, one representative
edition per work, every chunk in the denominator (outliers and non-included topics included), works
equal-weighted.  Topics = the review status given by --use (default: included).

Groups, per genre and per author with >= --min-author works carrying their signature (collaborations
included) and >= --min-rest other works:
    A = works of the genre whose author field contains the name (any collaborator counts);
    B = every other work of the genre (Anonymous works stay in B; Anonymous is never an author group).
The two groups of one comparison never share a work; different authors' groups can share collaborative
works, so the comparisons are not independent of one another.  The author field is split with the same
rule as 18_shakespeare.py (collaborators are separate names, never one person).

Roles (tragedy translations above all): the DEEP export's authors_display marks translators (", trans.")
and doubtful names ("(?)").  Each name of the corpus author field is matched to it: translator /
author / author (?) / original author (translated) / unresolved.  A translator is not an author group;
an "original author (translated)" group (Seneca) is compared but labelled as such.  A work in which the
author's role cannot be resolved is held out of that author's comparison (role_pending.csv) and the
effect on the group sizes is reported; the author field itself is never changed.

Divergence: Jensen–Shannon divergence, log2, bits — the divergence, not its square root.
    cond = the group mean of the selected topics, renormalised to sum 1;
    rest = the group means of the selected topics plus one bin for the remaining words.
Both are computed from the group MEAN profile (works equal-weighted), then compared.  If a group's
selected-topic coverage is zero the cond divergence is 'not computable' (no pseudo-count is added).

Reference and sensitivity: (1) random same-size groups — --draws draws of |A| works from A ∪ B, the rest
as the other group, same computation; median, 2.5–97.5 % range and the percentile of the observed value
(a reference range for group sizes, NOT a confidence interval; period and company are not controlled);
(2) leave-one-out over A (the dropped work goes to neither group; B unchanged); (3) sole-signature
variant when the author has >= --min-author sole-signature works (A = sole works; B unchanged).

Per author x genre: mean share of every selected topic in A and in B, the difference in percentage
points (a description of the profiles, not the topic's share of the divergence), works containing the
topic on each side, and for the five largest |differences| the three works supplying most of each side's
mean, with their contribution under the works-equal-weight measure.

Outputs (--out, default <agg>/author_by_genre/): author_counts.csv, comparison_works.csv, role_pending.csv,
author_jsd.csv, random_reference.csv, leave_one_out.csv, sole_signature.csv, topic_differences.csv,
topic_contributions.csv, fig1_author_jsd_random_reference.{png,svg}, fig2_topic_diff_heatmap_<genre>.{png,svg},
methods.md, checks.json, provenance.json.
"""
import argparse, csv, hashlib, json, platform, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

BLUE, ORANGE, RED, GREY, INK, MUTED, MID = '#2a78d6', '#eb6834', '#e34948', '#c9c9c4', '#0b0b0b', '#52514e', '#f0efec'
ROLE_AUTHOR = ('author', 'author (?)', 'original author (translated)', 'original author (translated) (?)', 'reviser', 'reviser (?)', 'adapter', 'adapter (?)')   # roles that count as the author's signature; translator / editor never do


# ---- reused from 18_shakespeare.py -----------------------------------------------------------------
def split_authors(v):
    return [p.strip() for p in re.split(r';\s*|(?<=[a-z])(?=[A-Z][a-z]+, )', v or '') if p.strip()]


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


# ---- reused from 20_company_coverage.py: DEEP export with realignment ------------------------------
def read_deep(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        rd = csv.reader(f); hdr = next(rd); n = len(hdr); ti = hdr.index('title_id'); rows = []
        for row in rd:
            k = len(row) - n
            if k > 0:
                js = [j for j in range(ti, ti + k + 1) if row[j] == row[0]]
                if not js or js[-1] - ti != k: raise SystemExit(f'DEEP row {row[:2]} cannot be realigned')
                s = js[-1] - ti; row = row[:ti] + row[ti + s:ti + s + (n - ti)]
            elif k < 0:
                row = row + [''] * (-k)
            rows.append(dict(zip(hdr, row)))
    return rows


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def both(A, B, topics):
    """(cond, rest) divergences between two work lists; cond is None when a side has no selected-topic words."""
    pa, pb = profile(A, topics, 'cond'), profile(B, topics, 'cond')
    cond = None if pa.sum() == 0 or pb.sum() == 0 else jsd(pa, pb)
    return cond, jsd(profile(A, topics, 'rest'), profile(B, topics, 'rest'))


def cov(ws): return float(np.mean([w['cat:included'] for w in ws]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--agg', required=True); ap.add_argument('--sheet', required=True)
    ap.add_argument('--chunk-meta', required=True); ap.add_argument('--deep', default='')
    ap.add_argument('--genres', default='comedy,tragedy,history'); ap.add_argument('--expect', default='comedy:151,tragedy:111,history:34')
    ap.add_argument('--min-author', type=int, default=5); ap.add_argument('--min-rest', type=int, default=10)
    ap.add_argument('--draws', type=int, default=1000); ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--use', default=''); ap.add_argument('--top-topics', type=int, default=5); ap.add_argument('--top-works', type=int, default=3)
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    agg = Path(a.agg); out = Path(a.out) if a.out else agg / 'author_by_genre'; out.mkdir(parents=True, exist_ok=True)
    cfg = json.load(open(agg / 'config.json')) if (agg / 'config.json').exists() else {}
    use = [u.strip() for u in a.use.split(',') if u.strip()] or cfg.get('use') or ['included']
    sheet = {int(r['topic']): r for r in csv.DictReader(open(a.sheet, encoding='utf-8'))}
    topics = sorted(t for t, r in sheet.items() if (r.get('use_in_genre_analysis') or '') in use)
    label = {t: (sheet[t].get('Label') or sheet[t].get('draft_label') or f'topic {t}') for t in topics}
    works = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8')))
    for w in works:
        for t in range(0, 200):
            if f't{t}' in w: w[f't{t}'] = float(w[f't{t}'])
        for c in ('cat:included', 'cat:outlier_hdbscan', 'words_mean'): w[c] = float(w[c])
        w['names'] = split_authors(w['author'])
    genres = [g.strip() for g in a.genres.split(',') if g.strip()]
    expect = {k: int(v) for k, v in (x.split(':') for x in a.expect.split(',') if ':' in x)}

    # ---- roles from DEEP authors_display -----------------------------------------------------------
    roles = {}   # (work_id, name) -> role
    deep_display = {}
    if a.deep and Path(a.deep).exists():
        cm = {}
        for r in csv.DictReader(open(a.chunk_meta, encoding='utf-8-sig')): cm.setdefault(r['edition_id'], r['deep_id'])
        by_ed = defaultdict(list)
        for r in read_deep(a.deep): by_ed[r['edition_id']].append(r)
        for w in works:
            did = cm.get(w['editions'], ''); row = next((x for x in by_ed.get(w['editions'], []) if x['deep_id'] == did), None)
            deep_display[w['work_id']] = row['authors_display'] if row else ''
    # the corpus author field concatenates names without a separator; the regex rule of 18_shakespeare.py splits
    # "Surname, GivenSurname, Given" but not names without a comma or with brackets. DEEP's authors_display lists
    # the same names separated by ';', so the field is re-split greedily against that list (the work's own names
    # first, then every name seen anywhere in the export); leftovers fall back to the regex rule and are reported.
    def deep_names(disp):
        return [re.sub(r',\s*(trans|rev|ed|adapt)\.?$', '', x.replace('(?)', '').strip()).strip() for x in disp.split(';') if x.strip()]
    all_names = sorted({nm for d in deep_display.values() for nm in deep_names(d)}, key=len, reverse=True)
    split_rows = []
    for w in works:
        own = sorted(deep_names(deep_display.get(w['work_id'], '')), key=len, reverse=True)
        rest = w['author'] or ''; got = []
        while rest:
            hit = next((nm for nm in own if rest.startswith(nm)), None) or next((nm for nm in all_names if rest.startswith(nm)), None)
            if not hit: break
            got.append(hit); rest = rest[len(hit):]
        leftover = split_authors(rest) if rest else []
        checked = got + leftover
        if checked != w['names'] or leftover:
            split_rows.append({'work_id': w['work_id'], 'title': w['title'], 'author_field': w['author'], 'regex_split': ' | '.join(w['names']), 'checked_split': ' | '.join(checked),
                               'leftover_not_matched_to_DEEP': ' | '.join(leftover), 'deep_authors_display': deep_display.get(w['work_id'], '')})
        if checked: w['names'] = checked
    for w in works:
        disp = deep_display.get(w['work_id'], '')
        entries = {}
        for e in [x.strip() for x in disp.split(';') if x.strip()]:
            nm = e; doubt = '(?)' in nm; nm = nm.replace('(?)', '').strip()
            m = re.search(r',\s*(trans|rev|ed|adapt)\.?$', nm)
            tag = {'trans': 'translator', 'rev': 'reviser', 'ed': 'editor', 'adapt': 'adapter'}[m.group(1)] if m else 'author'
            if m: nm = nm[:m.start()].strip()
            if doubt: tag += ' (?)'
            entries[nm] = tag
        has_trans = any(v.startswith('translator') for v in entries.values())
        for nm in w['names']:
            if nm == 'Anonymous': roles[(w['work_id'], nm)] = 'anonymous'; continue
            if not disp: roles[(w['work_id'], nm)] = 'unresolved (no DEEP authors_display)'; continue
            if nm not in entries: roles[(w['work_id'], nm)] = 'unresolved (name not in DEEP authors_display)'; continue
            tag = entries[nm]
            roles[(w['work_id'], nm)] = ('original author (translated)' + (' (?)' if tag.endswith('(?)') else '')) if (tag.startswith('author') and has_trans) else tag
        w['roles'] = {nm: roles[(w['work_id'], nm)] for nm in w['names']}

    # ---- eligibility per genre ---------------------------------------------------------------------
    count_rows, pending_rows, eligible = [], [], []   # eligible: (genre, name, kind)
    for g in genres:
        G = [w for w in works if w['genre_main'] == g]
        names = sorted({nm for w in G for nm in w['names'] if nm != 'Anonymous'})
        for nm in names:
            sig = [w for w in G if nm in w['names']]
            rl = Counter(w['roles'][nm] for w in sig)
            usable = [w for w in sig if w['roles'][nm] in ROLE_AUTHOR]
            pend = [w for w in sig if w['roles'][nm].startswith('unresolved')]
            trans = [w for w in sig if w['roles'][nm] == 'translator']
            sole = [w for w in sig if w['names'] == [nm]]
            rest = [w for w in G if nm not in w['names']]
            kinds = {w['roles'][nm] for w in usable}
            kind = ('original author of translated works' if kinds and kinds <= {'original author (translated)'} else
                    'author (some works translated)' if 'original author (translated)' in kinds else 'author')
            if len(sig) < a.min_author: reason = f'fewer than {a.min_author} works with the signature'
            elif len(usable) < a.min_author: reason = (f'only {len(usable)} usable after roles ({len(trans)} translator, {len(pend)} unresolved)' if usable or pend or trans else 'no usable works')
            elif len(rest) < a.min_rest: reason = f'fewer than {a.min_rest} other works'
            else: reason = ''
            if trans and len(trans) >= a.min_author and not usable: reason = f'translator in all {len(trans)} works — not an author group'
            count_rows.append({'genre': g, 'author': nm, 'n_works_with_signature': len(sig), 'n_sole_signature': len(sole), 'n_collaborative': len(sig) - len(sole),
                               'n_usable_as_author': len(usable), 'n_translator_role': len(trans), 'n_role_unresolved': len(pend),
                               'roles': '; '.join(f'{k} {v}' for k, v in rl.most_common()), 'n_other_works': len(rest), 'group_kind': kind if usable else '',
                               'eligible': 'Y' if not reason else '', 'reason_not_eligible': reason})
            for w in pend:
                pending_rows.append({'genre': g, 'author': nm, 'work_id': w['work_id'], 'title': w['title'], 'author_field': ' / '.join(w['names']),
                                     'deep_authors_display': deep_display.get(w['work_id'], ''), 'role': w['roles'][nm],
                                     'effect': f'held out of {nm}\'s comparison in {g} (A would be {len(usable) + len(pend)} with it; B unchanged)' if not reason else 'author not eligible anyway'})
            if not reason: eligible.append((g, nm, kind))
    count_rows.sort(key=lambda r: (genres.index(r['genre']), -r['n_works_with_signature'], r['author']))
    with open(out / 'author_counts.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(count_rows[0])); wr.writeheader(); wr.writerows(count_rows)
    with open(out / 'author_split_check.csv', 'w', newline='', encoding='utf-8') as f:
        cols = ['work_id', 'title', 'author_field', 'regex_split', 'checked_split', 'leftover_not_matched_to_DEEP', 'deep_authors_display']
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(split_rows)
    with open(out / 'role_pending.csv', 'w', newline='', encoding='utf-8') as f:
        cols = ['genre', 'author', 'work_id', 'title', 'author_field', 'deep_authors_display', 'role', 'effect']
        wr = csv.DictWriter(f, fieldnames=cols); wr.writeheader(); wr.writerows(pending_rows)

    # ---- comparisons ---------------------------------------------------------------------------------
    grp_rows, jsd_rows, rnd_rows, loo_rows, sole_rows, td_rows, tc_rows = [], [], [], [], [], [], []
    checks = {'genre_counts': {g: sum(1 for w in works if w['genre_main'] == g) for g in genres}, 'genre_counts_expected': expect,
              'genre_counts_match': all(sum(1 for w in works if w['genre_main'] == g) == expect.get(g, -1) for g in genres if g in expect),
              'n_selected_topics': len(topics), 'comparisons': []}
    for idx, (g, nm, kind) in enumerate(eligible):
        G = [w for w in works if w['genre_main'] == g]
        A = [w for w in G if nm in w['names'] and w['roles'][nm] in ROLE_AUTHOR]
        held = [w for w in G if nm in w['names'] and w['roles'][nm] not in ROLE_AUTHOR]
        B = [w for w in G if nm not in w['names']]
        ids_a, ids_b = {w['work_id'] for w in A}, {w['work_id'] for w in B}
        assert len(ids_a) == len(A) and len(ids_b) == len(B), 'duplicate works in a group'
        assert not (ids_a & ids_b), 'groups share a work'
        assert len(A) + len(B) + len(held) == len(G)
        for side, ws in (('A', A), ('B', B)):
            for w in ws:
                grp_rows.append({'genre': g, 'author': nm, 'group': side, 'work_id': w['work_id'], 'title': w['title'], 'author_field': ' / '.join(w['names']),
                                 'collaborative': 'Y' if len(w['names']) > 1 else '', 'role_of_author': w['roles'].get(nm, '') if side == 'A' else '',
                                 'year_first': w['year_first'], 'included_share': round(w['cat:included'], 4)})
        n_collab = sum(1 for w in A if len(w['names']) > 1)
        c_obs, r_obs = both(A, B, topics)
        # random same-size groups
        rng = np.random.default_rng([a.seed, idx]); pool = A + B; nA = len(A)
        rc, rr = [], []
        for _ in range(a.draws):
            pick = rng.choice(len(pool), nA, replace=False); s = set(pick.tolist())
            assert len(s) == nA
            SA = [pool[i] for i in pick]; SB = [pool[i] for i in range(len(pool)) if i not in s]
            c, r = both(SA, SB, topics); rc.append(c if c is not None else np.nan); rr.append(r)
        rc, rr = np.array(rc, float), np.array(rr, float)
        def ref(arr, obs):
            arr = arr[~np.isnan(arr)]
            if obs is None or len(arr) == 0: return {'median': '', 'p2_5': '', 'p97_5': '', 'percentile_of_observed': ''}
            return {'median': round(float(np.median(arr)), 4), 'p2_5': round(float(np.percentile(arr, 2.5)), 4), 'p97_5': round(float(np.percentile(arr, 97.5)), 4),
                    'percentile_of_observed': round(100 * float(np.mean(arr <= obs)), 1)}
        refc, refr = ref(rc, c_obs), ref(rr, r_obs)
        for measure, o, rf in (('cond', c_obs, refc), ('rest', r_obs, refr)):
            rnd_rows.append({'genre': g, 'author': nm, 'measure': measure, 'observed_bits': '' if o is None else round(o, 4), 'random_median': rf['median'],
                             'random_p2_5': rf['p2_5'], 'random_p97_5': rf['p97_5'], 'observed_percentile_in_random': rf['percentile_of_observed'],
                             'n_draws': a.draws, 'group_size': nA, 'pool_size': len(pool)})
        # leave-one-out
        lc, lr = [], []
        for w in A:
            A2 = [x for x in A if x is not w]; c, r = both(A2, B, topics)
            lc.append(c); lr.append(r)
            loo_rows.append({'genre': g, 'author': nm, 'dropped_work_id': w['work_id'], 'dropped_title': w['title'], 'n_A_after': len(A2),
                             'jsd_cond_bits': '' if c is None else round(c, 4), 'delta_cond': '' if (c is None or c_obs is None) else round(c - c_obs, 4),
                             'jsd_rest_bits': round(r, 4), 'delta_rest': round(r - r_obs, 4)})
        lc_ok = [(x, w) for x, w in zip(lc, A) if x is not None]
        loo_c = {'min': min(x for x, _ in lc_ok), 'max': max(x for x, _ in lc_ok), 'most': max(lc_ok, key=lambda p: abs(p[0] - c_obs))} if lc_ok and c_obs is not None else None
        loo_r = {'min': min(lr), 'max': max(lr), 'most': max(zip(lr, A), key=lambda p: abs(p[0] - r_obs))}
        # sole-signature variant
        S = [w for w in A if w['names'] == [nm]]
        sole = None
        if len(S) >= a.min_author:
            sc, sr = both(S, B, topics); sole = {'n': len(S), 'cov': cov(S), 'cond': sc, 'rest': sr}
            sole_rows.append({'genre': g, 'author': nm, 'n_sole_works': len(S), 'n_B': len(B), 'mean_included_share_sole': round(cov(S), 4), 'mean_included_share_B': round(cov(B), 4),
                              'jsd_cond_bits': '' if sc is None else round(sc, 4), 'jsd_rest_bits': round(sr, 4),
                              'jsd_cond_bits_all_signatures': '' if c_obs is None else round(c_obs, 4), 'jsd_rest_bits_all_signatures': round(r_obs, 4)})
        jsd_rows.append({'genre': g, 'author': nm, 'group_kind': kind, 'n_A': len(A), 'n_B': len(B), 'n_held_out_role_pending': len(held), 'n_collaborative_in_A': n_collab,
                         'mean_included_share_A': round(cov(A), 4), 'mean_included_share_B': round(cov(B), 4),
                         'jsd_cond_bits': '' if c_obs is None else round(c_obs, 4), 'jsd_rest_bits': round(r_obs, 4),
                         'random_cond_median': refc['median'], 'random_cond_p2_5': refc['p2_5'], 'random_cond_p97_5': refc['p97_5'], 'observed_cond_percentile': refc['percentile_of_observed'],
                         'random_rest_median': refr['median'], 'random_rest_p2_5': refr['p2_5'], 'random_rest_p97_5': refr['p97_5'], 'observed_rest_percentile': refr['percentile_of_observed'],
                         'loo_cond_min': '' if not loo_c else round(loo_c['min'], 4), 'loo_cond_max': '' if not loo_c else round(loo_c['max'], 4),
                         'loo_cond_most_influential_work': '' if not loo_c else loo_c['most'][1]['title'], 'loo_cond_delta_when_dropped': '' if not loo_c else round(loo_c['most'][0] - c_obs, 4),
                         'loo_rest_min': round(loo_r['min'], 4), 'loo_rest_max': round(loo_r['max'], 4), 'loo_rest_most_influential_work': loo_r['most'][1]['title'], 'loo_rest_delta_when_dropped': round(loo_r['most'][0] - r_obs, 4),
                         'n_sole_works': len(S), 'sole_jsd_cond_bits': '' if not sole or sole['cond'] is None else round(sole['cond'], 4), 'sole_jsd_rest_bits': '' if not sole else round(sole['rest'], 4),
                         'sole_mean_included_share': '' if not sole else round(sole['cov'], 4)})
        # topics
        MA = np.array([[w[f't{t}'] for t in topics] for w in A]); MB = np.array([[w[f't{t}'] for t in topics] for w in B])
        mA, mB = MA.mean(axis=0), MB.mean(axis=0); diff = (mA - mB) * 100
        for j, t in enumerate(topics):
            td_rows.append({'genre': g, 'author': nm, 'topic': t, 'label': label[t], 'mean_share_A_pct': round(mA[j] * 100, 3), 'mean_share_B_pct': round(mB[j] * 100, 3),
                            'mean_diff_pp': round(diff[j], 3), 'abs_diff_pp': round(abs(diff[j]), 3), 'works_with_topic_A': int((MA[:, j] > 0).sum()), 'works_with_topic_B': int((MB[:, j] > 0).sum()),
                            'n_A': len(A), 'n_B': len(B)})
        for j in np.argsort(-np.abs(diff))[:a.top_topics]:
            t = topics[j]
            for side, ws, M, m in (('A', A, MA, mA), ('B', B, MB, mB)):
                tot = M[:, j].sum()
                for k in np.argsort(-M[:, j])[:a.top_works]:
                    if M[k, j] <= 0: continue
                    tc_rows.append({'genre': g, 'author': nm, 'topic': t, 'label': label[t], 'mean_diff_pp': round(diff[j], 3), 'group': side, 'n_group': len(ws),
                                    'work_id': ws[k]['work_id'], 'title': ws[k]['title'], 'author_field': ' / '.join(ws[k]['names']), 'share_in_work_pct': round(M[k, j] * 100, 3),
                                    'contribution_to_group_mean_pp': round(M[k, j] / len(ws) * 100, 3), 'share_of_group_total': round(M[k, j] / tot, 3) if tot > 0 else ''})
        checks['comparisons'].append({'genre': g, 'author': nm, 'n_A': len(A), 'n_B': len(B), 'n_held': len(held), 'disjoint': True, 'no_duplicates': True,
                                      'random_group_size': nA, 'random_pool': len(pool), 'draws_with_cond_nan': int(np.isnan(rc).sum())})
        print(f'{g:8s} {nm:28s} A {len(A):3d} B {len(B):3d} cond {c_obs if c_obs is None else round(c_obs, 3)} (rnd med {refc["median"]}, {refc["p2_5"]}–{refc["p97_5"]}, pct {refc["percentile_of_observed"]}) rest {round(r_obs, 3)} (rnd med {refr["median"]}, pct {refr["percentile_of_observed"]})')

    def dump(name, rows, cols=None):
        if not rows:
            (out / name).write_text('', encoding='utf-8'); return
        with open(out / name, 'w', newline='', encoding='utf-8') as f:
            wr = csv.DictWriter(f, fieldnames=cols or list(rows[0])); wr.writeheader(); wr.writerows(rows)
    dump('comparison_works.csv', grp_rows); dump('author_jsd.csv', jsd_rows); dump('random_reference.csv', rnd_rows)
    dump('leave_one_out.csv', loo_rows); dump('sole_signature.csv', sole_rows, ['genre', 'author', 'n_sole_works', 'n_B', 'mean_included_share_sole', 'mean_included_share_B', 'jsd_cond_bits', 'jsd_rest_bits', 'jsd_cond_bits_all_signatures', 'jsd_rest_bits_all_signatures'])
    dump('topic_differences.csv', td_rows); dump('topic_contributions.csv', tc_rows)

    # ---- share-denominator check --------------------------------------------------------------------
    cats = [c for c in works[0] if c.startswith('cat:')]
    dev1 = max(abs(sum(float(w[c]) for c in cats) - 1) for w in works)
    tcols = [c for c in works[0] if re.fullmatch(r't\d+', c)]
    dev2 = max(abs(sum(w[c] for c in tcols) + w['cat:outlier_hdbscan'] - 1) for w in works)
    checks.update({'max_abs_dev_sum_categories_minus_1': dev1, 'max_abs_dev_sum_topics_plus_outlier_minus_1': dev2, 'all_groups_disjoint_and_unique': True,
                   'random_group_sizes_asserted': True, 'n_eligible': len(eligible), 'n_role_pending_records': len(pending_rows), 'n_author_fields_resplit_against_deep': len(split_rows)})
    json.dump(checks, open(out / 'checks.json', 'w'), indent=1)

    # ---- figures ---------------------------------------------------------------------------------------
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.edgecolor': GREY, 'axes.labelcolor': INK, 'xtick.color': MUTED, 'ytick.color': INK, 'svg.fonttype': 'none'})
    note = f'Representative editions · works equal-weighted · within-genre comparison · {len(topics)} {"/".join(use)} topics (share of all words; outliers in the denominator)'
    # figure 1
    panels = [g for g in genres if any(r['genre'] == g for r in jsd_rows)]
    xs = [max(float(r['jsd_cond_bits'] or 0), float(r['random_cond_p97_5'] or 0)) for r in jsd_rows]
    xmax = (max(xs) if xs else 0.5) * 1.12
    heights = [max(1.2, 0.42 * sum(1 for r in jsd_rows if r['genre'] == g) + 0.9) for g in panels]
    fig, axes = plt.subplots(len(panels), 1, figsize=(9.2, sum(heights) + 1.9), gridspec_kw={'height_ratios': heights}, squeeze=False)
    import matplotlib.transforms as mtransforms
    for ax, g in zip(axes[:, 0], panels):
        rows = sorted([r for r in jsd_rows if r['genre'] == g and r['jsd_cond_bits'] != ''], key=lambda r: -float(r['jsd_cond_bits']))
        ys = np.arange(len(rows))[::-1]
        tr = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)
        for y, r in zip(ys, rows):
            lo, hi, md, ob = float(r['random_cond_p2_5']), float(r['random_cond_p97_5']), float(r['random_cond_median']), float(r['jsd_cond_bits'])
            ax.plot([lo, hi], [y, y], color=GREY, lw=4, solid_capstyle='butt', zorder=1)
            ax.plot([md, md], [y - 0.22, y + 0.22], color=ORANGE, lw=2, zorder=2)
            ax.plot(ob, y, marker='D' if r['group_kind'] != 'author' else 'o', ms=7, color=BLUE, mec='white', mew=1.2, zorder=3, ls='none')
            ax.text(1.01, y, f'n = {r["n_A"]} · coverage {float(r["mean_included_share_A"]):.2f}', transform=tr, ha='left', va='center', fontsize=8, color=MUTED, clip_on=False)
        names = [(r['author'].split(',')[0] + ' (translations)' if r['group_kind'] == 'original author of translated works' else r['author']) for r in rows]
        ax.set_yticks(ys); ax.set_yticklabels(names); ax.set_ylim(-0.7, len(rows) - 0.3); ax.set_xlim(0, xmax)
        nG = sum(1 for w in works if w['genre_main'] == g)
        ax.set_title(f'{g.capitalize()} — {nG} works, {len(rows)} authors with ≥ {a.min_author} works', loc='left', fontsize=10, color=INK)
        ax.grid(axis='x', color='#eeeeea', lw=0.8); ax.set_axisbelow(True)
        for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
    axes[-1, 0].set_xlabel('Jensen–Shannon divergence between the author group and the rest of the genre\n(bits; selected topics renormalised)')
    handles = [Line2D([], [], marker='o', color=BLUE, ls='none', ms=7, label='observed (all signatures, collaborations included; diamond = original author of translated works)'),
               Line2D([], [], color=ORANGE, lw=2, label=f'median of {a.draws:,} random groups of the same size'),
               Line2D([], [], color=GREY, lw=4, label='2.5–97.5 % of the random groups — a reference range for the group size, not a confidence interval')]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(0.01, 0.0), ncol=1, frameon=False, fontsize=8)
    fig.suptitle('Author topic profiles against the rest of the same genre', x=0.01, y=0.988, ha='left', fontsize=12, color=INK)
    fig.text(0.01, 0.963, note, ha='left', fontsize=8, color=MUTED)
    fig.text(0.01, 0.948, 'Each panel is sorted on its own; the values are not comparable across genres (different rests, different group sizes).', ha='left', fontsize=8, color=MUTED)
    fig.tight_layout(rect=(0, 0.06, 0.84, 0.93))
    fig.savefig(out / 'fig1_author_jsd_random_reference.png', dpi=200); fig.savefig(out / 'fig1_author_jsd_random_reference.svg'); plt.close(fig)
    # figure 2: heatmaps, one per genre, shared colour scale
    cmap = LinearSegmentedColormap.from_list('div', [BLUE, MID, RED])
    sel = {}
    for g in panels:
        auths = [r['author'] for r in sorted([r for r in jsd_rows if r['genre'] == g], key=lambda r: -float(r['jsd_cond_bits'] or 0))]
        per = {au: sorted([r for r in td_rows if r['genre'] == g and r['author'] == au], key=lambda r: -r['abs_diff_pp'])[:3] for au in auths}
        ts = sorted({r['topic'] for rs in per.values() for r in rs})
        if len(ts) > 15:
            mx = {t: max(r['abs_diff_pp'] for r in td_rows if r['genre'] == g and r['topic'] == t) for t in ts}
            ts = sorted(ts, key=lambda t: -mx[t])[:15]
        M = np.array([[next(r['mean_diff_pp'] for r in td_rows if r['genre'] == g and r['author'] == au and r['topic'] == t) for au in auths] for t in ts])
        order = np.argsort(-np.abs(M).max(axis=1)); sel[g] = (auths, [ts[i] for i in order], M[order])
    vmax = max((np.abs(M).max() for _, _, M in sel.values()), default=1.0)
    for g, (auths, ts, M) in sel.items():
        nA = {r['author']: r['n_A'] for r in jsd_rows if r['genre'] == g}; kindof = {r['author']: r['group_kind'] for r in jsd_rows if r['genre'] == g}
        fig, ax = plt.subplots(figsize=(2.2 + 1.05 * len(auths), 2.1 + 0.36 * len(ts)))
        im = ax.imshow(M, cmap=cmap, norm=TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax), aspect='auto')
        ax.set_xticks(range(len(auths))); ax.set_xticklabels([f'{au.split(",")[0]}{" (transl.)" if kindof[au] == "original author of translated works" else ""}\n(n = {nA[au]})' for au in auths], fontsize=8)
        ax.set_yticks(range(len(ts))); ax.set_yticklabels([f'T{t}  {label[t][:48]}' for t in ts], fontsize=8)
        for i in range(len(ts)):
            for j in range(len(auths)):
                v = M[i, j]; ax.text(j, i, f'{v:+.1f}', ha='center', va='center', fontsize=7.5, color=INK if abs(v) < vmax * 0.6 else 'white')
        ax.set_xticks(np.arange(-.5, len(auths), 1), minor=True); ax.set_yticks(np.arange(-.5, len(ts), 1), minor=True)
        ax.grid(which='minor', color='white', lw=2); ax.tick_params(which='minor', length=0)
        for s in ax.spines.values(): s.set_visible(False)
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02); cb.set_label('author group mean − rest of genre mean (percentage points of all words)', fontsize=8); cb.outline.set_visible(False)
        ax.set_title(f'{g.capitalize()}: topics where an author group differs most from the rest of the genre', loc='left', fontsize=10, color=INK)
        fig.text(0.01, 0.01, f'Shown: each author\'s three largest |differences|, merged (max 15 topics); the full statistics use all {len(topics)} selected topics. ' + note + '. Same colour scale in all three genres.',
                 ha='left', fontsize=7, color=MUTED, wrap=True)
        fig.tight_layout(rect=(0, 0.07, 1, 1))
        fig.savefig(out / f'fig2_topic_diff_heatmap_{g}.png', dpi=200); fig.savefig(out / f'fig2_topic_diff_heatmap_{g}.svg'); plt.close(fig)

    # ---- methods and provenance --------------------------------------------------------------------------
    inputs = {'work_topic_share.csv': str(agg / 'work_topic_share.csv'), 'config.json': str(agg / 'config.json'), 'topic_sheet.csv': a.sheet, 'chunk_meta.csv': a.chunk_meta}
    if a.deep: inputs['DEEP_data.csv'] = a.deep
    prov = {'command': ' '.join(sys.argv), 'python': platform.python_version(), 'numpy': np.__version__, 'matplotlib': matplotlib.__version__,
            'params': {'genres': genres, 'min_author': a.min_author, 'min_rest': a.min_rest, 'draws': a.draws, 'seed': a.seed, 'use': use, 'n_topics': len(topics), 'top_topics': a.top_topics, 'top_works': a.top_works},
            'inputs_sha256': {k: (sha256(v) if Path(v).exists() else 'missing') for k, v in inputs.items()}, 'run': agg.parent.name}
    json.dump(prov, open(out / 'provenance.json', 'w'), indent=1)
    gc_txt = ', '.join(f'{g} {checks["genre_counts"][g]}' for g in genres); ex_txt = ', '.join(f'{g} {expect[g]}' for g in genres if g in expect)
    match_txt = 'match' if checks['genre_counts_match'] else 'DIFFER'
    md = ['# Author topic profiles within genre — methods', '',
          f'Run {agg.parent.name}, seed {a.seed}; {len(topics)} topics with review status {", ".join(use)}; works of genre_main {", ".join(genres)} '
          f'({gc_txt}; expected {ex_txt} — {match_txt}).', '',
          'Measure: share of a work\'s words in each topic (representative edition, every chunk in the denominator including outliers and topics outside the selection), works equal-weighted. Group profile = mean over works.',
          f'Groups: A = works of the genre whose author field contains the name (collaborations included; roles from DEEP authors_display: translator / author / author (?) / original author (translated); '
          f'unresolved roles held out — {len(pending_rows)} records, role_pending.csv); B = every other work of the genre (Anonymous works stay in B). Thresholds: A ≥ {a.min_author}, B ≥ {a.min_rest}. '
          'Groups of one comparison are disjoint; different authors\' groups can share collaborative works (comparisons are not independent).',
          'Divergence: Jensen–Shannon divergence, log2, bits (not the square-rooted distance). cond = selected-topic means renormalised; rest = selected-topic means plus one bin for the remaining words (checks the effect of coverage differences). cond is not computable when a side has no selected-topic words.',
          f'Reference: {a.draws} random groups of |A| works drawn from A ∪ B (seed {a.seed} + comparison index), the rest as the other group; median, 2.5–97.5 % range, percentile of the observed value. A reference range for the group sizes, not a confidence interval; period and company are not controlled. Leave-one-out: each work of A dropped in turn, B unchanged; delta = divergence without the work − observed, so a positive delta means the work was pulling the author group TOWARDS the rest and a negative delta means it was pushing the divergence up; the most influential work is the largest |delta|. Sole-signature variant when ≥ {a.min_author} sole-signature works (a smaller group; its divergence is not directly comparable with the all-signature value or with the random reference, which is drawn at the all-signature size).',
          'Topic tables: mean share per topic in A and B and their difference in percentage points (a description of the two profiles, not the topic\'s share of the divergence); works containing the topic; for the five largest |differences| the three works supplying most of each side\'s mean, with contribution = share / n (works equal-weighted) and share of the side\'s total.',
          'Figures: fig1 = observed cond divergence per author with the random median and 2.5–97.5 % range, panels per genre on one x scale, each sorted on its own (no cross-genre ranking); fig2 = per-genre heatmap of mean differences for a display subset of topics (each author\'s three largest, max 15), diverging scale centred at zero and shared across genres.',
          '', '| genre | author | kind | n A | n B | held out | collab. in A | cov A | cov B | JSD cond | rnd median | rnd 2.5–97.5 | pct | JSD rest | rnd median | pct | LOO cond range | most influential | sole n | sole cond |', '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|---|---:|---:|']
    for r in jsd_rows:
        md.append(f'| {r["genre"]} | {r["author"]} | {r["group_kind"]} | {r["n_A"]} | {r["n_B"]} | {r["n_held_out_role_pending"]} | {r["n_collaborative_in_A"]} | {r["mean_included_share_A"]:.2f} | {r["mean_included_share_B"]:.2f} | {r["jsd_cond_bits"]} | {r["random_cond_median"]} | {r["random_cond_p2_5"]}–{r["random_cond_p97_5"]} | {r["observed_cond_percentile"]} | {r["jsd_rest_bits"]} | {r["random_rest_median"]} | {r["observed_rest_percentile"]} | {r["loo_cond_min"]}–{r["loo_cond_max"]} | {r["loo_cond_most_influential_work"][:30]} ({r["loo_cond_delta_when_dropped"]}) | {r["n_sole_works"]} | {r["sole_jsd_cond_bits"]} |')
    (out / 'methods.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md[:12]))


if __name__ == '__main__':
    main()
