#!/usr/bin/env python3
"""01c_mask_names.py — a name-masked copy of the chunk texts, for a second embedding run.

    python 01c_mask_names.py --chunks <chunks_w500> --manifest <corpus_manifest.csv>
                             [--cast <cast_names_kim.csv>] [--overrides <csv>] [--placeholder someone]

Follows the mechanism of Kim's character-clustering pipeline (early-modern-drama-character-clustering,
code/02_build_character_documents.py, 2026-07): names are identified PER PLAY from that play's own cast
list, role words are never masked, and a cast name that is also a common English word is masked only
when it is capitalised. Differences, deliberate (this project asks about subject matter, not characters):
only PERSON names are masked — places, nations and deities are kept, since they are part of the subject
matter to be compared; repeated placeholders are not collapsed; nothing is averaged.

Steps, per edition of Grace's corpus:
  1. cast list = Kim's character table (data/corpus_master.xlsx sheet `characters`, exported to
     ab_spelling/cast_names_kim.csv: TCP, normalized name, speech-prefix forms) matched on the
     manifest's unit_ids (= Kim's TCP stem); an edition without a direct match falls back to the union
     of Kim's parts under the same base TCP ("base match"); the cast of every edition of the same work is
     pooled (same characters). Editions with no match at all are LISTED (name_mask_report.csv,
     matched = none) and left unmasked — rare capitalised words are never taken for names on their own.
  2. name tokens = every word of >= 3 letters in the normalized name (>= 4 in a prefix form: "For." "But."
     are abbreviations), minus role / title / sacred words (Kim's ROLE_WORDS + SACRED_KEEP), function
     words (Kim's FUNCTION_WORDS idea), personified abstractions (Love, Time, Fortune), countries /
     nations and the classical deities — "QUEEN MAB" contributes mab, not queen; a masque's Cupid stays.
  3. spelling variants: a capitalised-only token that is frequent in THIS edition (>= 3, capitalised in
     >= 90 % of its occurrences there) and within edit-similarity 0.85 of a cast token — or equal to it
     after I/J and u/v normalisation — is masked as a variant (Ieronimo ~ Hieronimo, Iuliet ~ Juliet).
     Frequent capitalised-only tokens that match nothing are written to name_mask_suggestions.csv for
     review, NOT masked.
  4. common-word protection: a cast token whose lower-case form occurs >= --common-min times in the
     corpus (bacon, frank, will, grace, page, rose ...) is masked only when it is capitalised; other
     cast tokens are masked in any case (sempronio printed lower-case is still Sempronio).
  5. overrides (--overrides, default ab_spelling/name_mask_overrides.csv if present): columns
     scope, token, decision[, note] — scope = work_id, edition_id or *; decision = mask | keep. A
     "mask" override masks the token in that scope even when no cast list has it; a "keep" override
     protects it. Overrides win over everything.
Masked tokens and their genitives (Calisto's, Calistos) become --placeholder ("someone", as Kim).

Writes to <chunks>/:
  chunks_B_masked.csv        chunk_id,text — the model input (same rows / order as chunks_B.csv)
  name_mask_report.csv       one row per edition: matched TCP(s), how, cast tokens, tokens masked, top names
  name_mask_tokens.csv       every masked token per edition with count and source (cast | variant | override)
  name_mask_suggestions.csv  frequent capitalised-only tokens NOT masked (no cast match) — review, add overrides
  name_mask_summary.json     totals, parameters, sha256 of chunks_B_masked.csv (02_embed records it too)
  chunks_B_masked.hashes.csv per-chunk sha1 of the masked text; chunks_B_masked.prev.csv + name_mask_changed_chunks.csv
                             when a previous masked text existed — 02_embed --reuse-from re-embeds only the changed chunks
  cast map overrides: ab_spelling/cast_map_overrides.csv (edition_id,kim_tcp,note) forces the cast list of an edition
                             (e.g. 1087 The Muses' Looking Glass → A10411.1: the manifest's unit id points at the wrong part)
Everything downstream keeps using the original chunks_B.csv for display, keywords and reading packs.
"""
import argparse, csv, difflib, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path

TOKEN = re.compile(r"[A-Za-z][A-Za-z'’]*")
NAME_CLEAN = re.compile(r"[^A-Za-z'’\- ]+")

# Kim 2026, code/02_build_character_documents.py — ROLE_WORDS (+ SACRED_KEEP): never masked
ROLE_WORDS = set("""
king queen prince princess duke duchess emperor empress lord lords lady ladies earl count countess baron knight squire sir madam
master mistress gentleman gentlemen gentlewoman gentlewomen citizen citizens courtier courtiers senator senators tribune consul
governor viceroy ambassador herald marshal general captain lieutenant sergeant soldier soldiers officer officers guard guards watch
watchman watchmen constable sheriff mayor alderman bailiff beadle justice judge lawyer notary clerk scrivener crier jailer jailor
gaoler keeper executioner hangman messenger post nuntius servant servants servingman serving-man attendant attendants page boy boys
girl lackey footman groom usher steward butler porter chamberlain hostess host drawer tapster vintner ostler cook carrier carter
clown fool jester vice musician musicians singer dancer actor player players prologue epilogue chorus presenter poet author priest
parson vicar curate friar monk abbot abbess nun bishop archbishop cardinal pope chaplain flamen prophet prophetess soothsayer augur
sibyl oracle doctor physician surgeon apothecary scholar student pedant tutor schoolmaster merchant mercer draper goldsmith jeweller
broker usurer banker pedlar chapman prentice apprentice tailor barber smith tanner weaver tinker cobbler shoemaker botcher miller
baker butcher brewer grocer fishwife sempster shepherd shepherdess herdsman ploughman farmer gardener forester hunter huntsman
falconer fisherman sailor sailors mariner mariners boatswain pilot pirate soldado beggar beggars thief thieves rogue rogues outlaw
outlaws bandit gipsy gypsy pander bawd courtesan whore wench man men woman women maid maids maiden virgin wife wives husband widow
widower mother father son sons daughter daughters brother brothers sister sisters uncle aunt nephew niece cousin grandam grandsire
nurse child children infant old young first second third fourth fifth ghost spirit spirits angel angels devil devils demon fiend
fury furies witch witches wizard conjurer magician enchanter fairy fairies nymph nymphs satyr satyrs muse muses genius shade sexton
gravedigger trumpeter drummer ensign standard-bearer scout spy hermit pilgrim palmer traveller stranger strangers neighbour
neighbours gossip crowd rabble mob omnes all both others another everyone dame sirrah goodman goodwife gaffer gammer signior signor
seignior monsieur madame mounsieur don donna senor tyrant conqueror champion warrior victor rebel rebels traitor traitors villain
villains slave slaves captive captives prisoner prisoners enemy enemies friend friends lover lovers paramour
god gods christ jesus jehovah heaven
mr mrs sr dr saint st
""".split())

# closed-class words: speech prefixes are often abbreviated ("For." Fortunio, "But." Butler, "Her." Hermione) and would
# otherwise poison the gazetteer (Kim's FUNCTION_WORDS); sklearn's list + the early-modern forms of 03_topics.py
FUNCTION_WORDS = set("""
thou thee thy thine ye hath doth art shalt hast didst wilt shall would could might must unto tis haue doe ile vs wil hee saye nowe
maye theyr dyd whiche mee vnto don come good man did make let like owe yet thus may go goe goeth came cometh yes yea nay say sayst
know knowest speak speaketh speake think thinkest thinke sir hys thys wyll yf hym suche nat wolde thu shee selfe le em se soft
verily marry troth well oh bee ha ane syr tyme lyke whych yow neuer th whil whilst vpon vppon vp vntill giue tell told telleth myne
longe for but not with her nor him his she they them then than that this these those when where why how who whom what which
all any both each few more most other some such own same too very can will just now here there once again ever never
""".split())
try:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    FUNCTION_WORDS |= set(ENGLISH_STOP_WORDS)
except Exception:
    pass

# kept on purpose (first version masks PERSONS only): personified abstractions that speak in moralities and masques,
# countries / nations / peoples, and the classical deities — all of them subject matter to be compared, not one play's people
PERSONIFICATIONS = set("""
love time fortune death nature conscience virtue vice wit folly pride envy wrath sloth lust gluttony avarice covetousness mercy
justice peace truth hope faith charity fame honour honor wisdom science reason fancy pleasure riches poverty youth age health wealth
mischief iniquity hypocrisy courage valour chastity beauty liberty tyranny war plenty famine night day sleep dream echo rumour rumor
mankind everyman world flesh soul body sin grace glory victory triumph concord discord peace order chaos silence fear
usury fraud money lucre simony bribery flattery ambition despair idleness labour labor industry knowledge ignorance error custom
""".split())
NATIONS = set("""
france england spain italy rome greece troy denmark scotland ireland wales britain germany flanders holland portugal turkey persia
egypt india africa europe asia venice florence naples milan athens thebes carthage sparta london paris navarre burgundy austria
bohemia hungary poland russia sweden norway castile aragon sicily cyprus rhodes malta arabia syria judea israel babylon assyria
french english spanish italian welsh irish scottish scots dutch german turkish turk turks danish roman romans greek greeks trojan trojans
british briton britons moor moors jew jews indian persian egyptian venetian florentine
""".split())
DEITIES = set("""
jupiter iupiter jove ioue iove juno iuno venus cupid mars apollo phoebus diana cynthia mercury hermes neptune pluto bacchus vulcan
pallas minerva ceres saturn hymen hercules alcides fortune flora aurora boreas zephyrus thetis proteus iris hecate luna sol phoebe
pan silvanus faunus priapus vesta janus ianus bellona nemesis morpheus somnus aeolus oceanus tethys titan atlas prometheus orpheus
""".split())
GUARD = ROLE_WORDS | FUNCTION_WORDS | PERSONIFICATIONS | NATIONS | DEITIES


def name_tokens(names_forms):
    """Kim's cast_name_tokens: every word >= 3 letters of the normalized name (>= 4 letters from a prefix form, which is often
    an abbreviation), minus role, function, personification, nation and deity words (GUARD)."""
    toks = set()
    for name, forms in names_forms:
        for i, form in enumerate([name] + (forms.split(' | ') if forms else [])):
            form = NAME_CLEAN.sub(' ', form or '')
            for t in form.split():
                t = t.strip("'’-").lower()
                if len(t) >= (3 if i == 0 else 4) and not t.isdigit(): toks.add(t)
    return {t for t in toks if t not in GUARD}


def ij_uv(t):
    t = t.lower()
    if t[:1] == 'j': t = 'i' + t[1:]
    return t.replace('v', 'u')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chunks', required=True); ap.add_argument('--manifest', required=True)
    ap.add_argument('--cast', default='', help='cast_names_kim.csv (default: ab_spelling/cast_names_kim.csv next to this code)')
    ap.add_argument('--overrides', default='', help='scope,token,decision csv (default: ab_spelling/name_mask_overrides.csv if present)')
    ap.add_argument('--cast-map', default='', help='edition_id,kim_tcp[,note] csv: force which of Kim\'s cast lists an edition uses (default: ab_spelling/cast_map_overrides.csv if present)')
    ap.add_argument('--placeholder', default='someone'); ap.add_argument('--common-min', type=int, default=20)
    ap.add_argument('--variant-sim', type=float, default=0.85)
    a = ap.parse_args()
    ch = Path(a.chunks); here = Path(__file__).resolve().parent.parent; csv.field_size_limit(10 ** 8)
    cast_path = Path(a.cast) if a.cast else here / 'cast_names_kim.csv'
    ovr_path = Path(a.overrides) if a.overrides else here / 'name_mask_overrides.csv'
    map_path = Path(a.cast_map) if a.cast_map else here / 'cast_map_overrides.csv'
    cast_map = {}
    if map_path.exists():
        for r in csv.DictReader(open(map_path, encoding='utf-8')):
            if r.get('edition_id', '').strip() and r.get('kim_tcp', '').strip(): cast_map[r['edition_id'].strip()] = [t.strip() for t in r['kim_tcp'].split(';') if t.strip()]

    meta = {r['chunk_id']: r for r in csv.DictReader(open(ch / 'chunk_meta.csv', encoding='utf-8'))}
    rows = list(csv.DictReader(open(ch / 'chunks_B.csv', encoding='utf-8')))
    man = {r['edition_id_effective']: r for r in csv.DictReader(open(a.manifest, encoding='utf-8'))}
    cast = defaultdict(list)
    for r in csv.DictReader(open(cast_path, encoding='utf-8')):
        cast[r['tcp'].strip()].append((r['name'] or '', r['forms'] or ''))
    by_base = defaultdict(set)
    for t in cast: by_base[t.split('.')[0]].add(t)

    # ---- editions → Kim's TCPs (exact unit id, else all parts under the base TCP), pooled per work
    ed_ids = sorted({m['edition_id'] for m in meta.values()}, key=int)
    ed_match = {}
    for e in ed_ids:
        if e in cast_map:
            ed_match[e] = ('override', [t for t in cast_map[e] if t in cast]); continue
        units = [u.strip() for u in (man.get(e, {}).get('unit_ids', '') or '').split(';') if u.strip()]
        exact = [u for u in units if u in cast]
        if exact: ed_match[e] = ('exact', exact); continue
        bases = sorted({t for u in units for t in by_base.get(u.split('.')[0], set())})
        ed_match[e] = ('base', bases) if bases else ('none', [])
    work_of = {e: meta[c]['work_id'] for c in meta for e in [meta[c]['edition_id']]}
    work_tcps = defaultdict(set)
    for e, (how, tcps) in ed_match.items(): work_tcps[work_of[e]].update(tcps)
    work_tokens = {w: name_tokens([nf for t in tcps for nf in cast[t]]) for w, tcps in work_tcps.items()}

    # ---- corpus statistics: lower-case frequency (common-word protection) and per-edition capitalised-only tokens
    low = Counter(); ed_tok = defaultdict(Counter); ed_cap = defaultdict(Counter)
    for r in rows:
        e = meta[r['chunk_id']]['edition_id']
        for t in TOKEN.findall(r['text']):
            t = t.rstrip("'’")
            if t.lower().endswith(("'s", "’s")): t = t[:-2]
            if not t: continue
            k = t.lower(); ed_tok[e][k] += 1
            if t[0].isupper(): ed_cap[e][k] += 1
            else: low[k] += 1
    common = {k for k, n in low.items() if n >= a.common_min}

    # ---- overrides
    ovr = defaultdict(dict)   # scope -> token -> decision
    if ovr_path.exists():
        for r in csv.DictReader(open(ovr_path, encoding='utf-8')):
            if r.get('token', '').strip(): ovr[(r.get('scope') or '*').strip()][r['token'].strip().lower()] = (r.get('decision') or '').strip().lower()

    # ---- per-edition mask sets
    ed_mask = {}; ed_source = {}; suggestions = []
    for e in ed_ids:
        w = work_of[e]; base = set(work_tokens.get(w, set())); src = {t: 'cast' for t in base}
        norm = {ij_uv(t): t for t in base}
        capo = [k for k, n in ed_cap[e].items() if n >= 3 and n / ed_tok[e][k] >= 0.9 and len(k) >= 3 and k not in GUARD]
        for k in capo:
            if k in base: continue
            if ij_uv(k) in norm: src[k] = 'variant'; continue
            m = difflib.get_close_matches(k, list(base), n=1, cutoff=a.variant_sim) if base else []
            if m: src[k] = 'variant'
            else: suggestions.append({'edition_id': e, 'work_id': w, 'title': meta[next(c for c in meta if meta[c]['edition_id'] == e)]['title'][:50], 'token': k, 'count': ed_cap[e][k],
                                      'note': 'capitalised-only, no cast match' if base else 'edition has no cast list'})
        for scope in ('*', w, e):
            for tok, dec in ovr.get(scope, {}).items():
                if dec == 'mask': src[tok] = 'override'
                elif dec == 'keep': src.pop(tok, None)
        ed_mask[e] = set(src); ed_source[e] = src

    # ---- masking
    ph = a.placeholder; per_ed_counts = defaultdict(Counter); total = 0
    def make_sub(e):
        ms = ed_mask[e]
        def sub(m):
            nonlocal total
            t = m.group(0); total += 1
            core = t.rstrip("'’"); poss = ''
            if core.lower().endswith(("'s", "’s")): core, poss = core[:-2], core[-2:]
            k = core.lower()
            if k not in ms: return t
            if k in common and not core[0].isupper(): return t     # common word in lower case: not the name
            per_ed_counts[e][k] += 1
            return ph + poss
        return sub
    prev = {}
    if (ch / 'chunks_B_masked.csv').exists():   # keep the previous version and list what changes, so 02_embed can re-embed only those chunks
        prev = {r['chunk_id']: hashlib.sha1(r['text'].encode('utf-8')).hexdigest() for r in csv.DictReader(open(ch / 'chunks_B_masked.csv', encoding='utf-8'))}
        (ch / 'chunks_B_masked.csv').replace(ch / 'chunks_B_masked.prev.csv')
    changed = []
    with open(ch / 'chunks_B_masked.csv', 'w', newline='', encoding='utf-8') as f, open(ch / 'chunks_B_masked.hashes.csv', 'w', newline='', encoding='utf-8') as fh:
        wr = csv.writer(f); wr.writerow(['chunk_id', 'text']); wh = csv.writer(fh); wh.writerow(['chunk_id', 'sha1'])
        for r in rows:
            e = meta[r['chunk_id']]['edition_id']
            t = TOKEN.sub(make_sub(e), r['text']) if ed_mask[e] else r['text']
            h = hashlib.sha1(t.encode('utf-8')).hexdigest(); wr.writerow([r['chunk_id'], t]); wh.writerow([r['chunk_id'], h])
            if prev and prev.get(r['chunk_id']) != h: changed.append(r['chunk_id'])
    with open(ch / 'name_mask_changed_chunks.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f); wr.writerow(['chunk_id']); wr.writerows([[c] for c in changed])

    # ---- reports
    title_of = {}
    for c, m in meta.items(): title_of.setdefault(m['edition_id'], m['title'])
    rep = []
    for e in ed_ids:
        how, tcps = ed_match[e]; cnt = per_ed_counts[e]
        rep.append({'edition_id': e, 'work_id': work_of[e], 'title': title_of[e][:60], 'matched': how, 'kim_tcp': '; '.join(tcps), 'n_cast_tokens': sum(1 for s in ed_source[e].values() if s == 'cast'),
                    'n_variant_tokens': sum(1 for s in ed_source[e].values() if s == 'variant'), 'n_override_tokens': sum(1 for s in ed_source[e].values() if s == 'override'),
                    'tokens_masked': sum(cnt.values()), 'words': sum(ed_tok[e].values()), 'top_masked': '; '.join(f'{k} {n}' for k, n in cnt.most_common(6))})
    with open(ch / 'name_mask_report.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=list(rep[0])); wr.writeheader(); wr.writerows(rep)
    with open(ch / 'name_mask_tokens.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.writer(f); wr.writerow(['edition_id', 'work_id', 'token', 'count', 'source', 'common_word'])
        for e in ed_ids:
            for k, n in per_ed_counts[e].most_common(): wr.writerow([e, work_of[e], k, n, ed_source[e].get(k, ''), 'yes' if k in common else ''])
    suggestions.sort(key=lambda r: -r['count'])
    with open(ch / 'name_mask_suggestions.csv', 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=['edition_id', 'work_id', 'title', 'token', 'count', 'note']); wr.writeheader(); wr.writerows(suggestions)
    sha = hashlib.sha256(open(ch / 'chunks_B_masked.csv', 'rb').read()).hexdigest()
    hows = Counter(h for h, _ in ed_match.values()); replaced = sum(sum(c.values()) for c in per_ed_counts.values())
    summary = {'editions': len(ed_ids), 'matched_exact': hows['exact'], 'matched_base': hows['base'], 'matched_override': hows['override'], 'unmatched': hows['none'],
               'changed_chunks_vs_previous': len(changed) if prev else None, 'cast_map_overrides': str(map_path) if map_path.exists() else '',
               'unmatched_editions': [e for e in ed_ids if ed_match[e][0] == 'none'],
               'tokens_total': total, 'tokens_replaced': replaced, 'share_replaced': round(replaced / max(total, 1), 5),
               'n_suggestions': len(suggestions), 'placeholder': ph, 'common_min': a.common_min, 'variant_sim': a.variant_sim,
               'cast_table': str(cast_path), 'overrides': str(ovr_path) if ovr_path.exists() else '', 'masked_sha256': sha}
    (ch / 'name_mask_summary.json').write_text(json.dumps(summary, indent=1))
    print(f'{len(ed_ids)} editions: cast list matched exactly {hows["exact"]}, by base TCP {hows["base"]}, by override {hows["override"]}, none {hows["none"]}; '
          + (f'{len(changed)} chunks changed vs the previous masked text (name_mask_changed_chunks.csv); ' if prev else '')
          + f'{replaced:,} of {total:,} tokens replaced ({100 * replaced / max(total, 1):.2f} %); {len(suggestions)} unmasked suggestions to review')
    print(f'→ {ch / "chunks_B_masked.csv"}  (sha256 {sha[:12]})\n   report {ch / "name_mask_report.csv"}; tokens {ch / "name_mask_tokens.csv"}; suggestions {ch / "name_mask_suggestions.csv"}')


if __name__ == '__main__':
    main()
