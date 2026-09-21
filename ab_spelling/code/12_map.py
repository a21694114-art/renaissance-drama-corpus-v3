#!/usr/bin/env python3
"""12_map.py — chunk-level interactive map (one point = one chunk), in the style of the
character-clustering site: one trace per topic (legend click = hide, double-click = isolate),
hover with the chunk's play / author / dates / genre / play type / company / theater / topic /
keywords / opening words, and dropdown menus that highlight one genre, decade, author, title,
play type, company, theater or topic category at a time (everything else fades).

  python 12_map.py --chunks <chunks dir> --runs <runs dir> --seed 42 \
        [--manifest build_v3/corpus_manifest.csv --deep <DEEP_data.csv>] [--out <html>]

Coordinates: a 2-D UMAP of the chunk embeddings (n_neighbors 15, min_dist 0.05, cosine,
random_state = seed), computed once and cached as topics_B_s<seed>/umap2.npy.  The clustering
itself was done on the 5-D UMAP (03_topics.py); the 2-D map is for looking only.
DEEP fields (optional, joined on the manifest's edition_id_effective = DEEP edition_id):
date_first_performance, company_first_performance_brit_display, theater, theater_type.
Plotly.js is inlined from the installed plotly package (falls back to the CDN).
"""
import argparse, csv, html, json, re
from collections import defaultdict
from pathlib import Path
import numpy as np

AXES = [('genre', 'Genre'), ('decade', 'Decade'), ('author', 'Author'), ('title', 'Title'), ('play_type', 'Play type'),
        ('company', 'Company'), ('theater', 'Theater'), ('cat', 'Topic category')]
PALETTE = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
           '#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3', '#fdb462', '#b3de69', '#fccde5', '#d9d9d9', '#bc80bd', '#ccebc5', '#ffed6f',
           '#2E91E5', '#E15F99', '#1CA71C', '#FB0D0D', '#DA16FF', '#222A2A', '#B68100', '#750D86', '#EB663B', '#511CFB', '#00A08B', '#FB00D1',
           '#FC0080', '#B2828D', '#6C7C32', '#778AAE', '#862A16', '#A777F1', '#620042', '#1616A7', '#DA60CA', '#6C4516', '#0D2A63', '#AF0038']


def facets(v, kind=None):
    """Split multi-valued metadata ('Adult Professional;Professional', 'Fletcher, John; Massinger, Philip')."""
    if not v or str(v).strip().lower() in ('', 'nan', 'none', 'n/a', 'not in britdrama'):
        return []
    if kind == 'author':
        parts = re.split(r';\s*|(?<=[a-z])(?=[A-Z][a-z]+, )', str(v))
    else:
        parts = re.split(r';\s*', str(v))
    return [p.strip() for p in parts if p and p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--manifest', default=''); ap.add_argument('--deep', default='')
    ap.add_argument('--snippet', type=int, default=220); ap.add_argument('--out', default='')
    ap.add_argument('--chunk-url', default='', help="URL template opened on click, e.g. chunks/{id}.html (site mode)")
    ap.add_argument('--embed', action='store_true', help='page fragment for embedding in the site (no <html> wrapper, shorter title)')
    ap.add_argument('--point-size', type=float, default=3.5, help='marker size in px for assigned chunks (unassigned slightly smaller)')
    ap.add_argument('--selected-size', type=float, default=0.0,
                    help='marker size in px for chunks highlighted by the dropdown (default: same as --point-size; they stand out by opacity, not size)')
    a = ap.parse_args()
    sel_size = a.selected_size if a.selected_size > 0 else a.point_size
    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'
    out = Path(a.out) if a.out else d / f'chunk_map_s{a.seed}.html'

    ids = [r['chunk_id'] for r in csv.DictReader(open(runs / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
    labels = {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8'))}
    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    cmap = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_map.csv', encoding='utf-8'))}
    sheet = {int(r['topic']): r for r in csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8'))}
    snippets = {}
    with open(ch / f'chunks_{a.variant}.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            snippets[r['chunk_id']] = r['text'][:a.snippet].rsplit(' ', 1)[0] + '…'
    deep = {}
    if a.deep and a.manifest:
        dd = {r['edition_id']: r for r in csv.DictReader(open(a.deep, encoding='utf-8-sig'))}
        for m in csv.DictReader(open(a.manifest, encoding='utf-8')):
            r = dd.get(m['edition_id_effective'])
            if r:
                deep[m['edition_id_effective']] = {'perf': r.get('date_first_performance', ''), 'company': r.get('company_first_performance_brit_display', '') or r.get('company_first_performance_annals_display', ''),
                                                   'theater': r.get('theater', ''), 'theater_type': r.get('theater_type', '')}

    # 2-D UMAP (cached)
    u2 = d / 'umap2.npy'
    if u2.exists():
        XY = np.load(u2)
    else:
        from umap import UMAP
        emb = np.load(runs / f'embeddings_{a.variant}.npy')
        print(f'UMAP 2-D on {emb.shape} …', flush=True)
        XY = UMAP(n_components=2, n_neighbors=15, min_dist=0.05, metric='cosine', random_state=a.seed).fit_transform(emb).astype(np.float32)
        np.save(u2, XY)
    assert XY.shape[0] == len(ids)

    def tlabel(t):
        if t == -1: return '-1: unassigned'
        r = sheet.get(t, {}); return f'{t}: {r.get("Label") or r.get("draft_label") or "topic"}'
    def clean(v):
        v = (v or '').strip(); return '' if v.lower() in ('none', 'n/a', 'nan') else v
    rows = []
    for i, c in enumerate(ids):
        m = meta[c]; t = labels[c]; r = sheet.get(t, {}); dp = deep.get(m['edition_id'], {})
        year = m['year']; decade = f'{int(year) // 10 * 10}s' if year.isdigit() else 'unknown'
        rows.append({'i': i, 'id': c, 'topic': t, 'tl': tlabel(t), 'cat': (r.get('use_in_genre_analysis') or ('unassigned' if t == -1 else 'unclassified')),
                     'title': m['title'], 'author': m['author'], 'year': year, 'decade': decade, 'genre': m['genre_deep'], 'play_type': m['play_type_deep'],
                     'company': clean(dp.get('company', '')), 'theater': clean(dp.get('theater', '')), 'theater_type': clean(dp.get('theater_type', '')),
                     'perf': clean(dp.get('perf', '')), 'tcp': m['tcp'], 'edition': m['edition_id'], 'nodes': f'{cmap[c]["node_start"]}–{cmap[c]["node_end"]}',
                     'words': cmap[c]['len_B_words'], 'kw': (r.get('ctfidf_top10') or '').replace('*', ''), 'snip': snippets.get(c, '')})
    def hover(x):
        """Reading-oriented hover: title / author / genre · company · theater / dates (publication vs first
        performance kept apart, DEEP ranges preserved) / topic / passage preview.  Tracing details (chunk id,
        nodes, TCP, play type, keywords) live on the chunk page."""
        h = html.escape
        theater_short = x['theater'].split(';')[0].strip() if x['theater'] else ''
        line3 = ' · '.join(v for v in (h(x['genre']), h(x['company']), h(theater_short)) if v)
        dates = f'Published {h(x["year"])}' + (f' · First performed (or written) {h(x["perf"])}' if x['perf'] else '')
        topic_line = f'<b>Topic {h(x["tl"])}</b>' if x['topic'] != -1 else '<b>Topic: unassigned</b> (no cluster)'
        parts = [f'<b>{h(x["title"])}</b>', h(x['author']), line3, dates, topic_line, '',
                 f'<i>Passage: {x["words"]} words · preview</i>',
                 '<br>'.join(h(x['snip'][k:k + 88]) for k in range(0, len(x['snip']), 88))]
        if a.chunk_url:
            parts += ['', '<i>Click to read the full passage.</i>']
        return '<br>'.join(parts)

    # traces: one per topic, unassigned first (drawn underneath)
    topics_sorted = sorted({x['topic'] for x in rows}, key=lambda t: (t != -1, t))
    traces = []; pos = {}
    for k, t in enumerate(topics_sorted):
        mem = [x for x in rows if x['topic'] == t]
        for j, x in enumerate(mem): pos[x['i']] = (k, j)
        col = '#d0d0d0' if t == -1 else PALETTE[(t) % len(PALETTE)]
        traces.append({'type': 'scattergl', 'mode': 'markers', 'name': tlabel(t)[:60], 'x': [float(XY[x['i'], 0]) for x in mem], 'y': [float(XY[x['i'], 1]) for x in mem],
                       'marker': {'size': a.point_size * (0.85 if t == -1 else 1), 'opacity': 0.35 if t == -1 else 0.8, 'color': col},
                       'selected': {'marker': {'size': sel_size, 'opacity': 1.0}}, 'unselected': {'marker': {'size': a.point_size * 0.7, 'opacity': 0.08}},
                       'hovertext': [hover(x) for x in mem], 'hoverinfo': 'text', 'customdata': [x['id'] for x in mem]})
    n_tr = len(traces)
    # dropdown menus
    menus = []
    for col, label in AXES:
        fac = defaultdict(list)
        for x in rows:
            for fv in (facets(x[col], 'author' if col == 'author' else None) if col not in ('decade', 'cat') else [x[col]]):
                fac[fv].append(x['i'])
        if not fac: continue
        keys = sorted(fac, key=(lambda v: (v == 'unknown', v)) if col == 'decade' else (lambda v: v.lower()))
        buttons = [{'label': f'All ({label})', 'method': 'restyle', 'args': [{'selectedpoints': [None] * n_tr}, list(range(n_tr))]}]
        for v in keys:
            per = [[] for _ in range(n_tr)]
            for i in fac[v]:
                k, j = pos[i]; per[k].append(j)
            buttons.append({'label': f'{v[:52]} ({len(fac[v])})', 'method': 'restyle', 'args': [{'selectedpoints': per}, list(range(n_tr))]})
        menus.append({'buttons': buttons, 'direction': 'down', 'showactive': True, 'x': 0, 'xanchor': 'left', 'y': 1, 'yanchor': 'bottom', 'bgcolor': 'white', 'bordercolor': '#ccc', 'font': {'size': 11}})
    nax = len(menus)
    for i, m in enumerate(menus): m['x'] = i * (0.94 / max(nax - 1, 1))
    layout = {'title': {'text': f'Chunks by topic — {runs.name}, seed {a.seed} · {len(rows):,} chunks · {len(topics_sorted) - 1} topics', 'x': 0.5, 'y': 0.99, 'font': {'size': 16}},
              'xaxis': {'visible': False}, 'yaxis': {'visible': False}, 'hovermode': 'closest', 'hoverlabel': {'align': 'left', 'font': {'size': 11}, 'bgcolor': 'white'},
              'legend': {'title': {'text': 'Topic<br><span style="font-size:11px;color:#888">click: hide · double-click: isolate</span>'}, 'itemsizing': 'constant', 'x': 1.01, 'y': 1, 'font': {'size': 10}},
              'updatemenus': menus, 'margin': {'l': 20, 'r': 20, 't': 110, 'b': 20}, 'paper_bgcolor': 'white', 'plot_bgcolor': 'white', 'height': 960}
    try:
        from plotly.offline import get_plotlyjs
        script = '<script>' + get_plotlyjs() + '</script>'
    except Exception:
        script = '<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>'
    note = (f'Each point is one ~500-word chunk; position = 2-D UMAP of its embedding (for viewing only — the clustering used the 5-D UMAP). Colour = topic (seed {a.seed}); grey = unassigned by HDBSCAN. '
            'Dropdowns highlight one genre, decade, author, title, play type, company, theater or topic category; the legend hides (click) or isolates (double-click) a topic. '
            'Company / theater / first-performance dates are from DEEP where recorded.' + (' <b>Click a point to open the chunk\'s page.</b>' if a.chunk_url else ''))
    body = f'''<div id="note">{note}</div><div id="map"></div>
<script>window.CHUNK_URL={json.dumps(a.chunk_url)};const T={json.dumps(traces)};const L={json.dumps(layout)};Plotly.newPlot('map',T,L,{{responsive:true,displaylogo:false}});
document.getElementById('map').on('plotly_click',e=>{{const id=e.points[0].customdata;if(window.CHUNK_URL)window.open(window.CHUNK_URL.replace('{{id}}',id),'_self');}});</script>'''
    if a.embed:
        page = script + body
    else:
        page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Chunk map — seed {a.seed}</title>{script}
<style>body{{margin:0;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif}} #note{{font-size:12px;color:#666;padding:6px 16px}}</style></head><body>{body}</body></html>'''
    out.write_text(page, encoding='utf-8')
    print(f'{len(rows)} chunks, {n_tr} traces, {nax} dropdowns → {out} ({out.stat().st_size // 1024 // 1024} MB)')


if __name__ == '__main__':
    main()
