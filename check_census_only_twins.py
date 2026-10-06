"""The real signature of the Tattershall fault.

Lynwood, St Ives and Elmsdale were census-only properties - made from a name in
the 1939 Register, carrying that one round and nothing else - standing beside a
numbered house on the same street that had every other round and was marked
empty for 1939. That is a house held twice, not two houses.

So: every census-only property whose only census round is 1939, listed with the
houses on its street that are marked empty for 1939.
"""
import os, json, psycopg2
P = json.load(open('data/all_props.json'))
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT property_id FROM census_unoccupied WHERE census_year=1939")
empty = {r[0] for r in cur.fetchall()}
cur.execute("""SELECT property_id, STRING_AGG(DISTINCT census_year::text, ',' ORDER BY census_year::text)
                 FROM census_entries WHERE property_id IS NOT NULL GROUP BY 1""")
years = dict(cur.fetchall())
flag = []
for p in P:
    if not p.get('census_only'): continue
    y = years.get(p['id'])
    if y != '1939': continue
    twins = [q for q in P if q['id'] in empty and str(q.get('street') or '') == str(p.get('street') or '')]
    flag.append((p, twins))
print(f"  {sum(1 for p in P if p.get('census_only'))} census-only properties")
print(f"  {len(flag)} of them hold 1939 and nothing else\n")
for p, twins in flag:
    mark = "   <-- and a house on its street is marked empty" if twins else ""
    print(f"   #{p['id']:<5} {(p.get('address') or ''):<44}{mark}")
    for t in twins[:4]:
        print(f"            empty for 1939: {t.get('address')}")
