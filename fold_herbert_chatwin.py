"""The 1881 Standard Hill household holds Herbert F Chatwin twice - #6742 and #7734,
both schedule 260, both aged 10, both scholars. #7734 is the one that carries his
born year and his 1939 row at 52 The Ropewalk, so #6742 is the copy to fold away."""
import os, sys, psycopg2
KEEP, DROP = 7734, 6742
apply = '--apply' in sys.argv
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for tbl in ('census_entries','property_residents','occupations','person_alias'):
    cur.execute(f"SELECT count(*) FROM {tbl} WHERE person_id=%s", (DROP,))
    print(f"  {tbl:<20} rows on #{DROP}: {cur.fetchone()[0]}")
cur.execute("SELECT id, census_year, census_household_num FROM census_entries WHERE person_id=%s", (DROP,))
print("  entries to remove:", cur.fetchall())
if apply:
    cur.execute("DELETE FROM census_entries WHERE person_id=%s", (DROP,))
    for tbl in ('property_residents','occupations','person_alias'):
        cur.execute(f"DELETE FROM {tbl} WHERE person_id=%s", (DROP,))
    cur.execute("DELETE FROM people WHERE id=%s", (DROP,))
    c.commit()
    print(f"\n  folded #{DROP} into #{KEEP}")
else:
    print("\n  preview only - pass --apply to fold")
