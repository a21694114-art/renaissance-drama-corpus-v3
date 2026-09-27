# Company metadata coverage — works of the frozen run

Works: 516 (one representative edition each; genre_main from the run). DEEP rows: 516 chosen by deep_id match, 0 by fallback, 0 without a DEEP row; 23 rows realigned (extra field in the export); 17 works whose other DEEP rows differ in a company/date/play-type field (see deep_row_selection.csv).

## britdrama: status of the company value

| status | works |
|---|---:|
| clear | 238 |
| uncertain | 20 |
| multiple (;) | 4 |
| multiple (and) | 1 |
| unacted | 4 |
| unknown | 30 |
| missing (n/a) | 189 |
| not in BritDrama | 30 |

## annals: status of the company value

| status | works |
|---|---:|
| clear | 231 |
| uncertain | 37 |
| multiple (;) | 10 |
| multiple (then) | 3 |
| multiple (and) | 2 |
| multiple (or) | 1 |
| unacted | 10 |
| unknown | 19 |
| missing (n/a) | 203 |

## title_page: status of the company value

| status | works |
|---|---:|
| clear | 174 |
| multiple (;) | 8 |
| missing (n/a) | 203 |
| missing (None) | 131 |

## Availability of a first-performance company (British Drama field) by genre and play type

Named (clear, uncertain or multiple) in British Drama: 263; in Annals: 284; in at least one of the two: 295; in both: 252. Clear single name in British Drama: 238.

| genre_main | works | named | unknown | unacted | not in BritDrama | missing (n/a) |
|---|---:|---:|---:|---:|---:|---:|
| comedy | 151 | 120 | 9 | 2 | 5 | 15 |
| tragedy | 111 | 58 | 14 | 2 | 3 | 34 |
| other/multi | 91 | 4 | 0 | 0 | 13 | 74 |
| masque | 38 | 2 | 0 | 0 | 3 | 33 |
| history | 34 | 29 | 3 | 0 | 1 | 1 |
| tragicomedy | 29 | 24 | 0 | 0 | 4 | 1 |
| moral | 28 | 8 | 1 | 0 | 1 | 18 |
| romance | 18 | 13 | 3 | 0 | 0 | 2 |
| pastoral | 15 | 5 | 0 | 0 | 0 | 10 |
| interlude | 1 | 0 | 0 | 0 | 0 | 1 |

| play_type_main (first token of the DEEP play type) | works | named | unknown | unacted | not in BritDrama | missing (n/a) |
|---|---:|---:|---:|---:|---:|---:|
| Adult Professional | 215 | 185 | 23 | 1 | 6 | 0 |
| Occasional | 99 | 2 | 0 | 0 | 6 | 91 |
| Boys Professional | 75 | 66 | 5 | 0 | 4 | 0 |
| Interlude | 36 | 1 | 0 | 0 | 5 | 30 |
| University/Inns of Court | 25 | 2 | 0 | 0 | 1 | 22 |
| Closet/Unacted | 22 | 0 | 0 | 3 | 3 | 16 |
| Translation | 20 | 0 | 0 | 0 | 0 | 20 |
| Professional | 10 | 6 | 0 | 0 | 4 | 0 |
| Nonprofessional | 8 | 0 | 0 | 0 | 1 | 7 |
| Boys Nonprofessional/School | 3 | 1 | 0 | 0 | 0 | 2 |
| Unknown | 2 | 0 | 2 | 0 | 0 | 0 |
| Private | 1 | 0 | 0 | 0 | 0 | 1 |

## British Drama vs Annals first-performance company

All works:

| relation | works |
|---|---:|
| neither named | 221 |
| identical | 205 |
| differ | 33 |
| only annals named | 32 |
| same base name | 14 |
| only britdrama named | 11 |

Works with a company NAMED in both sources (n = 252; unknown / unacted / n/a do not count as names); shares are of these 252:

| relation | works | share |
|---|---:|---:|
| identical | 205 | 81.3% |
| differ | 33 | 13.1% |
| same base name | 14 | 5.6% |

Works named in only one source or in neither, by the pair of statuses (British Drama, Annals):

| British Drama | Annals | works |
|---|---|---:|
| missing (n/a) | missing (n/a) | 189 |
| not in BritDrama | missing (n/a) | 13 |
| unknown | uncertain | 11 |
| unknown | unknown | 10 |
| not in BritDrama | clear | 10 |
| unknown | clear | 6 |
| clear | unknown | 5 |
| not in BritDrama | unacted | 5 |
| unacted | unacted | 4 |
| uncertain | unknown | 4 |
| unknown | multiple (;) | 2 |
| not in BritDrama | uncertain | 1 |
| unknown | multiple (or) | 1 |
| not in BritDrama | multiple (;) | 1 |
| uncertain | missing (n/a) | 1 |
| clear | unacted | 1 |

## Dates

Annals date_first_performance: 0 missing; 231 with limits in brackets; 104 circa/queried; 41 licensed; 46 works whose play_type says closet/unacted (date = composition by convention).
British Drama date: 30 missing (not in BritDrama), 249 with limits. Annals and British Drama years differ for 156 works (same year for 330).
Publication year is kept in its own column and is never used as a performance date.

## Largest companies — britdrama (clear values only; uncertain and multiple listed separately in company_coverage.csv)

Dates are the British Drama first-performance dates, i.e. the same source as the company value; the other source is in company_coverage.csv (xdate_*).

| company (raw) | works (clear) | same name uncertain | named in multiple values | genres | individual authors / signatures (top person) | British Drama years (records in this corpus) | British Drama limits | mean included share |
|---|---:|---:|---:|---|---|---|---|---:|
| King's Men | 52 | 0 | 0 | tragedy 22; comedy 14; tragicomedy 12; romance 3; history 1 | 19 / 26 (Shakespeare, William 14) | 1603–1636 | 1599–1639 | 0.374 |
| Queen Henrietta Maria's Men | 28 | 0 | 1 | comedy 18; tragedy 5; tragicomedy 4; pastoral 1 | 8 / 8 (Shirley, James 17) | 1626–1636 | 1625–1636 | 0.424 |
| Lord Chamberlain's (Hunsdon's) Men | 21 | 1 | 1 | comedy 10; history 7; tragedy 4 | 4 / 4 (Shakespeare, William 16) | 1595–1603 | 1593–1604 | 0.335 |
| Children of the Queen's Revels | 20 | 0 | 1 | comedy 14; tragedy 4; history 1; pastoral 1 | 9 / 11 (Chapman, George 7) | 1604–1610 | 1601–1612 | 0.325 |
| Admiral's (Nottingham's) Men | 14 | 0 | 1 | comedy 6; tragedy 5; history 1; romance 1; tragicomedy 1 | 12 / 11 (Dekker, Thomas 3) | 1587–1603 | 1587–1603 | 0.305 |
| Children of Paul's (second) | 14 | 1 | 1 | comedy 11; tragedy 2; romance 1 | 8 / 6 (Middleton, Thomas 5) | 1599–1606 | 1599–1607 | 0.411 |
| Queen Anne's Men | 11 | 1 | 0 | comedy 3; other/multi 3; history 2; tragedy 2; tragicomedy 1 | 6 / 6 (Heywood, Thomas 5) | 1604–1618 | 1603–1619 | 0.446 |
| Children of the King's Revels | 8 | 0 | 1 | comedy 6; tragedy 1; tragicomedy 1 | 8 / 7 (Barry, Lording 2) | 1607–1608 | 1606–1608 | 0.368 |
| Derby's (Strange's) Men | 8 | 2 | 0 | history 3; moral 2; comedy 1; romance 1; tragedy 1 | 7 / 5 (Anonymous 4) | 1589–1599 | 1589–1600 | 0.341 |
| Children of the Chapel (first) (Oxford's Boys) | 7 | 0 | 0 | comedy 4; tragedy 2; pastoral 1 | 8 / 6 (Lyly, John 2) | 1564–1588 | 1564–1590 | 0.472 |
| Lady Elizabeth's Men | 7 | 0 | 1 | comedy 4; tragicomedy 3 | 6 / 6 (Shirley, James 2) | 1613–1625 | 1613–1625 | 0.218 |
| Prince Henry's Men | 6 | 0 | 0 | comedy 3; history 2; other/multi 1 | 4 / 4 (Dekker, Thomas 4) | 1604–1611 | 1604–1612 | 0.371 |
| Children of Paul's (first) | 5 | 2 | 0 | comedy 4; pastoral 1 | 1 / 1 (Lyly, John 5) | 1588–1590 | 1585–1590 | 0.419 |
| Children of the Chapel (second) | 5 | 0 | 0 | comedy 3; moral 1; tragicomedy 1 | 4 / 4 (Jonson, Ben 2) | 1600–1603 | 1600–1604 | 0.443 |
| Queen Elizabeth's Men | 5 | 5 | 1 | history 3; comedy 1; romance 1 | 3 / 3 (Anonymous 3) | 1589–1592 | 1587–1595 | 0.458 |

## Largest companies — annals (clear values only; uncertain and multiple listed separately in company_coverage.csv)

Dates are the Annals first-performance dates, i.e. the same source as the company value; the other source is in company_coverage.csv (xdate_*).

| company (raw) | works (clear) | same name uncertain | named in multiple values | genres | individual authors / signatures (top person) | Annals years (records in this corpus) | Annals limits | mean included share |
|---|---:|---:|---:|---|---|---|---|---:|
| King's Men | 49 | 2 | 6 | tragedy 19; comedy 13; tragicomedy 11; romance 3; other/multi 2; history 1 | 19 / 25 (Shakespeare, William 12) | 1603–1637 | 1603–1639 | 0.372 |
| Queen Henrietta Maria's Men | 31 | 1 | 1 | comedy 20; tragedy 5; tragicomedy 4; masque 1; pastoral 1 | 10 / 10 (Shirley, James 17) | 1625–1640 | 1619–1640 | 0.424 |
| Lord Chamberlain's (Hunsdon's) Men | 20 | 1 | 1 | comedy 9; history 7; tragedy 3; tragicomedy 1 | 5 / 5 (Shakespeare, William 15) | 1591–1603 | 1590–1604 | 0.344 |
| Children of the Queen's Revels | 16 | 4 | 1 | comedy 8; tragedy 5; history 1; pastoral 1; tragicomedy 1 | 10 / 10 (Marston, John 6) | 1601–1610 | 1601–1611 | 0.363 |
| Admiral's (Nottingham's) Men | 14 | 4 | 0 | comedy 6; tragedy 4; romance 2; history 1; tragicomedy 1 | 12 / 11 (Dekker, Thomas 3) | 1587–1602 | 1587–1602 | 0.266 |
| Children of Paul's (second) | 14 | 4 | 2 | comedy 11; tragedy 2; romance 1 | 8 / 6 (Middleton, Thomas 5) | 1599–1606 | 1599–1607 | 0.411 |
| Queen Anne's Men | 12 | 2 | 1 | comedy 4; history 3; tragedy 2; other/multi 1; romance 1; tragicomedy 1 | 7 / 7 (Heywood, Thomas 6) | 1602–1619 | 1602–1621 | 0.421 |
| Derby's (Strange's) Men | 8 | 1 | 2 | history 3; tragedy 2; comedy 1; moral 1; romance 1 | 6 / 5 (Anonymous 4) | 1587–1601 | 1585–1604 | 0.305 |
| Children of the King's Revels | 7 | 1 | 0 | comedy 5; tragedy 1; tragicomedy 1 | 7 / 6 (Day, John 2) | 1604–1608 | 1604–1610 | 0.332 |
| Prince Henry's Men | 6 | 0 | 0 | comedy 3; history 2; other/multi 1 | 4 / 4 (Dekker, Thomas 4) | 1604–1612 | 1604–1615 | 0.371 |
| Beeston's Boys | 5 | 1 | 0 | comedy 2; tragicomedy 2; other/multi 1 | 5 / 4 (Glapthorne, Henry 2) | 1637–1638 | 1636–1640 | 0.387 |
| Children of Paul's (first) | 5 | 0 | 1 | comedy 4; pastoral 1 | 1 / 1 (Lyly, John 5) | 1585–1591 | 1583–1591 | 0.437 |
| Children of the Chapel (first) (Oxford's Boys) | 5 | 0 | 1 | comedy 2; tragedy 2; pastoral 1 | 6 / 5 (Lyly, John 1) | 1564–1588 | 1564–1594 | 0.531 |
| Lady Elizabeth's Men | 5 | 3 | 0 | comedy 3; tragicomedy 2 | 4 / 4 (Massinger, Philip 2) | 1613–1625 | 1613–1625 | 0.206 |
| Children of the Chapel (second) | 4 | 1 | 1 | comedy 3; moral 1 | 3 / 3 (Jonson, Ben 2) | 1600–1602 | 1600–1602 | 0.408 |

Year ranges are those of the works in this corpus that carry the value, not the company's period of activity. Names are raw DEEP strings; renamings and successions are listed in company_lineage_notes.csv for reference and are not applied.
