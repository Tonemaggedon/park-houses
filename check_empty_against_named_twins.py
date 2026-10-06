"""Houses marked empty for 1939 that have a near neighbour on the same street
holding a 1939 household under a house name.

The Tattershall Drive mistake came from a gaps list that treated a named house
and a numbered house as two. This looks for the same shape anywhere else: a
property marked blank, and another property within fifty metres on the same
street, carrying a name rather than a number, which does have a household.
"""
import os, json, math, psycopg2
P = json.load(open('data/all_props.json'))
byid = {p['id']: p for p in P}
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT property_id FROM census_unoccupied WHERE census_year=1939")
empty = [r[0] for r in cur.fetchall()]
cur.execute("""SELECT DISTINCT property_id FROM census_entries
                WHERE census_year=1939 AND property_id IS NOT NULL""")
has = {r[0] for r in cur.fetchall()}
def d(a, b):
    if not (a.get('lat') and b.get('lat')): return 9e9
    return math.hypot((a['lat']-b['lat'])*111320, (a['lng']-b['lng'])*67400)
flag = []
for e in empty:
    pe = byid.get(e)
    if not pe: continue
    for p in P:
        if p['id'] == e or p['id'] not in has: continue
        if str(p.get('street') or '') != str(pe.get('street') or ''): continue
        if not p.get('name'): continue         # the twin must be a NAMED house
        dist = d(pe, p)
        if dist <= 60:
            flag.append((round(dist), pe.get('address'), p.get('address')))
flag.sort()
print(f"  {len(empty)} houses marked empty for 1939")
print(f"  {len(flag)} sit within 60 m of a NAMED house on the same street that has a household\n")
for dist, a, b in flag:
    print(f"   {dist:>3} m  EMPTY: {a[:40]:<42} NAMED, occupied: {b[:40]}")
if not flag: print("   none - nothing else has the Tattershall shape")
