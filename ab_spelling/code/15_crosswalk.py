#!/usr/bin/env python3
"""15_crosswalk.py — what happened to each cluster of run A in run B (same chunks, different clustering).

    python 15_crosswalk.py --old <runs>/topics_B_s42 --new <runs2>/topics_B_s42 [--sheet <old topic_sheet.csv>] [--out <dir>]

Chunk-based matching (the only thing two runs share are the chunk ids): for every old cluster the new
cluster that holds most of its chunks, with Jaccard, recall (share of the old cluster's chunks now in
that new cluster) and precision (share of the new cluster that came from the old one); the share of
the old cluster's chunks that are now outliers; how many new clusters its chunks are spread over.
If the old topic_sheet.csv is given, the summary is grouped by use_in_genre_analysis, so one can read
off directly how the confirmed themes, the candidates, the single-work clusters and the pending clusters
fared — e.g. "22 of 54 single-work clusters dissolved (>= 70 % of their chunks now outliers or spread
over >= 3 clusters)".  Outputs: crosswalk_old_to_new.csv, crosswalk_new_from_old.csv, crosswalk.md.
Verdicts per old cluster: kept (J >= 0.5), merged (recall >= 0.7 but precision < 0.5: swallowed by a
bigger new cluster), split (recall < 0.7, spread >= 2, outliers < 0.5), dissolved (>= 0.7 of its chunks
now outliers), changed (everything else).
"""
import argparse, csv
from collections import Counter, defaultdict
from pathlib import Path


def load(d):
    return {r['chunk_id']: int(r['topic']) for r in csv.DictReader(open(Path(d) / 'doc_topics.csv', encoding='utf-8'))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old', required=True); ap.add_argument('--new', required=True)
    ap.add_argument('--sheet', default=''); ap.add_argument('--new-sheet', default='')
    ap.add_argument('--out', default='')
    a = ap.parse_args()
    old, new = load(a.old), load(a.new)
    out = Path(a.out) if a.out else Path(a.new); out.mkdir(parents=True, exist_ok=True)
    common = sorted(set(old) & set(new))
    om = defaultdict(set); nm = defaultdict(set)
    for c in common:
        if old[c] != -1: om[old[c]].add(c)
        if new[c] != -1: nm[new[c]].add(c)
    sheet = {int(r['topic']): r for r in csv.DictReader(open(a.sheet, encoding='utf-8'))} if a.sheet and Path(a.sheet).exists() else {}
    nsheet = {int(r['topic']): r for r in csv.DictReader(open(a.new_sheet, encoding='utf-8'))} if a.new_sheet and Path(a.new_sheet).exists() else {}
    name = lambda t: (sheet.get(t, {}).get('Label') or sheet.get(t, {}).get('draft_label') or f'T{t}')
    nname = lambda t: (nsheet.get(t, {}).get('Label') or nsheet.get(t, {}).get('draft_label') or f'T{t}')

    rows = []
    for t in sorted(om):
        cs = om[t]; dest = Counter(new[c] for c in cs); out_share = dest[-1] / len(cs)
        spread = sum(1 for k, v in dest.items() if k != -1 and v >= max(3, 0.05 * len(cs)))
        best, nb = max(((k, v) for k, v in dest.items() if k != -1), key=lambda kv: kv[1], default=(None, 0))
        if best is not None:
            recall = nb / len(cs); precision = nb / len(nm[best]); jac = nb / len(cs | nm[best])
        else:
            recall = precision = jac = 0.0
        if jac >= 0.5: verdict = 'kept'
        elif out_share >= 0.7: verdict = 'dissolved'
        elif recall >= 0.7 and precision < 0.5: verdict = 'merged'
        elif recall < 0.7 and spread >= 2 and out_share < 0.5: verdict = 'split'
        else: verdict = 'changed'
        rows.append({'old_topic': t, 'old_label': name(t)[:60], 'use_in_genre_analysis': sheet.get(t, {}).get('use_in_genre_analysis', ''), 'old_size': len(cs),
                     'best_new_topic': best if best is not None else '', 'best_new_label': nname(best)[:60] if best is not None else '', 'best_new_size': len(nm[best]) if best is not None else 0,
                     'recall': round(recall, 3), 'precision': round(precision, 3), 'jaccard': round(jac, 3), 'now_outliers': round(out_share, 3), 'spread_over': spread, 'verdict': verdict})
    with open(out / 'crosswalk_old_to_new.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    nrows = []
    for t in sorted(nm):
        cs = nm[t]; src = Counter(old[c] for c in cs); best, nb = src.most_common(1)[0]
        from_out = src[-1] / len(cs)
        nrows.append({'new_topic': t, 'new_label': nname(t)[:60], 'new_size': len(cs), 'main_old_topic': best, 'main_old_label': name(best)[:60] if best != -1 else '(outliers)',
                      'main_old_use': sheet.get(best, {}).get('use_in_genre_analysis', '') if best != -1 else '', 'share_from_main': round(nb / len(cs), 3), 'share_from_old_outliers': round(from_out, 3),
                      'n_old_sources': sum(1 for k, v in src.items() if k != -1 and v >= max(3, 0.05 * len(cs))),
                      'kind': ('new (mostly former outliers)' if from_out >= 0.5 else 'same as old' if nb / len(cs) >= 0.7 and best != -1 else 'union of several old' if sum(1 for k, v in src.items() if k != -1 and v >= max(3, 0.05 * len(cs))) >= 2 else 'reshuffled')})
    with open(out / 'crosswalk_new_from_old.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(nrows[0])); w.writeheader(); w.writerows(nrows)

    n_old_out = sum(1 for c in common if old[c] == -1); n_new_out = sum(1 for c in common if new[c] == -1)
    md = [f'# Crosswalk {Path(a.old).name} → {Path(a.new).name}', '',
          f'{len(common):,} shared chunks. Old: {len(om)} clusters, {n_old_out:,} outliers ({100 * n_old_out / len(common):.1f} %). New: {len(nm)} clusters, {n_new_out:,} outliers ({100 * n_new_out / len(common):.1f} %).', '',
          'Verdict per old cluster: kept = Jaccard ≥ 0.5 with one new cluster; merged = ≥ 70 % of its chunks went into a new cluster that is mostly other material; split = spread over ≥ 2 new clusters; dissolved = ≥ 70 % of its chunks are now outliers; changed = none of these.', '']
    by_use = defaultdict(list)
    for r in rows: by_use[r['use_in_genre_analysis'] or '(no sheet)'].append(r)
    md += ['| old category | clusters | chunks | kept | merged | split | dissolved | changed | chunks now outliers |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for u in ('included', 'candidate', 'pending', 'contextual_only', '(no sheet)', ''):
        rs = by_use.get(u)
        if not rs: continue
        vc = Counter(r['verdict'] for r in rs); chunks = sum(r['old_size'] for r in rs)
        outl = sum(r['old_size'] * r['now_outliers'] for r in rs) / chunks
        md.append(f'| {u} | {len(rs)} | {chunks:,} | {vc["kept"]} | {vc["merged"]} | {vc["split"]} | {vc["dissolved"]} | {vc["changed"]} | {100 * outl:.0f} % |')
    kinds = Counter(r['kind'] for r in nrows)
    md += ['', f'New clusters by origin: ' + ', '.join(f'{k} {v}' for k, v in kinds.most_common()) + '.', '']
    for u in ('included', 'candidate', 'pending', 'contextual_only', '(no sheet)'):
        rs = by_use.get(u)
        if not rs: continue
        md += [f'## {u} ({len(rs)})', '', '| old | size | verdict | best new cluster | recall | precision | J | now outliers |', '|---|---:|---|---|---:|---:|---:|---:|']
        for r in sorted(rs, key=lambda r: (r['verdict'], -r['old_size'])):
            bn = f'T{r["best_new_topic"]} {r["best_new_label"]} ({r["best_new_size"]})' if r['best_new_topic'] != '' else '—'
            md.append(f'| T{r["old_topic"]} {r["old_label"][:40]} | {r["old_size"]} | {r["verdict"]} | {bn} | {r["recall"]:.2f} | {r["precision"]:.2f} | {r["jaccard"]:.2f} | {r["now_outliers"]:.0%} |')
        md.append('')
    newish = [r for r in nrows if r['kind'] in ('new (mostly former outliers)', 'union of several old')]
    if newish:
        md += ['## New clusters not present before (from former outliers, or unions of several old clusters)', '', '| new | size | from old outliers | main old source | kind |', '|---|---:|---:|---|---|']
        md += [f'| T{r["new_topic"]} {r["new_label"][:40]} | {r["new_size"]} | {r["share_from_old_outliers"]:.0%} | T{r["main_old_topic"]} {r["main_old_label"][:36]} ({r["main_old_use"]}) | {r["kind"]} |' for r in sorted(newish, key=lambda r: -r['new_size'])]
    (out / 'crosswalk.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md[:14])); print(f'→ {out / "crosswalk.md"}')


if __name__ == '__main__':
    main()
