"""Three repairs on the two Cavendish Crescents.

1. Schedule 254 sat at "9 Cavendish Crescent (the side is not given)". A. Hagues
   has now said it is 9 Cavendish Crescent South - property 42.

2. Schedule 48 was split between two addresses: the housekeeper and the cook at
   17 Cavendish Crescent North, the head loose at "Pendower, Cavendish Crescent
   North". One schedule is one house, so the head joins them at 17.

3. The head was entered as a second John Shaw Perry. He is John Thorpe Perry,
   the one-year-old son of the Park Terrace merchant in 1861 - aged 79 in 1939,
   which is the birth year the Register gives him.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
CCS9, CCN17 = 42, 32
KEEP, DROP = 8037, 8392
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

print("1. schedule 254 -> 9 Cavendish Crescent South")
cur.execute("""SELECT id, source FROM census_entries
                WHERE census_year=1939 AND census_household_num=254""")
s254 = cur.fetchall()
for rid, src in s254:
    print(f"     row{rid}  {src[:72]}...")

print("\n2. schedule 48's head joins the two servants at 17 Cavendish Crescent North")
cur.execute("""SELECT id, source FROM census_entries WHERE person_id=%s AND census_year=1939""", (DROP,))
perry = cur.fetchall()
for rid, src in perry: print(f"     row{rid}  {src[:72]}...")

print(f"\n3. fold #{DROP} John Shaw Perry into #{KEEP} John Thorpe Perry")
for t in ('census_entries','property_residents','occupations','person_alias'):
    cur.execute(f"SELECT count(*) FROM {t} WHERE person_id=%s", (DROP,))
    print(f"     {t:<20} {cur.fetchone()[0]}")

if apply:
    old = '9 Cavendish Crescent (the side is not given)'
    new = '9 Cavendish Crescent South'
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address=%s, unresolved_address=NULL,
                          source=REPLACE(source, %s, %s)
                    WHERE census_year=1939 AND census_household_num=254""", (CCS9, new, old, new))
    print(f"\n  254: {cur.rowcount} rows moved to 9 Cavendish Crescent South")

    # the head's 1939 row moves onto the person we keep, and onto 17
    cur.execute("""UPDATE census_entries
                      SET person_id=%s, property_id=%s, address=%s, unresolved_address=NULL,
                          source=REPLACE(source, 'Pendower, Cavendish Crescent North',
                                                 '17 Cavendish Crescent North, the house named Pendower')
                    WHERE person_id=%s AND census_year=1939""",
                (KEEP, CCN17, '17 Cavendish Crescent North', DROP))
    print(f"  48: {cur.rowcount} row rehoused at 17 and rebound to #{KEEP}")

    cur.execute("UPDATE occupations SET person_id=%s WHERE person_id=%s", (KEEP, DROP))
    cur.execute("UPDATE people SET born_year=COALESCE(born_year,1860), sex=COALESCE(sex,'M') WHERE id=%s", (KEEP,))
    for t in ('census_entries','property_residents','occupations','person_alias'):
        cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (DROP,))
    cur.execute("DELETE FROM people WHERE id=%s", (DROP,))
    c.commit()
    print(f"  folded #{DROP} away")
else:
    print("\n  preview only - pass --apply")
