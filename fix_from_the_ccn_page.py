"""A. Hagues sent the Register page for schedules 41 to 49 of Cavendish Crescent
North. It answers a question written the same hour and corrects three names.

  * Thorsmore is schedule 45, ticked and left blank - the gap in the walk.
  * The grocer at 11 is Arthur W Richardson, not Richard W.
  * The family at 19 is Vaulkhard, not Vauckhard.
  * 15 is the house the page writes, in quotation marks, as "Flixton".
  * Margaret Vaulkhard is in the record twice, the second time under the
    married name stamped over her entry.

And, on his word, 18 Park Terrace stood empty.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
TWENTY_TWO_AND_FOUR, EIGHTEEN_PT = 36, 416
KEEP, DROP = 7479, 8594          # Margaret Vaulkhard / Margaret V Hyltonsmith
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

THORSMORE = ("Thorsmore, ticked and left blank at schedule 45 of the 1939 Register, ED letter code "
             "RMGC. The page runs 43 at number 18, 44 at Castle Mount, 45 at Thorsmore, then 46 at "
             "11 - so Thorsmore is the last house on the even side before the enumerator crosses "
             "over. 22 and 24 is the only even house left on the street, which is why the record "
             "puts it here, but the page gives no number and that identification is not proved.")
PT18 = ("18 Park Terrace stood empty on the night of 29 September 1939, on A. Hagues' reading of the "
        "page. Its schedule number is not yet known: the RMGC Park Terrace run has no room left for "
        "it - 151 is 16, 152 is 17, 153 to 156 are the four flats at 19, and 157 is 56 The Ropewalk.")

print("1. Thorsmore -> schedule 45, blank, at 22 and 24 Cavendish Crescent North")
print("2. 18 Park Terrace -> blank in 1939")
print("3. Vauckhard -> Vaulkhard")
cur.execute("SELECT id,first_name,last_name FROM people WHERE last_name='Vauckhard' ORDER BY id")
for r in cur.fetchall(): print(f"     #{r[0]} {r[1]} {r[2]}")
print("4. Richard W Richardson -> Arthur W Richardson (#7467)")
print(f"5. fold #{DROP} Margaret V Hyltonsmith into #{KEEP} Margaret H Vaulkhard")
cur.execute("SELECT id,census_year,census_household_num FROM census_entries WHERE person_id=%s",(DROP,))
print("     rows:", cur.fetchall())

if apply:
    for pid, note in ((TWENTY_TWO_AND_FOUR, THORSMORE), (EIGHTEEN_PT, PT18)):
        cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes) VALUES (%s,1939,%s)
                       ON CONFLICT (property_id, census_year) DO UPDATE SET notes=EXCLUDED.notes""", (pid, note))
    cur.execute("UPDATE people SET last_name='Vaulkhard' WHERE last_name='Vauckhard'")
    print(f"\n  {cur.rowcount} Vauckhards renamed")
    cur.execute("UPDATE person_alias SET last_name='Vaulkhard' WHERE last_name='Vauckhard'")
    cur.execute("UPDATE census_entries SET source=REPLACE(source,'Vauckhard','Vaulkhard') WHERE source ILIKE '%Vauckhard%'")
    cur.execute("UPDATE people SET first_name='Arthur W' WHERE id=7467 AND first_name='Richard W'")
    print(f"  Richardson renamed: {cur.rowcount}")
    # her married name becomes an alias, and the second person goes
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   VALUES (%s,'Margaret V','Hyltonsmith',1919,'A. Hagues')
                   ON CONFLICT DO NOTHING""", (KEEP,))
    cur.execute("DELETE FROM census_entries WHERE person_id=%s", (DROP,))
    for t in ('property_residents','occupations','person_alias'):
        cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (DROP,))
    cur.execute("DELETE FROM people WHERE id=%s", (DROP,))
    c.commit()
    print(f"  folded #{DROP} into #{KEEP}")
else:
    print("\n  preview only - pass --apply")
