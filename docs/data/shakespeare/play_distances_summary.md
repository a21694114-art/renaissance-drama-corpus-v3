# Reading single plays distributionally — topics_B_s42

Each work's profile = its shares of the 53 compared topics, renormalised; genre profiles = equal-weighted means over the genre's works, the work itself left out of its own genre. Distance = Jensen–Shannon divergence (bits). Comedy lean = d(comedy) − d(own genre); the percentile places the work among all works of its genre group (0 = closest to comedy of them all).

## Shakespeare's plays

| genre | play | nearest genre | d(own genre) | d(comedy) | comedy lean | percentile in genre | compared-topic share of words |
|---|---|---|---:|---:|---:|---:|---:|
| comedy | A Midsummer Night's Dream | pastoral | 0.7841 | 0.7841 | — | — | 37 % |
| comedy | As You Like It | pastoral | 0.5711 | 0.5711 | — | — | 55 % |
| comedy | Love's Labor's Lost | romance | 0.6661 | 0.6661 | — | — | 30 % |
| comedy | Much Ado About Nothing | tragicomedy | 0.4735 | 0.4735 | — | — | 50 % |
| comedy | The Comedy of Errors | comedy | 0.562 | 0.562 | — | — | 37 % |
| comedy | The Merchant of Venice (The Jew of Venic | tragicomedy | 0.5225 | 0.5225 | — | — | 38 % |
| comedy | The Merry Wives of Windsor | comedy | 0.7225 | 0.7225 | — | — | 19 % |
| comedy | The Taming of the Shrew | comedy | 0.7482 | 0.7482 | — | — | 15 % |
| comedy | The Tempest | masque | 0.7059 | 0.7059 | — | — | 24 % |
| comedy | The Two Gentlemen of Verona | pastoral | 0.6388 | 0.6388 | — | — | 17 % |
| comedy | Twelfth Night, or What You Will | comedy | 0.8247 | 0.8247 | — | — | 8 % |
| history | 1 Henry the Fourth | history | 0.5417 | 0.8569 | 0.3152 | 57.6 | 21 % |
| history | 1 Henry the Sixth | history | 0.5829 | 0.997 | 0.4141 | 81.8 | 55 % |
| history | 2 Henry the Fourth | romance | 0.6284 | 0.7746 | 0.1463 | 27.3 | 21 % |
| history | 2 Henry the Sixth (The First Part of the | history | 0.2959 | 0.8166 | 0.5208 | 93.9 | 34 % |
| history | 3 Henry the Sixth (The True Tragedy of R | history | 0.5433 | 0.7732 | 0.2299 | 48.5 | 38 % |
| history | Henry the Eighth (All Is True) | history | 0.7045 | 0.8876 | 0.1831 | 30.3 | 31 % |
| history | Henry the Fifth | history | 0.4998 | 0.8825 | 0.3826 | 75.8 | 48 % |
| history | King John | history | 0.4234 | 0.8939 | 0.4705 | 87.9 | 56 % |
| history | Richard the Second | tragicomedy | 0.6789 | 0.694 | 0.0151 | 21.2 | 17 % |
| history | Richard the Third | tragicomedy | 0.41 | 0.6123 | 0.2023 | 36.4 | 34 % |
| history | The Reign of King Edward the Third | history | 0.6399 | 0.8917 | 0.2518 | 51.5 | 49 % |
| romance | Cymbeline, King of Britain | tragedy | 0.7136 | 0.7608 | 0.0472 | 61.1 | 35 % |
| romance | Pericles, Prince of Tyre | pastoral | 0.8085 | 0.8278 | 0.0193 | 50.0 | 8 % |
| romance | The Winter's Tale | tragicomedy | 0.6869 | 0.6916 | 0.0047 | 38.9 | 20 % |
| tragedy | Antony and Cleopatra | tragedy | 0.6396 | 0.9025 | 0.2629 | 78.4 | 21 % |
| tragedy | Coriolanus | tragedy | 0.6759 | 0.9455 | 0.2696 | 81.1 | 69 % |
| tragedy | Hamlet, Prince of Denmark * | tragicomedy | 0.6095 | 0.733 | 0.1235 | 50.5 | 25 % |
| tragedy | Julius Caesar | tragedy | 0.6074 | 0.9077 | 0.3003 | 86.5 | 59 % |
| tragedy | King Lear * | tragicomedy | 0.582 | 0.5754 | -0.0065 | 18.0 | 23 % |
| tragedy | Macbeth | history | 0.7028 | 0.7767 | 0.074 | 38.7 | 21 % |
| tragedy | Master Arden of Faversham in Kent | pastoral | 0.649 | 0.7579 | 0.1089 | 46.8 | 18 % |
| tragedy | Othello, the Moor of Venice * | tragicomedy | 0.5456 | 0.5565 | 0.011 | 24.3 | 25 % |
| tragedy | Romeo and Juliet * | pastoral | 0.8076 | 0.7 | -0.1076 | 5.4 | 35 % |
| tragedy | Timon of Athens | moral | 0.9581 | 0.8033 | -0.1548 | 2.7 | 23 % |
| tragedy | Titus Andronicus | tragedy | 0.503 | 0.8735 | 0.3705 | 98.2 | 39 % |
| tragedy | Troilus and Cressida | pastoral | 0.8106 | 0.8589 | 0.0483 | 30.6 | 71 % |
| tragicomedy | All's Well That Ends Well | comedy | 0.5707 | 0.5386 | -0.032 | 6.9 | 48 % |
| tragicomedy | Measure for Measure | tragicomedy | 0.592 | 0.6139 | 0.022 | 13.8 | 74 % |
| tragicomedy | The Two Noble Kinsmen | tragicomedy | 0.3369 | 0.4126 | 0.0757 | 34.5 | 41 % |

\* Snyder's Comic Matrix four.

## His tragedies ordered by comedy lean (most comedy-leaning first)

| play | comedy lean | with the rest bin | percentile among all tragedies | topics pulling it towards comedy (play % / tragedy mean % / comedy mean %) |
|---|---:|---:|---:|---|
| Timon of Athens | -0.155 | -0.090 | 2.7 | T6 Money, debt and credit (14.34 / 0.26 / 1.81); T35 Fools, wit and railing (5.64 / 0.13 / 0.7); T37 Riches, poverty and covetous (2.96 / 0.05 / 0.11) |
| Romeo and Juliet * | -0.108 | -0.068 | 5.4 | T15 Friars and holy orders in pl (14.38 / 0.32 / 0.7); T4 Love-longing and the lover's (12.2 / 0.77 / 1.82); T33 Fathers, daughters and marri (2.14 / 0.07 / 0.92); T55 Fairies, fairy queens and en (2.05 / 0.0 / 0.13) |
| King Lear * | -0.006 | -0.035 | 18.0 | T11 Siblings, kin and confidants (6.16 / 0.71 / 1.21); T0 Court life: dukes, favour an (8.1 / 4.31 / 4.7); T51 Parents and children: blessi (2.11 / 0.1 / 0.25); T52 Prodigals, portions and poor (2.09 / 0.24 / 0.42) |
| Othello, the Moor of Venice * | +0.011 | -0.025 | 24.3 | T23 Husbands, wives and jealousy (5.6 / 0.45 / 0.95); T4 Love-longing and the lover's (3.95 / 0.85 / 1.82); T0 Court life: dukes, favour an (5.89 / 4.33 / 4.7) |
| Troilus and Cressida | +0.048 | +0.009 | 30.6 | T35 Fools, wit and railing (7.9 / 0.11 / 0.7); T4 Love-longing and the lover's (5.66 / 0.83 / 1.82); T37 Riches, poverty and covetous (2.07 / 0.06 / 0.11) |
| Macbeth | +0.074 | -0.017 | 38.7 | T51 Parents and children: blessi (3.21 / 0.09 / 0.25); T3 Sickness, physic and doctors (2.96 / 0.74 / 2.45) |
| Master Arden of Faversham in Kent | +0.109 | -0.008 | 46.8 | T4 Love-longing and the lover's (5.12 / 0.83 / 1.82) |
| Hamlet, Prince of Denmark * | +0.123 | +0.006 | 50.5 | T9 Theatre talk: prologues, poe (7.51 / 0.26 / 1.29); T26 Devils, hell and fiends (1.85 / 0.3 / 0.88) |
| Antony and Cleopatra | +0.263 | +0.041 | 78.4 | T11 Siblings, kin and confidants (2.13 / 0.75 / 1.21) |
| Coriolanus | +0.270 | +0.112 | 81.1 | T35 Fools, wit and railing (1.95 / 0.16 / 0.7) |
| Julius Caesar | +0.300 | +0.119 | 86.5 | T52 Prodigals, portions and poor (2.44 / 0.24 / 0.42) |
| Titus Andronicus | +0.370 | +0.120 | 98.2 |  |

## For comparison: the ten tragedies of the whole corpus that lean most towards comedy

| play | author | year | comedy lean |
|---|---|---:|---:|
| A Woman Killed with Kindness | Heywood, Thomas | 1607 | -0.186 |
| The Miseries of Enforced Marriage | Wilkins, George | 1607 | -0.175 |
| Love's Sacrifice | Ford, John | 1633 | -0.173 |
| Timon of Athens | Shakespeare, WilliamMiddleton, | 1623 | -0.155 |
| Cupid's Revenge | Beaumont, FrancisFletcher, Joh | 1615 | -0.151 |
| The Revenger's Tragedy | Middleton, Thomas | 1607 | -0.113 |
| Romeo and Juliet | Shakespeare, William | 1623 | -0.108 |
| The Duchess of Malfi | Webster, John | 1623 | -0.105 |
| The Unnatural Combat | Massinger, Philip | 1639 | -0.093 |
| The White Devil (Vittoria Corombona) | Webster, John | 1612 | -0.072 |

Illustrative, not a test: profiles are over the compared topics only (the unassigned rest of each play is not in them), and a play with a small compared-topic share has a rough profile.