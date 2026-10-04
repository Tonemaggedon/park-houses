"""Schedule 193 is 9 Cavendish Crescent North.

A. Hagues sent "9 ccn" with the schedule 254 block pasted beneath it - the same
block he sent earlier today under "9 ccs", which is where 254 now sits and where
the walk keeps it. So the heading is the new thing: 9 Cavendish Crescent North.
The household that belongs there is schedule 193, which has sat in the record
all day as "Cavendish Crescent North (no number given)".

Three things say 193 is number 9, and they are independent of each other.

  The walk.  191 is Hardwicke House, 192 is Haddon House, 193, then 194 at
  number 7, 195 at number 5, 196 at number 7 again - the divided house. An
  enumerator coming off Haddon House onto the odd side reaches 9 before 7.

  Elimination.  With 1 and 18a closed as blank this evening, 9 is the only
  house on Cavendish Crescent North with nothing at all for 1939, and 193 is
  the only household on the street with no house.

  A. Hagues' own reading.  He gave the run as "191 Hardwick 192 Haddon 193 no
  number 194 & 196 7 cc 195 5" - all of them North.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
PROP, SCHED, ADDR = 25, 193, "9 Cavendish Crescent North"
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.id, p.first_name, p.last_name, ce.occupation_at_census
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.census_year=1939 AND ce.census_household_num=%s AND ce.property_id IS NULL
                ORDER BY ce.id""", (SCHED,))
rows = cur.fetchall()
for r in rows: print(f"  row{r[0]} {r[1]} {r[2]} - {r[3]}")
cur.execute("SELECT count(*) FROM census_entries WHERE property_id=%s AND census_year=1939", (PROP,))
print(f"\n  {ADDR} currently holds {cur.fetchone()[0]} rows for 1939")
if apply:
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address=%s, unresolved_address=NULL,
                          source=REPLACE(source,'Cavendish Crescent North (no number given)',
                                 %s || ' - the number is not on the page. The walk gives it: 192 is '
                                 'Haddon House, 194 is number 7 and 195 is number 5, so 193 is the '
                                 'house before 7 on the odd side. It is also the only house left on '
                                 'the street with nothing for 1939')
                    WHERE census_year=1939 AND census_household_num=%s AND property_id IS NULL""",
                (PROP, ADDR, ADDR, SCHED))
    print(f"  {cur.rowcount} rows housed at {ADDR}")
    cur.execute("DELETE FROM census_unoccupied WHERE property_id=%s AND census_year=1939", (PROP,))
    c.commit()
else:
    print("\n  preview only - pass --apply")
