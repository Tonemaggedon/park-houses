# -*- coding: utf-8 -*-
"""Derby Terrace runs past number 9, and the 1881 page says so in numbers.

A. Hagues looked at the 1880s survey under the modern map and saw more buildings
on the terrace than the record has markers for - one gone where The Park Octagon
now stands, one at the far end absorbed into its neighbour - and said everything
might shift one along, which would give two more houses.

**The page is better than the map.** The 1881 enumerator does not write *Derby
Terrace* and leave it; he writes the Derby Road numbers:

    s66  141 Derby Terrace   King, Parker, Underwood, Wride   11 people
    s67  143 Derby Terrace   Felkin, Scrimshaw                 8
    s68-75                   145 down to 159, the nine the record holds
    s76  139 Derby Terrace   Taylor, Vickers                   7

So the terrace is **139 to 159**, not the 1 to 9 the record keeps - and two of
those three are already here under other names:

    139  Hampden House, 7 Clinton Terrace   #77
    143  Edgemont House                     #431
    141  nothing at all

**141 Derby Road is a house the record has never had.** It holds eleven people in
1881 and is in the 1871 round as well. And it is gone by 1921: that year the
enumerator takes Hampden House at schedule 51 and Edgemont at 52, consecutive,
with nothing between them - which is exactly the house A. Hagues saw missing.

Only what the page numbers outright is filed here. The three unnumbered 1871
households that follow 145 are almost certainly the same three doors, in the same
order, but that is the walk talking rather than the page, and it is left as a
question.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
d = json.load(open('data/all_props.json'))
P = {p['id']: p for p in d}
NEW_ID = 455
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

MOVES = [(67, 431, 'Edgemont House, 143 Derby Road'),
         (76, 77,  'Hampden House, 7 Clinton Terrace (139 Derby Road)')]
for sch, pid, label in MOVES:
    cur.execute("""SELECT count(*) FROM census_entries
                    WHERE census_year=1881 AND census_household_num=%s AND property_id IS NULL""", (sch,))
    print(f"  1881 s{sch} -> #{pid} {label}: {cur.fetchone()[0]} people")
cur.execute("""SELECT count(*) FROM census_entries
                WHERE census_year=1881 AND census_household_num=66 AND property_id IS NULL""")
print(f"  1881 s66 -> a new property, 141 Derby Road: {cur.fetchone()[0]} people")
print(f"  141 already in the list? {NEW_ID in P or any(str(p.get('no'))=='141' for p in d)}")

if not apply:
    print("\n  preview only - pass --apply")
    sys.exit()

for sch, pid, label in MOVES:
    cur.execute("""UPDATE census_entries SET property_id=%s, address=%s,
                     source = source || ' - the page numbers it, and that number is this house'
                    WHERE census_year=1881 AND census_household_num=%s AND property_id IS NULL""",
                (pid, label, sch))
    print(f"  filed s{sch}: {cur.rowcount} rows")

if not any(str(p.get('no')) == '141' for p in d):
    e = P[431]
    d.append({
        "id": NEW_ID, "address": "141 Derby Road (Derby Terrace)", "name": "",
        "street": "Derby Road", "no": "141",
        "lat": e['lat'], "lng": e['lng'], "census_only": True, "listed": "No",
        "desc": "",
        "history": "**A house the record never had.** The 1881 enumerator writes *141 Derby "
          "Terrace* outright and puts eleven people in it - King, Parker, Underwood and Wride - "
          "between 143 and 145, which the record keeps as Edgemont House and 9 Derby Terrace.\n\n"
          "**It is gone by 1921.** That year the enumerator takes Hampden House at schedule 51 and "
          "Edgemont at 52, one after the other with nothing between them, and 1939 does the same at "
          "196 and 197. So the house stood in 1871 and 1881 and had been pulled down or absorbed "
          "into a neighbour within forty years.\n\n"
          "**Found because A. Hagues put the 1880s survey under the modern map** and saw more "
          "buildings on the terrace than the record had markers for.",
        "sources": {
          "existence": "1881 census, schedule 66, headed \"141 Derby Terrace\" on the page.",
          "position": "**A placeholder, and known to be wrong.** It is Edgemont House's point, "
            "because 141 should sit beside 143 - but the record's Derby Terrace positions are "
            "seeded rather than surveyed and disagree with each other by hundreds of metres, so "
            "there was nothing honest to interpolate between. The whole row wants placing."
        }})
    json.dump(d, open("data/all_props.json", "w"), indent=1, ensure_ascii=False)
    cur.execute("""UPDATE census_entries SET property_id=%s, address='141 Derby Road (Derby Terrace)',
                     source = source || ' - the page numbers it 141, and the record now holds 141'
                    WHERE census_year=1881 AND census_household_num=66 AND property_id IS NULL""",
                (NEW_ID,))
    print(f"  created #{NEW_ID} 141 Derby Road and filed {cur.rowcount} people into it")
c.commit()
print("\n  committed")
