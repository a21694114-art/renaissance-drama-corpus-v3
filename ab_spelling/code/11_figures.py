#!/usr/bin/env python3
"""11_figures.py — one self-contained interactive HTML page for a topic run (Plotly.js inlined from
the installed plotly package, data inlined; needs numpy, plotly optional).

  python 11_figures.py --chunks <chunks dir> --runs <runs dir> --seed 42 [--out <html>]

Reads what 08_topic_sheet.py and 09_aggregate.py already wrote (topic_sheet.csv, aggregate/*.csv),
plus doc_topics.csv and embeddings_B.npy for the topic map.  Four views:
  1. Topic map — every topic as a bubble (size = chunks) on a 2-D classical-MDS projection of the
     topic centroids (cosine distances of the mean embeddings); colour = use category; hover shows
     label, keywords, works; clicking a bubble draws its keyword bars (class-TF-IDF / KeyBERT / MMR).
  2. Genre × topic — heatmap of the selected topics: mean share of a work's words, or share of
     works in which the topic occurs; hover gives mean, median, works-with-topic, Kruskal p / BH q.
  3. Works — pick a work: its topic composition (selected topics + the other categories), with
     the genre mean of each topic beside it.
  4. Table — all topics with size, works, concentration, category, keywords (sortable, filterable).
"""
import argparse, csv, json, html
from collections import defaultdict
from pathlib import Path
import numpy as np


def mds2d(D):
    """Classical MDS of a distance matrix to 2 dimensions."""
    n = D.shape[0]; J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    w, v = np.linalg.eigh(B)
    idx = np.argsort(w)[::-1][:2]
    return v[:, idx] * np.sqrt(np.maximum(w[idx], 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--runs', required=True)
    ap.add_argument('--seed', type=int, default=42); ap.add_argument('--variant', default='B')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    runs = Path(a.runs); ch = Path(a.chunks); d = runs / f'topics_{a.variant}_s{a.seed}'; agg = d / 'aggregate'
    out = Path(a.out) if a.out else d / f'topics_interactive_s{a.seed}.html'

    sheet = list(csv.DictReader(open(d / 'topic_sheet.csv', encoding='utf-8')))
    labels = {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(d / 'doc_topics.csv', encoding='utf-8'))}
    ids = [r['chunk_id'] for r in csv.DictReader(open(runs / f'embedding_ids_{a.variant}.csv', encoding='utf-8'))]
    emb = np.load(runs / f'embeddings_{a.variant}.npy').astype(np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9
    row_of = {c: i for i, c in enumerate(ids)}
    members = defaultdict(list)
    for c, t in labels.items():
        if t != -1: members[t].append(row_of[c])
    topics = [int(r['topic']) for r in sheet]
    C = np.stack([emb[members[t]].mean(axis=0) for t in topics]); C /= np.linalg.norm(C, axis=1, keepdims=True) + 1e-9
    D = np.sqrt(np.maximum(2 - 2 * (C @ C.T), 0))
    XY = mds2d(D)

    n_chunks = len(labels); n_out = sum(1 for t in labels.values() if t == -1)
    def name(r): return r['Label'] or r['draft_label'] or f'topic {r["topic"]}'
    def cat(r): return r['use_in_genre_analysis'] or 'unclassified'
    tdata = []
    for i, r in enumerate(sheet):
        tdata.append({'topic': int(r['topic']), 'label': name(r), 'cat': cat(r), 'status': r['review_status'], 'size': int(r['size']), 'words': int(r['words']),
                      'n_works': int(r['n_works']), 'n_works_ge3': int(r['n_works_ge3']), 'dom_work': r['dominant_work'], 'dom_share': float(r['dominant_work_share']),
                      'top3': float(r['top3_work_share']), 'top_works': r['top_works'], 'genre_mix': r['genre_mix_of_topic'], 'basis': r['pattern_basis'],
                      'ctfidf': r['ctfidf_top10'], 'keybert': r['keybert_top10'], 'mmr': r['mmr_top10'], 'names': r['names_in_top30'],
                      'x': float(XY[i, 0]), 'y': float(XY[i, 1])})

    # genre × topic
    gm = list(csv.DictReader(open(agg / 'genre_topic_mean.csv', encoding='utf-8')))
    kw = {int(r['topic']): r for r in csv.DictReader(open(agg / 'kruskal_by_topic.csv', encoding='utf-8'))} if (agg / 'kruskal_by_topic.csv').exists() else {}
    cov = {r['genre_main']: r for r in csv.DictReader(open(agg / 'genre_coverage.csv', encoding='utf-8'))}
    selected = sorted(kw) if kw else sorted(t['topic'] for t in tdata if t['cat'] in ('included', 'candidate'))
    genres = [r['genre_main'] for r in gm if r['genre_main'] != 'other/multi']
    gdata = {'genres': genres, 'n_works': {r['genre_main']: int(r['n_works']) for r in gm}, 'topics': selected,
             'mean': [[float(next(x for x in gm if x['genre_main'] == g)[f't{t} mean']) * 100 for g in genres] for t in selected],
             'median': [[float(next(x for x in gm if x['genre_main'] == g)[f't{t} median']) * 100 for g in genres] for t in selected],
             'works': [[int(next(x for x in gm if x['genre_main'] == g)[f't{t} works>0']) for g in genres] for t in selected],
             'p': {t: kw[t].get('kruskal_p', '') for t in selected if t in kw}, 'q': {t: kw[t].get('bh_q', '') for t in selected if t in kw},
             'coverage': {g: {k: float(v) for k, v in cov[g].items() if k not in ('genre_main', 'n_works')} for g in cov}}

    # works
    wrows = list(csv.DictReader(open(agg / 'work_topic_share.csv', encoding='utf-8')))
    cats = ['included', 'candidate', 'contextual_only', 'pending', 'outlier_hdbscan']
    wdata = [{'work_id': r['work_id'], 'title': r['title'], 'author': r['author'], 'year': r['year_first'], 'genre': r['genre_main'], 'genre_raw': r['genre_deep'],
              'play_type': r['play_type_main'], 'n_ed': int(r['n_editions']), 'words': int(r['words_mean']),
              'shares': {str(t): round(float(r[f't{t}']) * 100, 2) for t in selected if float(r[f't{t}']) > 0},
              'cats': {c: round(float(r[f'cat:{c}']) * 100, 1) for c in cats}} for r in wrows]
    genre_mean = {str(t): {g: gdata['mean'][i][j] for j, g in enumerate(genres)} for i, t in enumerate(selected)}

    payload = {'seed': a.seed, 'run': runs.name, 'n_chunks': n_chunks, 'n_outliers': n_out, 'topics': tdata, 'genre': gdata, 'works': wdata, 'genre_mean': genre_mean}
    # plotly.js: inline it from the installed plotly package so the file works offline and in
    # sandboxed previews (≈4.5 MB); fall back to the CDN only if plotly is not installed
    try:
        from plotly.offline import get_plotlyjs
        script = '<script>' + get_plotlyjs() + '</script>'
    except Exception:
        script = '<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>'
    page = (TEMPLATE.replace('__PLOTLY__', script).replace('__DATA__', json.dumps(payload, ensure_ascii=False))
            .replace('__TITLE__', html.escape(f'Topics — {runs.name}, seed {a.seed}')))
    out.write_text(page, encoding='utf-8')
    print(f'{len(tdata)} topics, {len(selected)} selected, {len(wdata)} works → {out} ({out.stat().st_size // 1024} KB)')


TEMPLATE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
__PLOTLY__
<style>
:root{--bg:#fbfaf7;--fg:#1f1d1a;--muted:#6b665e;--line:#e4e0d8;--panel:#ffffff;--accent:#2b5c8a;--c1:#2b5c8a;--c2:#b8862b;--c3:#8a8a8a;--c4:#c2553d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
header{padding:14px 20px 8px;border-bottom:1px solid var(--line)}header h1{margin:0;font-size:17px;font-weight:600}header p{margin:4px 0 0;color:var(--muted);font-size:12.5px}
nav{display:flex;gap:4px;padding:8px 20px 0;border-bottom:1px solid var(--line)}nav button{background:none;border:0;border-bottom:2px solid transparent;padding:8px 10px;font-size:13.5px;color:var(--muted);cursor:pointer}
nav button.on{color:var(--fg);border-bottom-color:var(--accent);font-weight:600}
section{display:none;padding:14px 20px}section.on{display:block}
.row{display:flex;gap:16px;flex-wrap:wrap}.panel{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:10px}
.small{font-size:12.5px;color:var(--muted)}label{font-size:12.5px;color:var(--muted);margin-right:10px}select,input{font:inherit;padding:4px 6px;border:1px solid var(--line);border-radius:4px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:12.5px}th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}th{cursor:pointer;background:#f3f0ea;position:sticky;top:0}
td.num,th.num{text-align:right}.tag{display:inline-block;padding:1px 6px;border-radius:10px;font-size:11px;color:#fff}
.tag.candidate,.tag.included{background:var(--c1)}.tag.contextual_only{background:var(--c2)}.tag.pending{background:var(--c3)}.tag.unclassified{background:var(--c4)}
#kw{min-width:360px;flex:1}#map{flex:2;min-width:520px}
</style></head><body>
<header><h1>__TITLE__</h1><p id="sub"></p></header>
<nav><button data-s="s1" class="on">Topic map</button><button data-s="s2">Genre × topic</button><button data-s="s3">Works</button><button data-s="s4">Table</button></nav>
<section id="s1" class="on"><div class="row"><div id="map" class="panel"></div><div id="kw" class="panel"><div class="small">Click a bubble to see its keywords. Bubble size = chunks; position = classical MDS of centroid cosine distances (nearby bubbles have similar text). Colour = use category: blue candidate/included, amber contextual (single work / story), grey pending.</div><div id="kwplot"></div><div id="kwinfo" class="small"></div></div></div></section>
<section id="s2"><div class="panel"><label>value <select id="gmode"><option value="mean">mean share of a work's words (%)</option><option value="median">median share (%)</option><option value="works">share of works with the topic (%)</option></select></label><span class="small">Works equal-weighted; editions averaged; all chunks in the denominator. Hover for median, works-with-topic and Kruskal–Wallis p / BH q. Rows sorted by their maximum.</span><div id="heat"></div><div id="covtab" class="small"></div></div></section>
<section id="s3"><div class="panel"><label>genre <select id="wgenre"></select></label><label>work <select id="wsel"></select></label><span id="winfo" class="small"></span><div id="wplot"></div><div class="small">Bars: share of this work's words in each selected topic (dark) next to the mean of its genre (light). Right: the work's words by category.</div></div></section>
<section id="s4"><div class="panel"><label>filter <input id="tfilter" placeholder="label, keyword, work…"></label><span class="small">click a header to sort</span><div style="max-height:70vh;overflow:auto"><table id="ttab"></table></div></div></section>
<script>
const D = __DATA__;
const COL = {included:'#2b5c8a', candidate:'#2b5c8a', contextual_only:'#b8862b', pending:'#8a8a8a', unclassified:'#c2553d'};
document.getElementById('sub').textContent = `${D.n_chunks.toLocaleString()} chunks · ${D.topics.length} topics · ${D.n_outliers.toLocaleString()} unassigned (${(100*D.n_outliers/D.n_chunks).toFixed(1)} %) · ${D.works.length} works · selected for genre comparison: ${D.genre.topics.length} topics`;
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.remove('on'));b.classList.add('on');document.querySelectorAll('section').forEach(s=>s.classList.toggle('on',s.id===b.dataset.s));window.dispatchEvent(new Event('resize'));});
const base = {paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'-apple-system,Segoe UI,Helvetica,Arial',size:12,color:'#1f1d1a'},margin:{l:40,r:20,t:30,b:40}};
// 1 topic map
const T = D.topics;
const trace = {x:T.map(t=>t.x), y:T.map(t=>t.y), mode:'markers+text', type:'scatter', text:T.map(t=>'T'+t.topic), textposition:'middle center', textfont:{size:9,color:'#fff'},
  marker:{size:T.map(t=>6+2.2*Math.sqrt(t.size)), color:T.map(t=>COL[t.cat]||COL.unclassified), opacity:0.85, line:{color:'#fff',width:1}},
  customdata:T.map(t=>[t.label,t.size,t.n_works,t.dom_work,(100*t.dom_share).toFixed(0),t.ctfidf,t.cat]),
  hovertemplate:'<b>T%{text} · %{customdata[0]}</b><br>%{customdata[1]} chunks · %{customdata[2]} works · dominant: %{customdata[3]} (%{customdata[4]} %)<br>%{customdata[5]}<br><i>%{customdata[6]}</i><extra></extra>'};
Plotly.newPlot('map',[trace],{...base,height:620,xaxis:{visible:false},yaxis:{visible:false},showlegend:false,hoverlabel:{align:'left'}},{responsive:true,displaylogo:false});
function kwbars(t){const parse=s=>s.split(',').map(x=>x.trim()).filter(Boolean);const lists=[['class-TF-IDF (uniform rule)',parse(t.ctfidf)],['KeyBERT-style (cosine to centroid)',parse(t.keybert)],['MMR (diversified)',parse(t.mmr)]];
  const host=document.getElementById('kwplot'); host.innerHTML='';
  lists.forEach(([n,ws],i)=>{const div=document.createElement('div');div.id='kwp'+i;host.appendChild(div);
    if(!ws.length){div.innerHTML=`<div class="small" style="padding:6px 0">${n}: —</div>`;return;}
    Plotly.newPlot(div,[{type:'bar',orientation:'h',x:ws.map((w,j)=>ws.length-j),y:ws,marker:{color:ws.map(w=>w.startsWith('*')?'#b8862b':'#2b5c8a')},hovertemplate:'%{y}<extra></extra>'}],
      {...base,height:30+20*ws.length,title:{text:n,font:{size:12},x:0,xanchor:'left'},margin:{l:110,r:10,t:26,b:6},xaxis:{visible:false},yaxis:{autorange:'reversed',automargin:true,tickfont:{size:11}}},{displaylogo:false,responsive:true,staticPlot:true});});
  document.getElementById('kwinfo').innerHTML=`<b>T${t.topic} · ${t.label}</b> <span class="tag ${t.cat}">${t.cat}</span><br>${t.size} chunks (${t.words.toLocaleString()} words) · ${t.n_works} works (${t.n_works_ge3} with ≥3 chunks) · dominant work ${t.dom_work} ${(100*t.dom_share).toFixed(0)} % · top-3 works ${(100*t.top3).toFixed(0)} %<br>works: ${t.top_works}<br>genre mix of topic: ${t.genre_mix}<br>basis: ${t.basis||'—'} · names in top-30: ${t.names||'—'}<br><i>* = capitalised in ≥80 % of occurrences (probable name); amber bars = probable names</i>`;}
document.getElementById('map').on('plotly_click',e=>kwbars(T[e.points[0].pointNumber]));
kwbars(T[0]);
// 2 genre heatmap
const G=D.genre; const tl=Object.fromEntries(T.map(t=>[t.topic,t.label]));
function heat(){const mode=document.getElementById('gmode').value; const M=mode==='works'?G.works.map((r,i)=>r.map((v,j)=>100*v/G.n_works[G.genres[j]])):G[mode];
  const order=[...M.keys()].sort((a,b)=>Math.max(...M[b])-Math.max(...M[a]));
  const z=order.map(i=>M[i]), y=order.map(i=>`T${G.topics[i]}  ${tl[G.topics[i]].slice(0,46)}`);
  const cd=order.map(i=>G.genres.map((g,j)=>[G.mean[i][j].toFixed(2),G.median[i][j].toFixed(2),G.works[i][j],G.n_works[g],G.p[G.topics[i]]||'',G.q[G.topics[i]]||'']));
  const zmax=Math.max(...z.flat()); const zs=z.map(r=>r.map(v=>Math.sqrt(v/zmax)));
  Plotly.react('heat',[{type:'heatmap',z:zs,x:G.genres.map(g=>`${g} (n=${G.n_works[g]})`),y:y,customdata:cd,colorscale:[[0,'#f7f9fc'],[1,'#1a3f6b']],showscale:false,
    text:z.map(r=>r.map(v=>v>=0.05?(mode==='works'?v.toFixed(0):v.toFixed(1)):'')),texttemplate:'%{text}',textfont:{size:10},xgap:2,ygap:2,
    hovertemplate:'<b>%{y}</b><br>%{x}<br>mean %{customdata[0]} % · median %{customdata[1]} % · works with topic %{customdata[2]}/%{customdata[3]}<br>Kruskal p %{customdata[4]} · BH q %{customdata[5]}<extra></extra>'}],
    {...base,height:Math.max(420,22*y.length+120),margin:{l:330,r:20,t:20,b:60},yaxis:{autorange:'reversed',tickfont:{size:11}},xaxis:{side:'bottom'}},{displaylogo:false,responsive:true});}
document.getElementById('gmode').onchange=heat; heat();
const cv=G.coverage; document.getElementById('covtab').innerHTML='<b>Where the rest of each genre\'s words are:</b> '+Object.keys(cv).map(g=>`${g}: selected ${(100*cv[g]['selected topics mean share of words']).toFixed(0)} %, contextual ${(100*cv[g]['contextual_only mean share of words']).toFixed(0)} %, pending ${(100*cv[g]['pending mean share of words']).toFixed(0)} %, unassigned ${(100*cv[g]['outlier_hdbscan mean share of words']).toFixed(0)} %`).join(' · ');
// 3 works
const W=D.works; const gsel=document.getElementById('wgenre'), wsel=document.getElementById('wsel');
[...new Set(W.map(w=>w.genre))].sort().forEach(g=>gsel.add(new Option(`${g} (${W.filter(w=>w.genre===g).length})`,g)));
function fillWorks(){wsel.innerHTML='';W.filter(w=>w.genre===gsel.value).sort((a,b)=>a.title.localeCompare(b.title)).forEach(w=>wsel.add(new Option(`${w.title.slice(0,60)} — ${w.author.slice(0,25)} (${w.year})`,w.work_id)));wplot();}
function wplot(){const w=W.find(x=>x.work_id===wsel.value); if(!w)return; const ts=Object.keys(w.shares).sort((a,b)=>w.shares[b]-w.shares[a]);
  document.getElementById('winfo').textContent=`${w.genre_raw} · ${w.play_type} · ${w.n_ed} edition(s) · ~${w.words.toLocaleString()} words`;
  const lab=ts.map(t=>`T${t} ${tl[t].slice(0,38)}`);
  const tr=[{type:'bar',orientation:'h',name:'this work',y:lab,x:ts.map(t=>w.shares[t]),marker:{color:'#2b5c8a'},hovertemplate:'%{y}: %{x:.1f} %<extra>this work</extra>'},
            {type:'bar',orientation:'h',name:`${w.genre} mean`,y:lab,x:ts.map(t=>(D.genre_mean[t]||{})[w.genre]||0),marker:{color:'#b9c9da'},hovertemplate:'%{y}: %{x:.1f} %<extra>genre mean</extra>'},
            {type:'bar',orientation:'h',name:'category',y:Object.keys(w.cats),x:Object.values(w.cats),xaxis:'x2',yaxis:'y2',marker:{color:['#2b5c8a','#2b5c8a','#b8862b','#8a8a8a','#d9d5cc']},hovertemplate:'%{y}: %{x:.1f} % of words<extra></extra>',showlegend:false}];
  Plotly.react('wplot',tr,{...base,height:Math.max(360,24*lab.length+120),barmode:'group',margin:{l:280,r:20,t:30,b:40},legend:{orientation:'h',y:1.08},
    grid:{rows:1,columns:2,pattern:'independent',columnwidths:[0.65,0.35]},yaxis:{autorange:'reversed'},xaxis:{title:'% of the work\'s words',ticksuffix:' %'},yaxis2:{autorange:'reversed'},xaxis2:{title:'% of words by category',ticksuffix:' %'}},{displaylogo:false,responsive:true});}
gsel.onchange=fillWorks; wsel.onchange=wplot; fillWorks();
// 4 table
const cols=[['topic','T',1],['label','label',0],['cat','use',0],['size','chunks',1],['n_works','works',1],['n_works_ge3','works ≥3',1],['dom_work','dominant work',0],['dom_share','dom. %',1],['ctfidf','class-TF-IDF',0],['keybert','KeyBERT',0]];
let sortk='size',sortd=-1;
function table(){const f=document.getElementById('tfilter').value.toLowerCase();const rows=T.filter(t=>!f||[t.label,t.ctfidf,t.keybert,t.dom_work,t.top_works,t.cat].join(' ').toLowerCase().includes(f)).sort((a,b)=>(a[sortk]>b[sortk]?1:a[sortk]<b[sortk]?-1:0)*sortd);
  document.getElementById('ttab').innerHTML='<tr>'+cols.map(c=>`<th class="${c[2]?'num':''}" data-k="${c[0]}">${c[1]}</th>`).join('')+'</tr>'+rows.map(t=>'<tr>'+cols.map(c=>{let v=t[c[0]];if(c[0]==='dom_share')v=(100*v).toFixed(0);if(c[0]==='cat')v=`<span class="tag ${t.cat}">${t.cat}</span>`;return `<td class="${c[2]?'num':''}">${v}</td>`;}).join('')+'</tr>').join('');
  document.querySelectorAll('#ttab th').forEach(h=>h.onclick=()=>{if(sortk===h.dataset.k)sortd=-sortd;else{sortk=h.dataset.k;sortd=1;}table();});}
document.getElementById('tfilter').oninput=table; table();
</script></body></html>'''

if __name__ == '__main__':
    main()
