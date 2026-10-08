# -*- coding: utf-8 -*-
"""The Lodge is Gartree Lodge. The record held one house as two.

  #436 The Lodge, Tattershall Drive  ->  #404 Gartree Lodge, 17a Tattershall Drive

**And the record already said so.** Gartree Lodge's own notes carry it: 17a
Tattershall Drive, going by The Lodge now, confirmed on the ground by
A. Hagues, with HM Land Registry's The Lodge on this street identified as this
house. The second property was created from the 1939 Register walk and never
reconciled with it.

**My 444 metres was measured to a point I invented.** Gartree Lodge's position
is confirmed; #436's was a guess off the schedule order, written into the
record as provisional and then quoted back as evidence. A provisional point
cannot refute a confirmed one.

**The 1939 empty mark on Gartree Lodge goes.** It was never empty that night -
George William Kerr, gardener, was in it, filed under the other property.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
DROP, KEEP = 436, 404
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

cur.execute("""SELECT ce.census_year, p.first_name, p.last_name, ce.age_at_census,
                      ce.census_household_num, ce.address
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id=%s ORDER BY ce.census_year, ce.id""", (DROP,))
for r in cur.fetchall():
    print("   #436 row", r)
cur.execute("""SELECT ce.census_year, p.first_name, p.last_name, ce.age_at_census
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id=%s ORDER BY ce.census_year, ce.id""", (KEEP,))
for r in cur.fetchall():
    print("   #404 row", r)
for t in ('property_residents', 'property_names', 'census_unoccupied'):
    for pid in (DROP, KEEP):
        cur.execute(f"SELECT count(*) FROM {t} WHERE property_id=%s", (pid,))
        n = cur.fetchone()[0]
        if n:
            print(f"   {t:<20} #{pid}  {n}")
cur.execute("SELECT census_year, notes FROM census_unoccupied WHERE property_id=%s", (KEEP,))
for r in cur.fetchall():
    print("   #404 empty mark", r)

if not apply:
    print("\n  preview only - pass --apply")
    sys.exit()

cur.execute("""UPDATE census_entries
                  SET property_id=%s, address='Gartree Lodge, 17a Tattershall Drive',
                      source = source || ' - The Lodge and Gartree Lodge are one house, '
                        'confirmed on the ground by A. Hagues; the record held them as two'
                WHERE property_id=%s""", (KEEP, DROP))
print("   census rows moved:", cur.rowcount)
cur.execute("""UPDATE property_residents SET property_id=%s WHERE property_id=%s
                AND NOT EXISTS (SELECT 1 FROM property_residents b
                  WHERE b.property_id=%s AND b.person_id=property_residents.person_id)""",
            (KEEP, DROP, KEEP))
for t in ('property_residents', 'property_names', 'property_research', 'property_watches',
          'census_unoccupied'):
    cur.execute(f"DELETE FROM {t} WHERE property_id=%s", (DROP,))
cur.execute("DELETE FROM census_unoccupied WHERE property_id=%s AND census_year=1939", (KEEP,))
print("   1939 empty mark removed from #404:", cur.rowcount)
c.commit()

d = json.load(open('data/all_props.json'))
byid = {p['id']: p for p in d}
k = byid[KEEP]
k['history'] = k['history'].rstrip() + (
    "\n\n**The 1939 Register names it The Lodge**, and the record carried that as a second "
    "property until A. Hagues joined them. Its household on 29 September 1939:\n\n"
    "| | |\n|---|---|\n"
    "| **George William Kerr**, 62 | Gardener, domestic |\n"
    "| **Mary Catherine Kerr** | Unpaid Domestic Duties |\n\n"
    "A gardener in 1939 where a chauffeur had been in 1921 - the house kept its purpose for "
    "eighteen years. The enumerator reached it at schedule 38, between 2 Albury Square and "
    "10 Cavendish Crescent North, which had been read as putting it at the north end of the "
    "drive near Carnoustie Lodge. It does not: the walk crosses to the Crescent at that point "
    "and the lodge it passes is this one, at the Cavendish Road East end of its own garden.")
k['sources']['residents'] = (k['sources']['residents'] +
    "; 1939 Register schedule 38, via The Lodge where the household was first filed")
d = [p for p in d if p['id'] != DROP]
json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
print(f"   #436 removed from the list; {len(d)} properties")
