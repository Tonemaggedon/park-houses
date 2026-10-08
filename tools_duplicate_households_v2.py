# -*- coding: utf-8 -*-
"""The duplicate-household check, rebuilt - because version one keyed on the surname.

tools_duplicate_households.py matched people on forename + surname + age and
reported no duplicated households anywhere in the record. That answer was wrong,
and the reason is the thing it matched on.

**The record's duplicates are duplicates of the page, not of the transcription.**
A household gets entered twice when the same enumerator's page is read twice -
once with the house number, once without, or once off the image and once off an
index. The two readings agree on the forename, the age, the schedule and usually
the occupation. **They disagree on the surname**, because a surname is the hardest
word on the sheet: Heeley or Keeley, Cottee or Cobbee, de Lascelle or Lasalle,
Bottomley or Bottomls.

So version one's key contained the one field the two readings never share.

This version pairs people on **property + year + forename + age** and then asks
how much of a household is paired. A household where most members have a twin
is a household entered twice, whatever the surnames say.
"""
import os, sys, json, psycopg2
from collections import defaultdict
from difflib import SequenceMatcher

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.property_id, ce.census_year, ce.census_household_num,
                      LOWER(TRIM(p.first_name)), ce.age_at_census, p.last_name,
                      p.id, ce.id, COALESCE(ce.occupation_at_census,''), COALESCE(ce.source,'')
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id IS NOT NULL AND ce.age_at_census IS NOT NULL
                  AND COALESCE(TRIM(p.first_name),'')<>''""")
rows = cur.fetchall()

# pair people on property + year + forename + age, ignoring the surname
pairs = defaultdict(list)
for r in rows:
    pairs[(r[0], r[1], r[3], r[4])].append(r)

# a household is (property, year, source). Count its paired members.
hh = defaultdict(set)
hh_paired = defaultdict(set)
for r in rows:
    hh[(r[0], r[1], r[9][:70])].add(r[6])
for k, v in pairs.items():
    if len(v) < 2:
        continue
    if len({x[5].lower().strip() for x in v}) < 2:
        continue          # same surname twice is version one's case, already clean
    for x in v:
        hh_paired[(x[0], x[1], x[9][:70])].add(x[6])

P = {p['id']: (p.get('address') or p.get('name')) for p in json.load(open('data/all_props.json'))}
out = []
for k, members in hh.items():
    p = hh_paired.get(k, set())
    if len(members) >= 2 and len(p) == len(members):
        out.append((len(members), k))
out.sort(reverse=True)

print(f"{len(out)} households where EVERY member has a same-forename, same-age twin "
      f"in the same house and year under a different surname\n")
for n, k in out:
    pid, yr, src = k
    others = sorted({x[5] for key, v in pairs.items() if key[0] == pid and key[1] == yr
                     and len(v) > 1 for x in v})
    print(f"  {n:>2} people  #{pid:<4} {str(P.get(pid))[:40]:<42} {yr}")
    print(f"             {src}")
print("\n  Version one found none of these. It matched on the surname, which is the "
      "one field two readings of the same page disagree about.")
