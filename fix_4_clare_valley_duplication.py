"""4 Clare Valley was in the record already, as the Wilkins family.

I checked schedule 51 and found it empty, so I entered the household. The
existing rows **carry no schedule number at all** - they are sourced only "1901
census, 4 Clare Valley - transcribed by A. Hagues" - so a check on the schedule
could not see them, any more than a check on the address could see the Brewhouse
Yard set. That is the third form the same mistake has taken today.

The fix keeps the older rows, which carry the household's history, and takes
A. Hagues' correction to the surname: **Wilkins becomes Page**. My eight rows go,
and the schedule number they carried - 51 - is written onto the rows that stay,
which is the one thing they were missing.

The servant the old rows call Ruth **Hallam** I read as Ruth Wallam. The older
reading stands and mine is kept as a variant.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
MINE = [11641,11642,11643,11644,11645,11646,11647,11648]
RENAME = [(3337,'Lawrence','Page'),(1948,'E Jessie','Page'),(3338,'L A','Page'),
          (3339,'Eleanor','Page'),(3340,'Jessie','Page')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT person_id FROM census_entries WHERE id = ANY(%s)", (MINE,))
people = [r[0] for r in cur.fetchall()]
print(f"  removing {len(MINE)} rows of mine and {len(people)} people")
for pid, fn, ln in RENAME:
    cur.execute("SELECT first_name,last_name FROM people WHERE id=%s", (pid,))
    print(f"   #{pid} {cur.fetchone()} -> {fn} {ln}")
if apply:
    cur.execute("DELETE FROM census_entries WHERE id = ANY(%s)", (MINE,))
    for pid in people:
        cur.execute("SELECT count(*) FROM census_entries WHERE person_id=%s", (pid,))
        if cur.fetchone()[0] == 0:
            for t in ('property_residents','occupations','person_alias'):
                cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (pid,))
            cur.execute("DELETE FROM people WHERE id=%s", (pid,))
    for pid, fn, ln in RENAME:
        cur.execute("""INSERT INTO person_alias (person_id,first_name,last_name,made_by)
                       SELECT %s, first_name, last_name, 'A. Hagues' FROM people WHERE id=%s
                        AND NOT EXISTS (SELECT 1 FROM person_alias a
                          WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM((SELECT first_name FROM people WHERE id=%s)))
                            AND LOWER(TRIM(a.last_name))='wilkins')""", (pid, pid, pid))
        cur.execute("UPDATE people SET first_name=%s, last_name=%s WHERE id=%s", (fn, ln, pid))
    cur.execute("""INSERT INTO person_alias (person_id,first_name,last_name,made_by)
                   VALUES (7133,'Ruth','Wallam','A. Hagues') ON CONFLICT DO NOTHING""")
    cur.execute("""UPDATE census_entries
                      SET census_household_num=51,
                          source = source || '; the household is SCHEDULE 51, and the surname is '
                                   'PAGE on A. Hagues'' reading of the page - the record had Wilkins'
                    WHERE property_id=62 AND census_year=1901 AND census_household_num IS NULL""")
    print(f"\n  {cur.rowcount} surviving rows given schedule 51 and the Page reading")
    c.commit()
    cur.execute("""SELECT p.first_name,p.last_name,ce.age_at_census,ce.relationship,ce.census_household_num
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.property_id=62 AND ce.census_year=1901 ORDER BY ce.id""")
    print("  4 Clare Valley, 1901:")
    for r in cur.fetchall(): print(f"     {r[0]} {r[1]}, {r[2]}, {r[3]}, s{r[4]}")
    import os as _os
    f='data/people_1901_4_clare_valley.json'
    if _os.path.exists(f): _os.remove(f); print("  import file removed")
else:
    print("\n  preview only - pass --apply")
