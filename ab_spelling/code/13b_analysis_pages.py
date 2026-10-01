#!/usr/bin/env python3
"""
13b_analysis_pages.py — the analysis pages of the site, built from the frozen result folders.

Called by 13_site.py (never on its own): it receives the site's shell helpers (head / mast / foot / crumbs),
the topic labels and the work → representative-edition map, reads

    <aggregate>/shakespeare/       18_shakespeare.py   (Shakespeare vs the rest of the genre; 19 play distances, download only)
    <aggregate>/author_by_genre/   22_author_by_genre.py (author groups vs the rest of the genre, random reference, contributions)
    <aggregate>/chronology/        23_chronology.py    (topics by estimated first-performance / composition decade)
    <aggregate>/company/           20/21               (company metadata coverage; candidate pair list — no company comparison yet)

and writes  shakespeare.html, chronology.html  and the copies of the result files under  <out>/data/<folder>/ .
It also hands 13_site.py the two landing cards, the links on the Genre and topic pages and the Methods sections.
Every number on the pages is read from those files; nothing is recomputed here except sums of counts for
display. Pages state the measure (representative editions, works equal-weighted, share of all words) and
the date of the result files they were built from.
"""
import csv, datetime, json, re, shutil
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIRS = ('shakespeare', 'author_by_genre', 'chronology', 'company', 'window_check')
FOLDER_ATTR = {'shakespeare': 'sh', 'author_by_genre': 'ab', 'chronology': 'ch', 'company': 'co', 'window_check': 'wc'}
SKIP_COPY = ('_superseded',)
GENRES3 = ('comedy', 'tragedy', 'history')

EXTRA_CSS = """
.masthead nav .navgrp{display:flex;align-items:center;gap:2px;border-left:1px solid var(--rule);border-right:1px solid var(--rule);margin:0 4px;padding:0 4px}
.masthead nav .navgrp i{font-style:normal;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;color:var(--faint);padding:0 6px;white-space:nowrap}
@media(max-width:760px){.masthead .in{flex-wrap:wrap;height:auto;min-height:46px;padding:6px 14px}.masthead nav{margin-left:0;flex-wrap:wrap}.masthead nav .navgrp{flex-wrap:wrap;border:0;padding:0;margin:0}th{top:0}}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:.4em 0 .8em}.tabs button{font:inherit;font-size:.85rem;padding:5px 13px;border:1px solid var(--rule);background:var(--card);border-radius:999px;cursor:pointer;color:var(--muted)}
.tabs button.on{background:var(--accent-soft);color:var(--accent-ink);border-color:#b9c9da;font-weight:600}.panel{display:none}.panel.on{display:block}
.pick{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;margin:.6em 0 1em;font-size:.9rem}.pick label{display:flex;flex-direction:column;gap:2px;color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.pick label{max-width:100%}.pick select{font:inherit;font-size:.92rem;max-width:min(100%,360px);width:max-content;color:var(--ink);text-transform:none;letter-spacing:0}
@media(max-width:600px){.pick select{max-width:calc(100vw - 48px)}}
.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px}.two>div{min-width:0}@media(max-width:820px){.two{grid-template-columns:minmax(0,1fr)}}
.note{font-size:.86rem;color:var(--muted);max-width:80ch}.caveat{background:var(--warm);border-left:3px solid #d9c27a;border-radius:0 8px 8px 0;padding:10px 14px;margin:.8em 0;font-size:.9rem;max-width:none}
.dl{font-size:.88rem;max-width:none;line-height:1.9}.dl a{margin-right:12px;white-space:nowrap}.stamp{font-size:.8rem;color:var(--faint);margin:0 0 1.4em}
.tblx{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}.tblx table{min-width:640px}.tblx th{position:static}
.masthead nav a{white-space:nowrap}.small{font-size:.82rem}
.sub{font-size:.8rem;color:var(--faint);font-weight:500;margin-left:6px}
/* overview charts (Authors page): pure HTML bars, no framework */
.ov{--s:#2a78d6;--o:#eb6834;--g:#8f8f89;--band:#e7e6e0}
.ov h3{font-size:1.02rem;font-weight:700;margin:1.8em 0 .3em;max-width:80ch}.ov .gtag{display:inline-block;font-size:.78rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--accent-ink);background:var(--accent-soft);border-radius:999px;padding:1px 10px;margin-left:8px;vertical-align:middle}
.ov .ovsub{margin:0 0 .6em;max-width:80ch}.ov .ovsum{margin:.2em 0 .8em;max-width:80ch;font-size:.92rem}
.legend{display:flex;flex-wrap:wrap;gap:6px 22px;font-size:.86rem;color:var(--muted);margin:.3em 0 .9em}.legend i{display:inline-block;width:14px;height:11px;border-radius:2px;vertical-align:-1px;margin-right:6px}
.legend i.s{background:var(--s)}.legend i.o{background:var(--o)}.legend i.g{background:var(--g)}.legend i.dot{width:12px;height:12px;border-radius:50%}.legend i.hollow{width:10px;height:10px;border-radius:50%;background:#fff;border:2px solid var(--g)}.legend i.band{background:var(--band);height:15px;vertical-align:-3px}.legend i.sen{background:repeating-linear-gradient(135deg,var(--g) 0 3px,#d9d8d2 3px 6px)}
.chart{margin:0 0 .4em}.tk{position:relative;height:100%;margin-right:56px}.tk .v{position:absolute;top:50%;transform:translateY(-50%);margin-left:6px;font-size:.84rem;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--ink);background:rgba(255,255,255,.82);padding:0 3px;border-radius:3px}
.axis{position:relative;height:1.6em;font-size:.76rem;color:var(--faint)}.axis span{position:absolute;transform:translateX(-50%);top:.2em}.axis:before{content:"";position:absolute;left:0;right:0;top:0;border-top:1px solid var(--rule)}
.axlab{font-size:.8rem;color:var(--muted);margin:.1em 0 0}
/* chart 1: paired bars per topic */
.pbrow{display:grid;grid-template-columns:minmax(0,15rem) minmax(0,1fr);gap:4px 16px;padding:7px 4px;border-top:1px solid var(--rule);cursor:pointer;border-radius:6px}.pbrow:hover,.pbrow:focus-visible{background:var(--soft);outline:none}.pbrow[aria-expanded=true]{background:var(--soft)}
.pbrow.axisrow{cursor:default;border-top:0;padding-top:0}.pbrow.axisrow:hover{background:none}
.pbl{font-size:.92rem;line-height:1.35;align-self:center}.pbl a{color:var(--ink);text-decoration:none;border-bottom:1px dotted var(--faint)}.pbl a:hover{color:var(--accent)}
.pbb{min-width:0}.pbar{display:grid;grid-template-columns:minmax(0,1fr) 6.2em;align-items:center;gap:6px;height:16px;margin:2px 0}.pbar .tk{height:16px}.pbar i{position:absolute;left:0;top:2px;height:12px;border-radius:0 3px 3px 0;display:block}.pbar i.s{background:var(--s)}.pbar i.o{background:var(--o)}
.pbar .m{font-size:.78rem;color:var(--faint);white-space:nowrap;font-variant-numeric:tabular-nums}
.pbar i,.pbar .v{transition:width .3s ease,left .3s ease}@media (prefers-reduced-motion:reduce){.pbar i,.pbar .v{transition:none}}
.ptog{display:flex;flex-wrap:wrap;align-items:center;gap:6px 8px;margin:.2em 0 .6em;font-size:.85rem}.ptog .plab{color:var(--muted);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;margin-right:4px}
.ptog button{font:inherit;font-size:.85rem;padding:5px 13px;border:1px solid var(--rule);background:var(--card);border-radius:999px;cursor:pointer;color:var(--muted)}.ptog button.on{background:var(--accent-soft);color:var(--accent-ink);border-color:#b9c9da;font-weight:600}
.ptog .pbtns{display:inline-flex;gap:6px;flex-wrap:nowrap}.ptog .pscope{color:var(--faint);font-size:.78rem;margin-left:4px}@media (max-width:520px){.ptog .plab{flex-basis:100%;margin:0}.ptog .pscope{flex-basis:100%;margin:0}}.ov .ptag{background:var(--soft);color:var(--muted)}.ov .pernote{font-size:.86rem;color:var(--muted)}
.pbnote{font-size:.78rem;color:var(--muted);margin:2px 0 0;line-height:1.35}.pbd{font-size:.86rem;color:var(--ink);background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:8px 12px;margin:6px 0 2px;max-width:70ch;line-height:1.5}.pbd b{font-weight:650}.pbd[hidden]{display:none}
/* chart 2: author divergence bars with the reference band */
.jbrow{display:grid;grid-template-columns:minmax(0,15rem) minmax(0,1fr);gap:4px 16px;align-items:center;padding:5px 4px;border-top:1px solid var(--rule);cursor:pointer;border-radius:6px}.jbrow:hover,.jbrow:focus-visible{background:var(--soft);outline:none}
.jbrow.axisrow{cursor:default;border-top:0;padding-top:0}.jbrow.axisrow:hover{background:none}
.jbl{font-size:.92rem;line-height:1.35}.jbrow.shakes .jbl{font-weight:650;color:var(--accent-ink)}
.jbb{position:relative;height:24px}.jbb .band{position:absolute;top:7px;height:10px;background:var(--band);border-radius:2px;display:block}.jbb .dot{position:absolute;top:50%;width:14px;height:14px;border-radius:50%;transform:translate(-50%,-50%);background:var(--g);box-shadow:0 0 0 2px #fff;display:block}.jbrow.shakes .jbb .dot{background:var(--s)}.jbrow.sen .jbb .dot{background:#fff;box-shadow:0 0 0 2px var(--g),0 0 0 4px #fff}.jbb .v{margin-left:12px}
.jsep{font-size:.8rem;color:var(--muted);border-top:2px solid var(--rule);margin-top:6px;padding:8px 4px 2px;font-style:italic}
.ov .chartnote{font-size:.84rem;color:var(--muted);max-width:80ch;margin:.5em 0 0}.ov details{margin:.6em 0 0;font-size:.9rem}
@media(max-width:640px){.pbrow,.jbrow{grid-template-columns:minmax(0,1fr);gap:2px}.pbl{padding-bottom:2px}.tk{margin-right:48px}.pbar{grid-template-columns:minmax(0,1fr) 5.6em}.ov h3{font-size:.98rem}}
"""


def _csv(p):
    return list(csv.DictReader(open(p, encoding='utf-8'))) if p.exists() else []


def _f(v, d=None):
    try: return float(v)
    except (TypeError, ValueError): return d


def _pct(v, nd=1):
    x = _f(v)
    return '—' if x is None else f'{x:.{nd}f}'


class Analysis:
    def __init__(self, ctx):
        self.c = ctx; agg = ctx['agg']; self.agg = agg; self.out = ctx['out']; self.E = ctx['E']
        self.sh = agg / 'shakespeare'; self.ab = agg / 'author_by_genre'; self.ch = agg / 'chronology'; self.co = agg / 'company'; self.wc = agg / 'window_check'
        self.have = {'shakespeare': (self.sh / 'jsd.csv').exists(), 'author_by_genre': (self.ab / 'author_jsd.csv').exists(),
                     'chronology': (self.ch / 'coverage.csv').exists(), 'company': (self.co / 'company_coverage.csv').exists(),
                     'window_check': (self.wc / 'window_topic_means.csv').exists() and (self.wc / 'window_works.csv').exists() and (self.wc / 'window_counts.csv').exists()}
        self.today = datetime.date.today().isoformat()
        # work → representative edition page, and titles/authors as the site shows them
        self.rep = ctx['rep_edition']; self.work_title = ctx['work_title']; self.work_author = ctx['work_author']
        self.label_of = ctx['label_of']; self.tpage = ctx['tpage']
        self.warnings = []

    # ---------------------------------------------------------------- helpers ------------------------------
    def stamp(self, *dirs):
        parts = []
        for d in dirs:
            p = getattr(self, FOLDER_ATTR[d])
            files = [x for x in p.glob('*') if x.is_file()]
            if files:
                m = max(x.stat().st_mtime for x in files); parts.append(f'{d} ({datetime.date.fromtimestamp(m).isoformat()})')
        return (f'Run <code>{self.E(self.c["runs_name"])}</code>, seed {self.c["seed"]} · {self.c["n_topics"]} included topics · result files: ' + ', '.join(parts)
                + f' · page built {self.today}. Measure: one representative edition per work, works equal-weighted, topic shares as a share of ALL words of a work (outliers and non-included topics stay in the denominator).')

    def work_link(self, work_id, title=None, root=''):
        e = self.rep.get(str(work_id)); t = self.E((title or self.work_title.get(str(work_id), f'work {work_id}'))[:60])
        return f'<a href="{root}plays/{e}.html">{t}</a>' if e else t

    def topic_link(self, t, root=''):
        return f'<a href="{root}{self.tpage(int(t))}">T{t} {self.E(self.label_of(int(t))[:44])}</a>'

    def dl(self, folder, names, labels=None):
        items = []
        for i, n in enumerate(names):
            if (getattr(self, FOLDER_ATTR[folder]) / n).exists():
                items.append(f'<a href="data/{folder}/{n}" download>{self.E(labels[i] if labels else n)}</a>')
        return '<p class="dl">' + ' '.join(items) + '</p>' if items else ''

    def copy_data(self):
        root = self.out / 'data'; root.mkdir(exist_ok=True)
        n = 0
        for d in DATA_DIRS:
            src = getattr(self, FOLDER_ATTR[d])
            if not src.exists(): continue
            dst = root / d
            if dst.exists(): shutil.rmtree(dst)
            for p in src.rglob('*'):
                if p.is_file() and not any(s in p.parts for s in SKIP_COPY) and p.suffix.lower() in ('.csv', '.md', '.png', '.svg', '.json'):
                    q = dst / p.relative_to(src); q.parent.mkdir(parents=True, exist_ok=True); shutil.copy(p, q); n += 1
        return n

    # ---------------------------------------------------------------- snippets for 13_site ----------------------
    def nav_items(self):
        items = [('genre.html', 'Genre')]
        if self.have['shakespeare'] or self.have['author_by_genre']: items.append(('shakespeare.html', 'Authors'))
        if self.have['chronology']: items.append(('chronology.html', 'Chronology'))
        return items

    def index_cards(self):
        cards = ''
        if self.have['shakespeare'] or self.have['author_by_genre']:
            cards += ('<div class="card"><h3><a href="shakespeare.html">Shakespeare and his contemporaries</a></h3><div class="whence">Within comedy, tragedy and history: how the topic shares of Shakespeare\'s works, and of every author with five or more works, compare with the rest of the genre — with a random same-size reference, and the works behind each difference.</div></div>')
        if self.have['chronology']:
            cards += ('<div class="card"><h3><a href="chronology.html">Chronology</a></h3><div class="whence">The corpus by estimated first-performance / composition decade: sample size per decade, mean topic shares within comedy, tragedy and history, and a way to trace any cell back to its works.</div></div>')
        return cards

    def genre_links(self):
        parts = []
        if self.have['shakespeare'] or self.have['author_by_genre']: parts.append('<a href="shakespeare.html">Shakespeare and his contemporaries</a> (author groups against the rest of the same genre)')
        if self.have['chronology']: parts.append('<a href="chronology.html">Chronology</a> (the same measure by estimated first-performance / composition decade)')
        return f'<p class="note">Related analyses: {" · ".join(parts)}.</p>' if parts else ''

    def topic_links(self, t):
        parts = []
        if self.have['author_by_genre']: parts.append(f'<a href="shakespeare.html#t{t}">author comparisons for this topic</a>')
        if self.have['chronology']: parts.append(f'<a href="chronology.html#t{t}">this topic by decade</a>')
        return f'<p class="note">In the analyses: {" · ".join(parts)}.</p>' if parts else ''

    # ---------------------------------------------------------------- Shakespeare page ---------------------------
    NOUNS = {'comedy': ('comedy', 'comedies'), 'tragedy': ('tragedy', 'tragedies'), 'history': ('history play', 'history plays')}

    def overview(self, aj, tbg, td):
        """The two overview charts (data + static HTML). Chart 1: the ten included topics with the highest simple average of
        the two groups' mean shares (Shakespeare's plays / other plays of the genre), raw shares of all words, the same topics
        in the same order on both sides. Chart 2: every author group's divergence on the selected topics (jsd_cond_bits of
        author_jsd.csv) with the 2.5–97.5 % range of the random same-size groups. Nothing is recomputed: values are read from
        topic_by_genre.csv (18) and author_jsd.csv (22); only the selection, the order and the sum of the ten means are done here."""
        E = self.E
        O = {'genres': [], 'nouns': self.NOUNS, 'topics': {}, 'authors': {}, 'tpage': {str(t): self.tpage(int(t)) for t in self.c['topics']}, 'shakes': 'Shakespeare, William'}
        checks = {}
        # ---- common-window check (24_window_check.py): the same ten topics, both sides restricted to the window ------
        # Means come from window_topic_means.csv; the works behind each side (top plays, contributions) are rebuilt from
        # work_topic_share.csv + the side / in_window flags of window_works.csv, with the same equal-weight rule, and are
        # cross-checked against the means and counts in the result files. Nothing is re-embedded or re-clustered.
        win = None
        if self.have['window_check']:
            wtm = {(r['genre'], int(r['topic'])): r for r in _csv(self.wc / 'window_topic_means.csv')}
            wcnt = {(r['genre'], r['variant']): r for r in _csv(self.wc / 'window_counts.csv')}
            wworks = _csv(self.wc / 'window_works.csv')
            wts = {r['work_id']: r for r in _csv(self.agg / 'work_topic_share.csv')}
            wlo, whi = None, None
            try:   # the window as the check was run with (checks.json "window": [lo, hi]; provenance args.window "lo,hi")
                v = json.loads((self.wc / 'checks.json').read_text(encoding='utf-8')).get('window')
                if isinstance(v, (list, tuple)) and len(v) == 2: wlo, whi = int(v[0]), int(v[1])
            except Exception: pass
            if wlo is None:
                try:
                    v = json.loads((self.wc / 'provenance.json').read_text(encoding='utf-8')).get('args', {}).get('window', '')
                    wlo, whi = (int(x) for x in re.findall(r'\d{4}', str(v))[:2])
                except Exception: pass
            if wlo is None or whi is None:
                self.warnings.append('window check: window years not found in checks.json / provenance.json — the period toggle is not shown')
            else:
                win = {'lo': wlo, 'hi': whi, 'label': f'{wlo}–{whi}', 'counts': {}}
        def side_rows(g, period, t):
            """works of one genre & side (period = 'full' | 'window'), the mean share of topic t (% of all words, works
            equal-weighted), the number of works with the topic, and the works supplying most of the mean."""
            res = {}
            for side_key, side_val in (('S', 'Shakespeare'), ('O', 'other')):
                ws = [w for w in wworks if w['genre'] == g and w['side'] == side_val and (period == 'full' or w['in_window'] == 'yes')]
                n = len(ws); vals = []
                for w in ws:
                    row = wts.get(w['work_id'])
                    if row is None: self.warnings.append(f'window check: work {w["work_id"]} ({w["title"][:30]}) missing in work_topic_share.csv'); continue
                    vals.append((100 * _f(row.get(f't{t}'), 0), w))
                tot = sum(v for v, _ in vals); mean = tot / n if n else 0.0
                top = sorted(vals, key=lambda x: -x[0])
                contrib = [[w['work_id'], w['title'], w['author_field'], round(v, 4), round(v / n, 4) if n else 0, round(v / tot, 4) if tot else 0, self.rep.get(w['work_id'], '')] for v, w in top[:3] if v > 0]
                res[side_key] = {'n': n, 'mean': mean, 'with': sum(1 for v, _ in vals if v > 0), 'top': contrib}
            return res
        for g in GENRES3:
            rows = [r for r in tbg if r['genre'] == g and r['variant'] == 'attributed']
            if not rows: continue
            O['genres'].append(g)
            rows = sorted(rows, key=lambda r: -((_f(r['mean_shakespeare'], 0) + _f(r['mean_others'], 0)) / 2))[:10]
            nS, nO = (rows[0]['works_with_topic_shakespeare'].split('/')[1], rows[0]['works_with_topic_others'].split('/')[1])
            out = []
            for r in rows:
                out.append([int(r['topic']), self.label_of(int(r['topic'])), round(100 * _f(r['mean_shakespeare'], 0), 4), round(100 * _f(r['mean_others'], 0), 4),
                            int(r['works_with_topic_shakespeare'].split('/')[0]), int(r['works_with_topic_others'].split('/')[0]),
                            r['shakespeare_top_play'], _f(r['shakespeare_top_play_share_of_side'], 0), r['others_top_play'], r['others_top_play_author'], _f(r['others_top_play_share_of_side'], 0), [], []])
            # sum of the ten equal-weighted means = mean over plays of the ten shares (works equal-weighted), per side
            O['topics'][g] = {'nS': int(nS), 'nO': int(nO), 'sumS': round(sum(x[2] for x in out), 2), 'sumO': round(sum(x[3] for x in out), 2), 'rows': out}
            checks[f'{g}_top10_topics'] = [x[0] for x in out]
            if win is not None and (g, 'window') in wcnt and all((g, x[0]) in wtm for x in out):
                # full-period works behind each side (same measure; cross-checked against topic_by_genre.csv)
                for x in out:
                    sr = side_rows(g, 'full', x[0])
                    if abs(sr['S']['mean'] - x[2]) > 0.02 or abs(sr['O']['mean'] - x[3]) > 0.02 or sr['S']['with'] != x[4] or sr['O']['with'] != x[5]:
                        self.warnings.append(f'window check: full-period recomputation differs for {g} T{x[0]}: {sr["S"]["mean"]:.3f}/{sr["O"]["mean"]:.3f} vs {x[2]}/{x[3]}')
                    if x[6] and sr['S']['top'] and sr['S']['top'][0][1] != x[6]: self.warnings.append(f'window check: top Shakespeare play differs for {g} T{x[0]}: {sr["S"]["top"][0][1]} vs {x[6]}')
                    if x[8] and sr['O']['top'] and sr['O']['top'][0][1] != x[8]: self.warnings.append(f'window check: top other play differs for {g} T{x[0]}: {sr["O"]["top"][0][1]} vs {x[8]}')
                    x[11], x[12] = sr['S']['top'], sr['O']['top']
                # the window: means and counts from the result files, works behind them recomputed from the same shares
                cw = wcnt[(g, 'window')]; wrows = []
                for x in out:
                    m = wtm[(g, x[0])]; sr = side_rows(g, 'window', x[0])
                    vS, vO = round(_f(m['mean_S_win_pct'], 0), 4), round(_f(m['mean_O_win_pct'], 0), 4)
                    wS, wO = int(m['works_with_topic_S_win'].split('/')[0]), int(m['works_with_topic_O_win'].split('/')[0])
                    if abs(sr['S']['mean'] - vS) > 0.02 or abs(sr['O']['mean'] - vO) > 0.02 or sr['S']['with'] != wS or sr['O']['with'] != wO or sr['S']['n'] != int(cw['n_shakespeare']) or sr['O']['n'] != int(cw['n_other']):
                        self.warnings.append(f'window check: recomputation differs for {g} T{x[0]} in the window: {sr["S"]["mean"]:.3f}/{sr["O"]["mean"]:.3f} ({sr["S"]["with"]}/{sr["S"]["n"]}, {sr["O"]["with"]}/{sr["O"]["n"]}) vs {vS}/{vO} ({m["works_with_topic_S_win"]}, {m["works_with_topic_O_win"]})')
                    tS = sr['S']['top'][0] if sr['S']['top'] else None; tO = sr['O']['top'][0] if sr['O']['top'] else None
                    wrows.append([x[0], x[1], vS, vO, wS, wO, tS[1] if tS else '', tS[5] if tS else 0, tO[1] if tO else '', tO[2] if tO else '', tO[5] if tO else 0, sr['S']['top'], sr['O']['top']])
                if int(cw['n_shakespeare']) != int(nS): self.warnings.append(f'window check: Shakespeare side changes inside the window in {g} ({cw["n_shakespeare"]} vs {nS}) — the page states that it does not')
                O['topics'][g]['win'] = {'nS': int(cw['n_shakespeare']), 'nO': int(cw['n_other']), 'sumS': round(sum(x[2] for x in wrows), 2), 'sumO': round(sum(x[3] for x in wrows), 2), 'rows': wrows}
                win['counts'][g] = {'full': [int(nS), int(nO)], 'window': [int(cw['n_shakespeare']), int(cw['n_other'])]}
                checks[f'{g}_window_counts'] = win['counts'][g]
            # authors: sorted by the observed divergence; Seneca (original author of translated works) shown apart at the end
            arows = [r for r in aj if r['genre'] == g]
            main = sorted([r for r in arows if r['group_kind'] != 'original author of translated works'], key=lambda r: -_f(r['jsd_cond_bits'], 0))
            apart = sorted([r for r in arows if r['group_kind'] == 'original author of translated works'], key=lambda r: -_f(r['jsd_cond_bits'], 0))
            def arow(r, sep):
                k = f'{g}|{r["author"]}'
                diffs = [(abs(_f(x['mean_diff_pp'], 0)), x['topic']) for x in td if x['genre'] == g and x['author'] == r['author']]
                best = max(diffs)[1] if diffs else ''
                surname = r['author'].split(',')[0]
                return [r['author'], surname, sep, int(r['n_A']), int(r['n_B']), _f(r['jsd_cond_bits']), _f(r['random_cond_p2_5']), _f(r['random_cond_p97_5']), _f(r['random_cond_median']),
                        _f(r['observed_cond_percentile']), _f(r['mean_included_share_A']), _f(r['mean_included_share_B']), best]
            O['authors'][g] = [arow(r, 0) for r in main] + [arow(r, 1) for r in apart]
        if win is not None and win['counts']: O['win'] = win
        O['dl'] = {'full': [('data/shakespeare/topic_by_genre.csv', 'topic_by_genre.csv')] if (self.sh / 'topic_by_genre.csv').exists() else [],
                   'window': [(f'data/window_check/{n}', n) for n in ('window_topic_means.csv', 'window_counts.csv', 'window_works.csv', 'summary.md') if (self.wc / n).exists()]}
        allv = [v for g in O['authors'] for a in O['authors'][g] for v in (a[5], a[7]) if v is not None]
        import math
        O['jmax'] = math.ceil(max(allv) * 10 - 1e-9) / 10 if allv else 1.0   # one shared axis for the three genres
        self.overview_checks = checks
        first = O['genres'][0] if O['genres'] else 'comedy'
        html = ('<h2 id="overview">Overview</h2>'
                '<div class="ov">'
                '<div class="pick"><label>genre<select id="og">' + ''.join(f'<option value="{g}">{g.capitalize()}</option>' for g in O['genres']) + '</select></label>'
                '<span class="note" style="margin:0">The choice applies to both charts below and to section C.' + (' The period buttons in the first chart apply to that chart only; the author chart and sections A–C use the full corpus.' if 'win' in O else '') + '</span></div>'
                # chart 1
                '<h3 id="ov1h">Which topics are most prominent in Shakespeare\'s plays and other plays of the same genre? <span class="gtag" id="ov1g"></span><span class="gtag ptag" id="ov1pt" hidden></span></h3>'
                '<p class="ovsub">Each pair of bars compares the average share of a topic in Shakespeare\'s plays and in other plays of the same genre.</p>'
                + (('<div class="ptog" id="ov1p" role="group" aria-label="Comparison period — this chart only"><span class="plab">Comparison period</span>'
                    '<span class="pbtns"><button type="button" data-p="full" class="on" aria-pressed="true">Full corpus</button><button type="button" data-p="window" aria-pressed="false">' + E(O['win']['label']) + '</button></span>'
                    '<span class="pscope">applies to this chart and its details only</span></div>'
                    '<p class="ovsum pernote" id="ov1per"></p>') if 'win' in O else '')
                + '<div class="legend" id="ov1l"></div>'
                '<div class="chart" id="ov1"></div>'
                '<p class="axlab">Average share of a play\'s words (%)</p>'
                '<p class="ovsum" id="ov1sum"></p>'
                '<p class="chartnote">Representative editions; plays weighted equally. Percentages include all words in the denominator, including text outside the selected topics. Only the ten most prominent topics are shown: those with the highest simple average of the two groups\' full-corpus mean shares, in that order on both sides' + (' and in both period views; the axis is scaled to the genre shown and fits both views' if 'win' in O else '; the axis is scaled to the genre shown') + '. '
                '<i>n/N plays</i> = plays of the group with at least one chunk assigned to the topic; a play without one is not thereby without the subject, and 0 means that no chunk of any play in the group was assigned to the topic. Where one play supplies more than half of a group\'s total for a topic, that play is named. Shakespeare\'s side includes collaborative plays carrying his signature. Click a row for the exact values and the works behind them; <a href="methods.html">Methods</a> has the measure.</p>'
                '<details><summary>Table: the ten topics with both groups\' values</summary><div class="tblx" id="ov1t"></div><p class="dl" id="ov1dl"></p></details>'
                # chart 2
                '<h3 id="ov2h">How far is each playwright\'s topic profile from the rest of the genre? <span class="gtag" id="ov2g"></span>' + ('<span class="gtag ptag">Full corpus</span>' if 'win' in O else '') + '</h3>'
                '<p class="ovsub">Jensen–Shannon divergence between each playwright\'s plays and the other plays of the same genre, on the 53 selected topics. A dot further to the right means a more different distribution of the selected topics — not greater literary originality or quality.</p>'
                '<div class="legend" id="ov2l"></div>'
                '<div class="chart" id="ov2"></div>'
                '<p class="axlab">Jensen–Shannon divergence (bits; the same axis for the three genres)</p>'
                '<p class="ovsum" id="ov2read"></p>'
                '<p class="chartnote" id="ov2n"></p>'
                '<details><summary>About this comparison</summary><p class="chartnote">Each playwright is compared with the remaining plays in the same genre. Plays are weighted equally; only authors represented by at least five plays are shown, collaborative plays included. '
                'The grey line shows results from randomly selected groups containing the same number of plays (1,000 draws, 2.5–97.5 %). It is a reference range, not a confidence interval, and it does not control for date, company or other factors; small groups can produce large divergences by chance, and the range helps to judge this. A dot inside the line does not mean the two groups are the same, and a dot outside it does not mean greater originality or value. '
                'Unlike the chart above, which uses all words of a play as the denominator, this divergence compares the relative distribution within the 53 selected topics only. Values are not a ranking across genres. Click a playwright to see which topics and which plays account for the difference (section C).</p></details>'
                '<details><summary>Table: divergence, group size, coverage and the random reference</summary><div class="tblx" id="ov2t"></div></details>'
                '</div>')
        return html, O

    def build_shakespeare(self):
        E = self.E; c = self.c
        jsd18 = _csv(self.sh / 'jsd.csv'); tbg = _csv(self.sh / 'topic_by_genre.csv'); works18 = _csv(self.sh / 'shakespeare_works.csv'); inv = _csv(self.sh / 'shared_inventory.csv')
        aj = _csv(self.ab / 'author_jsd.csv'); td = _csv(self.ab / 'topic_differences.csv'); tc = _csv(self.ab / 'topic_contributions.csv')
        loo = _csv(self.ab / 'leave_one_out.csv'); sole = _csv(self.ab / 'sole_signature.csv'); counts = _csv(self.ab / 'author_counts.csv'); pend = _csv(self.ab / 'role_pending.csv')
        # cross-source check: Shakespeare's groups in 18 and 22
        xcheck = []
        for g in GENRES3:
            r18 = next((r for r in jsd18 if r['genre'] == g and r['variant'] == 'attributed' and r['profile'].startswith('conditional')), None)
            r22 = next((r for r in aj if r['genre'] == g and r['author'] == 'Shakespeare, William'), None)
            if r18 and r22:
                same_n = (r18['n_shakespeare'] == r22['n_A'] and r18['n_others'] == r22['n_B']); same_j = abs(_f(r18['jsd_bits'], 0) - _f(r22['jsd_cond_bits'], 0)) < 5e-4
                xcheck.append({'genre': g, 'n18': f'{r18["n_shakespeare"]} vs {r18["n_others"]}', 'n22': f'{r22["n_A"]} vs {r22["n_B"]}', 'j18': r18['jsd_bits'], 'j22': r22['jsd_cond_bits'], 'null18': r18['permutation_null_median'], 'null22': r22['random_cond_median'], 'ok': same_n and same_j})
                if not (same_n and same_j): self.warnings.append(f'Shakespeare groups differ between 18 and 22 in {g}: {r18["n_shakespeare"]}/{r18["n_others"]} JSD {r18["jsd_bits"]} vs {r22["n_A"]}/{r22["n_B"]} JSD {r22["jsd_cond_bits"]}')
        # ---- section A -------------------------------------------------------------------------------------
        tabsA = '<div class="tabs" data-group="A">' + ''.join(f'<button data-tab="{g}"{" class=on" if i == 0 else ""}>{g.capitalize()}</button>' for i, g in enumerate(GENRES3)) + '</div>'
        panelsA = ''
        for i, g in enumerate(GENRES3):
            r22 = next((r for r in aj if r['genre'] == g and r['author'] == 'Shakespeare, William'), None)
            rc = next((r for r in jsd18 if r['genre'] == g and r['variant'] == 'attributed' and r['profile'].startswith('conditional')), None)
            rr = next((r for r in jsd18 if r['genre'] == g and r['variant'] == 'attributed' and not r['profile'].startswith('conditional')), None)
            sc = next((r for r in jsd18 if r['genre'] == g and r['variant'] == 'sole' and r['profile'].startswith('conditional')), None)
            sr = next((r for r in jsd18 if r['genre'] == g and r['variant'] == 'sole' and not r['profile'].startswith('conditional')), None)
            iv = next((r for r in inv if r['genre'] == g and r['variant'] == 'attributed'), None)
            if not rc: continue
            nS, nO = rc['n_shakespeare'], rc['n_others']
            facts = (f'<div class="facts"><div class="f"><b>{nS}</b><i>Shakespeare works</i></div><div class="f"><b>{nO}</b><i>other {g} works</i></div>'
                     + (f'<div class="f"><b>{100 * _f(r22["mean_included_share_A"]):.0f} % / {100 * _f(r22["mean_included_share_B"]):.0f} %</b><i>mean included coverage, Shakespeare / others</i></div>' if r22 else '')
                     + (f'<div class="f"><b>{r22["n_collaborative_in_A"]}</b><i>collaborative works on his side</i></div>' if r22 else '') + '</div>')
            wl = [w for w in works18 if w['genre_main'] == g]
            wlist = ', '.join(self.work_link(w['work_id'], w['title']) + (' <span class="sub">collab.</span>' if w['attribution'] != 'sole' else '') for w in sorted(wl, key=lambda w: w['title']))
            fig = f'shakespeare_{g}.png'
            fig_html = (f'<div class="fig"><a href="data/shakespeare/{fig}"><img class="heat" src="data/shakespeare/{fig}" alt="Shakespeare vs other {g}: largest topic differences"></a><p class="fighint">Largest differences in mean topic share; the annotation names a play that supplies half or more of one side\'s total. Click to enlarge.</p></div>' if (self.sh / fig).exists() else '')
            rows = sorted([r for r in tbg if r['genre'] == g and r['variant'] == 'attributed'], key=lambda r: -abs(_f(r['diff_pp'], 0)))
            def trow(r):
                return (f'<tr><td>{self.topic_link(r["topic"])}</td><td class="num">{100 * _f(r["mean_shakespeare"]):.2f}</td><td class="num">{100 * _f(r["mean_others"]):.2f}</td><td class="num">{_f(r["diff_pp"]):+.2f}</td>'
                        f'<td class="num">{E(r["works_with_topic_shakespeare"])}</td><td class="num">{E(r["works_with_topic_others"])}</td><td class="small">{E(r["shakespeare_top_play"][:34])}{(" (" + str(round(100 * _f(r["shakespeare_top_play_share_of_side"], 0))) + " %)") if r["shakespeare_top_play"] else ""}</td>'
                        f'<td class="small">{E(r["others_top_play"][:34])}{(" — " + E(r["others_top_play_author"][:22])) if r["others_top_play_author"] else ""}{(" (" + str(round(100 * _f(r["others_top_play_share_of_side"], 0))) + " %)") if r["others_top_play"] else ""}</td></tr>')
            thead = '<thead><tr><th>topic</th><th class="num">Shakespeare mean %</th><th class="num">others mean %</th><th class="num">diff. (pp)</th><th class="num">works with topic (S)</th><th class="num">(others)</th><th>top Shakespeare play (share of his side)</th><th>top other play — author (share of that side)</th></tr></thead>'
            tbl = (f'<div class="tblx"><table class="sortable">{thead}<tbody>' + ''.join(trow(r) for r in rows[:12]) + '</tbody></table></div>'
                   + f'<details><summary>All {len(rows)} included topics for {g}</summary><div class="tblx"><table class="sortable">{thead}<tbody>' + ''.join(trow(r) for r in rows) + '</tbody></table></div></details>')
            jsd_html = ('<details><summary>Divergence summary and the sole-signature variant</summary><div class="tblx"><table><thead><tr><th>variant</th><th>profile</th><th class="num">n Shakespeare / others</th><th class="num">JSD (bits)</th><th class="num">random-label median</th><th class="num">permutation p</th><th class="num">size-matched median</th></tr></thead><tbody>'
                        + ''.join(f'<tr><td>{E(r["variant"])}</td><td>{E(r["profile"])}</td><td class="num">{r["n_shakespeare"]} / {r["n_others"]}</td><td class="num">{r["jsd_bits"]}</td><td class="num">{r["permutation_null_median"]}</td><td class="num">{r["permutation_p"]}</td><td class="num">{r["size_matched_median"]}</td></tr>' for r in (rc, rr, sc, sr) if r)
                        + '</tbody></table></div><p class="note">JSD = Jensen–Shannon divergence between the two sides\' mean profiles, log2, in bits (the divergence, not its square root); "conditional" renormalises the included topics, the second profile adds the remaining words as one bin. The random-label median is the median divergence when the same number of works is drawn at random from the genre (a reference for the group size, not a confidence interval); the permutation p is exploratory. "sole" keeps only works whose author field is Shakespeare alone; its side is smaller, so its divergence is not directly comparable with the attributed value.'
                        + (f' Shared inventory: {100 * _f(iv["shakespeare_words_in_shared_topics_of_compared"]):.1f} % of his words in compared topics fall in topics the others also use (others: {100 * _f(iv["others_words_in_shared_topics_of_compared"]):.1f} %).' if iv else '') + '</p></details>')
            panelsA += (f'<div class="panel{" on" if i == 0 else ""}" data-group="A" data-tab="{g}">{facts}<p class="note">Shakespeare\'s side: every {g} work whose author field names him (collaborations and adaptations included): {wlist}. The other side is every other {g} work of the corpus. Signature rule as recorded in the author field of the corpus; no attribution research.</p>'
                        + fig_html + '<h3>Mean topic share on each side (largest differences first)</h3>' + tbl + jsd_html + '</div>')
        secA = ('<h2 id="within-genre">A. Shakespeare within genre</h2><p>For each of the three genres with enough works, the mean share of every included topic in Shakespeare\'s works is set beside the mean in all other works of that genre. A difference in mean share describes the two profiles; it says nothing about literary value, and a difference carried by one play is a fact about that play (the tables name the play that supplies most of a side).</p>'
                + tabsA + panelsA)
        # ---- section B ------------------------------------------------------------------------------------------
        def kind_label(r):
            return r['author'].split(',')[0] + ' <span class="sub">original author of English translations</span>' if r['group_kind'] == 'original author of translated works' else E(r['author'])
        def brow(r):
            return (f'<tr><td>{E(r["genre"])}</td><td>{kind_label(r)}</td><td class="num">{r["n_A"]}</td><td class="num">{r["n_B"]}</td><td class="num">{r["n_collaborative_in_A"]}</td><td class="num">{100 * _f(r["mean_included_share_A"]):.0f} / {100 * _f(r["mean_included_share_B"]):.0f}</td>'
                    f'<td class="num">{r["jsd_cond_bits"]}</td><td class="num">{r["random_cond_median"]} ({r["random_cond_p2_5"]}–{r["random_cond_p97_5"]})</td><td class="num">{r["observed_cond_percentile"]}</td><td class="num">{r["jsd_rest_bits"]} ({r["observed_rest_percentile"]})</td>'
                    f'<td class="small">{r["loo_cond_min"]}–{r["loo_cond_max"]}; {E(r["loo_cond_most_influential_work"][:32])} ({_f(r["loo_cond_delta_when_dropped"], 0):+.3f})</td><td class="num">{r["n_sole_works"]}{(" · " + r["sole_jsd_cond_bits"]) if r["sole_jsd_cond_bits"] else ""}</td></tr>')
        rowsB = sorted(aj, key=lambda r: (GENRES3.index(r['genre']) if r['genre'] in GENRES3 else 9, -_f(r['jsd_cond_bits'], 0)))
        tblB = ('<div class="tblx"><table class="sortable"><thead><tr><th>genre</th><th>author group</th><th class="num">works</th><th class="num">rest</th><th class="num">collab.</th><th class="num">coverage % A / rest</th><th class="num">JSD cond.</th><th class="num">random median (2.5–97.5 %)</th><th class="num">percentile</th><th class="num">JSD + rest bin (pct.)</th><th>leave-one-out range; most influential work (Δ when dropped)</th><th class="num">sole works · JSD</th></tr></thead><tbody>'
                + ''.join(brow(r) for r in rowsB) + '</tbody></table></div>')
        elig = defaultdict(list); nelig = defaultdict(list)
        for r in counts:
            (elig if r['eligible'] else nelig)[r['genre']].append(r)
        thr_txt = ', '.join(f'{g}: ' + ', '.join(f'{E(r["author"])} ({r["n_works_with_signature"]})' for r in sorted(elig[g], key=lambda r: -int(r['n_works_with_signature']))) for g in GENRES3 if elig[g])
        near = ', '.join(f'{E(r["author"])} ({r["genre"]}, {r["n_works_with_signature"]})' for g in GENRES3 for r in nelig[g] if int(r['n_works_with_signature']) >= 4 and int(r['n_usable_as_author']) > 0)
        figB = ('<div class="fig"><a href="data/author_by_genre/fig1_author_jsd_random_reference.png"><img class="heat" src="data/author_by_genre/fig1_author_jsd_random_reference.png" alt="Author JSD against the rest of the genre with the random same-size reference"></a><p class="fighint">Dot = observed divergence (all signatures); tick = median of 1,000 random groups of the same size; grey bar = their 2.5–97.5 % range. Click to enlarge.</p></div>'
                if (self.ab / 'fig1_author_jsd_random_reference.png').exists() else '')
        tabsH = '<div class="tabs" data-group="H">' + ''.join(f'<button data-tab="{g}"{" class=on" if i == 0 else ""}>{g.capitalize()}</button>' for i, g in enumerate(GENRES3) if (self.ab / f'fig2_topic_diff_heatmap_{g}.png').exists()) + '</div>'
        panelsH = ''.join(f'<div class="panel{" on" if i == 0 else ""}" data-group="H" data-tab="{g}"><div class="fig"><a href="data/author_by_genre/fig2_topic_diff_heatmap_{g}.png"><img class="heat" src="data/author_by_genre/fig2_topic_diff_heatmap_{g}.png" alt="{g}: mean-share differences, author group minus rest of genre"></a><p class="fighint">Author group mean minus the rest-of-genre mean, percentage points of all words; each author\'s three largest |differences|, at most 15 topics; one colour scale for the three genres.</p></div></div>'
                          for i, g in enumerate(GENRES3) if (self.ab / f'fig2_topic_diff_heatmap_{g}.png').exists())
        pend_html = ''
        if pend:
            pend_html = ('<details><summary>Records held out because the author\'s role could not be resolved (' + str(len(pend)) + ')</summary><div class="tblx"><table><thead><tr><th>genre</th><th>author</th><th>work</th><th>author field</th><th>DEEP authors</th><th>effect</th></tr></thead><tbody>'
                         + ''.join(f'<tr><td>{E(r["genre"])}</td><td>{E(r["author"])}</td><td>{self.work_link(r["work_id"], r["title"])}</td><td class="small">{E(r["author_field"])}</td><td class="small">{E(r["deep_authors_display"])}</td><td class="small">{E(r["effect"])}</td></tr>' for r in pend) + '</tbody></table></div></details>')
        secB = ('<h2 id="authors">B. Authors within genre</h2>'
                '<p>The same comparison for every author with at least five works carrying their signature in a genre (collaborations included; the rest of the genre must have at least ten works). JSD is the Jensen–Shannon divergence (log2, bits) between the author group\'s mean topic profile and the rest of the genre\'s; a larger value means the two profiles are further apart. It is a difference of topic distributions, not a ranking of originality or quality.</p>'
                '<div class="caveat">The grey range is what the same divergence looks like for 1,000 random groups of the same number of works drawn from the same genre — a reference for the group size, <b>not a confidence interval</b>, and it does not control for period or company. Each genre has its own rest group and its own sizes, so values are not comparable across genres and each panel is sorted on its own. Translators are never an author group; Seneca\'s group consists of English translations and is labelled as the original author of translated works. Different authors\' groups can share collaborative works, so the rows are not independent.</div>'
                + figB + tblB
                + f'<p class="note">Eligible authors and works with their signature — {thr_txt}. Just below the threshold (4 works): {near or "none"}. Roles are taken from the DEEP author list (translator / reviser / doubtful); the author field of the corpus is the signature rule and was not changed.</p>'
                + pend_html + '<h3>Where the profiles differ most</h3>' + tabsH + panelsH)
        # ---- section C: interactive ----------------------------------------------------------------------------------
        authors_by_genre = defaultdict(list)
        for r in rowsB: authors_by_genre[r['genre']].append(r['author'])
        D = {'genres': [g for g in GENRES3 if authors_by_genre[g]], 'authors': {g: authors_by_genre[g] for g in GENRES3}, 'kind': {f'{r["genre"]}|{r["author"]}': r['group_kind'] for r in aj},
             'n': {f'{r["genre"]}|{r["author"]}': [int(r['n_A']), int(r['n_B'])] for r in aj}, 'labels': {}, 'diff': {}, 'contrib': {}}
        for r in td:
            k = f'{r["genre"]}|{r["author"]}'; D['labels'][r['topic']] = r['label']
            D['diff'].setdefault(k, {})[r['topic']] = [_f(r['mean_share_A_pct']), _f(r['mean_share_B_pct']), _f(r['mean_diff_pp']), int(r['works_with_topic_A']), int(r['works_with_topic_B'])]
        for r in tc:
            k = f'{r["genre"]}|{r["author"]}|{r["topic"]}'
            D['contrib'].setdefault(k, {'A': [], 'B': []})[r['group']].append([r['work_id'], r['title'], r['author_field'], _f(r['share_in_work_pct']), _f(r['contribution_to_group_mean_pp']), _f(r['share_of_group_total'], 0), self.rep.get(r['work_id'], '')])
        D['tpage'] = {str(t): self.tpage(int(t)) for t in self.c['topics']}
        D['aj'] = {f'{r["genre"]}|{r["author"]}': [_f(r['jsd_cond_bits']), _f(r['random_cond_p2_5']), _f(r['random_cond_p97_5']), _f(r['random_cond_median']), _f(r['observed_cond_percentile']), _f(r['mean_included_share_A']), _f(r['mean_included_share_B'])] for r in aj}
        secO, O = self.overview(aj, tbg, td)
        secC = ('<h2 id="which-works">C. Which works account for the difference?</h2>'
                '<p>Pick a genre, an author and a topic. The card shows the mean share of the topic on each side, the difference in percentage points, how many works on each side contain the topic at all, and the three works that supply most of each side\'s mean. Contribution = the work\'s share divided by the number of works on its side (works equal-weighted), also given as the work\'s share of the side\'s total. A <b>difference in mean share</b> describes the two profiles; it is not the topic\'s share of the divergence, which is a different quantity and is not shown.</p>'
                '<div class="pick"><label>genre<select id="cg"></select></label><label>author<select id="ca"></select></label><label>topic<select id="ct"></select></label></div><div id="cout"></div>'
                '<p class="note">Work links open the representative edition; the "chunks" link opens the topic page at the row of that work\'s most typical chunk in the topic.</p>')
        # ---- details and downloads ---------------------------------------------------------------------------------
        loo_by = defaultdict(list)
        for r in loo: loo_by[(r['genre'], r['author'])].append(r)
        loo_html = ''.join(f'<details><summary>{E(g)} — {E(au)}: {len(rs)} works dropped in turn</summary><div class="tblx"><table class="small"><thead><tr><th>dropped work</th><th class="num">JSD cond. without it</th><th class="num">Δ</th><th class="num">JSD + rest bin</th><th class="num">Δ</th></tr></thead><tbody>'
                           + ''.join(f'<tr><td>{self.work_link(r["dropped_work_id"], r["dropped_title"])}</td><td class="num">{r["jsd_cond_bits"]}</td><td class="num">{r["delta_cond"]}</td><td class="num">{r["jsd_rest_bits"]}</td><td class="num">{r["delta_rest"]}</td></tr>' for r in rs) + '</tbody></table></div></details>'
                           for (g, au), rs in sorted(loo_by.items(), key=lambda kv: (GENRES3.index(kv[0][0]) if kv[0][0] in GENRES3 else 9, kv[0][1])))
        sole_html = ('<div class="tblx"><table><thead><tr><th>genre</th><th>author</th><th class="num">sole works</th><th class="num">rest</th><th class="num">coverage sole / rest</th><th class="num">JSD cond. sole</th><th class="num">all signatures</th><th class="num">JSD + rest bin sole</th><th class="num">all signatures</th></tr></thead><tbody>'
                     + ''.join(f'<tr><td>{E(r["genre"])}</td><td>{E(r["author"])}</td><td class="num">{r["n_sole_works"]}</td><td class="num">{r["n_B"]}</td><td class="num">{100 * _f(r["mean_included_share_sole"]):.0f} / {100 * _f(r["mean_included_share_B"]):.0f}</td><td class="num">{r["jsd_cond_bits"]}</td><td class="num">{r["jsd_cond_bits_all_signatures"]}</td><td class="num">{r["jsd_rest_bits"]}</td><td class="num">{r["jsd_rest_bits_all_signatures"]}</td></tr>' for r in sole) + '</tbody></table></div>') if sole else ''
        xrows = ''.join(f'<tr><td>{E(x["genre"])}</td><td class="num">{x["n18"]}</td><td class="num">{x["n22"]}</td><td class="num">{x["j18"]}</td><td class="num">{x["j22"]}</td><td class="num">{x["null18"]}</td><td class="num">{x["null22"]}</td><td>{"same works, same divergence" if x["ok"] else "DIFFER — check"}</td></tr>' for x in xcheck)
        secD = ('<h2 id="details">Details and downloads</h2>'
                '<h3>Cross-check between sections A and B</h3><p class="note">Section A comes from the Shakespeare comparison script, section B from the author comparison script. Shakespeare\'s groups are the same works in both; the table shows the two scripts\' divergences and their random references side by side.</p>'
                + '<div class="tblx"><table class="small"><thead><tr><th>genre</th><th class="num">A: works vs rest</th><th class="num">B: works vs rest</th><th class="num">A: JSD cond.</th><th class="num">B: JSD cond.</th><th class="num">A: permutation median</th><th class="num">B: random median</th><th>check</th></tr></thead><tbody>' + xrows + '</tbody></table></div>'
                + '<h3>Leave-one-out</h3><p class="note">Each work of an author group dropped in turn, the rest of the genre unchanged; Δ = divergence without the work minus the observed value, so a positive Δ means the work was pulling the group towards the rest of the genre and a negative Δ that it was pushing the divergence up.</p>' + loo_html
                + '<h3>Sole-signature variant</h3><p class="note">Author group restricted to works whose author field carries the author alone (only where five or more exist); the rest of the genre still excludes every work with the author\'s signature. Smaller groups: not directly comparable with the all-signature value or with the random reference.</p>' + sole_html
                + '<h3>Downloads</h3><p class="note">Author comparison (22_author_by_genre.py):</p>' + self.dl('author_by_genre', ['author_jsd.csv', 'random_reference.csv', 'topic_differences.csv', 'topic_contributions.csv', 'leave_one_out.csv', 'sole_signature.csv', 'comparison_works.csv', 'author_counts.csv', 'role_pending.csv', 'author_split_check.csv', 'methods.md', 'checks.json', 'provenance.json', 'fig0_author_jsd_overview.png', 'fig0_author_jsd_overview.svg', 'fig0_author_jsd_overview_data.csv', 'fig1_author_jsd_random_reference.svg', 'fig2_topic_diff_heatmap_comedy.svg', 'fig2_topic_diff_heatmap_tragedy.svg', 'fig2_topic_diff_heatmap_history.svg'])
                + '<p class="note">Shakespeare comparison (18_shakespeare.py):</p>' + self.dl('shakespeare', ['topic_by_genre.csv', 'jsd.csv', 'shared_inventory.csv', 'shakespeare_works.csv', 'genre_pairs_jsd.csv', 'genre_shared_inventory.csv', 'shakespeare_summary.md'])
                + (('<p class="note">Common-window check (24_window_check.py; the ' + E(O['win']['label']) + ' view of the first overview chart): both sides restricted to works whose estimated first-performance / composition year falls in the window, the measure unchanged; works whose date limits cross a window edge are also placed by their lower and upper limits.</p>' + self.dl('window_check', ['window_topic_means.csv', 'window_counts.csv', 'window_works.csv', 'window_top10.csv', 'window_jsd.csv', 'excluded_by_decade.csv', 'summary.md', 'methods.md', 'checks.json', 'provenance.json'])) if 'win' in O else '')
                + '<details><summary>Exploratory play-level comparisons (supplementary; downloads only)</summary><p class="note">Each play\'s topic profile measured against the mean profile of each genre group (Jensen–Shannon divergence on the included topics, the play left out of its own genre\'s mean). This measures how far a play\'s topic distribution sits from the genre averages; it does not reassign any play to another genre, and it is not shown as a result on this page.</p>' + self.dl('shakespeare', ['play_distances.csv', 'shakespeare_play_distances.csv', 'shakespeare_play_pull.csv', 'play_distances_summary.md', 'othello_panel.png']) + '</details>')
        JS = ('<script>const D=' + json.dumps(D, ensure_ascii=False) + ';const O=' + json.dumps(O, ensure_ascii=False) + ';'
              r"""
const $=id=>document.getElementById(id);const g=$('cg'),a=$('ca'),t=$('ct'),o=$('cout');
const fill=(s,vals,labels)=>{s.innerHTML='';vals.forEach((v,i)=>{const op=document.createElement('option');op.value=v;op.textContent=labels?labels[i]:v;s.appendChild(op);});};
fill(g,D.genres,D.genres.map(x=>x[0].toUpperCase()+x.slice(1)));
const fillA=()=>{const au=D.authors[g.value]||[];fill(a,au,au.map(x=>x+(D.kind[g.value+'|'+x]==='original author of translated works'?' (translations; original author)':'')));};
const fillT=()=>{const k=g.value+'|'+a.value;const dd=D.diff[k]||{};const ts=Object.keys(dd).sort((x,y)=>Math.abs(dd[y][2])-Math.abs(dd[x][2]));fill(t,ts,ts.map(x=>'T'+x+' '+D.labels[x]+' ('+(dd[x][2]>=0?'+':'')+dd[x][2].toFixed(1)+' pp)'));};
const esc=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const side=(rows,n,lab)=>{if(!rows||!rows.length)return '<p class="note">no work on this side contains the topic</p>';return '<div class="tblx"><table class="small"><thead><tr><th>work</th><th>author field</th><th class="num">share in work %</th><th class="num">contribution to side mean (pp)</th><th class="num">share of side total</th><th></th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+(r[6]?'<a href="plays/'+r[6]+'.html">'+esc(r[1])+'</a>':esc(r[1]))+' <span class="sub">work '+r[0]+'</span></td><td class="small">'+esc(r[2])+'</td><td class="num">'+r[3].toFixed(2)+'</td><td class="num">'+r[4].toFixed(2)+'</td><td class="num">'+Math.round(100*r[5])+' %</td><td><a href="'+D.tpage[t.value]+'#w'+r[0]+'">chunks</a></td></tr>').join('')+'</tbody></table>';};
const ord=p=>{const r=Math.round(p);const s=(r%100>=11&&r%100<=13)?'th':({1:'st',2:'nd',3:'rd'}[r%10]||'th');return r+s;};
const show=()=>{const k=g.value+'|'+a.value;const v=(D.diff[k]||{})[t.value];if(!v){o.innerHTML='';return;}const n=D.n[k];const c=D.contrib[k+'|'+t.value]||{A:[],B:[]};const s=D.aj[k];
o.innerHTML=(s?'<p class="note"><b>'+esc(a.value)+'</b> in '+esc(g.value)+': divergence '+s[0].toFixed(3)+' bits on the selected topics ('+n[0]+' works against '+n[1]+' others); included-topic coverage '+Math.round(100*s[5])+' % / '+Math.round(100*s[6])+' %; '+ord(s[4])+' percentile of 1,000 random groups of the same size (their 2.5–97.5 % range: '+s[1].toFixed(3)+'–'+s[2].toFixed(3)+'). Topics in the list are sorted by the absolute difference of mean shares.</p>':'')
+'<div class="facts"><div class="f"><b>'+v[0].toFixed(2)+' %</b><i>mean share, '+esc(a.value)+' ('+n[0]+' works)</i></div><div class="f"><b>'+v[1].toFixed(2)+' %</b><i>mean share, rest of '+esc(g.value)+' ('+n[1]+' works)</i></div><div class="f"><b>'+(v[2]>=0?'+':'')+v[2].toFixed(2)+' pp</b><i>difference of means</i></div><div class="f"><b>'+v[3]+' / '+n[0]+'</b><i>works with the topic, author side</i></div><div class="f"><b>'+v[4]+' / '+n[1]+'</b><i>works with the topic, rest</i></div></div>'
+'<div class="two"><div><h3>'+esc(a.value)+' — works supplying most of the mean</h3>'+side(c.A,n[0])+'</div><div><h3>Rest of '+esc(g.value)+' — works supplying most of the mean</h3>'+side(c.B,n[1])+'</div></div>';};
g.addEventListener('change',()=>{fillA();fillT();show();});a.addEventListener('change',()=>{fillT();show();});t.addEventListener('change',show);
fillA();fillT();
const h=location.hash.match(/^#t(\d+)$/);if(h){let best=null;for(const gg of D.genres){for(const au of D.authors[gg]){const v=(D.diff[gg+'|'+au]||{})[h[1]];if(v&&(!best||Math.abs(v[2])>best[2]))best=[gg,au,Math.abs(v[2])];}}if(best){g.value=best[0];fillA();a.value=best[1];fillT();t.value=h[1];}}
show();
if(h&&D.diff[g.value+'|'+a.value]){const og=$('og');if(og){og.value=g.value;og.dispatchEvent(new Event('change'));}setTimeout(()=>$('which-works').scrollIntoView(),50);}
document.querySelectorAll('.tabs').forEach(tb=>tb.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{const grp=tb.dataset.group;tb.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));document.querySelectorAll('.panel[data-group="'+grp+'"]').forEach(p=>p.classList.toggle('on',p.dataset.tab===b.dataset.tab));})));
/* ---- overview charts (data in O) ---- */
const og=$('og');if(og){
const cap=x=>x[0].toUpperCase()+x.slice(1);const att=s=>esc(s).replace(/"/g,'&quot;');
const fmt=v=>v===0?'0%':(v<0.05?'<0.1%':v.toFixed(1)+'%');
const nice=mx=>{for(const st of [0.5,1,2,5,10,20]){if(mx/st<=7)return [Math.ceil(mx/st-1e-9)*st,st];}return [Math.ceil(mx/50)*50,50];};
const axis=(mx,st,dec)=>{let h='<div class="tk"><div class="axis">';for(let v=0;v<=mx+1e-9;v+=st){h+='<span style="left:'+(100*v/mx)+'%">'+v.toFixed(dec)+'</span>';}return h+'</div></div>';};
const jump=(gg,au,tt)=>{if(g.value!==gg){g.value=gg;fillA();}a.value=au;fillT();if(tt!==undefined&&tt!==''&&[...t.options].some(x=>x.value==tt))t.value=String(tt);show();$('which-works').scrollIntoView({behavior:'smooth'});};
const pl=(k,n)=>k+' of '+n+' play'+(n===1?'':'s');
let per='full';const hasW=!!O.win;const perLabel=()=>per==='window'?O.win.label:'Full corpus';
const pdata=gg=>{const T=O.topics[gg];return (per==='window'&&T&&T.win)?T.win:T;};
const worksTxt=(top,n)=>top&&top.length?top.map(w=>'<i>'+esc(w[1])+'</i>'+(w[2]&&!/Shakespeare/.test(w[2])?' ('+esc(w[2].split(',')[0])+')':'')+' — '+w[3].toFixed(1)+'% of its words, '+Math.round(100*w[5])+'% of this side’s total').join('; '):'';
const renderTopics=gg=>{const T=O.topics[gg];if(!T){$('ov1').innerHTML='';return;}
const both=T.rows.concat(T.win?T.win.rows:[]);const mx=Math.max(...both.flatMap(r=>[r[2],r[3]]));const [ax,st]=nice(mx);$('ov1g').textContent=cap(gg);
let h='';T.rows.forEach(r=>{const [tt,lab]=r;const bar=cls=>'<div class="pbar"><div class="tk"><i class="'+cls+'" style="width:0%"></i><span class="v" style="left:0%"></span></div><span class="m"></span></div>';
h+='<div class="pbrow" role="button" tabindex="0" aria-expanded="false" data-t="'+tt+'"><div class="pbl"><a href="'+O.tpage[tt]+'">'+esc(lab)+'</a><span class="sub">T'+tt+'</span></div><div class="pbb">'+bar('s')+bar('o')+'<div class="pbn"></div><div class="pbd" hidden></div></div></div>';});
h+='<div class="pbrow axisrow"><div class="pbl"></div><div class="pbb"><div class="pbar">'+axis(ax,st,st<1?1:0)+'<span class="m"></span></div></div></div>';$('ov1').innerHTML=h;$('ov1').dataset.ax=ax;
$('ov1').querySelectorAll('.pbrow[role=button]').forEach(row=>{const tog=()=>{const d=row.querySelector('.pbd');const open=d.hasAttribute('hidden');d.toggleAttribute('hidden',!open);row.setAttribute('aria-expanded',open?'true':'false');};
row.addEventListener('click',e=>{const j=e.target.closest('[data-jump]');if(j){e.preventDefault();jump(gg,O.shakes,j.dataset.jump);return;}if(e.target.closest('a'))return;tog();});
row.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&!e.target.closest('a')){e.preventDefault();tog();}});});
updateTopics(gg);};
const updateTopics=gg=>{const T=O.topics[gg];if(!T)return;const P=pdata(gg);const W=per==='window'&&P!==T;const ax=+$('ov1').dataset.ax;const nn=O.nouns[gg];
$('ov1l').innerHTML='<span><i class="s"></i>Shakespeare’s plays (n = '+P.nS+')</span><span><i class="o"></i>Other plays in the genre (n = '+P.nO+(W?', of '+T.nO:'')+')</span>';
const pt=$('ov1pt');if(pt){pt.textContent=perLabel();pt.hidden=!hasW;}
const pn=$('ov1per');if(pn){pn.innerHTML=W?'<b>The same Shakespeare plays remain in both views. Switching the period changes the comparison group.</b> Here the other plays are the '+P.nO+' of the '+T.nO+' other '+nn[1]+' whose estimated first-performance / composition year falls in '+O.win.label+' (inclusive; British Drama date first, Annals fallback). Dates inside the window are not matched between the two groups.':
'<b>Full corpus:</b> all '+T.nO+' other '+nn[1]+', whatever their date. The '+O.win.label+' view keeps the same Shakespeare plays and restricts the other plays to those with an estimated first-performance / composition year in that window.';}
$('ov1sum').innerHTML='On average, these ten topics account for <b>'+P.sumS.toFixed(1)+'%</b> of the words in a Shakespeare '+nn[0]+' and <b>'+P.sumO.toFixed(1)+'%</b> of the words in one of the other '+nn[1]+(W?' of '+O.win.label:'')+'.';
const rows=$('ov1').querySelectorAll('.pbrow[role=button]');
P.rows.forEach((r,i)=>{const row=rows[i];if(!row)return;const [tt,lab,vS,vO,wS,wO,tS,sS,tO,aO,sO,cS,cO]=r;const bars=row.querySelectorAll('.pbar');
[[bars[0],vS,wS,P.nS],[bars[1],vO,wO,P.nO]].forEach(([b,v,w,n])=>{b.querySelector('i').style.width=(100*v/ax)+'%';const vv=b.querySelector('.v');vv.style.left=(100*v/ax)+'%';vv.textContent=fmt(v);b.querySelector('.m').textContent=w+'/'+n+' plays';});
let notes='';if(sS>0.5&&tS)notes+='<div class="pbnote">'+Math.round(100*sS)+'% of Shakespeare’s share comes from <i>'+esc(tS)+'</i></div>';if(sO>0.5&&tO)notes+='<div class="pbnote">'+Math.round(100*sO)+'% of the other plays’ share comes from <i>'+esc(tO)+'</i>'+(aO?' ('+esc(aO.split(',')[0])+')':'')+'</div>';
row.querySelector('.pbn').innerHTML=notes;
const zero=v=>v===0?' No chunk of any play on this side was assigned to this topic; this does not mean the plays lack the subject.':'';
const wS_=worksTxt(cS,P.nS),wO_=worksTxt(cO,P.nO);
row.querySelector('.pbd').innerHTML='<b>T'+tt+' '+esc(lab)+'</b>'+(hasW?' <span class="sub">'+esc(perLabel())+'</span>':'')+'<br>Shakespeare’s plays'+(W?' (all '+P.nS+' fall in '+O.win.label+')':'')+': '+vS.toFixed(2)+'% of a play’s words on average; '+pl(wS,P.nS)+' with at least one chunk in the topic'+(tS?'; '+esc(tS)+' supplies '+Math.round(100*sS)+'% of this side’s total':'')+'.'+zero(vS)+(wS_?'<br><span class="sub" style="margin:0">Works supplying most of this side’s mean (share ÷ '+P.nS+' plays):</span> '+wS_+'.':'')
+'<br>Other plays in the genre'+(W?' ('+P.nO+' of '+T.nO+', '+O.win.label+')':'')+': '+vO.toFixed(2)+'% on average; '+pl(wO,P.nO)+(tO?'; '+esc(tO)+(aO?' ('+esc(aO)+')':'')+' supplies '+Math.round(100*sO)+'%':'')+'.'+zero(vO)+(wO_?'<br><span class="sub" style="margin:0">Works supplying most of this side’s mean (share ÷ '+P.nO+' plays):</span> '+wO_+'.':'')
+'<br><a href="'+O.tpage[tt]+'">Explore this topic</a> · <a href="#which-works" data-jump="'+tt+'">Works behind this topic (section C'+(hasW?' — full corpus':'')+')</a>';
row.title=lab+': Shakespeare '+vS.toFixed(2)+'%, others '+vO.toFixed(2)+'%'+(W?' ('+O.win.label+')':'');});
$('ov1t').innerHTML='<table class="small"><caption class="sub" style="text-align:left;margin:0 0 4px">'+esc(perLabel())+(W?': other plays restricted to '+O.win.label:'')+'</caption><thead><tr><th>topic</th><th class="num">Shakespeare mean %</th><th class="num">plays with topic</th><th class="num">others mean %</th><th class="num">plays with topic</th><th>top Shakespeare play (share of side)</th><th>top other play (share of side)</th></tr></thead><tbody>'+P.rows.map(r=>'<tr><td><a href="'+O.tpage[r[0]]+'">T'+r[0]+' '+esc(r[1])+'</a></td><td class="num">'+r[2].toFixed(2)+'</td><td class="num">'+r[4]+' / '+P.nS+'</td><td class="num">'+r[3].toFixed(2)+'</td><td class="num">'+r[5]+' / '+P.nO+'</td><td class="small">'+(r[6]?esc(r[6])+' ('+Math.round(100*r[7])+' %)':'—')+'</td><td class="small">'+(r[8]?esc(r[8])+(r[9]?' — '+esc(r[9]):'')+' ('+Math.round(100*r[10])+' %)':'—')+'</td></tr>').join('')+'</tbody></table>';
const dl=$('ov1dl');if(dl&&O.dl){const L=O.dl[W?'window':'full']||[];dl.innerHTML=L.length?'Data for this view: '+L.map(f=>'<a href="'+f[0]+'" download>'+esc(f[1])+'</a>').join(' '):'';}};
const ptog=$('ov1p');if(ptog){ptog.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.p===per)return;per=b.dataset.p;ptog.querySelectorAll('button').forEach(x=>{const on=x===b;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on?'true':'false');});updateTopics(og.value);}));}
const renderAuthors=gg=>{const A=O.authors[gg]||[];const mx=O.jmax;$('ov2g').textContent=cap(gg);
$('ov2l').innerHTML='<span><i class="dot s"></i>Shakespeare</span><span><i class="dot g"></i>other playwrights</span>'+(A.some(r=>r[2])?'<span><i class="hollow"></i>original author of plays in English translation</span>':'')+'<span><i class="band"></i>range of 1,000 random groups of the same size (2.5–97.5 %)</span>';
let h='',sep=false;A.forEach(r=>{const [full,sur,apart,n,nB,j,lo,hi,med,pct,cA,cB,best]=r;if(apart&&!sep){sep=true;h+='<div class="jsep">Shown separately: original author of plays in English translation (not one of the playwrights)</div>';}
const name=apart?sur+' (English translations, '+n+' plays)':sur+' ('+n+' plays)';const isS=full===O.shakes;
h+='<div class="jbrow'+(isS?' shakes':'')+(apart?' sen':'')+'" role="button" tabindex="0" data-a="'+att(full)+'" data-t="'+best+'" title="'+att(full)+': JSD '+j.toFixed(4)+' bits; '+n+' plays vs '+nB+'; coverage '+Math.round(100*cA)+' % / '+Math.round(100*cB)+' %; '+ord(pct)+' percentile of the random groups ('+lo.toFixed(3)+'–'+hi.toFixed(3)+')"><div class="jbl">'+esc(name)+'</div><div class="jbb"><div class="tk"><b class="band" style="left:'+(100*lo/mx)+'%;width:'+(100*(hi-lo)/mx)+'%"></b><i class="dot" style="left:'+(100*j/mx)+'%"></i><span class="v" style="left:'+(100*j/mx)+'%">'+j.toFixed(2)+'</span></div></div></div>';});
h+='<div class="jbrow axisrow"><div class="jbl"></div><div class="jbb">'+axis(mx,0.1,1)+'</div></div>';$('ov2').innerHTML=h;
const k=A.filter(r=>!r[2]).length;const pos=r=>r[5]>r[7]?'above':(r[5]<r[6]?'below':'inside');const nm=r=>r[2]?'the '+r[1]+' translations':r[1]+'’s '+O.nouns[gg][1];const jn=x=>x.length===1?x[0]:x.slice(0,-1).join(', ')+' and '+x[x.length-1];
const shk=A.find(r=>r[0]===O.shakes);const ab=A.filter(r=>r[0]!==O.shakes&&pos(r)==='above').map(nm);const be=A.filter(r=>r[0]!==O.shakes&&pos(r)==='below').map(nm);
let rd=shk?'<b>Shakespeare’s observed difference lies '+pos(shk)+' the reference range for random groups of the same size.</b>':'';
const cap1=x=>x.charAt(0).toUpperCase()+x.slice(1);if(ab.length)rd+=' '+cap1(jn(ab))+' lie beyond the upper end of their ranges'+(be.length?', while '+jn(be)+' lie below the lower end.':'.');else if(be.length)rd+=' '+cap1(jn(be))+' lie below the lower end of their ranges.';
$('ov2read').innerHTML=rd;
$('ov2n').textContent=(k<=2?'Only '+(k===1?'one playwright reaches':(k===2?'two':k)+' playwrights reach')+' the threshold of five '+O.nouns[gg][1]+'. ':'')+'Dot = observed difference, further right = larger; grey line = the middle 95 % of random groups with the same number of plays, a reference for the group size, not a confidence interval. Sorted by the observed value.';
$('ov2t').innerHTML='<table class="small"><thead><tr><th>author group</th><th class="num">plays</th><th class="num">rest of genre</th><th class="num">JSD, selected topics (bits)</th><th class="num">random groups: median (2.5–97.5 %)</th><th class="num">percentile</th><th class="num">coverage % group / rest</th></tr></thead><tbody>'+A.map(r=>'<tr><td>'+esc(r[0])+(r[2]?' <span class="sub">English translations</span>':'')+'</td><td class="num">'+r[3]+'</td><td class="num">'+r[4]+'</td><td class="num">'+r[5].toFixed(4)+'</td><td class="num">'+r[8].toFixed(3)+' ('+r[6].toFixed(3)+'–'+r[7].toFixed(3)+')</td><td class="num">'+r[9].toFixed(1)+'</td><td class="num">'+Math.round(100*r[10])+' / '+Math.round(100*r[11])+'</td></tr>').join('')+'</tbody></table>';
$('ov2').querySelectorAll('.jbrow[role=button]').forEach(row=>{const go=()=>jump(gg,row.dataset.a,row.dataset.t);row.addEventListener('click',go);row.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});});};
const renderOv=()=>{const gg=og.value;renderTopics(gg);renderAuthors(gg);if(g.value!==gg&&D.authors[gg]&&D.authors[gg].length){g.value=gg;fillA();fillT();show();}
['A','H'].forEach(grp=>{const b=document.querySelector('.tabs[data-group="'+grp+'"] button[data-tab="'+gg+'"]');if(b&&!b.classList.contains('on'))b.click();});};
og.addEventListener('change',renderOv);renderOv();}
</script>""")
        page = (c['head']('Shakespeare and his contemporaries') + c['mast']('', 'shakespeare.html') + c['crumbs']('<a href="index.html">Home</a>', 'Shakespeare and his contemporaries')
                + '<h1>Shakespeare and His Contemporaries</h1>'
                + '<p class="lede">What is compared here is the distribution of a fixed set of topics — the share of a work\'s words that falls in each of the included clusters — for one author\'s works against the rest of the same genre. It is not a measure of literary value, of an author\'s whole style, or of originality; it is a description of where the topic profiles sit relative to each other, with the works behind every difference kept in view.</p>'
                + f'<p class="stamp">{self.stamp("shakespeare", "author_by_genre")}</p>'
                + '<p class="note">Sections: <a href="#overview">Overview</a> · <a href="#within-genre">A. Shakespeare within genre</a> · <a href="#authors">B. Authors within genre</a> · <a href="#which-works">C. Which works account for the difference?</a> · <a href="#details">Details and downloads</a></p>'
                + secO + secA + secB + secC + secD + JS + c['foot']())
        (self.out / 'shakespeare.html').write_text(page, encoding='utf-8')
        return page

    # ---------------------------------------------------------------- Chronology page ------------------------------
    def build_chronology(self):
        E = self.E; c = self.c
        cov = _csv(self.ch / 'coverage.csv'); gc = _csv(self.ch / 'genre_composition.csv'); ic = _csv(self.ch / 'included_coverage.csv')
        ts = _csv(self.ch / 'topic_stats.csv'); tw = _csv(self.ch / 'topic_top_works.csv'); dates = _csv(self.ch / 'dates_by_work.csv')
        sc = _csv(self.ch / 'sensitivity_counts.csv'); bw = _csv(self.ch / 'boundary_works.csv'); sd = _csv(self.ch / 'sources_differ.csv'); au = _csv(self.ch / 'author_composition.csv')
        wts = {r['work_id']: r for r in _csv(self.agg / 'work_topic_share.csv')}
        prov = json.load(open(self.ch / 'provenance.json')) if (self.ch / 'provenance.json').exists() else {}
        call = next((r for r in cov if r['scope'] == 'all'), None)
        not_usable = [d for d in dates if not d['in_period_analysis']]
        decades = [k[2:] for k in call.keys() if k.startswith('n_1')] if call else []
        # ---- A ------------------------------------------------------------------------------------------------------
        facts = ''
        if call:
            facts = (f'<div class="facts"><div class="f"><b>{call["n_works"]}</b><i>works in the corpus</i></div><div class="f"><b>{call["n_in_period_analysis"]}</b><i>with a usable date (used on this page)</i></div><div class="f"><b>{call["n_not_usable"]}</b><i>set aside</i></div>'
                     f'<div class="f"><b>{call["n_british_drama"]} / {call["n_annals_fallback"]}</b><i>date from British Drama / Annals fallback</i></div><div class="f"><b>{call["n_first_performance"]} / {call["n_composition"]} / {call["n_kind_unclear"]}</b><i>estimated first performance / composition / kind unclear</i></div>'
                     f'<div class="f"><b>{call["n_crossing_decade_boundary"]}</b><i>limits cross a decade boundary</i></div><div class="f"><b>{call["n_sources_differ"]} ({call["n_sources_differ_decade"]})</b><i>two sources differ (in a different decade)</i></div></div>')
        nu_txt = '; '.join(f'{self.work_link(d["work_id"], d["title"])} — {E(d["reason"])}' for d in not_usable) or 'none'
        gcols = [k[2:] for k in gc[0].keys() if k.startswith('n_') and k != 'n_works'] if gc else []
        gtable = ('<div class="tblx"><table class="small"><thead><tr><th>decade</th><th class="num">works</th>' + ''.join(f'<th class="num">{E(g)}</th>' for g in gcols) + '<th class="num">first perf.</th><th class="num">composition</th><th class="num">unclear</th></tr></thead><tbody>'
                  + ''.join(f'<tr><td>{E(r["decade"])}</td><td class="num">{r["n_works"]}</td>' + ''.join(f'<td class="num">{r["n_" + g] if r["n_" + g] != "0" else ""}</td>' for g in gcols) + f'<td class="num">{r["n_first_performance"]}</td><td class="num">{r["n_composition"]}</td><td class="num">{r["n_kind_unclear"]}</td></tr>' for r in gc) + '</tbody></table></div>')
        secA = ('<h2 id="composition">A. Corpus composition</h2>' + facts
                + '<div class="fig"><a href="data/chronology/fig1_corpus_composition.png"><img class="heat" src="data/chronology/fig1_corpus_composition.png" alt="Composition of this corpus by decade of the adopted date, stacked by genre"></a><p class="fighint">Works of this corpus by decade of the adopted date, stacked by genre group; totals above the bars. Click to enlarge.</p></div>'
                + f'<p class="note">Works set aside: {nu_txt}. The rest of the site keeps all {call["n_works"] if call else ""} works; only this page works with the {call["n_in_period_analysis"] if call else ""}. Genre groups are those of the Genre page (British Drama label, Annals fallback, or other/multi).</p>'
                + '<details><summary>Works per decade and genre composition (table)</summary>' + gtable + '</details>')
        # ---- B -----------------------------------------------------------------------------------------------------
        secB = ('<h2 id="sample">B. Sample size and coverage</h2><p>Before any topic is read by decade: how many works each genre has in each decade, and how much of those works\' text the included topics cover. Cells with fewer than five works are not shown in the heatmaps; five to nine are shown but marked sparse; ten or more are shown — a display rule, not a reliability claim. No decades were merged.</p>'
                + '<div class="fig"><a href="data/chronology/fig2_sample_and_coverage.png"><img class="heat" src="data/chronology/fig2_sample_and_coverage.png" alt="Works per decade and mean included coverage, three genres"></a><p class="fighint">Top row: works per decade (dashed lines at 5 and 10). Bottom row: equal-weighted mean of the share of a work\'s words in the included topics. Click to enlarge.</p></div>')
        # ---- C -----------------------------------------------------------------------------------------------------
        tabsC = '<div class="tabs" data-group="C">' + ''.join(f'<button data-tab="{g}"{" class=on" if i == 0 else ""}>{g.capitalize()}</button>' for i, g in enumerate(GENRES3)) + '</div>'
        panelsC = ''
        for i, g in enumerate(GENRES3):
            cells = sorted({(r['decade'], int(r['n_works']), r['display_status']) for r in ts if r['genre'] == g})
            big = [d for d, n, s in cells if n >= 10]
            rule = (f'the 15 topics with the largest range (max − min) of decade means across the {len(big)} decades with ten or more works' if len(big) >= 2 else 'the 15 topics with the largest overall mean share in the genre (fewer than two decades have ten or more works, so no "largest change" selection was made)')
            hist_note = ('<div class="caveat">History has only one decade with ten or more works; the conditions for a comparison between decades are not met, and no statement about change over time is made for history here.</div>' if g == 'history' and len(big) < 2 else '')
            cellline = ' · '.join(f'{d}: {n}' + ('' if n >= 10 else (' (sparse)' if n >= 5 else ' (not shown)')) for d, n, s in cells)
            full = ''
            dec_g = [d for d, n, s in cells if n >= 5]
            if dec_g:
                by = defaultdict(dict)
                for r in ts:
                    if r['genre'] == g and r['decade'] in dec_g: by[int(r['topic'])][r['decade']] = r
                full = ('<details><summary>All included topics by decade (mean share %, cells with ≥ 5 works)</summary><div class="tblx"><table class="sortable small"><thead><tr><th>topic</th>' + ''.join(f'<th class="num">{E(d)}<br><span class="sub">n = {next(n for dd, n, s in cells if dd == d)}</span></th>' for d in dec_g) + '</tr></thead><tbody>'
                        + ''.join(f'<tr><td>{self.topic_link(t)}</td>' + ''.join(f'<td class="num">{_pct(by[t][d]["mean_share_pct"]) if d in by[t] else ""}</td>' for d in dec_g) + '</tr>' for t in sorted(by, key=lambda t: -max(_f(x["mean_share_pct"], 0) for x in by[t].values()))) + '</tbody></table></div></details>')
            panelsC += (f'<div class="panel{" on" if i == 0 else ""}" data-group="C" data-tab="{g}">{hist_note}<p class="note">Works per decade — {cellline}.</p>'
                        f'<div class="fig"><a href="data/chronology/fig3_topic_decade_heatmap_{g}.png"><img class="heat" src="data/chronology/fig3_topic_decade_heatmap_{g}.png" alt="{g}: mean topic share by decade"></a><p class="fighint">Mean share of a work\'s words (%), raw values, one colour scale for the three genres; hatched = fewer than five works. Topics shown: {rule}. Click to enlarge.</p></div>' + full + '</div>')
        secC = ('<h2 id="by-decade">C. Topics by decade</h2><p>Within each genre, the mean share of each included topic in the works of each decade. The heatmap shows at most 15 topics; the full table below it and the download hold all included topics. Nothing here is a test: a higher value in one decade is a description of the works that fall in that decade, and the cells can be traced back to their works in section D.</p>'
                + tabsC + panelsC)
        # ---- D: interactive ---------------------------------------------------------------------------------------
        D = {'genres': list(GENRES3), 'labels': {}, 'cells': {}, 'stats': {}, 'top': {}, 'works': {}, 'tpage': {str(t): self.tpage(int(t)) for t in c['topics']}, 'topics': [str(t) for t in c['topics']]}
        for r in ts:
            D['labels'][r['topic']] = r['label']
            D['cells'].setdefault(r['genre'], {})[r['decade']] = [int(r['n_works']), r['display_status']]
            D['stats'][f'{r["genre"]}|{r["decade"]}|{r["topic"]}'] = [_f(r['mean_share_pct']), _f(r['median_share_pct']), int(r['works_with_topic'])]
        for r in tw:
            D['top'].setdefault(f'{r["genre"]}|{r["decade"]}|{r["topic"]}', []).append([r['work_id'], r['title'], r['author_field'], _f(r['share_in_work_pct']), _f(r['contribution_to_group_mean_pp']), _f(r['share_of_group_total'], 0)])
        for d in dates:
            if not d['in_period_analysis'] or d['genre_main'] not in GENRES3: continue
            w = wts.get(d['work_id'], {})
            shares = {str(t): round(100 * _f(w.get(f't{t}'), 0), 2) for t in c['topics']} if w else {}
            D['works'].setdefault(f'{d["genre_main"]}|{d["decade_main"]}', []).append([d['work_id'], d['title'], d['author_field'], d['adopted_year'], d['source_used'], d['lower_limit'], d['upper_limit'], d['date_kind'], d['flags'], d['date_brit_raw'], d['date_annals_raw'], self.rep.get(d['work_id'], ''), shares])
        secD = ('<h2 id="trace">D. Trace a cell back to works</h2><p>Pick a genre, a decade and a topic. The card gives the mean and median share of the topic across the works of that cell, how many of them contain the topic, and the three works supplying most of the mean (contribution = share ÷ number of works in the cell). The table below lists every work of the cell with its adopted year, the source of that year, the bracketed limits, the date kind, and its topic share within the play (percentage of the representative text\'s words assigned to the selected topic, unassigned text included in the denominator). Works with the same title are distinguished by work id and author.</p>'
                '<div class="pick"><label>genre<select id="dg"></select></label><label>decade<select id="dd"></select></label><label>topic<select id="dt"></select></label></div><div id="dout"></div>')
        # ---- dates and details -------------------------------------------------------------------------------------
        srows = ''.join(f'<tr><td>{E(r["scope"])}</td><td>{E(r["grouping"])}</td><td class="num">{r["n_moved"]}</td>' + ''.join(f'<td class="num">{r["n_" + d] if r["n_" + d] != "0" else ""}</td>' for d in decades) + '</tr>' for r in sc)
        stable = ('<div class="tblx"><table class="small"><thead><tr><th>scope</th><th>grouping</th><th class="num">moved</th>' + ''.join(f'<th class="num">{E(d)}</th>' for d in decades) + '</tr></thead><tbody>' + srows + '</tbody></table></div>') if sc else ''
        secE = ('<h2 id="dates">How the dates were chosen</h2>'
                '<p>The date of a work is the British Drama first-performance date (Wiggins &amp; Richardson, via DEEP); the Annals of English Drama date is used only when British Drama has no entry, and the reason is recorded for every work. The leading year of the source string is the adopted year; the bracketed limits of the same source are the lower and upper limit. Notes such as "licensed" or "revised" are accompanying events and do not disqualify the year; later revision dates never widen the limits. Publication years are never used as substitutes and the two sources are never averaged. '
                'The kind of date follows the DEEP play type: estimated first performance where a performance setting is named, composition where the play type is closet or unacted only, and unclear where both or neither apply; a translation is not thereby unacted. A date whose meaning cannot be settled is set aside rather than guessed.</p>'
                '<div class="caveat"><b>Two kinds of decade on this site.</b> The Map filters by <b>publication decade</b> of the edition. This page groups by the <b>estimated first-performance / composition decade</b> of the work. Chunk and play pages print the Annals date as DEEP records it; section D shows the source actually adopted for each work, so a work can carry an Annals date on its page and a British Drama date here without any contradiction. '
                'Nothing here claims that the whole text of the representative edition existed in the estimated year, and counts per decade describe the works that survive and were selected for this corpus, not how many plays were written or staged.</div>'
                + f'<h3>Sensitivity of the grouping</h3><p class="note">Works whose limits cross a decade boundary ({len(bw)}) were regrouped by their lower limit and, separately, by their upper limit; all other works keep their decade. These two groupings are boundary cases for the sensitivity of the decade grouping — not two claims about the real dates, and they do not exhaust the dating uncertainty. Circa or queried years without limits were not given ± years. Works whose two sources give different years ({len(sd)}) are listed in the download; no further dating research was done.</p>' + stable
                + '<h3>Downloads</h3>' + self.dl('chronology', ['dates_by_work.csv', 'coverage.csv', 'genre_composition.csv', 'included_coverage.csv', 'topic_stats.csv', 'topic_top_works.csv', 'author_composition.csv', 'boundary_works.csv', 'sensitivity_counts.csv', 'topic_stats_sensitivity.csv', 'sources_differ.csv', 'range_only_works.csv', 'methods.md', 'checks.json', 'provenance.json', 'fig1_corpus_composition.svg', 'fig2_sample_and_coverage.svg', 'fig3_topic_decade_heatmap_comedy.svg', 'fig3_topic_decade_heatmap_tragedy.svg', 'fig3_topic_decade_heatmap_history.svg']))
        JS = ('<script>const D=' + json.dumps(D, ensure_ascii=False) + ';'
              r"""
const $=id=>document.getElementById(id);const g=$('dg'),d=$('dd'),t=$('dt'),o=$('dout');
const fill=(s,vals,labels)=>{s.innerHTML='';vals.forEach((v,i)=>{const op=document.createElement('option');op.value=v;op.textContent=labels?labels[i]:v;s.appendChild(op);});};
const esc=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;');
fill(g,D.genres,D.genres.map(x=>x[0].toUpperCase()+x.slice(1)));
const fillD=()=>{const cs=D.cells[g.value]||{};const ds=Object.keys(cs).sort();fill(d,ds,ds.map(x=>x+'  (n = '+cs[x][0]+(cs[x][0]<5?', not shown in the heatmap':cs[x][0]<10?', sparse':'')+')'));};
const fillT=()=>{const ts=D.topics.slice().sort((x,y)=>((D.stats[g.value+'|'+d.value+'|'+y]||[0])[0])-((D.stats[g.value+'|'+d.value+'|'+x]||[0])[0]));fill(t,ts,ts.map(x=>'T'+x+' '+D.labels[x]+' ('+((D.stats[g.value+'|'+d.value+'|'+x]||[0])[0]).toFixed(1)+' %)'));};
const show=()=>{const k=g.value+'|'+d.value+'|'+t.value;const s=D.stats[k];const cell=(D.cells[g.value]||{})[d.value];const ws=D.works[g.value+'|'+d.value]||[];if(!s||!cell){o.innerHTML='<p class="note">no works in this cell</p>';return;}
const top=(D.top[k]||[]);const rep={};ws.forEach(w=>rep[w[0]]=w[11]);
let h='<div class="facts"><div class="f"><b>'+s[0].toFixed(2)+' %</b><i>mean share of the topic</i></div><div class="f"><b>'+s[1].toFixed(2)+' %</b><i>median</i></div><div class="f"><b>'+s[2]+' / '+cell[0]+'</b><i>works containing the topic</i></div><div class="f"><b>'+esc(cell[1])+'</b><i>display status</i></div></div>';
h+='<h3>Works supplying most of the mean</h3>'+(top.length?'<div class="tblx"><table class="small"><thead><tr><th>work</th><th>author field</th><th class="num">share in work %</th><th class="num">contribution to cell mean (pp)</th><th class="num">share of cell total</th><th></th></tr></thead><tbody>'+top.map(r=>'<tr><td>'+(rep[r[0]]?'<a href="plays/'+rep[r[0]]+'.html">'+esc(r[1])+'</a>':esc(r[1]))+' <span class="sub">work '+r[0]+'</span></td><td class="small">'+esc(r[2])+'</td><td class="num">'+r[3].toFixed(2)+'</td><td class="num">'+r[4].toFixed(2)+'</td><td class="num">'+Math.round(100*r[5])+' %</td><td><a href="'+D.tpage[t.value]+'#w'+r[0]+'">chunks</a></td></tr>').join('')+'</tbody></table>':'<p class="note">no work in this cell contains the topic</p>');
h+='<h3>All '+ws.length+' works of the cell</h3><div class="tblx"><table class="sortable small"><thead><tr><th>work</th><th>author field</th><th class="num">adopted year</th><th>source</th><th class="num">limits</th><th>date kind</th><th>flags</th><th>British Drama</th><th>Annals</th><th class="num">Topic share within play (%) — T'+esc(t.value)+'</th></tr></thead><tbody>'
+ws.slice().sort((a,b)=>(a[3]-b[3])||a[1].localeCompare(b[1])).map(w=>'<tr><td>'+(w[11]?'<a href="plays/'+w[11]+'.html">'+esc(w[1])+'</a>':esc(w[1]))+' <span class="sub">work '+w[0]+'</span></td><td class="small">'+esc(w[2])+'</td><td class="num">'+esc(w[3])+'</td><td class="small">'+esc(w[4])+'</td><td class="num">'+(w[5]?esc(w[5])+'–'+esc(w[6]):'')+'</td><td class="small">'+esc(w[7])+'</td><td class="small">'+esc(w[8])+'</td><td class="small">'+esc(w[9])+'</td><td class="small">'+esc(w[10])+'</td><td class="num">'+((w[12]||{})[t.value]!=null?(w[12][t.value]).toFixed(2):'')+'</td></tr>').join('')+'</tbody></table></div><p class="note">Topic share within play (%): percentage of the representative text\'s words assigned to this topic, including unassigned text in the denominator.</p>';
o.innerHTML=h;};
g.addEventListener('change',()=>{fillD();fillT();show();});d.addEventListener('change',()=>{fillT();show();});t.addEventListener('change',show);
fillD();const cs0=D.cells[g.value]||{};const best=Object.keys(cs0).sort((x,y)=>cs0[y][0]-cs0[x][0])[0];if(best)d.value=best;fillT();
const h=location.hash.match(/^#t(\d+)$/);if(h&&D.topics.includes(h[1])){fillT();t.value=h[1];}
show();
document.querySelectorAll('.tabs').forEach(tb=>tb.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{const grp=tb.dataset.group;tb.querySelectorAll('button').forEach(x=>x.classList.toggle('on',x===b));document.querySelectorAll('.panel[data-group="'+grp+'"]').forEach(p=>p.classList.toggle('on',p.dataset.tab===b.dataset.tab));})));
</script>""")
        page = (c['head']('Chronology') + c['mast']('', 'chronology.html') + c['crumbs']('<a href="index.html">Home</a>', 'Chronology')
                + '<h1>Chronology <span class="sub">topics by estimated first-performance / composition decade, in this corpus</span></h1>'
                + '<p class="lede">The works of this corpus grouped by the decade of their estimated first performance or, for closet and unacted plays, composition, and the mean share of each included topic within comedy, tragedy and history in each decade. These are distributions of the works that survive and were selected for the corpus — not counts of what was performed or written in a decade, and not a history of the stage. The page is exploratory: it shows sample sizes first, then means, and lets every cell be traced back to its works.</p>'
                + f'<p class="stamp">{self.stamp("chronology")}</p>'
                + '<p class="note">Sections: <a href="#composition">A. Corpus composition</a> · <a href="#sample">B. Sample size and coverage</a> · <a href="#by-decade">C. Topics by decade</a> · <a href="#trace">D. Trace a cell back to works</a> · <a href="#dates">How the dates were chosen</a></p>'
                + secA + secB + secC + secD + secE + JS + c['foot']())
        (self.out / 'chronology.html').write_text(page, encoding='utf-8')
        return page

    # ---------------------------------------------------------------- Methods sections ------------------------------
    def methods_html(self):
        E = self.E; h = ''
        if self.have['author_by_genre']:
            h += ('<h2>Author comparison (Shakespeare and his contemporaries)</h2>'
                  '<p>Author groups: within one genre group, every work whose author field contains the name (collaborations included) against every other work of the genre; Anonymous is never a group; groups need at least five works and the rest at least ten. Roles are read from the DEEP author list: a translator is never an author group, a reviser counts as a signature, an original author of English translations (Seneca) is compared but labelled as such, and a work in which the author\'s role cannot be resolved is held out of that author\'s comparison. The corpus author field is split against DEEP\'s separated name list so that concatenated collaborators are never read as one person; the field itself was not changed and no attribution research was done.</p>'
                  '<p>Divergence: Jensen–Shannon divergence, log2, in bits (the divergence, not the square-rooted distance), between the two groups\' mean topic profiles (works equal-weighted): once on the included topics renormalised to 100 %, once with the remaining words as an extra bin (which checks the effect of coverage differences). Reference: 1,000 random groups of the same number of works drawn from the same genre, the rest as the other group — a reference range for the group size, not a confidence interval; period and company are not controlled. Leave-one-out drops each work of the author group in turn with the rest unchanged; a sole-signature variant is reported where at least five sole-signature works exist. Per topic the pages give the difference of mean shares in percentage points and the works supplying most of each side\'s mean (share ÷ number of works); the mean-share difference is not the topic\'s share of the divergence.</p>'
                  '<p>Overview charts (top of the Authors page): the first chart shows, for the genre chosen, the ten included topics with the highest simple average of the two groups\' mean shares (Shakespeare\'s plays; all other plays of the genre), the same topics in the same order on both sides. The values are the equal-weighted mean shares of all words from the Shakespeare comparison table, not renormalised to the ten topics or to the included topics; the sum quoted is the mean over plays of the ten shares. "n/N plays" counts the plays of a group with at least one chunk assigned to the topic; a play without one is not thereby without the subject. Where one play supplies more than half of a group\'s total for a topic, the play is named. The second chart shows the divergence on the selected topics (the "conditional" value of the author table) for every author group of the genre, sorted by value, with the 2.5–97.5 % range of the 1,000 random same-size groups as a band and one axis for the three genres; Seneca\'s English translations are shown apart from the playwrights. The two charts use different denominators — shares of all words in the first, the relative distribution within the selected topics in the second — and neither is a ranking of originality or quality.</p>'
                  + ('<p>Comparison period (first overview chart): a toggle restricts the comparison to the pre-set common window of the window check (24_window_check.py) — both sides limited to works whose estimated first-performance / composition year (British Drama first, Annals fallback) falls in the window, both ends inclusive; publication years and date limits are not used for membership. The ten topics and their order stay those of the full corpus, the axis is shared by the two views, and the measure is unchanged (works equal-weighted, shares of all words). Means and plays-with-topic counts come from window_topic_means.csv and window_counts.csv; the works behind each side are rebuilt from work_topic_share.csv with the window\'s work list and are cross-checked against those files at build time. All of Shakespeare\'s dated plays in the three genres fall inside the window, so only the other side changes. The author chart, its random reference and sections A–C use the full corpus; the window does not match dates within it and does not remove the effect of date.</p>' if self.have['window_check'] else ''))
        if self.have['chronology']:
            h += ('<h2>Chronology</h2>'
                  '<p>Date of a work: the British Drama first-performance date; Annals only when British Drama has no entry (reason recorded). The leading year is the adopted year, the bracketed limits of the same source are the limits; licence and revision notes are accompanying events; later revision ranges never widen the limits; publication years are never substituted and the two sources are never averaged. Date kind from the DEEP play type: estimated first performance, composition (closet / unacted), or unclear. Decades are fixed ten-year bins on the adopted year, one per work, none merged; cells with fewer than five works are blank in the figures, five to nine are marked sparse. Sensitivity: works whose limits cross a decade boundary regrouped by lower and by upper limit — boundary cases for the grouping, not alternative datings. '
                  'The Map filters by publication decade of the edition; the Chronology page groups by estimated first-performance / composition decade of the work; both are labelled as such. All figures are on the representative editions, works equal-weighted, and the included topics are a subset of the words of every work.</p>')
        if self.have['company']:
            cov = _csv(self.co / 'company_coverage.csv'); agr = _csv(self.co / 'company_source_agreement.csv')
            st = Counter(); top = []
            for r in cov:
                if r['source'] == 'britdrama':
                    st[r['status'].split(' ')[0]] += int(r['n_works'])
                    if r['status'] == 'clear': top.append(r)
            top = sorted(top, key=lambda r: -int(r['n_works']))[:8]
            both = [r for r in agr if r['both_sources_named']]; rel = Counter(r['britdrama_vs_annals'] for r in both)
            h += ('<h2>Company metadata coverage</h2>'
                  f'<p>DEEP gives a first-performance company from British Drama and one from the Annals, plus the company named on the title page of the edition. Per work (representative edition) the British Drama value is: a clear single name for {st.get("clear", 0)} works, a queried name for {st.get("uncertain", 0)}, several names for {st.get("multiple", 0)}, unknown for {st.get("unknown", 0)}, unacted for {st.get("unacted", 0)}, no entry for {st.get("not", 0) + st.get("missing", 0)} (masques and entertainments, interludes, university and closet plays, translations). '
                  f'Where both sources name a company ({len(both)} works) they give the identical string for {rel.get("identical", 0)}, the same name with a different qualifier for {rel.get("same base name", 0)} and different names for {rel.get("differ", 0)}. Names are kept exactly as recorded; renamings and successions (Chamberlain\'s → King\'s, Chapel → Queen\'s Revels, …) are listed as reference notes and are not merged. '
                  'Largest company groups by the clear British Drama value: ' + ', '.join(f'{E(r["company_raw"])} ({r["n_works"]}; {E(r["genre_composition"][:60])})' for r in top) + '.</p>'
                  '<p>No company comparison is published: what exists is this coverage overview and a candidate list for one comedy pair (Children of the Queen\'s Revels vs Children of Paul\'s (second)) with the works\' dates and attribution divergences, which is a scope for a future reading, not a result about company style.</p>'
                  + self.dl('company', ['company_coverage.csv', 'company_fields_by_work.csv', 'company_source_agreement.csv', 'company_name_notes.csv', 'company_lineage_notes.csv', 'theatre_coverage.csv', 'deep_row_selection.csv', 'company_coverage_summary.md'])
                  + (self.dl('company', ['pair_Children_of_the_Queen_s_Revels_vs_Children_of_Paul_s_second_comedy/pair_works.csv', 'pair_Children_of_the_Queen_s_Revels_vs_Children_of_Paul_s_second_comedy/pair_summary.md'], ['candidate pair: work list (csv)', 'candidate pair: summary (md)'])))
        return h

    # ---------------------------------------------------------------- build ------------------------------------------
    def build(self):
        n = self.copy_data(); made = []
        if self.have['shakespeare'] or self.have['author_by_genre']:
            self.build_shakespeare(); made.append('shakespeare.html')
        if self.have['chronology']:
            self.build_chronology(); made.append('chronology.html')
        for w in self.warnings: print('WARNING (13b):', w)
        print(f'analysis pages: {", ".join(made) or "none"}; {n} result files copied to data/')
        return made


def prepare(ctx):
    return Analysis(ctx)
