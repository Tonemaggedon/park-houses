# -*- coding: utf-8 -*-
"""What a visitor would hit on Monday. Read-only."""
import os, json, psycopg2
P = {p['id']: p for p in json.load(open('data/all_props.json'))}
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
def q1(sql, a=()):
    cur.execute(sql, a); r = cur.fetchone(); return r[0] if r else None

print("== SIZE")
print("  properties in the list   ", len(P))
print("  people                   ", q1("SELECT count(*) FROM people"))
print("  census rows              ", q1("SELECT count(*) FROM census_entries"))
print("  rows filed to a house    ", q1("SELECT count(*) FROM census_entries WHERE property_id IS NOT NULL"))
print("  rows NOT filed           ", q1("SELECT count(*) FROM census_entries WHERE property_id IS NULL"))
print("  people with no census row", q1("""SELECT count(*) FROM people p
        WHERE NOT EXISTS (SELECT 1 FROM census_entries ce WHERE ce.person_id=p.id)"""))

print("\n== EMPTY HOUSE PAGES - no census, no empty mark, no description, no history")
cur.execute("SELECT DISTINCT property_id FROM census_entries WHERE property_id IS NOT NULL")
has = {r[0] for r in cur.fetchall()}
cur.execute("SELECT DISTINCT property_id FROM census_unoccupied")
has |= {r[0] for r in cur.fetchall()}
bare = [p for p in P.values() if p['id'] not in has
        and not (p.get('desc') or '').strip() and not (p.get('history') or '').strip()]
for p in bare: print(f"   #{p['id']:<4} {p.get('address')}")
print(f"   {len(bare)} bare")

print("\n== NO POSITION AT ALL (would not draw on the map)")
cur.execute("SELECT id FROM coords")
co = {r[0] for r in cur.fetchall()}
nopos = [p for p in P.values() if p['id'] not in co and not (p.get('lat') and p.get('lng'))]
for p in nopos[:20]: print(f"   #{p['id']:<4} {p.get('address')}")
print(f"   {len(nopos)} with no position")

print("\n== PEOPLE WITH NO NAME")
print("  ", q1("""SELECT count(*) FROM people
        WHERE COALESCE(TRIM(first_name),'')='' AND COALESCE(TRIM(last_name),'')=''"""))

print("\n== RESEARCH QUESTIONS (public at /research)")
print("  in the file", len(json.load(open('data/research_questions.json'))['questions']))
print("  in the db  ", q1("SELECT count(*) FROM research_questions"))
print("  answered   ", q1("SELECT count(*) FROM research_questions WHERE status='answered'"))

print("\n== DUPLICATED HOUSEHOLDS still present (v2 check)")
cur.execute("""SELECT ce.property_id, ce.census_year, LOWER(TRIM(p.first_name)), ce.age_at_census,
                      p.last_name, p.id
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id IS NOT NULL AND ce.age_at_census IS NOT NULL
                  AND COALESCE(TRIM(p.first_name),'')<>''""")
from collections import defaultdict
g = defaultdict(list)
for r in cur.fetchall(): g[(r[0], r[1], r[2], r[3])].append(r)
pairs = {k: v for k, v in g.items() if len(v) > 1 and len({x[4].lower().strip() for x in v}) > 1}
hh = defaultdict(set)
for k, v in pairs.items():
    for x in v: hh[(x[0], x[1])].add(x[5])
for (pid, yr), people in sorted(hh.items(), key=lambda t: -len(t[1])):
    if len(people) >= 4:
        print(f"   {len(people):>2} people  #{pid:<4} {str(P.get(pid,{}).get('address'))[:40]:<42} {yr}")
print(f"   {len(pairs)} name-and-age pairs across {len(hh)} house-years")
