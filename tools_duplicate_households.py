# -*- coding: utf-8 -*-
"""The check that would have caught today's three duplications.

A household is duplicated when the same people appear twice in one census year.
Neither the address nor the schedule number can be relied on to find it - the
record holds rows with no address, rows with no schedule, and schedule numbers
shared between districts. A name and an age are what every census row has.

So: find every pair of census rows in the same year where two different people
carry the same forename, surname and age. Then group those pairs by the two
households they sit in. A household appearing many times over is a household
entered twice.
"""
import os, sys, json, psycopg2
from collections import defaultdict

P = json.load(open('data/all_props.json'))
props = {p['id']: (p.get('address') or p.get('name')) for p in P}
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""
  SELECT ce.census_year,
         LOWER(TRIM(p.first_name)) fn, LOWER(TRIM(p.last_name)) ln, ce.age_at_census,
         ce.id, ce.person_id, ce.property_id, ce.census_household_num,
         COALESCE(NULLIF(ce.address,''), ce.unresolved_address), LEFT(COALESCE(ce.source,''),40)
    FROM census_entries ce JOIN people p ON p.id=ce.person_id
   WHERE ce.age_at_census IS NOT NULL
     AND COALESCE(TRIM(p.first_name),'')<>'' AND COALESCE(TRIM(p.last_name),'')<>''
""")
rows = cur.fetchall()
byname = defaultdict(list)
for r in rows:
    byname[(r[0], r[1], r[2], r[3])].append(r)

pairs = defaultdict(list)   # (year, household A, household B) -> [names]
for key, group in byname.items():
    if len(group) < 2: continue
    # only count rows on DIFFERENT people - one person legitimately has one row per year
    if len({g[5] for g in group}) < 2: continue
    def house(g):
        return (props.get(g[6]) or g[8] or f"schedule {g[7]}" or "?")
    seen = set()
    for i in range(len(group)):
        for j in range(i+1, len(group)):
            a, b = group[i], group[j]
            if a[5] == b[5]: continue
            ha, hb = house(a), house(b)
            k = (key[0],) + tuple(sorted([str(ha), str(hb)]))
            if (k, key[1], key[2]) in seen: continue
            seen.add((k, key[1], key[2]))
            pairs[k].append(f"{key[1].title()} {key[2].title()} ({key[3]})")

big = sorted(((len(v), k, v) for k, v in pairs.items()), reverse=True)
print(f"=== {len(pairs)} household pairs share at least one name-and-age ===\n")
print("--- three or more shared people: these are duplicated households ---")
n = 0
for cnt, k, names in big:
    if cnt < 3: break
    n += 1
    year, ha, hb = k
    print(f"  {year}  {ha[:44]}")
    print(f"        {hb[:44]}")
    print(f"        {cnt} shared: {', '.join(names[:6])}" + (" ..." if cnt > 6 else ""))
print(f"\n  {n} household pairs share three or more people")
two = [x for x in big if x[0] == 2]
print(f"  {len(two)} share exactly two - worth a look")
for cnt, k, names in two[:12]:
    print(f"     {k[0]}  {k[1][:38]:<40} | {k[2][:38]:<40} {', '.join(names)}")
