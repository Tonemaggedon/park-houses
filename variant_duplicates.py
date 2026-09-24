#!/usr/bin/env python3
"""
Duplicate people neither tool on the site can find.

Both site tools bucket on the surname LETTER FOR LETTER - the duplicates page
and "Join up people entered under a census short form" alike. So a duplicate
made by two spellings of a surname is invisible to both: Crendson beside
Crewdson, Flersheim beside Hersheim, Tomnroe beside Townroe, Slack beside
Black. An import that reads an enumerator's hand one way, where an earlier
transcription read it another, makes one of these every time.

This fuzzes the surname and expands the forename abbreviations, using the same
table the site's own merge tool uses, so "Chas. E. Tomnroe" can be seen beside
"Charles Edward Townroe".

It compares the people of one census year against EVERYONE in the record, not
just against each other - Charles Edward Townroe is held from 1891 alone, so a
scan of 1901 against 1901 could never see him.

It reports; it changes nothing. Merging is done on the site.

Usage:
  railway run python3 variant_duplicates.py --year 1901
  railway run python3 variant_duplicates.py --year 1901 --xlsx
  railway run python3 variant_duplicates.py            # everybody against everybody
"""

import os, re, sys, difflib, unicodedata, argparse
import psycopg2

# The census short forms, as server.js keeps them, so the two agree about what
# a forename is instead of disagreeing quietly.
ABBR = {
    'geo': 'george', 'chas': 'charles', 'wm': 'william', 'jno': 'john',
    'jas': 'james', 'thos': 'thomas', 'fredk': 'frederick', 'edwd': 'edward',
    'richd': 'richard', 'robt': 'robert', 'saml': 'samuel', 'benjn': 'benjamin',
    'danl': 'daniel', 'josh': 'joseph', 'jos': 'joseph', 'elizth': 'elizabeth',
    'eliz': 'elizabeth', 'margt': 'margaret', 'catharine': 'catherine',
    'cathe': 'catherine', 'hy': 'henry', 'alexr': 'alexander', 'matw': 'matthew',
    'andw': 'andrew', 'chris': 'christopher', 'nichs': 'nicholas',
    'phil': 'philip', 'sarh': 'sarah',
}

# A surname is a variant of another when it is nearly the same word. Below this
# the pairs stop being spellings of one name and start being different families.
SURNAME_MIN = 0.78
BORN_WITHIN = 2


def database_url():
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 '
                         + os.path.basename(__file__))
    return v


def norm(s):
    s = unicodedata.normalize('NFKD', (s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', s.lower())


def forenames(s):
    out = []
    for part in re.split(r'[^A-Za-z]+', s or ''):
        n = norm(part)
        if n:
            out.append(ABBR.get(n, n))
    return out


def same_forename(a, b):
    """True when two spellings can be one name: the first forenames agree once
    the short forms are expanded, and a lone initial stands for the name beside
    it."""
    fa, fb = forenames(a), forenames(b)
    if not fa or not fb:
        return False
    x, y = fa[0], fb[0]
    if x == y:
        return True
    if len(x) == 1 or len(y) == 1:
        return x[0] == y[0]
    if x.startswith(y) or y.startswith(x):
        return True
    return difflib.SequenceMatcher(None, x, y).ratio() >= 0.8


def later_forenames_conflict(a, b):
    """The trap in this report: William EDWARD Radford beside William HENRY
    Radford, Samuel WAITE Johnson beside Samuel GEORGE Johnson. The surname is
    identical and the first forename agrees, so everything else about the pair
    looks perfect - and they are two different men.

    Only full words count. An initial standing where a name is written is the
    ordinary way a census abbreviates, and proves nothing either way."""
    fa, fb = forenames(a)[1:], forenames(b)[1:]
    for x, y in zip(fa, fb):
        if len(x) == 1 or len(y) == 1:
            if x[0] != y[0]:
                return True
            continue
        if x == y or x.startswith(y) or y.startswith(x):
            continue
        if difflib.SequenceMatcher(None, x, y).ratio() >= 0.8:
            continue
        return True
    return False


INITIAL = re.compile(r'^[A-Z]\.?$')

ap = argparse.ArgumentParser(add_help=False)
ap.add_argument('--year', type=int, help='the round just imported')
ap.add_argument('--xlsx', action='store_true')
ap.add_argument('-h', '--help', action='help')
args = ap.parse_args()

conn = psycopg2.connect(database_url())
conn.set_session(readonly=True)
cur = conn.cursor()
cur.execute("""
    SELECT p.id, p.first_name, p.last_name, p.born_year,
           (SELECT string_agg(DISTINCT c.census_year::text, ',' ORDER BY c.census_year::text)
              FROM census_entries c WHERE c.person_id = p.id),
           (SELECT string_agg(DISTINCT COALESCE(NULLIF(TRIM(c.unresolved_address), ''), ''), ' | ')
              FROM census_entries c WHERE c.person_id = p.id),
           (SELECT string_agg(DISTINCT c.property_id::text, ',')
              FROM census_entries c WHERE c.person_id = p.id AND c.property_id IS NOT NULL)
      FROM people p""")
everyone = cur.fetchall()

if args.year:
    cur.execute("""SELECT DISTINCT person_id FROM census_entries WHERE census_year = %s""",
                (args.year,))
    ids = {r[0] for r in cur.fetchall()}
    left = [p for p in everyone if p[0] in ids]
else:
    left = everyone

pairs, seen = [], set()
for a in left:
    for b in everyone:
        if a[0] == b[0]:
            continue
        key = tuple(sorted((a[0], b[0])))
        if key in seen:
            continue
        # A surname that is a bare initial is a ditto mark misread, not a
        # variant spelling. Those are a different job, and a different report.
        if INITIAL.match((a[2] or '').strip()) or INITIAL.match((b[2] or '').strip()):
            continue
        if a[3] and b[3] and abs(a[3] - b[3]) > BORN_WITHIN:
            continue
        sa, sb = norm(a[2]), norm(b[2])
        if not sa or not sb:
            continue
        if sa == sb:
            ratio = 1.0
        else:
            if abs(len(sa) - len(sb)) > 3:
                continue
            ratio = difflib.SequenceMatcher(None, sa, sb).ratio()
            if ratio < SURNAME_MIN:
                continue
        if not same_forename(a[1], b[1]):
            continue
        seen.add(key)
        notes = []
        if not a[3] or not b[3]:
            notes.append('NO BIRTH YEAR on one side - this rests on the name alone')
        if later_forenames_conflict(a[1], b[1]):
            notes.append('SECOND FORENAME DIFFERS - very likely two people')
        # The same house on both sides is about as good as this gets: either
        # the same unresolved address off the page, or the same property once
        # somebody has filed them.
        def houses(p):
            txt = {x.strip() for x in (p[5] or '').split('|') if x.strip()}
            ids = {x for x in (p[6] or '').split(',') if x}
            return txt, ids
        at, ai = houses(a); bt, bi = houses(b)
        # A filed row names a house outright, so a shared property id is proof.
        # An UNFILED row carries only what the enumerator wrote in the address
        # column, and that is very often a bare street - "Pelham Crescent" with
        # no number. Two strangers on one street shared it, and this graded them
        # near proof: John Scott Wells was matched to John R Ellis that way.
        # So text only counts where it names a particular house - a number in it,
        # or a house name set off by a comma.
        def names_a_house(t):
            return bool(re.search(r'\d', t)) or ',' in t
        shared_txt = {t for t in (at & bt) if names_a_house(t)}
        if (ai & bi) or shared_txt:
            notes.append('SAME HOUSE on both sides - near proof')
        elif at & bt:
            notes.append('same street, no number either side - weak')
        # Keep the record that carries more of the person's life - more census
        # years first, and where those are equal, the fuller spelling of the
        # name: Charles Edward Townroe over Chas. E. Tomnroe.
        def weight(p):
            years = len((p[4] or '').split(',')) if p[4] else 0
            return (years, len(norm(p[1]) + norm(p[2])))
        keep, drop = (a, b) if weight(a) >= weight(b) else (b, a)
        pairs.append((round(ratio, 2), keep, drop, '; '.join(notes)))

pairs.sort(key=lambda t: (-t[0], norm(t[1][2])))

scope = f'the {args.year} round' if args.year else 'the whole record'
print(f'Variant-spelling duplicates in {scope}: {len(pairs)} pair(s)')
print('Compared against every person in the record, not only against each other.\n')
for ratio, keep, drop, notes in pairs:
    print(f'  [{ratio}]  keep #{keep[0]:<5} {keep[1]} {keep[2]}  b.{keep[3]}   ({keep[4] or "no census"})')
    print(f'          join #{drop[0]:<5} {drop[1]} {drop[2]}  b.{drop[3]}   ({drop[4] or "no census"})')
    where = (keep[5] or drop[5] or '').strip(' |')
    if where:
        print(f'          {where[:88]}')
    if notes:
        print(f'          ** {notes}')

if args.xlsx and pairs:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook(); ws = wb.active; ws.title = 'Variant spellings'
    ws.append(['likeness', 'keep id', 'keep', 'born', 'its censuses',
               'join id', 'joined', 'born', 'its censuses', 'address',
               'worth knowing', 'same person? (y/n)'])
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='2F4858')
    for ratio, keep, drop, notes in pairs:
        ws.append([ratio, f'#{keep[0]}', f'{keep[1]} {keep[2]}', keep[3], keep[4] or '',
                   f'#{drop[0]}', f'{drop[1]} {drop[2]}', drop[3], drop[4] or '',
                   (keep[5] or drop[5] or '').strip(' |')[:60], notes, ''])
    for i, w in enumerate([9, 9, 28, 7, 17, 9, 28, 7, 17, 34, 40, 17], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical='top', wrap_text=True)
    ws.freeze_panes = 'A2'
    out = os.path.expanduser(f'~/Desktop/Variant spellings{" " + str(args.year) if args.year else ""}.xlsx')
    wb.save(out)
    print(f'\nWritten: {out}')

flagged = [p for p in pairs if 'two people' in p[3]]
thin = [p for p in pairs if 'name alone' in p[3]]
solid = [p for p in pairs if 'near proof' in p[3]]
print(f'\n  {len(solid)} carry the same address on both sides - near proof.')
print(f'  {len(flagged)} have a SECOND FORENAME that differs - very likely two people, not one.')
print(f'  {len(thin)} rest on the name alone, one side having no birth year.')

cur.close()
conn.close()
