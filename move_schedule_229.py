"""The old 1939 import put schedule 229 - Henry J Holmes, taxi driver, and
Frances M - at 19 Cavendish Crescent South, which is also where it put schedule
231. A. Hagues has read the House column as 1, which leaves 231 alone at 19."""
import os, sys, psycopg2
apply = '--apply' in sys.argv
CCS1 = 38
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.id,p.first_name,p.last_name,ce.property_id,ce.source
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.census_year=1939 AND ce.census_household_num=229
                  AND ce.source NOT ILIKE '%RMG%' ORDER BY ce.id""")
rows = cur.fetchall()
for r in rows: print(f"  row{r[0]} {r[1]} {r[2]} | prop {r[3]} | {r[4]}")
if apply:
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='1 Cavendish Crescent South', unresolved_address=NULL,
                          source = source || ', 1 Cavendish Crescent South'
                    WHERE census_year=1939 AND census_household_num=229 AND source NOT ILIKE %s""",
                (CCS1, '%RMG%'))
    c.commit()
    print(f"\n  {cur.rowcount} rows moved to 1 Cavendish Crescent South")
else:
    print("\n  preview only - pass --apply")
