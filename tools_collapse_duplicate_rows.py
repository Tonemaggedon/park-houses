#!/usr/bin/env python3
"""
One person, one census night, one house - and two rows for it.

Nobody is in a house twice in a year, so one of the two is spurious. But which
is spurious is not obvious: often one row has the source and the other has the
better reading. So this does not simply delete. It picks the fuller row, fills
whatever that row is missing FROM the other, and only then deletes it.

The fuller row is the one with the most filled columns, with two thumbs on the
scale: a relationship that is a word beats one that is a schedule number
("Head" over "1"), and the longer relationship beats the shorter, because
"Head (widow)" says something "Head" does not.

Usage:
  railway run python3 tools_collapse_duplicate_rows.py          # show what would happen
  railway run python3 tools_collapse_duplicate_rows.py --apply  # do it
"""

import os, json, sys, re
import psycopg2

APPLY = '--apply' in sys.argv
cn = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = cn.cursor()
props = {p['id']: p.get('address','') for p in json.load(open('data/all_props.json'))}
FIELDS = ['relationship','age_at_census','occupation_at_census','birth_place','marital_status',
          'source','census_household_num','address','birth_lat','birth_lng']
def score(r):
    d = dict(zip(FIELDS, r))
    s = sum(1 for f in FIELDS if d[f] not in (None, ''))
    rel = (d['relationship'] or '').strip()
    if rel and not re.fullmatch(r'\d+', rel): s += 3      # a word beats a schedule number
    s += len(d['birth_place'] or '') / 1000.0             # the fuller birthplace
    s += len(rel) / 1000.0                               # and the fuller relationship:
                                                         # "Head (widow)" says more than "Head"
    return s
cur.execute("""SELECT person_id, census_year, property_id, array_agg(id ORDER BY id)
                 FROM census_entries WHERE property_id IS NOT NULL
                GROUP BY 1,2,3 HAVING COUNT(*)>1""")
for person, yr, prop, ids in cur.fetchall():
    cur.execute("SELECT first_name, last_name FROM people WHERE id=%s",(person,))
    nm = ' '.join(x for x in cur.fetchone() if x)
    rows = {}
    for i in ids:
        cur.execute(f"SELECT {','.join(FIELDS)} FROM census_entries WHERE id=%s",(i,))
        rows[i] = cur.fetchone()
    best = max(ids, key=lambda i: score(rows[i]))
    others = [i for i in ids if i != best]
    print(f"\n#{person} {nm}  {yr}  {props.get(prop,'')}")
    for i in ids:
        d = dict(zip(FIELDS, rows[i]))
        tag = 'KEEP  ' if i == best else 'absorb'
        print(f"   {tag} row {i}: rel={d['relationship']!r} age={d['age_at_census']} occ={d['occupation_at_census']!r}")
        print(f"          born={d['birth_place']!r}  source={(d['source'] or '')[:46]!r}")
    fills = []
    for f in FIELDS:
        if dict(zip(FIELDS, rows[best]))[f] in (None, ''):
            for i in others:
                v = dict(zip(FIELDS, rows[i]))[f]
                if v not in (None, ''): fills.append((f, v)); break
    if fills: print("   filling from the absorbed row:", ', '.join(f for f,_ in fills))
    if APPLY:
        if fills:
            cur.execute(f"UPDATE census_entries SET {', '.join(f+'=%s' for f,_ in fills)} WHERE id=%s",
                        [v for _,v in fills] + [best])
        cur.execute("DELETE FROM census_entries WHERE id = ANY(%s)", (others,))
        print(f"   kept {best}, deleted {cur.rowcount}")
if APPLY: cn.commit(); print("\nWritten.")
else: print("\nNothing written. Run again with --apply.")
