# Shakespeare against the rest, within genre — topics_B_s42

Measure: share of a work's words in each topic (representative editions, every chunk in the denominator, works equal-weighted) — the same as the Genre page. Compared topics: 53 (included). Genres with at least 3 Shakespeare works and 10 others: comedy, tragedy, history, tragicomedy, romance. Two variants: "attributed" = every work whose author field names Shakespeare (collaborations and adaptations included), "sole" = author field is Shakespeare alone.

## The works

| genre | work | authors (field) | year | attribution |
|---|---|---|---:|---|
| comedy | A Midsummer Night's Dream | Shakespeare, William | 1600 | sole |
| comedy | As You Like It | Shakespeare, William | 1623 | sole |
| comedy | Love's Labor's Lost | Shakespeare, William | 1598 | sole |
| comedy | Much Ado About Nothing | Shakespeare, William | 1600 | sole |
| comedy | The Comedy of Errors | Shakespeare, William | 1623 | sole |
| comedy | The Merchant of Venice (The Jew of Venice) | Shakespeare, William | 1600 | sole |
| comedy | The Merry Wives of Windsor | Shakespeare, William | 1623 | sole |
| comedy | The Taming of the Shrew | Shakespeare, William | 1623 | sole |
| comedy | The Tempest | Shakespeare, William | 1623 | sole |
| comedy | The Two Gentlemen of Verona | Shakespeare, William | 1623 | sole |
| comedy | Twelfth Night, or What You Will | Shakespeare, William | 1623 | sole |
| history | 1 Henry the Fourth | Shakespeare, William | 1598 | sole |
| history | 1 Henry the Sixth | Anonymous / Marlowe, Christopher / Shake | 1623 | collaborative / adapted |
| history | 2 Henry the Fourth | Shakespeare, William | 1600 | sole |
| history | 2 Henry the Sixth (The First Part of the Contention  | Anonymous / Marlowe, Christopher / Shake | 1600 | collaborative / adapted |
| history | 3 Henry the Sixth (The True Tragedy of Richard Duke  | Anonymous / Marlowe, Christopher / Shake | 1623 | collaborative / adapted |
| history | Henry the Eighth (All Is True) | Shakespeare, William / Fletcher, John | 1623 | collaborative / adapted |
| history | Henry the Fifth | Shakespeare, William | 1600 | sole |
| history | King John | Shakespeare, William | 1623 | sole |
| history | Richard the Second | Shakespeare, William | 1597 | sole |
| history | Richard the Third | Shakespeare, William | 1623 | sole |
| history | The Reign of King Edward the Third | Anonymous / Shakespeare, William | 1596 | collaborative / adapted |
| romance | Cymbeline, King of Britain | Shakespeare, William | 1623 | sole |
| romance | Pericles, Prince of Tyre | Shakespeare, William / Wilkins, George | 1609 | collaborative / adapted |
| romance | The Winter's Tale | Shakespeare, William | 1623 | sole |
| tragedy | Antony and Cleopatra | Shakespeare, William | 1623 | sole |
| tragedy | Coriolanus | Shakespeare, William | 1623 | sole |
| tragedy | Hamlet, Prince of Denmark | Shakespeare, William | 1623 | sole |
| tragedy | Julius Caesar | Shakespeare, William | 1623 | sole |
| tragedy | King Lear | Shakespeare, William | 1608 | sole |
| tragedy | Macbeth | Shakespeare, William / Middleton, Thomas | 1623 | collaborative / adapted |
| tragedy | Master Arden of Faversham in Kent | Anonymous / Kyd, Thomas / Shakespeare, W | 1592 | collaborative / adapted |
| tragedy | Othello, the Moor of Venice | Shakespeare, William | 1623 | sole |
| tragedy | Romeo and Juliet | Shakespeare, William | 1623 | sole |
| tragedy | Timon of Athens | Shakespeare, William / Middleton, Thomas | 1623 | collaborative / adapted |
| tragedy | Titus Andronicus | Peele, George / Shakespeare, William | 1594 | collaborative / adapted |
| tragedy | Troilus and Cressida | Shakespeare, William | 1623 | sole |
| tragicomedy | All's Well That Ends Well | Shakespeare, William / Middleton, Thomas | 1623 | collaborative / adapted |
| tragicomedy | Measure for Measure | Shakespeare, William / Middleton, Thomas | 1623 | collaborative / adapted |
| tragicomedy | The Two Noble Kinsmen | Shakespeare, William / Fletcher, John | 1634 | collaborative / adapted |

## Divergence (one summary per genre)

Jensen–Shannon divergence in bits between the two sides' mean profiles; bootstrap = works resampled within each side; permutation = Shakespeare labels reassigned at random among the genre's works; size-matched = the larger side subsampled to the smaller side's size. A divergence says how far two weightings differ, not what differs — read the composition tables for that.

Reading the columns: the bootstrap interval is biased upward for a side of ten-odd works (resampling duplicates works and roughens the profile), so it should be read as a spread, not as a range that must contain the observed value; the permutation null median is the divergence a random set of the same size shows against the rest, and the size-matched median is the divergence of Shakespeare's set against equally small random sets of the others — the two numbers to compare the observed value with.

| genre | variant | profile | n (S / others) | JSD | 95 % bootstrap | permutation null median | permutation p | size-matched median |
|---|---|---|---:|---:|---|---:|---:|---:|
| comedy | attributed | conditional on the compared topics | 11 / 140 | 0.2129 | 0.2191–0.4024 | 0.196 | 0.3596 | 0.3325 |
| comedy | attributed | compared topics + the rest as one bin | 11 / 140 | 0.0696 | 0.071–0.1327 | 0.0682 | 0.4625 | 0.1076 |
| comedy | sole | conditional on the compared topics | 11 / 140 | 0.2129 | 0.2151–0.3991 | 0.1927 | 0.3187 | 0.3391 |
| comedy | sole | compared topics + the rest as one bin | 11 / 140 | 0.0696 | 0.0706–0.1332 | 0.0678 | 0.4605 | 0.1122 |
| tragedy | attributed | conditional on the compared topics | 12 / 99 | 0.2773 | 0.2603–0.4983 | 0.226 | 0.1698 | 0.3679 |
| tragedy | attributed | compared topics + the rest as one bin | 12 / 99 | 0.1099 | 0.1026–0.2116 | 0.0971 | 0.2947 | 0.1557 |
| tragedy | sole | conditional on the compared topics | 8 / 99 | 0.35 | 0.3132–0.581 | 0.2831 | 0.1798 | 0.4706 |
| tragedy | sole | compared topics + the rest as one bin | 8 / 99 | 0.1458 | 0.1229–0.2758 | 0.1238 | 0.2547 | 0.2008 |
| history | attributed | conditional on the compared topics | 11 / 23 | 0.2948 | 0.2243–0.5194 | 0.2385 | 0.1618 | 0.3367 |
| history | attributed | compared topics + the rest as one bin | 11 / 23 | 0.1099 | 0.0838–0.2107 | 0.092 | 0.2118 | 0.1275 |
| history | sole | conditional on the compared topics | 6 / 23 | 0.2661 | 0.2289–0.5076 | 0.3237 | 0.7822 | 0.3815 |
| history | sole | compared topics + the rest as one bin | 6 / 23 | 0.0946 | 0.0803–0.2004 | 0.1234 | 0.8492 | 0.1384 |
| tragicomedy | attributed | conditional on the compared topics | 3 / 26 | 0.3407 | 0.2721–0.6018 | 0.3579 | 0.5784 | 0.5275 |
| tragicomedy | attributed | compared topics + the rest as one bin | 3 / 26 | 0.1741 | 0.1123–0.41 | 0.1309 | 0.1219 | 0.2487 |
| romance | attributed | conditional on the compared topics | 3 / 15 | 0.5971 | 0.5288–0.8398 | 0.563 | 0.3217 | 0.7129 |
| romance | attributed | compared topics + the rest as one bin | 3 / 15 | 0.1376 | 0.1052–0.2388 | 0.1338 | 0.4486 | 0.1639 |

## Shared inventory

Of each side's words in the compared topics, the share sitting in topics that BOTH sides use (any work), and in topics that reach a mean of 1 % on both sides.

| genre | variant | topics used S / others / both | S words in shared topics | others' words in shared topics | S in both ≥1 % | others in both ≥1 % | S exclusive (of all words) | others exclusive |
|---|---|---|---:|---:|---:|---:|---:|---:|
| comedy | attributed | 33 / 51 / 33 | 100.0 % | 81.4 % | 48.9 % | 40.0 % | 0.00 % | 6.45 % |
| comedy | sole | 33 / 51 / 33 | 100.0 % | 81.4 % | 48.9 % | 40.0 % | 0.00 % | 6.45 % |
| tragedy | attributed | 28 / 51 / 27 | 99.5 % | 73.8 % | 61.1 % | 46.8 % | 0.17 % | 11.16 % |
| tragedy | sole | 20 / 51 / 19 | 99.4 % | 59.8 % | 68.7 % | 46.8 % | 0.26 % | 17.12 % |
| history | attributed | 21 / 29 / 15 | 95.8 % | 71.3 % | 87.3 % | 64.2 % | 1.54 % | 10.87 % |
| history | sole | 18 / 29 / 15 | 96.0 % | 71.3 % | 83.5 % | 68.0 % | 1.33 % | 10.87 % |
| tragicomedy | attributed | 23 / 34 / 16 | 72.5 % | 79.9 % | 45.3 % | 65.6 % | 14.99 % | 6.62 % |
| romance | attributed | 15 / 39 / 13 | 85.1 % | 29.4 % | 25.7 % | 20.7 % | 3.14 % | 17.80 % |

### Genres (all works)

| genre | works | words in topics present in all three core genres (of compared) | in topics ≥ floor in all three | exclusive to this genre among the core |
|---|---:|---:|---:|---:|
| comedy | 151 | 74.2 % | 18.8 % | 0.0 % |
| tragedy | 111 | 76.7 % | 26.5 % | 1.4 % |
| history | 34 | 91.8 % | 13.8 % | 8.2 % |
| tragicomedy | 29 | 84.9 % | 40.2 % | — |
| moral | 28 | 76.1 % | 4.8 % | — |
| romance | 18 | 72.7 % | 11.2 % | — |
| pastoral | 15 | 57.7 % | 8.0 % | — |
| masque | 38 | 73.0 % | 0.0 % | — |

## comedy — attributed: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T4 Love-longing and the lover's complaint | 4.36 % (5/11) | 1.62 % (41/140) | +2.73 | A Midsummer Night's Dream 32 %; As You Like It 24 %; Love's Labor's Lost 23 % | The Fair Maid of the Exchange (Anonymous) 7 %; top author Marston, John 16 % |
| T8 Captains, gallants and cheats | 0.00 % (0/11) | 1.86 % (27/140) | -1.86 | — | The Puritan, or The Widow of Watling (Middleton, Thomas) 11 %; top author Middleton, Thomas 23 % |
| T55 Fairies, fairy queens and enchanted desi | 1.54 % (2/11) | 0.01 % (1/140) | +1.52 | A Midsummer Night's Dream 72 %; The Merry Wives of Windsor 28 % **one play** | The Jealous Lovers (Randolph, Thomas) 100 %; top author Randolph, Thomas 100 % **one play** |
| T22 Shepherds, flocks and Pan | 1.72 % (2/11) | 0.36 % (8/140) | +1.36 | As You Like It 85 %; The Two Gentlemen of Verona 15 % **one play** | The Maid's Metamorphosis (Anonymous) 29 %; top author Lyly, John 29 % |
| T27 Uncles, nephews and cousins: kinship and | 0.00 % (0/11) | 1.32 % (37/140) | -1.32 | — | The City Match (Mayne, Jasper) 11 %; top author Middleton, Thomas 18 % |
| T9 Theatre talk: prologues, poets and playe | 0.22 % (1/11) | 1.37 % (41/140) | -1.15 | As You Like It 100 % **one play** | The Antipodes (Brome, Richard) 8 %; top author Jonson, Ben 34 % |
| T3 Sickness, physic and doctors | 1.39 % (3/11) | 2.54 % (40/140) | -1.14 | The Merry Wives of Windsor 46 %; The Merchant of Venice (The Jew of 32 %; The Comedy of Errors 22 % | The Family of Love (Barry, Lording) 13 %; top author Jonson, Ben 22 % |
| T32 Rings and jewels as tokens | 1.57 % (3/11) | 0.49 % (17/140) | +1.08 | The Merchant of Venice (The Jew of 45 %; The Comedy of Errors 38 %; The Two Gentlemen of Verona 18 % | The Two Merry Milkmaids, or The Best (Cumber, John) 22 %; top author Cumber, John 22 % |
| T11 Siblings, kin and confidants | 0.22 % (1/11) | 1.29 % (39/140) | -1.07 | The Taming of the Shrew 100 % **one play** | Greene's Tu Quoque, or The City Gall (Cooke, John) 9 %; top author Nabbes, Thomas 10 % |
| T24 Apollo, Phoebus and the Muses | 0.00 % (0/11) | 1.04 % (12/140) | -1.04 | — | Apollo Shroving (Hawkins, William) 44 %; top author Hawkins, William 44 % |
| T0 Court life: dukes, favour and honour | 3.84 % (6/11) | 4.76 % (41/140) | -0.92 | Much Ado About Nothing 23 %; The Tempest 22 %; As You Like It 21 % | The Opportunity (Shirley, James) 13 %; top author Shirley, James 44 % |
| T45 Widows, wooing and remarriage | 0.00 % (0/11) | 0.86 % (14/140) | -0.86 | — | A Trick to Catch the Old One (Middleton, Thomas) 26 %; top author Middleton, Thomas 32 % |

## comedy — sole: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T4 Love-longing and the lover's complaint | 4.36 % (5/11) | 1.62 % (41/140) | +2.73 | A Midsummer Night's Dream 32 %; As You Like It 24 %; Love's Labor's Lost 23 % | The Fair Maid of the Exchange (Anonymous) 7 %; top author Marston, John 16 % |
| T8 Captains, gallants and cheats | 0.00 % (0/11) | 1.86 % (27/140) | -1.86 | — | The Puritan, or The Widow of Watling (Middleton, Thomas) 11 %; top author Middleton, Thomas 23 % |
| T55 Fairies, fairy queens and enchanted desi | 1.54 % (2/11) | 0.01 % (1/140) | +1.52 | A Midsummer Night's Dream 72 %; The Merry Wives of Windsor 28 % **one play** | The Jealous Lovers (Randolph, Thomas) 100 %; top author Randolph, Thomas 100 % **one play** |
| T22 Shepherds, flocks and Pan | 1.72 % (2/11) | 0.36 % (8/140) | +1.36 | As You Like It 85 %; The Two Gentlemen of Verona 15 % **one play** | The Maid's Metamorphosis (Anonymous) 29 %; top author Lyly, John 29 % |
| T27 Uncles, nephews and cousins: kinship and | 0.00 % (0/11) | 1.32 % (37/140) | -1.32 | — | The City Match (Mayne, Jasper) 11 %; top author Middleton, Thomas 18 % |
| T9 Theatre talk: prologues, poets and playe | 0.22 % (1/11) | 1.37 % (41/140) | -1.15 | As You Like It 100 % **one play** | The Antipodes (Brome, Richard) 8 %; top author Jonson, Ben 34 % |
| T3 Sickness, physic and doctors | 1.39 % (3/11) | 2.54 % (40/140) | -1.14 | The Merry Wives of Windsor 46 %; The Merchant of Venice (The Jew of 32 %; The Comedy of Errors 22 % | The Family of Love (Barry, Lording) 13 %; top author Jonson, Ben 22 % |
| T32 Rings and jewels as tokens | 1.57 % (3/11) | 0.49 % (17/140) | +1.08 | The Merchant of Venice (The Jew of 45 %; The Comedy of Errors 38 %; The Two Gentlemen of Verona 18 % | The Two Merry Milkmaids, or The Best (Cumber, John) 22 %; top author Cumber, John 22 % |
| T11 Siblings, kin and confidants | 0.22 % (1/11) | 1.29 % (39/140) | -1.07 | The Taming of the Shrew 100 % **one play** | Greene's Tu Quoque, or The City Gall (Cooke, John) 9 %; top author Nabbes, Thomas 10 % |
| T24 Apollo, Phoebus and the Muses | 0.00 % (0/11) | 1.04 % (12/140) | -1.04 | — | Apollo Shroving (Hawkins, William) 44 %; top author Hawkins, William 44 % |
| T0 Court life: dukes, favour and honour | 3.84 % (6/11) | 4.76 % (41/140) | -0.92 | Much Ado About Nothing 23 %; The Tempest 22 %; As You Like It 21 % | The Opportunity (Shirley, James) 13 %; top author Shirley, James 44 % |
| T45 Widows, wooing and remarriage | 0.00 % (0/11) | 0.86 % (14/140) | -0.86 | — | A Trick to Catch the Old One (Middleton, Thomas) 26 %; top author Middleton, Thomas 32 % |

## tragedy — attributed: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T2 Roman politics: senate, consuls and civi | 11.86 % (4/12) | 5.73 % (23/99) | +6.13 | Coriolanus 45 %; Julius Caesar 38 %; Titus Andronicus 11 % | Catiline His Conspiracy (Jonson, Ben) 15 %; top author Jonson, Ben 27 % |
| T0 Court life: dukes, favour and honour | 1.17 % (2/12) | 4.73 % (19/99) | -3.56 | King Lear 58 %; Othello, the Moor of Venice 42 % **one play** | The Revenger's Tragedy (Middleton, Thomas) 14 %; top author Shirley, James 19 % |
| T1 Death, grief and revenge | 3.98 % (8/12) | 7.06 % (72/99) | -3.08 | Hamlet, Prince of Denmark 26 %; Master Arden of Faversham in Kent 26 %; Othello, the Moor of Venice 12 % | Antonio's Revenge (2 Antonio and Mel (Marston, John) 5 %; top author Massinger, Philip 8 % |
| T17 Eastern conquest: Persians, Turks and so | 0.00 % (0/12) | 2.69 % (12/99) | -2.69 | — | 1 Tamburlaine the Great (Marlowe, Christopher) 26 %; top author Marlowe, Christopher 40 % |
| T7 The Trojan war: conflict and its afterma | 4.80 % (2/12) | 2.39 % (12/99) | +2.42 | Troilus and Cressida 97 %; Hamlet, Prince of Denmark 3 % **one play** | Troas (Seneca's Sixth Tragedy) (Heywood, Jasper / Sene) 41 %; top author Seneca, Lucius Annaeus 69 % |
| T4 Love-longing and the lover's complaint | 2.24 % (4/12) | 0.71 % (20/99) | +1.54 | Romeo and Juliet 45 %; Troilus and Cressida 21 %; Master Arden of Faversham in Kent 19 % | The Wars of Cyrus, King of Persia (Anonymous) 11 %; top author Marston, John 18 % |
| T20 Hercules: labours, suffering and virtue | 0.00 % (0/12) | 1.45 % (6/99) | -1.45 | — | Hercules Oetaeus (Hercules on Mount  (Seneca, Lucius Annaeus) 54 %; top author Seneca, Lucius Annaeus 96 % **one play** |
| T36 Hell, Furies and the language of punishm | 0.00 % (0/12) | 1.45 % (21/99) | -1.45 | — | Oedipus (Seneca's Fifth Tragedy) (Seneca, Lucius Annaeus) 19 %; top author Seneca, Lucius Annaeus 56 % |
| T25 Kings, power and law: political sententi | 0.25 % (1/12) | 1.65 % (19/99) | -1.41 | Macbeth 100 % **one play** | Mustapha (Greville, Fulke) 38 %; top author Greville, Fulke 53 % |
| T35 Fools, wit and railing | 1.29 % (3/12) | 0.04 % (2/99) | +1.25 | Troilus and Cressida 51 %; Timon of Athens 36 %; Coriolanus 13 % **one play** | The Cruel Brother (Davenant, William) 65 %; top author Davenant, William 65 % **one play** |
| T34 Thebes and royal catastrophe: siege, sla | 0.22 % (1/12) | 1.46 % (11/99) | -1.24 | Titus Andronicus 100 % **one play** | Antigone, the Theban Princess (May, Thomas) 33 %; top author May, Thomas 38 % |
| T59 Spanish courts: war, honour and courtshi | 0.00 % (0/12) | 1.24 % (8/99) | -1.24 | — | 1 Jeronimo, with the Wars of Portuga (Anonymous) 64 %; top author Anonymous 64 % **one play** |

## tragedy — sole: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T2 Roman politics: senate, consuls and civi | 15.81 % (3/8) | 5.73 % (23/99) | +10.08 | Coriolanus 51 %; Julius Caesar 42 %; Antony and Cleopatra 7 % **one play** | Catiline His Conspiracy (Jonson, Ben) 15 %; top author Jonson, Ben 27 % |
| T7 The Trojan war: conflict and its afterma | 7.20 % (2/8) | 2.39 % (12/99) | +4.82 | Troilus and Cressida 97 %; Hamlet, Prince of Denmark 3 % **one play** | Troas (Seneca's Sixth Tragedy) (Heywood, Jasper / Sene) 41 %; top author Seneca, Lucius Annaeus 69 % |
| T1 Death, grief and revenge | 3.38 % (5/8) | 7.06 % (72/99) | -3.68 | Hamlet, Prince of Denmark 46 %; Othello, the Moor of Venice 21 %; King Lear 15 % | Antonio's Revenge (2 Antonio and Mel (Marston, John) 5 %; top author Massinger, Philip 8 % |
| T0 Court life: dukes, favour and honour | 1.75 % (2/8) | 4.73 % (19/99) | -2.98 | King Lear 58 %; Othello, the Moor of Venice 42 % **one play** | The Revenger's Tragedy (Middleton, Thomas) 14 %; top author Shirley, James 19 % |
| T17 Eastern conquest: Persians, Turks and so | 0.00 % (0/8) | 2.69 % (12/99) | -2.69 | — | 1 Tamburlaine the Great (Marlowe, Christopher) 26 %; top author Marlowe, Christopher 40 % |
| T4 Love-longing and the lover's complaint | 2.73 % (3/8) | 0.71 % (20/99) | +2.02 | Romeo and Juliet 56 %; Troilus and Cressida 26 %; Othello, the Moor of Venice 18 % **one play** | The Wars of Cyrus, King of Persia (Anonymous) 11 %; top author Marston, John 18 % |
| T25 Kings, power and law: political sententi | 0.00 % (0/8) | 1.65 % (19/99) | -1.65 | — | Mustapha (Greville, Fulke) 38 %; top author Greville, Fulke 53 % |
| T34 Thebes and royal catastrophe: siege, sla | 0.00 % (0/8) | 1.46 % (11/99) | -1.46 | — | Antigone, the Theban Princess (May, Thomas) 33 %; top author May, Thomas 38 % |
| T20 Hercules: labours, suffering and virtue | 0.00 % (0/8) | 1.45 % (6/99) | -1.45 | — | Hercules Oetaeus (Hercules on Mount  (Seneca, Lucius Annaeus) 54 %; top author Seneca, Lucius Annaeus 96 % **one play** |
| T36 Hell, Furies and the language of punishm | 0.00 % (0/8) | 1.45 % (21/99) | -1.45 | — | Oedipus (Seneca's Fifth Tragedy) (Seneca, Lucius Annaeus) 19 %; top author Seneca, Lucius Annaeus 56 % |
| T15 Friars and holy orders in plot | 1.80 % (1/8) | 0.36 % (7/99) | +1.44 | Romeo and Juliet 100 % **one play** | The Jew of Malta (Marlowe, Christopher) 31 %; top author Marlowe, Christopher 57 % |
| T59 Spanish courts: war, honour and courtshi | 0.00 % (0/8) | 1.24 % (8/99) | -1.24 | — | 1 Jeronimo, with the Wars of Portuga (Anonymous) 64 %; top author Anonymous 64 % **one play** |

## history — attributed: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T10 England and France: war, embassy and pea | 13.45 % (6/11) | 3.19 % (6/23) | +10.26 | The Reign of King Edward the Third 30 %; 1 Henry the Sixth 24 %; Henry the Fifth 24 % | 1 The Troublesome Reign of King John (Anonymous) 35 %; top author Anonymous 57 % |
| T18 Rebels, barons and the king's wars at ho | 3.11 % (5/11) | 9.16 % (9/23) | -6.05 | 2 Henry the Sixth (The First Part  27 %; 2 Henry the Fourth 25 %; 1 Henry the Fourth 25 % | The Valiant Scot (W., J.) 30 %; top author Anonymous 31 % |
| T43 York and Lancaster: dynastic claims and  | 5.77 % (6/11) | 1.78 % (6/23) | +3.99 | 1 Henry the Sixth 31 %; 3 Henry the Sixth (The True Traged 30 %; 2 Henry the Sixth (The First Part  20 % | 1 The Troublesome Reign of King John (Anonymous) 43 %; top author Anonymous 69 % |
| T5 Christian faith, sin and salvation | 0.00 % (0/11) | 3.15 % (2/23) | -3.15 | — | The Love of King David and Fair Bath (Peele, George) 97 %; top author Peele, George 97 % **one play** |
| T15 Friars and holy orders in plot | 0.00 % (0/11) | 2.33 % (4/23) | -2.33 | — | Edward the First (Peele, George) 52 %; top author Peele, George 52 % **one play** |
| T6 Money, debt and credit | 0.00 % (0/11) | 1.62 % (5/23) | -1.62 | — | Thomas Lord Cromwell (S., W.) 41 %; top author S., W. 41 % |
| T0 Court life: dukes, favour and honour | 2.27 % (6/11) | 3.27 % (3/23) | -1.00 | Richard the Third 29 %; Richard the Second 19 %; 3 Henry the Sixth (The True Traged 17 % | The Duchess of Suffolk (Drue, Thomas) 68 %; top author Drue, Thomas 68 % **one play** |
| T2 Roman politics: senate, consuls and civi | 0.00 % (0/11) | 0.92 % (2/23) | -0.91 | — | Fuimus Troes (The True Trojans) (Fisher, Jasper) 71 %; top author Fisher, Jasper 71 % **one play** |
| T7 The Trojan war: conflict and its afterma | 0.00 % (0/11) | 0.60 % (2/23) | -0.60 | — | Fuimus Troes (The True Trojans) (Fisher, Jasper) 85 %; top author Fisher, Jasper 85 % **one play** |
| T30 Constables, justices and the watch | 0.00 % (0/11) | 0.56 % (2/23) | -0.56 | — | When You See Me You Know Me (Henry t (Rowley, Samuel) 64 %; top author Rowley, Samuel 64 % **one play** |
| T14 Royal love, favour and dynastic relation | 0.90 % (3/11) | 1.44 % (4/23) | -0.54 | 2 Henry the Fourth 42 %; Richard the Third 37 %; Henry the Eighth (All Is True) 21 % | 1 If You Know Not Me You Know Nobody (Heywood, Thomas) 80 %; top author Heywood, Thomas 87 % **one play** |
| T47 Knaves, thieves and bawds | 0.56 % (1/11) | 0.10 % (1/23) | +0.46 | 1 Henry the Fourth 100 % **one play** | 1 Edward the Fourth (Heywood, Thomas) 100 %; top author Heywood, Thomas 100 % **one play** |

## history — sole: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T10 England and France: war, embassy and pea | 10.48 % (2/6) | 3.19 % (6/23) | +7.29 | Henry the Fifth 57 %; King John 43 % **one play** | 1 The Troublesome Reign of King John (Anonymous) 35 %; top author Anonymous 57 % |
| T18 Rebels, barons and the king's wars at ho | 4.16 % (4/6) | 9.16 % (9/23) | -5.00 | 2 Henry the Fourth 35 %; 1 Henry the Fourth 34 %; Henry the Fifth 17 % | The Valiant Scot (W., J.) 30 %; top author Anonymous 31 % |
| T5 Christian faith, sin and salvation | 0.00 % (0/6) | 3.15 % (2/23) | -3.15 | — | The Love of King David and Fair Bath (Peele, George) 97 %; top author Peele, George 97 % **one play** |
| T15 Friars and holy orders in plot | 0.00 % (0/6) | 2.33 % (4/23) | -2.33 | — | Edward the First (Peele, George) 52 %; top author Peele, George 52 % **one play** |
| T31 Popes, cardinals and the crown | 1.63 % (1/6) | 3.33 % (5/23) | -1.69 | King John 100 % **one play** | When You See Me You Know Me (Henry t (Rowley, Samuel) 46 %; top author Rowley, Samuel 46 % |
| T6 Money, debt and credit | 0.00 % (0/6) | 1.62 % (5/23) | -1.62 | — | Thomas Lord Cromwell (S., W.) 41 %; top author S., W. 41 % |
| T1 Death, grief and revenge | 3.24 % (4/6) | 2.11 % (10/23) | +1.12 | King John 49 %; Richard the Third 28 %; Richard the Second 12 % | The Famous History of Sir Thomas Wya (Heywood, Thomas / Dekk) 28 %; top author Heywood, Thomas 45 % |
| T47 Knaves, thieves and bawds | 1.02 % (1/6) | 0.10 % (1/23) | +0.92 | 1 Henry the Fourth 100 % **one play** | 1 Edward the Fourth (Heywood, Thomas) 100 %; top author Heywood, Thomas 100 % **one play** |
| T2 Roman politics: senate, consuls and civi | 0.00 % (0/6) | 0.92 % (2/23) | -0.91 | — | Fuimus Troes (The True Trojans) (Fisher, Jasper) 71 %; top author Fisher, Jasper 71 % **one play** |
| T39 Profit, conscience and dishonest dealing | 0.68 % (1/6) | 0.00 % (0/23) | +0.68 | Henry the Fifth 100 % **one play** | — |
| T0 Court life: dukes, favour and honour | 2.64 % (3/6) | 3.27 % (3/23) | -0.63 | Richard the Third 45 %; Richard the Second 30 %; Henry the Fifth 25 % | The Duchess of Suffolk (Drue, Thomas) 68 %; top author Drue, Thomas 68 % **one play** |
| T7 The Trojan war: conflict and its afterma | 0.00 % (0/6) | 0.60 % (2/23) | -0.60 | — | Fuimus Troes (The True Trojans) (Fisher, Jasper) 85 %; top author Fisher, Jasper 85 % **one play** |

## tragicomedy — attributed: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T15 Friars and holy orders in plot | 9.96 % (1/3) | 0.00 % (0/26) | +9.97 | Measure for Measure 100 % **one play** | — |
| T0 Court life: dukes, favour and honour | 11.70 % (3/3) | 5.53 % (10/26) | +6.17 | All's Well That Ends Well 55 %; Measure for Measure 27 %; The Two Noble Kinsmen 18 % **one play** | The Malcontent (Marston, John) 45 %; top author Marston, John 45 % |
| T32 Rings and jewels as tokens | 4.39 % (1/3) | 0.53 % (1/26) | +3.85 | All's Well That Ends Well 100 % **one play** | A Challenge for Beauty (Heywood, Thomas) 100 %; top author Heywood, Thomas 100 % **one play** |
| T40 Sin, guilt and violent loss within famil | 3.94 % (1/3) | 0.09 % (1/26) | +3.85 | Measure for Measure 100 % **one play** | The Lost Lady (Berkeley, William) 100 %; top author Berkeley, William 100 % **one play** |
| T1 Death, grief and revenge | 5.19 % (2/3) | 8.27 % (19/26) | -3.08 | Measure for Measure 75 %; The Two Noble Kinsmen 25 % **one play** | 1 The Cid (The Valiant Cid) (Rutter, Joseph / Corne) 17 %; top author Anonymous 21 % |
| T14 Royal love, favour and dynastic relation | 1.33 % (1/3) | 3.24 % (9/26) | -1.90 | The Two Noble Kinsmen 100 % **one play** | Philaster, or Love Lies a-Bleeding (Beaumont, Francis / Fl) 33 %; top author Beaumont, Francis 45 % |
| T50 Fleets, armies and generals: war by sea  | 0.00 % (0/3) | 1.48 % (6/26) | -1.48 | — | The Young Admiral (Shirley, James) 51 %; top author Shirley, James 51 % **one play** |
| T34 Thebes and royal catastrophe: siege, sla | 1.32 % (1/3) | 0.00 % (0/26) | +1.32 | The Two Noble Kinsmen 100 % **one play** | — |
| T5 Christian faith, sin and salvation | 1.58 % (1/3) | 0.41 % (2/26) | +1.17 | Measure for Measure 100 % **one play** | A Knack to Know an Honest Man (Anonymous) 75 %; top author Anonymous 75 % **one play** |
| T3 Sickness, physic and doctors | 2.98 % (2/3) | 1.82 % (5/26) | +1.15 | All's Well That Ends Well 77 %; The Two Noble Kinsmen 23 % **one play** | The Fair Maid of Bristol (Anonymous) 36 %; top author Anonymous 36 % |
| T47 Knaves, thieves and bawds | 0.79 % (1/3) | 0.00 % (0/26) | +0.79 | Measure for Measure 100 % **one play** | — |
| T30 Constables, justices and the watch | 0.77 % (1/3) | 0.00 % (0/26) | +0.77 | Measure for Measure 100 % **one play** | — |

## romance — attributed: the twelve largest differences

| topic | Shakespeare mean (works with it) | others mean (works with it) | diff (pp) | his side supplied by | their side supplied by |
|---|---:|---:|---:|---|---|
| T22 Shepherds, flocks and Pan | 0.00 % (0/3) | 2.79 % (2/15) | -2.79 | — | Mucedorus (and Amadine) (Anonymous) 89 %; top author Anonymous 89 % **one play** |
| T17 Eastern conquest: Persians, Turks and so | 0.00 % (0/3) | 2.72 % (4/15) | -2.72 | — | The Four Prentices of London (Heywood, Thomas) 45 %; top author Heywood, Thomas 51 % |
| T4 Love-longing and the lover's complaint | 0.00 % (0/3) | 2.69 % (5/15) | -2.69 | — | Blurt, Master Constable, or The Span (Anonymous) 51 %; top author Anonymous 62 % **one play** |
| T32 Rings and jewels as tokens | 2.46 % (1/3) | 0.00 % (0/15) | +2.46 | Cymbeline, King of Britain 100 % **one play** | — |
| T38 Death, parting and grief at court | 2.49 % (2/3) | 0.17 % (1/15) | +2.32 | The Winter's Tale 50 %; Cymbeline, King of Britain 50 % **one play** | A Shoemaker a Gentleman (Rowley, William) 100 %; top author Rowley, William 100 % **one play** |
| T2 Roman politics: senate, consuls and civi | 2.37 % (1/3) | 0.50 % (1/15) | +1.87 | Cymbeline, King of Britain 100 % **one play** | A Shoemaker a Gentleman (Rowley, William) 100 %; top author Rowley, William 100 % **one play** |
| T60 Imperial Rome: rulers, favour and politi | 1.86 % (1/3) | 0.18 % (1/15) | +1.68 | Cymbeline, King of Britain 100 % **one play** | The Trial of Chivalry (This Gallant  (Anonymous) 100 %; top author Anonymous 100 % **one play** |
| T10 England and France: war, embassy and pea | 0.00 % (0/3) | 1.37 % (3/15) | -1.37 | — | Orlando Furioso (Greene, Robert) 65 %; top author Greene, Robert 65 % **one play** |
| T8 Captains, gallants and cheats | 0.00 % (0/3) | 1.26 % (4/15) | -1.26 | — | The Trial of Chivalry (This Gallant  (Anonymous) 40 %; top author Anonymous 63 % |
| T18 Rebels, barons and the king's wars at ho | 0.00 % (0/3) | 1.18 % (2/15) | -1.18 | — | George a Green, the Pinner of Wakefi (Greene, Robert) 70 %; top author Greene, Robert 100 % **one play** |
| T0 Court life: dukes, favour and honour | 0.00 % (0/3) | 1.15 % (2/15) | -1.15 | — | Blurt, Master Constable, or The Span (Anonymous) 69 %; top author Anonymous 100 % **one play** |
| T12 Olympian gods: Jupiter, Juno, Venus and  | 1.30 % (2/3) | 0.15 % (1/15) | +1.14 | The Winter's Tale 52 %; Cymbeline, King of Britain 48 % **one play** | The Strange Discovery (Gough, J.) 100 %; top author Gough, J. 100 % **one play** |

Reading: a difference carried by one play is a fact about that play, not about the author; a difference spread over many works on both sides is the kind that supports a claim. Nothing here removes, merges or subsets topics.