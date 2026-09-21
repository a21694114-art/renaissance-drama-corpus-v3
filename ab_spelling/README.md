# ab_spelling — does EarlyPrint regularization help the topic model?

First experiment on corpus v3: the same 580 documents, the same chunk map, the same embedding
model and BERTopic settings, run twice —

- **A** `texts_analysis_en/` — original spelling
- **B** `texts_analysis_en_reg/` — r3 regularized spelling

The chunk map is defined once on v3 node indices (`01_chunk_map.py`; 24,343 chunks of up to
2,000 characters of original-spelling text, whole nodes, long nodes split at sentence
boundaries into the same number of pieces in A and B), so chunk *i* is the same passage in
both variants. Embeddings: `thenlper/gte-large`, batch 16 (`02_embed.py`). Topics: UMAP
(5 comp., 15 neighbours, min_dist 0.05, cosine) → HDBSCAN (min_cluster_size 30) → c-TF-IDF
with the previous pipeline's stopword list, identical for A and B (`03_topics.py`). Seeds 42,
43, 44. `04_compare.py` reports assignment agreement (ARI/NMI), topic counts, outliers, the
share of top-10 keywords that are spelling variants, spelling doublets within a topic, NPMI
coherence, cross-seed stability, and side-by-side keywords of the largest topics.

```
python3 -m venv .venv-ab && source .venv-ab/bin/activate
pip install -r ab_spelling/requirements.txt
bash ab_spelling/run_ab.sh smoke     # 20 documents, one seed — check that everything runs
bash ab_spelling/run_ab.sh full      # 580 documents, three seeds
```

Outputs are written outside the repository (`../sep6/ab_spelling_out/`); the comparison
report is `runs/compare/compare_report.md`. Judge A vs B from keywords, representative
chunks, stability and outliers together, not from a single number.
