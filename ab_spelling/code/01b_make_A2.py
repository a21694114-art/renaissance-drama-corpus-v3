#!/usr/bin/env python3
"""01b_make_A2.py — variant A2: the original-spelling chunks with ONLY the two mechanical
normalizations that the regularized view also applies to its fallback nodes: long s -> s and
word-initial VV/vv -> W/w.  No lexical regularization.  A2 isolates the effect of EarlyPrint's
`reg` from the effect of removing the long-s character, which the first A/B run showed to
dominate the embedding space (HDBSCAN split A into two blobs = chunks with / without ſ)."""
import csv, re, sys
from pathlib import Path
src = Path(sys.argv[1]) / 'chunks_A.csv'; dst = Path(sys.argv[1]) / 'chunks_A2.csv'
n = 0
with open(src, encoding='utf-8') as f, open(dst, 'w', encoding='utf-8', newline='') as g:
    w = csv.writer(g); w.writerow(['chunk_id', 'text'])
    for r in csv.DictReader(f):
        t = r['text'].replace('ſ', 's')
        t = re.sub(r'\bVV', 'W', t); t = re.sub(r'\bvv', 'w', t); t = re.sub(r'\bVv', 'W', t)
        w.writerow([r['chunk_id'], t]); n += 1
print(f'chunks_A2.csv written: {n} chunks')
