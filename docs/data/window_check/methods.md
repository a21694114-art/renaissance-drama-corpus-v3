24_window_check.py — common time-window sensitivity check for the Shakespeare-vs-rest comparison.

Question answered: do the within-genre differences between Shakespeare's plays and the other plays of the genre
persist when both groups are restricted to plays whose estimated first-performance / composition year falls in
one common window (default 1590–1613, the span of Shakespeare's own dated works in the three genres)?

What it does NOT do: it does not re-embed, re-cluster, re-review or change any measure; it does not control for
date (a common window is not a matched date distribution); it does not show that any difference is caused by
period; it does not reuse the full-period random reference (the random groups were drawn from the full genre).
It re-aggregates the existing work-level topic shares (aggregate/work_topic_share.csv) with the existing dates
(aggregate/chronology/dates_by_work.csv, 23_chronology.py: British Drama first, Annals fallback) under one rule
applied identically to both sides, and reports counts, coverage, topic means, differences and a descriptive JSD
for the full period and for the window side by side. Works whose bracketed date limits cross a window edge are
listed, and the same tables are repeated with those works placed by their lower limit and by their upper limit
(membership sensitivity); the window itself is fixed in advance and is not changed after seeing results.

Inputs (all existing files):  --agg <aggregate dir> (work_topic_share.csv, config.json, chronology/dates_by_work.csv,
shakespeare/topic_by_genre.csv + jsd.csv for the cross-check)  --sheet topic_sheet.csv
Outputs (--out, default <agg>/window_check/): window_works.csv, window_counts.csv, window_topic_means.csv,
window_top10.csv, window_jsd.csv, excluded_by_decade.csv, summary.md, methods.md, checks.json, provenance.json.

Run 2026-09-28: window 1590–1613; genres comedy, tragedy, history; 53 topics (included).
