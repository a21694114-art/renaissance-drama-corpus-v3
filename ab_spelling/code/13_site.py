#!/usr/bin/env python3
"""13_site.py — the static evidence site (GitHub Pages root), one topic run.

  python 13_site.py --chunks <chunks dir> --runs <runs dir> --seed 42 --manifest build_v3/corpus_manifest.csv \
        [--deep <DEEP_data.csv>] [--out docs] [--repo-url https://github.com/<user>/<repo>] [--credit "Name"]

Writes <out>/:
  index.html               landing: facts, what the site offers, how to read it
  map.html                 chunk-level interactive map (12_map.py, click a point → its chunk page)
  topics.html              master index of all topics, grouped by use category
  topic_NN.html            one page per topic: keywords, facts, genre mix, typical chunks per work,
                           full roster (sortable) and keyword-highlighted excerpts
  genre.html               the genre comparison (09_aggregate.py tables + heatmaps) when present
  plays/<edition>.html     one page per edition: metadata (manifest + DEEP), topic composition,
                           the sequence of chunks with their topics
  chunks/<chunk_id>.html   one page per chunk: metadata, topic + typicality (cosine to the topic
                           centroid), topic in the other seeds, highlighted excerpts, full regularized
                           text, original spelling (if chunks_A.csv is present), previous / next chunk
  methods.html             the pipeline with the parameters actually used (read from run files)
  site.css, site.js        shared stylesheet and the sortable-table script
Everything is derived from files the pipeline already wrote; nothing is recomputed except the
cosine typicality and (once, cached) the 2-D UMAP for the map.
"""
import argparse, hashlib, csv, html, json, re, shutil, subprocess, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

CAT_LABEL = {'included': 'cross-work theme (confirmed)', 'candidate': 'cross-work theme (candidate)', 'contextual_only': 'single work / story',
             'pending': 'pending review', 'unclassified': 'unclassified', 'unassigned': 'unassigned'}
CAT_ORDER = ['included', 'candidate', 'pending', 'contextual_only', 'unclassified']
E = html.escape


def excerpts(text, keywords, n=2, half=170):
    """Windows of ±half characters around the densest keyword hits; returns [(html, hits)]."""
    if not keywords: return []
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\w{0,2}\b", re.I)
    hits = [(m.start(), m.group(0)) for m in pat.finditer(text)]
    if not hits: return []
    wins = []
    used = [False] * len(hits)
    for i, (p, w) in enumerate(hits):
        if used[i]: continue
        lo, hi = max(0, p - half), min(len(text), p + half)
        inside = [j for j, (q, _) in enumerate(hits) if lo <= q < hi]
        score = len({hits[j][1].lower() for j in inside})
        wins.append((score, lo, hi, inside))
    wins.sort(key=lambda w: (-w[0], w[1]))
    out, taken = [], []
    for score, lo, hi, inside in wins:
        if any(not (hi <= a or lo >= b) for a, b in taken): continue
        taken.append((lo, hi))
        seg = text[lo:hi]
        seg = pat.sub(lambda m: '\x00' + m.group(0) + '\x01', seg)
        seg = E(seg).replace('\x00', '<mark>').replace('\x01', '</mark>')
        out.append(('…' if lo > 0 else '') + seg + ('…' if hi < len(text) else ''))
        if len(out) >= n: break
    return out


def facets(v, kind=None):
    if not v or str(v).strip().lower() in ('', 'nan', 'none', 'n/a'): return []
    parts = re.split(r';\s*|(?<=[a-z])(?=[A-Z][a-z]+, )', str(v)) if kind == 'author' else re.split(r';\s*', str(v))
    return [p.strip() for p in parts if p.strip()]


def clean(v):
    v = (v or '').strip(); return '' if v.lower() in ('none', 'n/a', 'nan', 'not in britdrama') else v


def authors(v):
    """Display form of the manifest's author field, whose names are run together ('AnonymousFletcher, JohnMassinger, Philip')."""
    return ' / '.join(facets(v, 'author')) or (v or '')


def highlight(text, keywords):
    """The whole text with the topic's words marked (same matching rule as excerpts)."""
    if not keywords: return E(text)
    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\w{0,2}\b", re.I)
    return E(pat.sub(lambda m: '\x00' + m.group(0) + '\x01', text)).replace('\x00', '<mark>').replace('\x01', '</mark>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--manifest', required=True); ap.add_argument('--deep', default='')
    ap.add_argument('--out', default='docs'); ap.add_argument('--repo-url', default='')
    ap.add_argument('--title', default='Renaissance Drama — Topics'); ap.add_argument('--credit', default='')
    ap.add_argument('--no-map', action='store_true'); ap.add_argument('--limit-chunk-pages', type=int, default=0)
    ap.add_argument('--use', default='', help='categories in the genre comparison; default: aggregate/config.json if present, else included,candidate')
    a = ap.parse_args()
    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'; agg = d / 'aggregate'
    agg_cfg = json.load(open(agg / 'config.json')) if (agg / 'config.json').exists() else {}
    gassign = {r['work_id']: r for r in csv.DictReader(open(agg / 'genre_assignment.csv', encoding='utf-8'))} if (agg / 'genre_assignment.csv').exists() else {}
    use_cats = [u.strip() for u in a.use.split(',') if u.strip()] if a.use else (agg_cfg.get('use') or ['included', 'candidate'])
    in_cmp = lambda cat: cat in use_cats
    CAT_LABEL.update({'included': 'cross-work theme (confirmed' + (', in the genre comparison)' if 'included' in use_cats else ')'),
                      'candidate': 'cross-work theme (candidate' + (', in the genre comparison)' if 'candidate' in use_cats else ' — not yet in the comparison)')})
    out = Path(a.out); (out / 'chunks').mkdir(parents=True, exist_ok=True); (out / 'plays').mkdir(exist_ok=True)
    code_dir = Path(__file__).resolve().parent

    # ---------------- data ----------------
    ids = [r['chunk_id'] for r in csv.DictReader(open(runs / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
    row_of = {c: i for i, c in enumerate(ids)}
    _dt = list(csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8')))
    labels = {r['chunk_id']: int(r['topic']) for r in _dt}
    in_fit = {r['chunk_id']: r.get('in_fit', '1') == '1' for r in _dt}; n_fit = sum(in_fit.values()); n_placed = len(in_fit) - n_fit
    other = {}
    for p in sorted(runs.glob(f'topics_{a.variant}_s*')):
        s = int(p.name.split('_s')[1])
        if s != a.seed and (p / 'doc_topics.csv').exists():
            other[s] = {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(p / 'doc_topics.csv', encoding='utf-8'))}
    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    cmap = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_map.csv', encoding='utf-8'))}
    texts = {r['chunk_id']: r['text'] for r in csv.DictReader(open(ch / f'chunks_{a.variant}.csv', encoding='utf-8'))}
    orig = {}
    if (ch / 'chunks_A.csv').exists():
        try:
            orig = {r['chunk_id']: r['text'] for r in csv.DictReader(open(ch / 'chunks_A.csv', encoding='utf-8'))}
        except OSError:
            print('chunks_A.csv not readable (cloud placeholder?) — original spelling omitted')
    sheet = {int(r['topic']): r for r in csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8'))}
    kw30 = defaultdict(list)
    if (d / 'top_words_classtfidf.csv').exists():
        for r in csv.DictReader(open(d / 'top_words_classtfidf.csv', encoding='utf-8')):
            kw30[int(r['topic'])].append(r['word'])
    manifest = {r['edition_id_effective']: r for r in csv.DictReader(open(a.manifest, encoding='utf-8'))}
    deep = {}
    if a.deep and Path(a.deep).exists():
        deep = {r['edition_id']: r for r in csv.DictReader(open(a.deep, encoding='utf-8-sig'))}
    run_info = json.load(open(d / 'run.json')) if (d / 'run.json').exists() else {}
    emb_info = json.load(open(runs / f'embedding_{a.variant}.json')) if (runs / f'embedding_{a.variant}.json').exists() else {}
    chunk_info = json.load(open(ch / 'chunk_map_summary.json')) if (ch / 'chunk_map_summary.json').exists() else {}

    # typicality
    emb = np.load(runs / f'embeddings_{a.variant}.npy').astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    members = defaultdict(list)
    for c, t in labels.items():
        if t != -1: members[t].append(c)
    topics = sorted(members)
    # a rebuild on another run (e.g. 95 → 63 topics) must not leave the old run's topic pages and figures behind
    stale = [p for p in out.glob('topic_*.html') if not re.fullmatch(r'topic_(\d+)\.html', p.name) or int(re.fullmatch(r'topic_(\d+)\.html', p.name).group(1)) not in members]
    stale += [p for p in out.glob('*.png')]   # genre figures are copied again below from the current aggregate dir
    for p in stale: p.unlink()
    if stale: print(f'removed {len(stale)} stale files from {out}')
    cent = {t: emb[[row_of[c] for c in members[t]]].mean(axis=0) for t in topics}
    for t in topics: cent[t] /= np.linalg.norm(cent[t]) + 1e-9
    C = np.stack([cent[t] for t in topics])
    sims = emb @ C.T                                   # n_chunks × n_topics
    typ = {}; nearest = {}
    for c in ids:
        i = row_of[c]; t = labels[c]
        j = int(np.argmax(sims[i])); nearest[c] = (topics[j], float(sims[i, j]))
        typ[c] = float(sims[i, topics.index(t)]) if t != -1 else float('nan')

    def label_of(t):
        if t == -1: return 'unassigned'
        r = sheet.get(t, {}); return r.get('Label') or r.get('draft_label') or f'topic {t}'
    def cat_of(t):
        if t == -1: return 'unassigned'
        return sheet.get(t, {}).get('use_in_genre_analysis') or 'unclassified'
    def tpage(t): return f'topic_{t:02d}.html'
    def badge(cat): return f'<span class="badge b-{cat}">{E(CAT_LABEL.get(cat, cat))}</span>'
    def chip(t, root=''):
        if t == -1: return '<span class="chip chip-out">unassigned</span>'
        return f'<a class="chip" href="{root}{tpage(t)}">T{t} {E(label_of(t)[:40])}</a>'

    # editions
    ed_chunks = defaultdict(list)
    for c in ids: ed_chunks[meta[c]['edition_id']].append(c)
    for e in ed_chunks: ed_chunks[e].sort(key=lambda c: (int(cmap[c]['node_start']), int(cmap[c]['piece_start'])))
    years = [int(m['year']) for m in manifest.values() if m['year_effective'].isdigit()] if False else [int(meta[c]['year']) for c in ids if meta[c]['year'].isdigit()]
    n_works = len({m['work_id'] for m in meta.values()})

    # ---------------- shell ----------------
    def head(title, root=''):
        return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
                f'<title>{E(title)} · {E(a.title)}</title><link rel="stylesheet" href="{root}site.css?v={ASSET_V}"><script defer src="{root}site.js?v={ASSET_V}"></script></head><body>')
    def mast(root='', active=''):
        items = [('index.html', 'Home'), ('map.html', 'Map'), ('topics.html', 'Topics'), ('plays.html', 'Plays'), ('genre.html', 'Genre'), ('methods.html', 'Methods')]
        nav = ''.join(f'<a href="{root}{h}"{" class=active" if active == h else ""}>{n}</a>' for h, n in items if h != 'genre.html' or agg.exists())
        if a.repo_url: nav += f'<a href="{E(a.repo_url)}">GitHub</a>'
        return f'<div class="masthead"><div class="in"><a class="brand" href="{root}index.html">{E(a.title)} <span>· seed {a.seed}</span></a><nav>{nav}</nav></div></div><div class="wrap">'
    def foot():
        c = f'{E(a.credit)} · ' if a.credit else ''
        return f'<div class="footer">{c}generated by <code>13_site.py</code> from run <code>{E(runs.name)}</code>, seed {a.seed}. Texts: EEBO-TCP / EarlyPrint (CC BY-NC 3.0). Metadata: DEEP, Wiggins &amp; Richardson.</div></div></body></html>'
    def crumbs(*parts):
        return '<nav class="crumbs">' + ' › '.join(parts) + '</nav>'

    CSS = """
:root{--ink:#1b1b22;--muted:#5f5f6b;--faint:#8b8b95;--accent:#2b5c8a;--accent-ink:#1f4468;--accent-soft:#e9f0f7;--bg:#fbfbf8;--card:#fff;--rule:#e6e6df;--soft:#f3f3ec;--warm:#f8f4e8;--maxw:1080px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Helvetica,Arial,sans-serif}
.masthead{position:sticky;top:0;z-index:9;background:rgba(255,255,255,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--rule)}
.masthead .in{max-width:var(--maxw);margin:0 auto;padding:0 24px;height:46px;display:flex;align-items:center;gap:18px}
.masthead .brand{font-weight:700;color:var(--ink);text-decoration:none;white-space:nowrap}.masthead .brand span{color:var(--faint);font-weight:500}
.masthead nav{margin-left:auto;display:flex;gap:2px;font-size:.88rem}.masthead nav a{color:var(--muted);text-decoration:none;padding:4px 10px;border-radius:6px}
.masthead nav a:hover,.masthead nav a.active{color:var(--accent-ink);background:var(--accent-soft)}
.wrap{max-width:var(--maxw);margin:0 auto;padding:30px 24px 80px}.wrap.wide{max-width:1500px}
nav.crumbs{font-size:.82rem;color:var(--faint);margin:0 0 1.4em}nav.crumbs a{color:var(--muted);text-decoration:none}nav.crumbs a:hover{text-decoration:underline}
h1{font-size:1.8rem;font-weight:750;letter-spacing:-.02em;line-height:1.2;margin:0 0 .3em}
h2{font-size:1.02rem;font-weight:700;margin:2.6em 0 .8em;padding-bottom:.4em;border-bottom:1px solid var(--rule);display:flex;align-items:baseline;gap:8px}
h2::before{content:"";width:22px;height:4px;border-radius:2px;background:var(--accent);align-self:center;flex:none;opacity:.85}
h3{font-size:.95rem;font-weight:650;margin:1.4em 0 .4em}p{max-width:78ch}.lede{color:var(--muted);margin:0 0 1.2em;max-width:80ch}a{color:var(--accent)}
code{background:var(--soft);border-radius:4px;padding:1px 5px;font-size:.88em}
.facts{display:flex;flex-wrap:wrap;gap:6px 34px;margin:1.2em 0 1.5em}.facts .f b{display:block;font-size:1.25rem;font-weight:700;line-height:1.25;font-variant-numeric:tabular-nums}
.facts .f i{font-style:normal;display:block;font-size:.76rem;color:var(--muted);letter-spacing:.04em;text-transform:uppercase}
.badge,.chip{display:inline-block;font-size:.66rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;border-radius:999px;padding:2px 8px;margin-left:6px;vertical-align:2px;background:#ececec;color:#55555f;white-space:nowrap;text-decoration:none}
.b-included,.b-candidate{background:#dfe9f4;color:#1f4468}.b-contextual_only{background:#f5eecb;color:#7a6a2e}.b-pending{background:#ececec;color:#55555f}.b-unassigned,.chip-out{background:#f0f0f0;color:#8b8b95}
.chip{text-transform:none;letter-spacing:0;font-weight:600;font-size:.72rem;margin:0 4px 0 0;background:#e9f0f7;color:#1f4468}.chip:hover{background:#d5e3f1}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:1em 0}
.card{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:14px 16px}.card h3{margin:0 0 .3em}.card .who a{font-weight:650;text-decoration:none}.card .whence{font-size:.85rem;color:var(--muted)}
.card .snip{font-size:.86rem;margin-top:.5em;color:#333}
table{border-collapse:collapse;width:100%;font-size:.88rem;margin:.6em 0 1.2em}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--rule);vertical-align:top}
th{background:var(--soft);font-weight:650;position:sticky;top:46px}table.sortable th{cursor:pointer}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.excerpt{background:var(--warm);border-left:3px solid #d9c27a;border-radius:0 8px 8px 0;padding:10px 14px;margin:.6em 0;font-size:.92rem;line-height:1.55}
mark{background:#fff3a8;padding:0 2px;border-radius:2px}
.text{background:var(--card);border:1px solid var(--rule);border-radius:10px;padding:16px 20px;white-space:pre-wrap;font-size:.95rem;line-height:1.65}
.kw{display:flex;gap:8px;flex-wrap:wrap}.kw span{background:var(--accent-soft);color:var(--accent-ink);border-radius:6px;padding:2px 8px;font-size:.85rem}.kw span.nm{background:#f5eecb;color:#7a6a2e}
.bars{display:grid;grid-template-columns:max-content 1fr max-content;gap:4px 10px;align-items:center;font-size:.86rem;max-width:760px}.bars .bar{height:10px;background:var(--accent);border-radius:3px;opacity:.85}.bars .lab{color:var(--muted)}
.seq td.t{white-space:nowrap}.pn{display:flex;justify-content:space-between;margin:1.5em 0;font-size:.9rem}
.footer{margin-top:3em;padding-top:1em;border-top:1px solid var(--rule);font-size:.8rem;color:var(--faint)}
details summary{cursor:pointer;color:var(--accent)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:800px){.grid2{grid-template-columns:1fr}}
img.heat{display:block;max-width:100%;max-height:78vh;width:auto;height:auto;margin:0 auto;border:1px solid var(--rule);border-radius:8px;cursor:zoom-in;background:#fff}
.fig{margin:0 0 .6em}.fig .fighint{text-align:center;font-size:.78rem;color:var(--faint);margin:.35em 0 0}
#lb{position:fixed;inset:0;z-index:50;background:rgba(20,20,26,.93);display:none;overflow:auto}#lb.on{display:block}#lb .stage{min-height:100%;display:flex;padding:52px 16px 24px}
#lb img{display:block;max-width:none;margin:auto;cursor:zoom-in;background:#fff;border-radius:4px}#lb.big img{cursor:grab}#lb .bar{position:fixed;top:0;left:0;right:0;height:44px;display:flex;align-items:center;gap:8px;padding:0 14px;background:rgba(0,0,0,.55);color:#eee;font-size:.85rem;z-index:51}
#lb .bar button,#lb .bar a{font:inherit;color:#fff;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.25);border-radius:6px;padding:4px 10px;cursor:pointer;text-decoration:none}#lb .bar button:hover,#lb .bar a:hover{background:rgba(255,255,255,.26)}#lb .bar .sp{flex:1}#lb .bar .pct{min-width:4em;text-align:center;font-variant-numeric:tabular-nums}
#note{font-size:.8rem;color:var(--muted);margin:0 0 .4em}#filters{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;margin:0 0 .6em;font-size:.8rem;color:var(--muted)}
#filters select{max-width:220px;font-size:.8rem}#filters button{font-size:.8rem}#count{color:var(--accent-ink);font-weight:600}#map{height:calc(100vh - 190px);min-height:560px}
input.filterbox{width:100%;max-width:520px;font:inherit;font-size:.95rem;padding:8px 12px;border:1px solid var(--rule);border-radius:8px;margin:.2em 0 1em;background:var(--card)}
.metaline{color:var(--muted);font-size:.95rem;margin:0 0 1.2em;max-width:none}.metaline b{color:var(--ink);font-weight:600}
"""
    JS = """document.querySelectorAll('table.sortable').forEach(t=>{const ths=t.querySelectorAll('th');ths.forEach((th,i)=>th.addEventListener('click',()=>{const tb=t.tBodies[0];const rows=[...tb.rows];const dir=th.dataset.dir==='asc'?'desc':'asc';ths.forEach(x=>x.dataset.dir='');th.dataset.dir=dir;
const val=r=>{const c=r.cells[i];const v=c.dataset.v!==undefined?c.dataset.v:c.textContent.trim();const n=parseFloat(v);return isNaN(n)?v.toLowerCase():n};
rows.sort((a,b)=>{const x=val(a),y=val(b);return (x>y?1:x<y?-1:0)*(dir==='asc'?1:-1)});rows.forEach(r=>tb.appendChild(r));}));});
document.querySelectorAll('input.filterbox').forEach(inp=>{const items=[...document.querySelectorAll(inp.dataset.target)];const out=document.getElementById(inp.dataset.count);
const run=()=>{const q=inp.value.trim().toLowerCase().split(/\s+/).filter(Boolean);let n=0;items.forEach(el=>{const t=(el.dataset.search||el.textContent).toLowerCase();const ok=q.every(w=>t.includes(w));el.style.display=ok?'':'none';if(ok)n++;});
document.querySelectorAll('h2[data-group]').forEach(h=>{const any=items.some(el=>el.dataset.group===h.dataset.group&&el.style.display!=='none');h.style.display=any?'':'none';});if(out)out.textContent=q.length?n+' shown':'';};
inp.addEventListener('input',run);});
/* lightbox for figures: click = fit to screen; +/- or click the image = zoom; 1:1 = full size; Esc closes */
(()=>{const figs=[...document.querySelectorAll('a>img.heat')];if(!figs.length)return;
const lb=document.createElement('div');lb.id='lb';lb.innerHTML='<div class="bar"><span class="ttl"></span><span class="sp"></span><button data-z="-">&minus;</button><span class="pct"></span><button data-z="+">+</button><button data-z="fit">Fit to screen</button><button data-z="1">1:1</button><a class="open" target="_blank" rel="noopener">Open file</a><button data-z="x">Close &times;</button></div><div class="stage"><img alt=""></div>';
document.body.appendChild(lb);const img=lb.querySelector('img'),pct=lb.querySelector('.pct'),ttl=lb.querySelector('.ttl'),open=lb.querySelector('.open');let sc=1;
const fitScale=()=>Math.min((window.innerWidth-40)/img.naturalWidth,(window.innerHeight-84)/img.naturalHeight,1);
const apply=()=>{img.style.width=Math.round(img.naturalWidth*sc)+'px';pct.textContent=Math.round(sc*100)+' %';lb.classList.toggle('big',sc>fitScale()+1e-6);};
const show=(a)=>{ttl.textContent=a.querySelector('img').alt||'';open.href=a.href;img.onload=()=>{sc=fitScale();apply();lb.scrollTo(0,0);};img.src=a.href;lb.classList.add('on');document.body.style.overflow='hidden';};
const hide=()=>{lb.classList.remove('on');document.body.style.overflow='';img.removeAttribute('src');};
figs.forEach(im=>im.parentElement.addEventListener('click',e=>{if(e.metaKey||e.ctrlKey||e.button)return;e.preventDefault();show(im.parentElement);}));
lb.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{const z=b.dataset.z;if(z==='x')return hide();if(z==='fit')sc=fitScale();else if(z==='1')sc=1;else if(z==='+')sc=Math.min(sc*1.25,4);else sc=Math.max(sc/1.25,0.05);apply();}));
img.addEventListener('click',()=>{sc=(sc>fitScale()+1e-6)?fitScale():1;apply();});
lb.querySelector('.stage').addEventListener('click',e=>{if(e.target===e.currentTarget)hide();});
document.addEventListener('keydown',e=>{if(!lb.classList.contains('on'))return;if(e.key==='Escape')hide();else if(e.key==='+'||e.key==='=')lb.querySelector('[data-z="+"]').click();else if(e.key==='-')lb.querySelector('[data-z="-"]').click();});
window.addEventListener('resize',()=>{if(lb.classList.contains('on')&&!lb.classList.contains('big')){sc=fitScale();apply();}});})();"""
    (out / 'site.css').write_text(CSS, encoding='utf-8'); (out / 'site.js').write_text(JS, encoding='utf-8')
    ASSET_V = hashlib.md5((CSS + JS).encode('utf-8')).hexdigest()[:8]   # cache-buster: browsers reload site.css / site.js whenever they change
    (out / '.nojekyll').write_text('', encoding='utf-8')   # GitHub Pages: serve files as they are (no Jekyll pass over 18k pages)

    # ---------------- chunk pages ----------------
    def deep_fields(e):
        r = deep.get(e, {})
        return {'first performance / composition (Annals)': clean(r.get('date_first_performance', '')), 'first performance (BritDrama)': clean(r.get('date_first_performance_brit_display', '')),
                'company (BritDrama)': clean(r.get('company_first_performance_brit_display', '')),
                'company (Annals)': clean(r.get('company_first_performance_annals_display', '')), 'theater': clean(r.get('theater', '')), 'theater type': clean(r.get('theater_type', '')),
                'title-page company': clean(r.get('title_page_company_display', '')), 'printer': clean(r.get('printer', '')), 'publisher': clean(r.get('publisher', '')),
                'format': clean(r.get('format', '')), 'STC': clean(r.get('stc', '')), 'Greg': clean(r.get('greg_full', '')), 'genre (Annals)': clean(r.get('genre_annals_display', '')),
                'genre (BritDrama)': clean(r.get('genre_brit_display', '')), 'BritDrama no.': clean(r.get('brit_drama_number', '')),
                'title page': clean(re.sub(r'<[^>]+>', '', r.get('title_page_title', ''))), 'title-page performance note': clean(re.sub(r'<[^>]+>', '', r.get('title_page_performance', '')))}

    n_pages = 0
    chunk_ids = ids if not a.limit_chunk_pages else ids[:a.limit_chunk_pages]
    for c in chunk_ids:
        m, cm, t = meta[c], cmap[c], labels[c]
        e = m['edition_id']; seq = ed_chunks[e]; k = seq.index(c)
        prev_c = seq[k - 1] if k > 0 else None; next_c = seq[k + 1] if k + 1 < len(seq) else None
        kws = kw30.get(t, [])[:15] if t != -1 else kw30.get(nearest[c][0], [])[:15]
        ex = excerpts(texts[c], kws, n=2)
        df = deep_fields(e)
        rows = [('Play', f'<a href="../plays/{e}.html">{E(m["title"])}</a>'), ('Author', E(authors(m['author']))), ('Publication year (edition)', E(m['year']))]
        for kk in ('first performance / composition (Annals)', 'first performance (BritDrama)', 'company (BritDrama)', 'theater'):
            if df[kk]: rows.append((kk[0].upper() + kk[1:], E(df[kk])))
        rows += [('Genre (British Drama)', E(m['genre_deep'])), ('Play type', E(m['play_type_deep'])), ('Edition / TCP / DEEP', f'edition {e} · TCP {E(m["tcp"])} · DEEP {E(m["deep_id"])}'),
                 ('Position', f'nodes {cm["node_start"]}–{cm["node_end"]} (positions in the processed text, not lines of the printed book)' + (f' · piece {cm["piece_start"]}–{cm["piece_end"]} of a split node' if cm['n_pieces_end'] != '1' or cm['piece_start'] != '0' else '') + f' · chunk {k + 1} of {len(seq)} in this edition'),
                 ('Length', f'{cm["len_B_words"]} words · {cm["len_B_tokens"]} tokens' + (f' · flags: {E(cm["flags"])}' if cm['flags'] else '')),
                 ('Topic (seed %d)' % a.seed, (f'<a href="../{tpage(t)}">T{t} — {E(label_of(t))}</a> {badge(cat_of(t))} · typicality {typ[c]:.3f} (cosine to the topic centroid)' if t != -1
                                               else f'unassigned by HDBSCAN · nearest topic <a href="../{tpage(nearest[c][0])}">T{nearest[c][0]} — {E(label_of(nearest[c][0]))}</a> at {nearest[c][1]:.3f}'))]
        if other:
            rows.append(('Other seeds', ' · '.join(f'seed {s_}: ' + (f'T{lab[c]}' if lab[c] != -1 else 'unassigned') for s_, lab in sorted(other.items())) + ' — topic numbers are assigned independently in each run; equal or different numbers say nothing by themselves'))
        meta_html = '<table>' + ''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in rows) + '</table>'
        orig_html = f'<details><summary>Original spelling (EEBO-TCP, unregularized)</summary><div class="text">{E(orig[c])}</div></details>' if c in orig else ''
        pn = (f'<div class="pn"><span>{"<a href=%s.html>← previous chunk</a>" % prev_c if prev_c else ""}</span><span><a href="../plays/{e}.html">all chunks of this edition</a></span><span>{"<a href=%s.html>next chunk →</a>" % next_c if next_c else ""}</span></div>')
        line2 = ' · '.join(v for v in (E(m['genre_deep']), E(df['company (BritDrama)']), E(df['theater'].split(';')[0].strip()) if df['theater'] else '') if v)
        dates = f'published {E(m["year"])}' + (f' · first performed or written {E(df["first performance / composition (Annals)"])} (Annals)' if df['first performance / composition (Annals)'] else '')
        topic_txt = (f'{chip(t, "../")} typicality {typ[c]:.2f}' if t != -1 else f'<span class="chip chip-out">unassigned</span> nearest {chip(nearest[c][0], "../")}')
        kw_note = (f'<p class="lede" style="font-size:.85rem">Marked words are the most distinguishing words of {"T%d" % t if t != -1 else "the nearest topic T%d" % nearest[c][0]}: <em>{E(", ".join(kws[:10]))}</em>.</p>' if kws else '')
        page = (head(f'Chunk {c}', '../') + mast('../') + crumbs('<a href="../index.html">Home</a>', f'<a href="../plays/{e}.html">{E(m["title"][:50])}</a>', f'chunk {c}')
                + f'<h1>{E(m["title"])} <span style="color:var(--faint);font-weight:500">· chunk {k + 1} of {len(seq)}</span></h1>'
                + f'<p class="metaline"><b>{E(authors(m["author"]))}</b> · {dates}<br>{line2}<br>{topic_txt} · {cm["len_B_words"]} words</p>'
                + pn + kw_note + f'<div class="text">{highlight(texts[c], kws)}</div>' + pn
                + '<h2>Details</h2><details><summary>Metadata, position in the edition, topic in the other seeds</summary>' + meta_html + '</details>' + orig_html + foot())
        (out / 'chunks' / f'{c}.html').write_text(page, encoding='utf-8'); n_pages += 1
        if n_pages % 2000 == 0: print(f'  {n_pages} chunk pages', flush=True)

    # ---------------- play pages ----------------
    for e, seq in ed_chunks.items():
        m = manifest.get(e, {}); mm = meta[seq[0]]
        words = sum(int(cmap[c]['len_B_words']) for c in seq)
        by_t = Counter()
        for c in seq: by_t[labels[c]] += int(cmap[c]['len_B_words'])
        comp = sorted(by_t.items(), key=lambda kv: -kv[1])
        bars = ''.join(f'<div class="lab">{chip(t, "../")}</div><div><div class="bar" style="width:{100 * w / words:.1f}%"></div></div><div class="num">{100 * w / words:.1f} %</div>' for t, w in comp[:14])
        df = deep_fields(e)
        info = [('Title', E(mm['title'])), ('Author', E(authors(mm['author']))), ('Publication year (edition)', E(mm['year'])), ('Genre (British Drama)', E(mm['genre_deep'])), ('Play type', E(mm['play_type_deep'])),
                ('Work / edition / TCP / DEEP', f'work {E(mm["work_id"])} · edition {e} · TCP {E(mm["tcp"])} · DEEP {E(mm["deep_id"])}')]
        ga = gassign.get(mm['work_id'])
        if ga:
            src = {'britdrama': 'from the British Drama label', 'annals': 'British Drama label compound or missing → Annals label used', 'none': 'no single main genre in British Drama or Annals → outside the single-genre comparison'}[ga['genre_source']]
            info.insert(4, ('Genre group (comparison)', f'{E(ga["genre_main"])} — {src}' + (f' · Annals: {E(ga["genre_annals"])}' if ga['genre_annals'] else '')))
        info += [(k[0].upper() + k[1:], E(v)) for k, v in df.items() if v]
        if m: info.append(('Corpus build', f'{E(m.get("corpus_version", ""))} · nodes {E(m.get("n_nodes[texts_analysis_en]", ""))} · witness {E(m.get("witness_role", "") or "single")}'))
        other_eds = sorted(x for x in ed_chunks if x != e and meta[ed_chunks[x][0]]['work_id'] == mm['work_id'])
        oe = (' · other editions of this work: ' + ', '.join(f'<a href="{x}.html">{x} ({E(meta[ed_chunks[x][0]]["year"])})</a>' for x in other_eds)) if other_eds else ''
        rows = ''.join(f'<tr><td class="num">{i + 1}</td><td class="num">{cmap[c]["node_start"]}–{cmap[c]["node_end"]}</td><td class="num">{cmap[c]["len_B_words"]}</td><td class="t">{chip(labels[c], "../")}</td>'
                       f'<td class="num">{"" if labels[c] == -1 else f"{typ[c]:.2f}"}</td><td><a href="../chunks/{c}.html">{E(texts[c][:110])}…</a></td></tr>' for i, c in enumerate(seq))
        page = (head(mm['title'], '../') + mast('../') + crumbs('<a href="../index.html">Home</a>', '<a href="../plays.html">Plays</a>', E(mm['title'][:60]))
                + f'<h1>{E(mm["title"])}</h1><p class="lede">{E(authors(mm["author"]))}, published {E(mm["year"])} · {E(mm["genre_deep"])} · {E(mm["play_type_deep"])}{oe}</p>'
                + f'<div class="facts"><div class="f"><b>{len(seq)}</b><i>chunks</i></div><div class="f"><b>{words:,}</b><i>words</i></div><div class="f"><b>{len([t for t in by_t if t != -1])}</b><i>topics</i></div><div class="f"><b>{100 * by_t[-1] / words:.0f} %</b><i>unassigned</i></div></div>'
                + '<h2>Metadata</h2><table>' + ''.join(f'<tr><th>{k}</th><td>{v}</td></tr>' for k, v in info) + '</table>'
                + '<h2>Topic composition (share of words)</h2><div class="bars">' + bars + '</div>'
                + '<h2>Chunks in order</h2><table class="sortable seq"><thead><tr><th class="num">#</th><th class="num">nodes</th><th class="num">words</th><th>topic</th><th class="num">typ.</th><th>opening</th></tr></thead><tbody>' + rows + '</tbody></table>' + foot())
        (out / 'plays' / f'{e}.html').write_text(page, encoding='utf-8')

    # ---------------- plays index ----------------
    prow = ''
    for e, seq in sorted(ed_chunks.items(), key=lambda kv: (meta[kv[1][0]]['title'].lower(), meta[kv[1][0]]['year'])):
        mm = meta[seq[0]]; df = deep_fields(e); w = sum(int(cmap[c]['len_B_words']) for c in seq)
        prow += (f'<tr data-search="{E(mm["title"] + " " + authors(mm["author"]) + " " + mm["year"] + " " + mm["genre_deep"] + " " + df["company (BritDrama)"])}"><td><a href="plays/{e}.html">{E(mm["title"][:70])}</a></td><td>{E(authors(mm["author"])[:40])}</td>'
                 f'<td class="num">{E(mm["year"])}</td><td>{E(df["first performance / composition (Annals)"])}</td><td>{E(mm["genre_deep"][:24])}</td><td>{E(df["company (BritDrama)"][:32])}</td><td class="num">{len(seq)}</td><td class="num">{100 * sum(int(cmap[c]["len_B_words"]) for c in seq if labels[c] == -1) / w:.0f} %</td></tr>')
    page = (head('Plays') + mast('', 'plays.html') + crumbs('<a href="index.html">Home</a>', 'Plays')
            + f'<h1>All editions</h1><p class="lede">{len(ed_chunks)} editions of {n_works} works. Each page lists the edition\'s chunks in order with their topics; dates are publication years, the Annals date is the first performance or composition.</p>'
            + '<input class="filterbox" type="search" placeholder="Find a play — title, author, year, genre, company…" data-target="table.plays tbody tr" data-count="pcount"> <span id="pcount" style="font-size:.85rem;color:var(--muted)"></span>'
            + '<table class="sortable plays"><thead><tr><th>title</th><th>author</th><th class="num">published</th><th>first performed / written (Annals)</th><th>genre (British Drama)</th><th>company (BritDrama)</th><th class="num">chunks</th><th class="num">unassigned</th></tr></thead><tbody>' + prow + '</tbody></table>' + foot())
    (out / 'plays.html').write_text(page, encoding='utf-8')

    # ---------------- topic pages ----------------
    kw_lists = {}
    for t in topics:
        r = sheet[t]
        def kwspan(s): return ''.join(f'<span class="{"nm" if w.startswith("*") else ""}">{E(w.lstrip("*"))}</span>' for w in s.split(', ') if w)
        mem = members[t]; works = Counter(meta[c]['work_id'] for c in mem)
        title_of = {}
        for c in mem: title_of.setdefault(meta[c]['work_id'], (meta[c]['title'], meta[c]['author'], meta[c]['year']))
        genres = Counter(meta[c]['genre_deep'] for c in mem)
        # typical chunk per work, best 8 works by count then typicality
        best_per_work = {w: max((c for c in mem if meta[c]['work_id'] == w), key=lambda c: typ[c]) for w in works}
        land = [best_per_work[w] for w, _ in works.most_common(8)]
        cards = ''.join(f'<div class="card"><div class="who"><a href="chunks/{c}.html">{E(meta[c]["title"][:48])}</a> <span class="badge">typ. {typ[c]:.2f}</span></div>'
                        f'<div class="whence">{E(authors(meta[c]["author"])[:44])}, {E(meta[c]["year"])} · {E(meta[c]["genre_deep"])} · {works[meta[c]["work_id"]]} chunks of this work here</div>'
                        f'<div class="snip">{E(texts[c][:180])}…</div></div>' for c in land)
        gb = ''.join(f'<div class="lab">{E(g)}</div><div><div class="bar" style="width:{100 * n / len(mem):.1f}%"></div></div><div class="num">{n} ({100 * n / len(mem):.0f} %)</div>' for g, n in genres.most_common(8))
        wl = ', '.join(f'<a href="#w{w}">{E(title_of[w][0][:40])}</a> ({n})' for w, n in works.most_common(15))
        roster = sorted(mem, key=lambda c: (int(meta[c]['year']) if meta[c]['year'].isdigit() else 9999, -typ[c]))
        rows = ''.join(f'<tr id="{"w" + meta[c]["work_id"] if best_per_work.get(meta[c]["work_id"]) == c else ""}"><td><a href="chunks/{c}.html">{c}</a></td><td>{E(meta[c]["title"][:55])}</td><td>{E(authors(meta[c]["author"])[:34])}</td>'
                       f'<td class="num">{E(meta[c]["year"])}</td><td>{E(meta[c]["genre_deep"][:22])}</td><td class="num">{cmap[c]["len_B_words"]}</td><td class="num">{typ[c]:.3f}</td></tr>' for c in roster)
        ex_html = ''
        for c in sorted(mem, key=lambda c: -typ[c])[:12]:
            ex = excerpts(texts[c], kw30.get(t, [])[:15], n=1)
            if ex: ex_html += f'<div class="excerpt"><b><a href="chunks/{c}.html">{E(meta[c]["title"][:50])}</a></b> ({E(meta[c]["year"])}) · typ. {typ[c]:.2f}<br>{ex[0]}</div>'
        st = r.get('review_status') or 'draft_ai'
        facts = (f'<div class="facts"><div class="f"><b>{len(mem)}</b><i>chunks</i></div><div class="f"><b>{int(r["words"]):,}</b><i>words</i></div><div class="f"><b>{len(works)}</b><i>works</i></div>'
                 f'<div class="f"><b>{r["n_works_ge3"]}</b><i>works with ≥3 chunks</i></div><div class="f"><b>{100 * float(r["dominant_work_share"]):.0f} %</b><i>dominant work</i></div><div class="f"><b>{100 * float(r["top3_work_share"]):.0f} %</b><i>top-3 works</i></div></div>')
        note = f'<div class="excerpt" style="border-color:#b9c9da;background:#f3f7fb"><b>Classification</b> {badge(cat_of(t))} · basis: {E(r.get("pattern_basis") or "—")} · status: {E(st)}' + (f'<br>{E(r.get("basis", ""))}' if r.get('basis') else '') + (f'<br>Notes: {E(r["Notes"])}' if r.get('Notes') else '') + '</div>'
        page = (head(f'T{t} {label_of(t)}') + mast('', 'topics.html') + crumbs('<a href="index.html">Home</a>', '<a href="topics.html">Topics</a>', f'T{t}')
                + f'<h1>Topic {t} — {E(label_of(t))}</h1><p class="lede">Dominant work: <b>{E(r["dominant_work"])}</b> · genre mix of this topic: {E(r["genre_mix_of_topic"])}</p>' + facts + note
                + f'<h2>Keywords</h2><h3>Class-TF-IDF (uniform rule)</h3><div class="kw">{kwspan(r["ctfidf_top10"])}</div><h3>KeyBERT-style (cosine of word to topic centroid)</h3><div class="kw">{kwspan(r["keybert_top10"])}</div><h3>MMR (diversified)</h3><div class="kw">{kwspan(r["mmr_top10"])}</div><p class="lede" style="font-size:.85rem;margin-top:.6em">Amber = capitalised in ≥80 % of occurrences (probable name).</p>'
                + '<h2>Most typical chunk of each of the leading works</h2><div class="cards">' + cards + '</div>'
                + '<h2>Genre mix (chunks of this topic)</h2><div class="bars">' + gb + '</div><p class="lede" style="font-size:.85rem">This is the direction topic → genre; the share of each genre\'s text that falls in this topic is on the <a href="genre.html">Genre</a> page.</p>'
                + f'<h2>Works</h2><p>{wl}{" …" if len(works) > 15 else ""}</p>'
                + '<h2>Excerpts</h2>' + ex_html
                + f'<h2>All {len(mem)} chunks (chronological; click a header to sort)</h2><table class="sortable"><thead><tr><th>chunk</th><th>play</th><th>author</th><th class="num">published</th><th>genre</th><th class="num">words</th><th class="num">typicality</th></tr></thead><tbody>' + rows + '</tbody></table>' + foot())
        (out / tpage(t)).write_text(page, encoding='utf-8')

    # ---------------- topics index ----------------
    groups = defaultdict(list)
    for t in topics: groups[cat_of(t)].append(t)
    sec = ''
    for cat in CAT_ORDER:
        if not groups[cat]: continue
        sec += f'<h2 data-group="{cat}">{E(CAT_LABEL[cat])} <span style="font-weight:400;color:var(--faint)">· {len(groups[cat])} topics</span></h2>'
        for t in sorted(groups[cat], key=lambda t: -len(members[t])):
            r = sheet[t]; mem = members[t]
            wk = Counter(meta[c]['work_id'] for c in mem)
            best = [max((c for c in mem if meta[c]['work_id'] == w), key=lambda c: typ[c]) for w, _ in wk.most_common(3)]   # each leading work's most typical chunk
            protos = ' · '.join(f'<a href="chunks/{c}.html">{E(meta[c]["title"][:34])}</a> ({E(meta[c]["year"])}, typ. {typ[c]:.2f})' for c in best)
            srch = E(f'T{t} {label_of(t)} {r["ctfidf_top10"]} {r["dominant_work"]} {r["genre_mix_of_topic"]}')
            sec += (f'<div class="card" data-group="{cat}" data-search="{srch}"><h3><a href="{tpage(t)}">Topic {t} — {E(label_of(t))}</a></h3><div class="whence">{protos}</div>'
                    f'<div class="whence" style="margin-top:4px">{len(mem)} chunks · {r["n_works"]} works · dominant {E(r["dominant_work"][:36])} {100 * float(r["dominant_work_share"]):.0f} % · {E(r["genre_mix_of_topic"][:60])}</div>'
                    f'<div class="snip"><i>{E(r["ctfidf_top10"].replace("*", ""))}</i></div></div>')
    page = (head('Topics') + mast('', 'topics.html') + crumbs('<a href="index.html">Home</a>', 'Topics')
            + f'<h1>All topics</h1><p class="lede">{len(topics)} HDBSCAN clusters over {len(ids):,} chunks from {len(ed_chunks)} editions ({n_works} works); {sum(1 for c in ids if labels[c] == -1):,} chunks ({100 * sum(1 for c in ids if labels[c] == -1) / len(ids):.0f} %) are unassigned. '
              'Topics are grouped by how they are used: cross-work themes enter the genre comparison; single-work or single-story clusters are kept for context; pending ones await reading. Each entry links the most typical chunk of each of its three leading works (by chunk count).</p>'
            + '<input class="filterbox" type="search" placeholder="Find a topic — by number, label, keyword or dominant work…" data-target="div.card[data-group]" data-count="tcount"> <span id="tcount" style="font-size:.85rem;color:var(--muted)"></span>'
            + sec + foot())
    (out / 'topics.html').write_text(page, encoding='utf-8')

    # ---------------- genre page ----------------
    if agg.exists() and (agg / 'kruskal_by_topic.csv').exists():
        kw = list(csv.DictReader(open(agg / 'kruskal_by_topic.csv', encoding='utf-8')))
        cov = list(csv.DictReader(open(agg / 'genre_coverage.csv', encoding='utf-8')))
        for f in ('heatmap_selected_topics.png', 'heatmap_prevalence.png'):
            if (agg / f).exists(): shutil.copy(agg / f, out / f)
        gfig = ''
        for f, cap in (('genre_stacked_top20_works_renorm.png', 'Top 20 selected topics per genre, rescaled to the words those topics cover (coverage above each bar)'),
                       ('genre_panels_top20_works.png', 'The same topics per genre as bars; values are the mean share of a work\'s words')):
            if (agg / f).exists():
                shutil.copy(agg / f, out / f); gfig += f'<h2>{E(cap)}</h2><div class="fig"><a href="{f}"><img class="heat" src="{f}" alt="{E(cap)}"></a><p class="fighint">Shown fitted to the screen — click to enlarge and zoom.</p></div>'
        per_genre = [p_ for p_ in sorted(agg.glob('genre_*_top20_works.png')) if not p_.name.startswith(('genre_stacked', 'genre_panels'))]
        if per_genre:
            for p_ in per_genre: shutil.copy(p_, out / p_.name)
            gfig += '<p class="lede" style="font-size:.85rem">Per-genre bar charts: ' + ' · '.join(f'<a href="{p_.name}">{E(p_.name.split("_")[1])}</a>' for p_ in per_genre) + '</p>'
        rest_cats = [c for c in ('included', 'candidate', 'contextual_only', 'pending', 'unclassified') if c not in use_cats and any(float(r.get(f'{c} mean share of words', 0) or 0) > 0 for r in cov)]
        cat_head = {'included': 'confirmed themes (not in comparison)', 'candidate': 'candidates (not in comparison)', 'contextual_only': 'single work / story', 'pending': 'pending', 'unclassified': 'unclassified'}
        covt = ('<table><thead><tr><th>genre</th><th class="num">works</th><th class="num">in the comparison</th>' + ''.join(f'<th class="num">{E(cat_head[c])}</th>' for c in rest_cats) + '<th class="num">unassigned</th></tr></thead><tbody>'
                + ''.join(f'<tr><td>{E(r["genre_main"])}</td><td class="num">{r["n_works"]}</td><td class="num">{100 * float(r["selected topics mean share of words"]):.0f} %</td>'
                          + ''.join(f'<td class="num">{100 * float(r[f"{c} mean share of words"]):.0f} %</td>' for c in rest_cats)
                          + f'<td class="num">{100 * float(r["outlier_hdbscan mean share of words"]):.0f} %</td></tr>' for r in cov) + '</tbody></table>'
                + f'<p class="lede" style="font-size:.85rem">"In the comparison" = the {agg_cfg.get("n_selected", "selected")} topics of the categories {E(", ".join(use_cats))}; every row sums to 100 % of the genre\'s words (works equal-weighted).</p>')
        if gassign:
            nsrc = Counter(r['genre_source'] for r in gassign.values())
            ann_rows = sorted((r for r in gassign.values() if r['genre_source'] == 'annals'), key=lambda r: (r['genre_main'], r['title']))
            covt += (f'<h3>How works were placed in a genre</h3><p class="lede" style="font-size:.9rem">Rule: the British Drama label (Wiggins &amp; Richardson, via DEEP) is used when it is a single main genre ({nsrc.get("britdrama", 0)} works); '
                     f'when it is compound or missing, the Annals of English Drama label (Harbage, Schoenbaum &amp; Wagonheim, via DEEP) is used when <i>it</i> is a single main genre ({nsrc.get("annals", 0)} works; "Morality" read as moral); '
                     f'otherwise the work stays outside the single-genre comparison ({nsrc.get("none", 0)} works). Both raw labels and the source used are kept for every work (<code>genre_assignment.csv</code>) and shown on its play page.</p>')
            if ann_rows:
                covt += (f'<details><summary>Works placed by the Annals label ({len(ann_rows)})</summary><table><thead><tr><th>work</th><th class="num">year</th><th>British Drama</th><th>Annals</th><th>placed in</th></tr></thead><tbody>'
                         + ''.join(f'<tr><td>{E(r["title"][:64])}</td><td class="num">{E(r["year_first"])}</td><td>{E(r["genre_britdrama"])}</td><td>{E(r["genre_annals"])}</td><td>{E(r["genre_main"])}</td></tr>' for r in ann_rows) + '</tbody></table></details>')
        if (agg / 'other_multi_works.csv').exists():
            om = list(csv.DictReader(open(agg / 'other_multi_works.csv', encoding='utf-8')))
            n_om = sum(int(r['n_works']) for r in om); has_ann = 'annals' in (om[0] if om else {})
            covt += (f'<h3>Works outside the single-genre comparison ({n_om} works)</h3><p class="lede" style="font-size:.9rem">Kept in the corpus and on every other page, but not placed in one genre: neither British Drama nor Annals gives them a single main genre. Described here, not tested.</p>'
                     '<table><thead><tr><th>British Drama label</th><th class="num">works</th><th class="num">editions</th>' + ('<th>Annals label(s)</th>' if has_ann else '') + '<th>examples</th></tr></thead><tbody>'
                     + ''.join(f'<tr><td>{E(r["genre_deep"])}</td><td class="num">{r["n_works"]}</td><td class="num">{r["n_editions"]}</td>' + (f'<td>{E(r["annals"])}</td>' if has_ann else '') + f'<td style="font-size:.85rem;color:var(--muted)">{E(r["examples"])}</td></tr>' for r in om) + '</tbody></table>')
        def qk(r):
            q = r.get('bh_q', ''); return -1 if q == '<1e-5' else (float(q) if q else 1)
        kwt = '<table class="sortable"><thead><tr><th>topic</th><th>highest genre (mean; works with topic)</th><th>one-work</th><th>second</th><th class="num">ratio</th><th class="num">p</th><th class="num">q</th></tr></thead><tbody>' + ''.join(
            f'<tr><td><a href="{tpage(int(r["topic"]))}">T{r["topic"]} {E(r["label"][:44])}</a></td><td>{E(r["highest"])} ({100 * float(r["mean " + r["highest"]]):.2f} %; {r["highest_works_with_topic"]})</td><td>{r["single_work_driven"]}</td>'
            f'<td>{E(r["second"])} ({100 * float(r["mean " + r["second"]]):.2f} %)</td><td class="num">{r["ratio_high_second"]}</td><td class="num">{r["kruskal_p"]}</td><td class="num">{r.get("bh_q", "")}</td></tr>' for r in sorted(kw, key=qk)) + '</tbody></table>'
        page = (head('Genre') + mast('', 'genre.html').replace('<div class="wrap">', '<div class="wrap wide">') + crumbs('<a href="index.html">Home</a>', 'Genre')
                + f'<h1>Topics across genres</h1><p class="lede">Shares are of a work\'s words: chunks are aggregated to editions, editions of one work are averaged, and works enter their genre with equal weight. Every chunk stays in the denominator, so the selected topics never describe a whole genre — the rest of each genre\'s words is shown alongside. The comparison uses the topics classified as <b>{E(", ".join(use_cats))}</b>; the stacked figure below rescales those topics to 100 % of the words they cover (the coverage is printed above each bar), so its percentages are shares of the covered text, not of the genre.</p>'
                + '<h2>Coverage</h2>' + covt + gfig
                + '<h2>Mean share of a work\'s words (square-root colour scale)</h2><div class="fig"><a href="heatmap_selected_topics.png"><img class="heat" src="heatmap_selected_topics.png" alt="Mean share of a work\'s words, selected topics by genre"></a></div>'
                + '<h2>Share of works in which the topic occurs</h2><div class="fig"><a href="heatmap_prevalence.png"><img class="heat" src="heatmap_prevalence.png" alt="Share of works in which each topic occurs, by genre"></a></div>'
                + '<p class="lede" style="font-size:.85rem">Every figure is shown fitted to the screen; click one to enlarge it, then use + / − / 1:1, or click the image to switch between fit and full size (Esc closes).</p>'
                + '<h2>Kruskal–Wallis across genres (Benjamini–Hochberg q)</h2><p class="lede" style="font-size:.9rem">"one-work" = a single work holds ≥50 % of the highest genre\'s total share, so that mean is one play, not the genre. Descriptive only.</p>' + kwt + foot())
        (out / 'genre.html').write_text(page, encoding='utf-8')

    # ---------------- methods ----------------
    def kv(dct, keys): return ''.join(f'<tr><th>{E(k)}</th><td>{E(str(dct.get(k, "")))}</td></tr>' for k in keys if k in dct)
    page = (head('Methods') + mast('', 'methods.html') + crumbs('<a href="index.html">Home</a>', 'Methods') + '<h1>Methods</h1>'
            + '<h2>Corpus</h2><p>The English performance-language view of corpus v3 (EEBO-TCP texts, DEEP metadata, 580 edition documents): the language presented as spoken, sung or recited in performance — speeches, choruses, songs, and reviewed prologues, epilogues and inductions attributed to their edition, whether encoded in the body, front or back matter. Selection combines structural XML rules with recorded contextual decisions (the corpus repository\'s decision tables). Speaker labels, encoded stage directions, notes, headings and running titles are removed at extraction; book-level dedications and plot summaries are excluded. '
              'Spelling: a second view applies EarlyPrint\'s <code>reg</code> token by token where a node could be aligned to EarlyPrint (99.5 % of nodes paired; accepted <code>reg</code> values at 19 % of token positions); unaligned nodes keep the extracted text with only long <i>s</i> and word-initial <i>VV</i> normalized. EarlyPrint can supply corrected readings where its transcription has them, but the pairing does not establish that every <code>&lt;gap&gt;</code> was restored. The unregularized text is shown on each chunk page for comparison.</p>'
            + '<h2>Chunking</h2><table>' + kv(chunk_info, ['docs', 'chunks', 'rule', 'words_median', 'words_p10', 'words_p90', 'long_nodes_split', 'long_nodes_unsplit', 'short_docs', 'tokenizer', 'tokens_median', 'tokens_max']) + '</table>'
            + '<h2>Embedding</h2><table>' + kv(emb_info, ['model', 'revision', 'max_seq_length', 'batch_size', 'n_chunks', 'dim', 'device']) + '</table>'
            + '<h2>Clustering</h2><p>UMAP to 5 dimensions (n_neighbors 15, min_dist 0.05, cosine) → HDBSCAN (min_cluster_size 30, Euclidean, EOM). Three seeds were run; this site shows seed %d and reports each chunk\'s topic in the other seeds on its page.</p><table>' % a.seed + kv(run_info, ['n_chunks', 'n_topics', 'outlier_share', 'hdbscan_clusters', 'seed']) + '</table>'
            + '<h2>Keywords and labels</h2><p>Class-TF-IDF (BERTopic\'s <code>ClassTfidfTransformer</code>, default settings) on one document per topic with a uniform vectorizer (min_df 1, max_df 1.0, alphabetic tokens, a stop-list including early-modern function-word spellings); KeyBERT-style words rank the same candidates by cosine to the topic centroid with the embedding model; MMR diversifies them (λ 0.5). Words capitalised in ≥80 % of their occurrences are marked as probable names. Labels are written by the researcher from the keywords and the chunks; AI drafts are marked as such until confirmed.</p>'
            + '<h2>Typicality</h2><p>Cosine similarity between a chunk\'s embedding and the mean embedding of its topic. Unassigned chunks show their nearest topic instead.</p>'
            + '<h2>Genre comparison</h2><p>Chunk → edition → work → genre, word-weighted, editions of a work averaged, works equal-weighted; only topics classified as cross-work themes enter the comparison, and the share of each genre\'s words that falls outside them is reported. Kruskal–Wallis across genres with ≥10 works, Benjamini–Hochberg over the selected topics; descriptive.</p>'
            + ('<p>Genre of a work: the British Drama label (Wiggins &amp; Richardson, via DEEP) when it is a single main genre; when it is compound or missing, the Annals of English Drama label (Harbage, Schoenbaum &amp; Wagonheim, via DEEP) when that is a single main genre; otherwise the work is described but not placed in a genre. Both labels and the source used are recorded for every work (see the Genre page and each play page).</p>' if agg_cfg.get('n_by_genre_source', {}).get('annals') else '')
            + '<h2>Map</h2><p>The chunk map is a separate 2-D UMAP of the embeddings (same neighbourhood settings) for viewing only; colours are the seed-%d topics.</p>' % a.seed + foot())
    (out / 'methods.html').write_text(page, encoding='utf-8')

    # ---------------- map ----------------
    if not a.no_map:
        cmd = [sys.executable, str(code_dir / '12_map.py'), '--chunks', str(ch), '--runs', str(runs), '--seed', str(a.seed), '--variant', a.variant,
               '--out', str(out / '_map_fragment.html'), '--chunk-url', 'chunks/{id}.html', '--embed']
        if a.deep: cmd += ['--manifest', a.manifest, '--deep', a.deep]
        subprocess.run(cmd, check=True)
        frag = (out / '_map_fragment.html').read_text(encoding='utf-8'); (out / '_map_fragment.html').unlink()
        page = head('Map') + mast('', 'map.html').replace('<div class="wrap">', '<div class="wrap wide">') + frag + foot()
        (out / 'map.html').write_text(page, encoding='utf-8')

    # ---------------- landing ----------------
    n_out = sum(1 for c in ids if labels[c] == -1)
    n_cmp = sum(len(groups[c]) for c in use_cats); n_inc = len(groups['included']); n_cand = len(groups['candidate'])
    page = (head('Home') + mast('', 'index.html')
            + f'<h1>{E(a.title)}</h1><p class="lede">A topic map of early modern English drama, built from ~500-word chunks of every play in the corpus: what each stretch of a play is about, which of those concerns recur across works, and how they are distributed across genres. Every number on the site leads back to the chunks it was computed from.</p>'
            + f'<div class="facts"><div class="f"><b>{len(ids):,}</b><i>chunks</i></div>' + (f'<div class="f"><b>{n_fit:,}</b><i>in the model (one edition per work); {n_placed:,} placed from other editions</i></div>' if n_placed else '') + f'<div class="f"><b>{len(ed_chunks)}</b><i>editions</i></div><div class="f"><b>{n_works}</b><i>works</i></div><div class="f"><b>{len(topics)}</b><i>topics</i></div><div class="f"><b>{n_cmp}</b><i>in the genre comparison ({E(", ".join(use_cats))})</i></div><div class="f"><b>{n_inc} / {n_cand}</b><i>confirmed / candidate themes</i></div><div class="f"><b>{min(years)}–{max(years)}</b><i>publication years</i></div></div>'
            + '<div class="cards">'
            + ('<div class="card"><h3><a href="map.html">Interactive map</a></h3><div class="whence">Every chunk as a point, coloured by topic; filter by genre, publication decade, author, title, play type, company or theater (filters combine); click a point for its page.</div></div>' if not a.no_map else '')
            + '<div class="card"><h3><a href="plays.html">Plays</a></h3><div class="whence">Every edition with its chunks in order, topic composition, DEEP metadata and other editions of the same work; searchable.</div></div>'
            + '<div class="card"><h3><a href="topics.html">Topics</a></h3><div class="whence">All clusters with keywords, works, typical chunks and full rosters — grouped into cross-work themes, single-work clusters and pending ones.</div></div>'
            + ('<div class="card"><h3><a href="genre.html">Genre</a></h3><div class="whence">How the cross-work themes are distributed across comedy, tragedy, history, tragicomedy, moral, romance, pastoral and masque.</div></div>' if (out / 'genre.html').exists() else '')
            + '<div class="card"><h3><a href="methods.html">Methods</a></h3><div class="whence">Corpus, chunking, embedding model, clustering, keywords, typicality and aggregation — with the parameters actually used.</div></div></div>'
            + '<h2>What a topic page shows</h2><p>The three keyword lists, the size of the cluster and how far it is concentrated in one work, its genre mix, the most typical chunk of each leading work, keyword-highlighted excerpts, and a sortable roster of every member chunk with its typicality.</p>'
            + '<h2>What a chunk page shows</h2><p>The play, author, publication year and Annals performance date, company and theater where DEEP records them, the topic with its typicality, then the full regularized text with the topic\'s distinguishing words marked and links to the previous and next chunk; the metadata table (edition, TCP and DEEP ids, node positions, topic in the other seeds) and the original spelling are folded below it.</p>'
            + f'<h2>How to read the numbers</h2><p>{n_out:,} chunks ({100 * n_out / len(ids):.0f} %) are unassigned by HDBSCAN; they are counted in every denominator and never deleted. Roughly two thirds of the clusters gather the chunks of a single play or a single story; they are shown but kept out of the genre comparison, which uses only themes that recur across works.</p>' + foot())
    (out / 'index.html').write_text(page, encoding='utf-8')
    total = sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
    print(f'site → {out}: {n_pages} chunk pages, {len(ed_chunks)} play pages, {len(topics)} topic pages; {total / 1e6:.0f} MB')


if __name__ == '__main__':
    main()
