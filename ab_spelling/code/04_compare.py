#!/usr/bin/env python3
"""04_compare.py — compare topic models fitted on original (A) and regularized (B) spelling.

  python 04_compare.py --chunks <chunks dir> --runs <runs dir> --reg-pairs <reg_pairs_texts_analysis_en.csv>

For every seed that has both topics_A_s<seed>/ and topics_B_s<seed>/:
  * agreement of chunk→topic assignments (ARI, NMI), on all chunks and on chunks assigned in both;
  * number of topics, outlier share, vectorizer vocabulary size;
  * keyword quality per model: share of top-10 words that are early-modern spelling variants
    (forms EarlyPrint regularizes: surface_lower in reg_pairs that is not itself a reg target),
    number of topics whose top-10 contains a spelling doublet (e.g. loue + love),
    NPMI coherence of the top-10 words over the model's own cleaned chunks;
  * stability: ARI between seeds within a variant.
Writes <runs>/compare/compare_summary.json and compare_report.md (tables + side-by-side top words
for the 15 largest A topics at the first seed and their best-matching B topics).
The report is descriptive; whether B is "better" is a judgement to be made from keywords,
representative chunks, stability and outliers together, not from any single number.
"""
import argparse, csv, json, math, re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

STOP_RE = re.compile(r'\b[a-z]+\b')


def load_topics(path):
    return {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(path / 'doc_topics.csv', encoding='utf-8'))}


def load_top_words(path, k=10):
    tw = defaultdict(list)
    for r in csv.DictReader(open(path / 'top_words.csv', encoding='utf-8')):
        if int(r['rank']) <= k:
            tw[int(r['topic'])].append(r['word'])
    tw.pop(-1, None)
    return tw


def agreement(ta, tb):
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
    common = sorted(set(ta) & set(tb))
    la = [ta[c] for c in common]; lb = [tb[c] for c in common]
    both = [(x, y) for x, y in zip(la, lb) if x != -1 and y != -1]
    asg_a = {c for c in common if ta[c] != -1}; asg_b = {c for c in common if tb[c] != -1}
    out = {'n_common': len(common), 'ari_all': round(adjusted_rand_score(la, lb), 4), 'nmi_all': round(normalized_mutual_info_score(la, lb), 4),
           'n_assigned_in_both': len(both),
           'assigned_set_jaccard': round(len(asg_a & asg_b) / max(1, len(asg_a | asg_b)), 4)}
    if both:
        out['ari_assigned_both'] = round(adjusted_rand_score([x for x, _ in both], [y for _, y in both]), 4)
        out['nmi_assigned_both'] = round(normalized_mutual_info_score([x for x, _ in both], [y for _, y in both]), 4)
    return out


def npmi(top_words, docs_tokens, n_docs):
    """Mean NPMI over word pairs of each topic's top words; docs_tokens: word -> set(doc idx)."""
    per_topic = {}
    for t, words in top_words.items():
        vals = []
        for w1, w2 in combinations(words, 2):
            d1, d2 = docs_tokens.get(w1, set()), docs_tokens.get(w2, set())
            c12 = len(d1 & d2)
            if not d1 or not d2:
                continue
            p1, p2 = len(d1) / n_docs, len(d2) / n_docs
            if c12 == 0:
                vals.append(-1.0); continue
            p12 = c12 / n_docs
            if p12 >= 1.0:          # both words in every document: no information, skip the pair
                continue
            vals.append(math.log(p12 / (p1 * p2)) / -math.log(p12))
        if vals:
            per_topic[t] = sum(vals) / len(vals)
    return per_topic


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True)
    ap.add_argument('--runs', required=True)
    ap.add_argument('--reg-pairs', required=True)
    ap.add_argument('--top-k', type=int, default=10)
    ap.add_argument('--pairs', default='A:B', help='comma-separated variant pairs, e.g. A:B,A2:B,A:A2')
    a = ap.parse_args()
    runs = Path(a.runs); out = runs / 'compare'; out.mkdir(exist_ok=True)

    # spelling-variant lexicon from the regularization pairs table
    surf, targets = set(), set()
    reg_of = defaultdict(set)
    for r in csv.DictReader(open(a.reg_pairs, encoding='utf-8')):
        s, t = r['surface_lower'], r['reg_lower'].strip("'")
        if t == s:                      # possessive/contraction apostrophes only (achilles -> achilles'): not a spelling change
            continue
        if s.isalpha():
            surf.add(s)
        if t.isalpha():
            targets.add(t)
        reg_of[s].add(t)
    variant_lex = surf - targets

    pairs_arg = [tuple(p.split(':')) for p in a.pairs.split(',')]
    variants = sorted({v for p in pairs_arg for v in p})
    def seeds_of(v): return {int(p.name.split('_s')[1]) for p in runs.glob(f'topics_{v}_s*')}
    summary = {'pairs': a.pairs, 'per_pair': {}, 'stability': {}, 'variant_lexicon_size': len(variant_lex)}
    texts = {}
    for v in variants:
        texts[v] = {r['chunk_id']: set(STOP_RE.findall(r['text'].lower())) for r in csv.DictReader(open(Path(a.chunks) / f'chunks_{v}.csv', encoding='utf-8'))}
    work_of = {r['chunk_id']: r['work_id'] for r in csv.DictReader(open(Path(a.chunks) / 'chunk_meta.csv', encoding='utf-8'))} if (Path(a.chunks) / 'chunk_meta.csv').exists() else {}
    def concentration(t_of):
        members = defaultdict(list)
        for c, t in t_of.items():
            if t != -1: members[t].append(c)
        ge90 = sum(1 for m in members.values() if work_of and Counter(work_of[c] for c in m).most_common(1)[0][1] / len(m) >= 0.9)
        return ge90
    LABEL = {'A': 'A original', 'A2': 'A2 long-s/VV normalized', 'B': 'B regularized'}
    report = ['# Spelling variants compared: ' + ', '.join(f'{v} = {LABEL.get(v, v)}' for v in variants), '']
    for VA, VB in pairs_arg:
      seeds = sorted(seeds_of(VA) & seeds_of(VB))
      if not seeds:
          report += [f'## {VA} vs {VB}: no common seed', '']; continue
      summary['per_pair'][f'{VA}:{VB}'] = {'seeds': seeds, 'per_seed': {}}
      report += [f'# {VA} vs {VB}', '']
      for s in seeds:
          pa, pb = runs / f'topics_{VA}_s{s}', runs / f'topics_{VB}_s{s}'
          ta, tb = load_topics(pa), load_topics(pb)
          ra, rb = json.load(open(pa / 'run.json')), json.load(open(pb / 'run.json'))
          twa, twb = load_top_words(pa, a.top_k), load_top_words(pb, a.top_k)
          res = {'agreement': agreement(ta, tb)}
          for v, r, tw in ((VA, ra, twa), (VB, rb, twb)):
              words = [w for ws in tw.values() for w in ws]
              variant_share = sum(w in variant_lex for w in words) / max(1, len(words))
              doublets = sum(1 for ws in tw.values() if any(w in reg_of and (reg_of[w] & set(ws)) for w in ws))
              ids = list(texts[v])
              idx = {c: i for i, c in enumerate(ids)}
              needed = set(words)
              docs_tokens = defaultdict(set)
              for c, toks in texts[v].items():
                  for w in toks & needed:
                      docs_tokens[w].add(idx[c])
              coh = npmi(tw, docs_tokens, len(ids))
              res[v] = {'n_topics': r['n_topics'], 'outlier_share': r['outlier_share'], 'vocabulary_size': r['vocabulary_size'],
                        'min_df_used': r.get('min_df_used', ''), 'clusters_ge90_one_work': concentration(ta if v == VA else tb),
                        'top_words_variant_spelling_share': round(variant_share, 4), 'topics_with_spelling_doublet': doublets,
                        'distinct_top_words': len(set(words)), 'npmi_mean': round(sum(coh.values()) / max(1, len(coh)), 4)}
          summary['per_pair'][f'{VA}:{VB}']['per_seed'][s] = res
          report += [f'## seed {s}', '', f'| | {LABEL.get(VA, VA)} | {LABEL.get(VB, VB)} |', '|---|---:|---:|']
          for k, label in (('n_topics', 'topics'), ('outlier_share', 'outlier share'), ('clusters_ge90_one_work', 'clusters with ≥90 % of chunks from one work'),
                           ('vocabulary_size', 'c-TF-IDF vocabulary'), ('min_df_used', 'min_df actually used'),
                           ('top_words_variant_spelling_share', 'share of top-10 words that are spelling variants'),
                           ('topics_with_spelling_doublet', 'topics with a spelling doublet in top-10'),
                           ('distinct_top_words', 'distinct top-10 words'), ('npmi_mean', 'NPMI coherence (top-10)')):
              report.append(f'| {label} | {res[VA][k]} | {res[VB][k]} |')
          ag = res['agreement']
          report += ['', f'Assignment agreement {VA}↔{VB}: ARI {ag["ari_all"]} / NMI {ag["nmi_all"]} on {ag["n_common"]} chunks; '
                     f'on the {ag["n_assigned_in_both"]} chunks assigned in both: ARI {ag.get("ari_assigned_both")} / NMI {ag.get("nmi_assigned_both")}; '
                     f'Jaccard of the assigned (non-outlier) sets {ag["assigned_set_jaccard"]}.', '']

    # stability across seeds within each variant
    for v in variants:
        pairs = {}
        seeds = sorted(seeds_of(v))
        for s1, s2 in combinations(seeds, 2):
            t1, t2 = load_topics(runs / f'topics_{v}_s{s1}'), load_topics(runs / f'topics_{v}_s{s2}')
            g = agreement(t1, t2)
            pairs[f'{s1}-{s2}'] = f"{g['ari_all']} / {g.get('ari_assigned_both')} / {g['assigned_set_jaccard']}"
        summary['stability'][v] = pairs
    keys = sorted({k for v in variants for k in summary['stability'][v]})
    if keys:
        report += ['# Stability across seeds (ARI all chunks / ARI on chunks assigned in both / Jaccard of assigned sets)', '', '| seeds | ' + ' | '.join(variants) + ' |', '|---|' + '---:|' * len(variants)]
        for k in keys:
            report.append(f'| {k} | ' + ' | '.join(str(summary['stability'][v].get(k, '')) for v in variants) + ' |')
        report.append('')

    # side-by-side keywords for every pair: 15 largest topics of the first variant at its first seed, matched by chunk overlap
    for VA, VB in pairs_arg:
      seeds = sorted(seeds_of(VA) & seeds_of(VB))
      if not seeds:
          continue
      s = seeds[0]
      ta, tb = load_topics(runs / f'topics_{VA}_s{s}'), load_topics(runs / f'topics_{VB}_s{s}')
      twa, twb = load_top_words(runs / f'topics_{VA}_s{s}', a.top_k), load_top_words(runs / f'topics_{VB}_s{s}', a.top_k)
      sizes = Counter(t for t in ta.values() if t != -1)
      report += [f'# Largest {VA} topics (seed {s}) and their best-matching {VB} topics', '', f'| {VA} topic (size) | {VA} top words | {VB} topic (overlap) | {VB} top words |', '|---|---|---|---|']
      for t, n in sizes.most_common(15):
          members = {c for c, x in ta.items() if x == t}
          ov = Counter(tb[c] for c in members if c in tb and tb[c] != -1)
          bt, bn = (ov.most_common(1)[0] if ov else (None, 0))
          report.append(f'| {t} ({n}) | {", ".join(twa.get(t, []))} | {bt} ({bn}/{n}) | {", ".join(twb.get(bt, [])) if bt is not None else ""} |')
      report.append('')
    (out / 'compare_summary.json').write_text(json.dumps(summary, indent=1))
    (out / 'compare_report.md').write_text('\n'.join(report), encoding='utf-8')
    print('\n'.join(report[:40]))
    print(f'... written to {out}')


if __name__ == '__main__':
    main()
