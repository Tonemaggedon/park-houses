# -*- coding: utf-8 -*-
"""The eight households the surname-keyed duplicate check could not see.

Found by tools_duplicate_households_v2.py: the same enumerator's page read
twice, once with the house number and once without, the two readings agreeing
on forename, age, schedule and occupation and disagreeing on the surname -
Heeley or Keeley, Cottee or Cobbee, de Lascelle or Lasalle.

**The tie-break is the one fold_lenton_avenue_1881_twice.py already used and
A. Hagues accepted: keep the row that names the house and cites the piece
number, drop the weaker row, and leave the other spelling behind as an alias**,
so a search under either name still finds the person. Nothing is lost but the
duplication.

Where the two rows cannot be told apart that way, the pair is LEFT ALONE and
printed, because choosing between Heeley and Keeley on no evidence is not the
record's business.

  railway run python3 fold_eight_duplicated_households.py          # preview
  railway run python3 fold_eight_duplicated_households.py --apply
"""
import os, sys, re, json, psycopg2
from collections import defaultdict

APPLY = '--apply' in sys.argv
P = {p['id']: (p.get('address') or p.get('name')) for p in json.load(open('data/all_props.json'))}
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.id, ce.person_id, ce.property_id, ce.census_year, ce.census_household_num,
                      LOWER(TRIM(p.first_name)), ce.age_at_census, p.first_name, p.last_name,
                      COALESCE(ce.source,''), COALESCE(ce.address,''),
                      COALESCE(ce.occupation_at_census,'')
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id IS NOT NULL AND ce.age_at_census IS NOT NULL
                  AND COALESCE(TRIM(p.first_name),'')<>''""")
rows = cur.fetchall()
g = defaultdict(list)
for r in rows:
    g[(r[2], r[3], r[5], r[6])].append(r)

# Leads the apparatus rule gets wrong, overridden by eye. A fuller source is
# not a better reading when the word it produced is not a name: *Bottomls* is a
# transcription artefact and *Bottomley* is a Nottinghamshire surname, and the
# weaker row's own note - "surname unread, begins" - is the transcriber saying so.
PREFER = {'bottomley'}
PIECE = re.compile(r'\bRG\s*\d+\s*/\s*\d+', re.I)
def strength(r):
    """How much apparatus the row's source carries."""
    s, addr = r[9], r[10]
    n = 0
    if PIECE.search(s): n += 2                     # cites the piece
    if addr.strip(): n += 1                        # carries an address
    if re.search(r'\b\d+\s+\w', s.split(' - ')[0]): n += 1   # the source names a number
    if 'not identified' in s or 'no number' in s or 'image ' in s: n -= 2
    return n

folds, left = [], []
for k, v in sorted(g.items()):
    if len(v) != 2: continue
    if len({x[8].lower().strip() for x in v}) < 2: continue
    a, b = sorted(v, key=strength, reverse=True)
    pref = [x for x in v if x[8].lower().strip() in PREFER]
    if len(pref) == 1:
        a = pref[0]; b = [x for x in v if x is not a][0]
        folds.append((k, a, b)); continue
    if strength(a) <= strength(b):
        left.append((k, a, b)); continue
    folds.append((k, a, b))     # a is the fuller row; keep its person

byhouse = defaultdict(list)
for k, a, b in folds: byhouse[(k[0], k[1])].append((a, b))
print(f"{len(folds)} pairs fold, {len(left)} left alone\n")
for (pid, yr), items in sorted(byhouse.items(), key=lambda t: -len(t[1])):
    print(f"  #{pid} {P.get(pid)} {yr} - {len(items)} people")
    for a, b in items:
        print(f"      keep {a[7]} {a[8]:<13} (row {a[0]}, {a[9][:46]})")
        print(f"      drop {b[7]} {b[8]:<13} (row {b[0]}, {b[9][:46]})")
if left:
    print("\n  LEFT ALONE - the two rows carry the same apparatus, so nothing picks between them:")
    for k, a, b in left:
        print(f"    #{k[0]} {P.get(k[0])} {k[1]}  {a[7]} {a[8]} / {b[8]}")

if not APPLY:
    print("\n  Nothing written. Add --apply.")
    sys.exit()

n = 0
for k, a, b in folds:
    keep_person, drop_person = a[1], b[1]
    if keep_person == drop_person: continue
    cur.execute("DELETE FROM census_entries WHERE id=%s", (b[0],))
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, made_by)
                   VALUES (%s,%s,%s,'fold-duplicate-household') ON CONFLICT DO NOTHING""",
                (keep_person, b[7], b[8]))
    cur.execute("""UPDATE census_entries SET person_id=%s WHERE person_id=%s
                    AND NOT EXISTS (SELECT 1 FROM census_entries z
                      WHERE z.person_id=%s AND z.census_year=census_entries.census_year)""",
                (keep_person, drop_person, keep_person))
    cur.execute("DELETE FROM census_entries WHERE person_id=%s", (drop_person,))
    # Only tables this schema actually has. An exception here would roll the whole
    # transaction back - which is what went wrong the first time this was run, and
    # why nothing but the last pair was written.
    for t in ('property_residents', 'occupations'):
        cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (drop_person,))
    cur.execute("DELETE FROM people WHERE id=%s", (drop_person,))   # the rest cascades
    n += 1
c.commit()
print(f"\n  committed - {n} people folded, each leaving its other reading as an alias")
