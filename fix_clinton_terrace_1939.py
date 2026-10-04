"""A. Hagues sent schedules 190, 192 and 193 under the heading Clifton Terrace.
They are Clinton Terrace - the walk runs 119, 121, 125, 127, 129, 131, 133, 135
and 139 Derby Road without a break, and the Clinton Terrace houses are the ones
that carry Derby Road numbers. All three households were already in the record
at the right houses.

What his pages do give:

  * Enid May is in the record twice on the same schedule, once as Hurden and
    once as Mead, both born 6 March 1920 and both cigarette workers.
  * Tom Percy Sampson had no birth date.
  * Eight people carry index readings of their names that the record does not
    hold, so a search under the index spelling finds nobody.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
KEEP, DROP = 7817, 8614
ALIASES = [(7817,'Enid May','Murden'), (7817,'Enid Mary','Mead'),
           (7818,'Wenna R','Scheweizer'), (7819,'Arthur G','Fork'),
           (7820,'Frank','Carr'), (7821,'Alfred','Hodgson'),
           (7822,'Sydney','Defeyser'), (7825,'James B','Fernie'),
           (7826,'Samuel William','Slaton'), (7827,'John Bradby','Pearl')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT id, census_year, census_household_num FROM census_entries WHERE person_id=%s", (DROP,))
print(f"  #{DROP} Enid Mary Mead carries {cur.fetchall()}")
cur.execute("SELECT born_date FROM people WHERE id=7832")
print(f"  #7832 Tom Percy Sampson born_date: {cur.fetchone()[0]}")
print(f"  {len(ALIASES)} index readings to add as variants")
if apply:
    for t in ('census_entries','property_residents','occupations','person_alias'):
        cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (DROP,))
    cur.execute("DELETE FROM people WHERE id=%s", (DROP,))
    cur.execute("UPDATE people SET born_date='1877-11-12', born_year=1877 WHERE id=7832 AND born_date IS NULL")
    # the index gives the unit, where the record had only the rank
    cur.execute("""UPDATE census_entries SET occupation_at_census='Lieutenant, Territorial Army, 148th Brigade HQ'
                    WHERE person_id=7820 AND census_year=1939""")
    n = 0
    for pid, fn, ln in ALIASES:
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, made_by)
                       VALUES (%s,%s,%s,'A. Hagues') ON CONFLICT DO NOTHING""", (pid, fn, ln))
        n += cur.rowcount
    c.commit()
    print(f"\n  folded #{DROP} into #{KEEP}, Sampson dated, {n} variants added")
else:
    print("\n  preview only - pass --apply")
