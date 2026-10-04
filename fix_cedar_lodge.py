"""A. Hagues sent schedule 56 again. The household was already in at Cedar Lodge,
Tunnel Road, but his page corrects the daughter's middle initial and her birth
year, gives her married name, and gives the servant the name she went by."""
import os, sys, psycopg2
apply = '--apply' in sys.argv
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT id,first_name,last_name,born_date,born_year,known_as FROM people WHERE id IN (7488,7490)")
for r in cur.fetchall(): print("  before:", r)
if apply:
    cur.execute("""UPDATE people SET first_name='Audrey H', born_date='1914-07-18', born_year=1914
                    WHERE id=7488""")
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   VALUES (7488,'Audrey H','Jones',1914,'A. Hagues') ON CONFLICT DO NOTHING""")
    cur.execute("UPDATE people SET known_as='Cecily' WHERE id=7490")
    cur.execute("""UPDATE census_entries SET age_at_census=25 WHERE person_id=7488 AND census_year=1939""")
    c.commit()
    cur.execute("SELECT id,first_name,last_name,born_date,born_year,known_as FROM people WHERE id IN (7488,7490)")
    for r in cur.fetchall(): print("  after: ", r)
else: print("  preview only")
