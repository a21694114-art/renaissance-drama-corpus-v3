# Topic shares by decade — methods and coverage

Run topics_B_s42; 53 topics (included); genre counts comedy 151 (expected 151), tragedy 111 (expected 111), history 34 (expected 34).

Date rule: British Drama first-performance date first; Annals only when British Drama is absent or has no usable year (reason recorded per work). The leading year of the string is the date; bracketed limits of the same source are the lower / upper limit; licence and revision notes are accompanying events and do not disqualify the date; later revision ranges never widen the limits; publication years are never used; the two sources are never averaged. Date kind from the DEEP play type: first performance (a performance setting is named), composition (closet / unacted only), kind unclear (both or neither, or queried). A range without a point year would be kept as "range only" and grouped only if it lies within one decade (none in this corpus). Dates whose meaning cannot be settled are pending, not guessed.
Decades: floor(year / 10) × 10 on the adopted point year; each work in exactly one decade; no merging. Display: < 5 works blank, 5–9 sparse, ≥ 10 shown — a display rule, not a reliability claim.
Measure: share of a work's words per topic (all words in the denominator, selected topics not renormalised), works equal-weighted; composition counts are by works; coverage means are equal-weighted means of work-level shares. Top works per cell: contribution = share / n (works equal-weighted) and share of the group total.
Sensitivity: works whose own-source limits cross a decade boundary are regrouped by lower limit and, separately, by upper limit; other works keep their decade; circa or queried years without limits get no ± years. The two groupings are boundary cases for the grouping's sensitivity, not two claims about the real dates, and do not exhaust the dating uncertainty; a range-only work (none here) would ADD to the sample under the limit groupings rather than move. Works whose two sources differ are listed (sources_differ.csv) without further dating research.
Figures: fig1 = composition of this corpus by decade (stacked by genre_main, totals) — not a count of plays written or staged; fig2 = per genre, works per decade and mean included coverage in two facet rows (no dual axis); fig3 = per-genre heatmap, at most 15 topics chosen by max − min of the decade means across decades with ≥ 10 works (or by overall genre mean when fewer than two such decades), raw percentages on one colour scale for the three genres; cells with < 5 works blank, 5–9 marked sparse. No sensitivity figures (tables only).

## Coverage

| scope | works | placed | not usable | British Drama | Annals fallback | first perf. | composition | kind unclear | circa/queried | with limits | cross boundary | sources differ (diff. decade) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 516 | 515 | 1 | 486 | 29 | 469 | 31 | 15 | 21 | 264 | 112 | 156 (39) |
| comedy | 151 | 151 | 0 | 146 | 5 | 147 | 2 | 2 | 2 | 83 | 28 | 45 (10) |
| tragedy | 111 | 111 | 0 | 108 | 3 | 83 | 22 | 6 | 5 | 73 | 36 | 36 (7) |
| history | 34 | 34 | 0 | 33 | 1 | 33 | 0 | 1 | 0 | 27 | 14 | 17 (5) |

Not usable: Albertus Wallenstein — only source is marked incorrect in DEEP — pending

## Works per decade (all placed works) and genre composition

| decade | works | composition (by works) | first perf. | composition | unclear |
|---|---:|---|---:|---:|---:|
| 1490–1499 | 2 | other/multi 2 | 2 | 0 | 0 |
| 1500–1509 | 0 |  | 0 | 0 | 0 |
| 1510–1519 | 3 | other/multi 2; moral 1 | 3 | 0 | 0 |
| 1520–1529 | 7 | other/multi 6; comedy 1 | 7 | 0 | 0 |
| 1530–1539 | 4 | other/multi 2; comedy 1; moral 1 | 4 | 0 | 0 |
| 1540–1549 | 0 |  | 0 | 0 | 0 |
| 1550–1559 | 10 | moral 6; comedy 2; other/multi 1; tragedy 1 | 9 | 1 | 0 |
| 1560–1569 | 23 | tragedy 14; moral 6; comedy 2; interlude 1 | 15 | 8 | 0 |
| 1570–1579 | 11 | moral 4; other/multi 3; comedy 2; masque 1; tragedy 1 | 8 | 1 | 2 |
| 1580–1589 | 33 | tragedy 12; comedy 10; history 4; moral 3; other/multi 2; pastoral 1; romance 1 | 31 | 2 | 0 |
| 1590–1599 | 69 | comedy 20; history 18; tragedy 12; romance 8; other/multi 6; moral 2; pastoral 2; tragicomedy 1 | 63 | 5 | 1 |
| 1600–1609 | 113 | comedy 45; tragedy 29; other/multi 10; masque 7; history 6; tragicomedy 6; romance 4; moral 3; pastoral 3 | 106 | 5 | 2 |
| 1610–1619 | 81 | comedy 20; other/multi 20; tragedy 19; masque 11; history 3; romance 3; tragicomedy 3; pastoral 2 | 79 | 2 | 0 |
| 1620–1629 | 73 | comedy 22; other/multi 19; tragedy 13; masque 8; tragicomedy 7; history 2; moral 1; pastoral 1 | 69 | 3 | 1 |
| 1630–1639 | 84 | comedy 26; other/multi 17; tragicomedy 12; masque 10; tragedy 9; pastoral 6; romance 2; history 1; moral 1 | 72 | 4 | 8 |
| 1640–1649 | 2 | masque 1; tragedy 1 | 1 | 0 | 1 |

## Genre × decade: works and mean included coverage

| genre | decade | works | status | mean included | outlier | pending | contextual only | candidate | unclassified |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| comedy | 1520–1529 | 1 | insufficient (< 5) | 0.2383 | 0.7147 | 0.047 | 0.0 | 0.0 | 0.0 |
| comedy | 1530–1539 | 1 | insufficient (< 5) | 0.3618 | 0.5661 | 0.0721 | 0.0 | 0.0 | 0.0 |
| comedy | 1550–1559 | 2 | insufficient (< 5) | 0.1328 | 0.8544 | 0.0128 | 0.0 | 0.0 | 0.0 |
| comedy | 1560–1569 | 2 | insufficient (< 5) | 0.2205 | 0.7246 | 0.055 | 0.0 | 0.0 | 0.0 |
| comedy | 1570–1579 | 2 | insufficient (< 5) | 0.3531 | 0.6469 | 0.0 | 0.0 | 0.0 | 0.0 |
| comedy | 1580–1589 | 10 | shown (≥ 10) | 0.378 | 0.6152 | 0.0068 | 0.0 | 0.0 | 0.0 |
| comedy | 1590–1599 | 20 | shown (≥ 10) | 0.2495 | 0.6696 | 0.0384 | 0.0426 | 0.0 | 0.0 |
| comedy | 1600–1609 | 45 | shown (≥ 10) | 0.3443 | 0.6031 | 0.0402 | 0.0124 | 0.0 | 0.0 |
| comedy | 1610–1619 | 20 | shown (≥ 10) | 0.3229 | 0.6377 | 0.0229 | 0.0165 | 0.0 | 0.0 |
| comedy | 1620–1629 | 22 | shown (≥ 10) | 0.3809 | 0.5873 | 0.0167 | 0.0151 | 0.0 | 0.0 |
| comedy | 1630–1639 | 26 | shown (≥ 10) | 0.4081 | 0.5608 | 0.0183 | 0.0128 | 0.0 | 0.0 |
| tragedy | 1550–1559 | 1 | insufficient (< 5) | 0.9627 | 0.0373 | 0.0 | 0.0 | 0.0 | 0.0 |
| tragedy | 1560–1569 | 14 | shown (≥ 10) | 0.3964 | 0.5961 | 0.0075 | 0.0 | 0.0 | 0.0 |
| tragedy | 1570–1579 | 1 | insufficient (< 5) | 0.1168 | 0.8832 | 0.0 | 0.0 | 0.0 | 0.0 |
| tragedy | 1580–1589 | 12 | shown (≥ 10) | 0.4615 | 0.5338 | 0.0047 | 0.0 | 0.0 | 0.0 |
| tragedy | 1590–1599 | 12 | shown (≥ 10) | 0.4261 | 0.5586 | 0.0063 | 0.009 | 0.0 | 0.0 |
| tragedy | 1600–1609 | 29 | shown (≥ 10) | 0.401 | 0.5746 | 0.0177 | 0.0067 | 0.0 | 0.0 |
| tragedy | 1610–1619 | 19 | shown (≥ 10) | 0.3951 | 0.5864 | 0.0184 | 0.0 | 0.0 | 0.0 |
| tragedy | 1620–1629 | 13 | shown (≥ 10) | 0.4357 | 0.5457 | 0.0186 | 0.0 | 0.0 | 0.0 |
| tragedy | 1630–1639 | 9 | sparse (5–9) | 0.4464 | 0.5475 | 0.0061 | 0.0 | 0.0 | 0.0 |
| tragedy | 1640–1649 | 1 | insufficient (< 5) | 0.3423 | 0.5798 | 0.0778 | 0.0 | 0.0 | 0.0 |
| history | 1580–1589 | 4 | insufficient (< 5) | 0.4189 | 0.5694 | 0.0062 | 0.0055 | 0.0 | 0.0 |
| history | 1590–1599 | 18 | shown (≥ 10) | 0.3886 | 0.5462 | 0.0272 | 0.038 | 0.0 | 0.0 |
| history | 1600–1609 | 6 | sparse (5–9) | 0.3067 | 0.6651 | 0.0069 | 0.0212 | 0.0 | 0.0 |
| history | 1610–1619 | 3 | insufficient (< 5) | 0.3466 | 0.6534 | 0.0 | 0.0 | 0.0 | 0.0 |
| history | 1620–1629 | 2 | insufficient (< 5) | 0.6004 | 0.3996 | 0.0 | 0.0 | 0.0 | 0.0 |
| history | 1630–1639 | 1 | insufficient (< 5) | 0.0 | 1.0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Sensitivity: works per decade under the three groupings

| scope | grouping | moved | 1490–1499 | 1500–1509 | 1510–1519 | 1520–1529 | 1530–1539 | 1540–1549 | 1550–1559 | 1560–1569 | 1570–1579 | 1580–1589 | 1590–1599 | 1600–1609 | 1610–1619 | 1620–1629 | 1630–1639 | 1640–1649 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | main | 0 | 2 | 0 | 3 | 7 | 4 | 0 | 10 | 23 | 11 | 33 | 69 | 113 | 81 | 73 | 84 | 2 |
| all | lower limit | 60 | 2 | 0 | 4 | 6 | 6 | 2 | 12 | 19 | 10 | 50 | 60 | 116 | 78 | 73 | 75 | 2 |
| all | upper limit | 61 | 2 | 0 | 3 | 4 | 7 | 0 | 9 | 23 | 11 | 20 | 75 | 114 | 78 | 67 | 96 | 6 |
| comedy | main | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 2 | 2 | 2 | 10 | 20 | 45 | 20 | 22 | 26 | 0 |
| comedy | lower limit | 14 | 0 | 0 | 1 | 0 | 1 | 0 | 2 | 2 | 3 | 13 | 18 | 45 | 22 | 18 | 26 | 0 |
| comedy | upper limit | 17 | 0 | 0 | 0 | 1 | 1 | 0 | 2 | 2 | 2 | 6 | 21 | 47 | 20 | 16 | 32 | 1 |
| tragedy | main | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 14 | 1 | 12 | 12 | 29 | 19 | 13 | 9 | 1 |
| tragedy | lower limit | 18 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 11 | 1 | 16 | 12 | 30 | 15 | 15 | 6 | 1 |
| tragedy | upper limit | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 14 | 1 | 8 | 15 | 27 | 14 | 14 | 16 | 1 |
| history | main | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 18 | 6 | 3 | 2 | 1 | 0 |
| history | lower limit | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 16 | 7 | 2 | 1 | 0 | 0 |
| history | upper limit | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 8 | 2 | 2 | 2 | 0 |
