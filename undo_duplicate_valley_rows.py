"""Clare Valley and Park Valley were already in the record, and I duplicated them.

The existing transcription is sourced "1901 census, Brewhouse Yard and Standard
Hill, Castle ward - read from the enumerator's pages supplied by A. Hagues" and
covers **schedules 47 to 121**. Its rows carry no address field, only the source
line, so the check I ran - which looked for an address naming the street - found
nothing and I transcribed the pages a second time.

Forty rows went in where my reading of a name or an age differed from the
existing one, so the guard did not catch them: Rose Aster against Rose Asher,
Mag Millwood against Mag. Millwood, Ruth Snell at 21 against 27, and so on.
Those forty are removed, and the people made for them with them.

**The Ropewalk work stands.** The existing transcription starts at schedule 47;
The Ropewalk is schedules 1 to 27 and was genuinely absent.

Also: Annie M Pawn at 32 The Ropewalk is **Annie M Tawn**, on A. Hagues' reading.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
MINE = "%read from the enumerator's page by A. Hagues%"
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.id, ce.person_id, p.first_name, p.last_name, ce.census_household_num
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.census_year=1901 AND ce.census_household_num BETWEEN 49 AND 72
                  AND ce.source LIKE %s ORDER BY ce.census_household_num""", (MINE,))
rows = cur.fetchall()
print(f"  {len(rows)} rows of mine to remove:")
for r in rows[:10]: print(f"     s{r[4]} #{r[1]} {r[2]} {r[3]}")
if len(rows) > 10: print(f"     ... and {len(rows)-10} more")
cur.execute("SELECT id FROM people WHERE first_name='Annie M' AND last_name='Pawn'")
print("  Annie M Pawn -> Tawn:", cur.fetchall())
if apply:
    ids = [r[1] for r in rows]
    cur.execute("""DELETE FROM census_entries WHERE census_year=1901
                    AND census_household_num BETWEEN 49 AND 72 AND source LIKE %s""", (MINE,))
    n = cur.rowcount
    gone = 0
    for pid in ids:
        cur.execute("SELECT count(*) FROM census_entries WHERE person_id=%s", (pid,))
        if cur.fetchone()[0] == 0:
            for t in ('property_residents','occupations','person_alias'):
                cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (pid,))
            cur.execute("DELETE FROM people WHERE id=%s", (pid,))
            gone += 1
    cur.execute("UPDATE people SET last_name='Tawn' WHERE first_name='Annie M' AND last_name='Pawn'")
    cur.execute("""UPDATE census_entries
                      SET source = REPLACE(source,'the forename is not clear and may be Minnie or Nina',
                                  'A. Hagues reads the surname Tawn')
                    WHERE census_year=1901 AND census_household_num=16""")
    c.commit()
    print(f"\n  {n} duplicate rows removed, {gone} people with them; Annie M Tawn corrected")
    for f in ('data/people_1901_clare_and_park_valley.json',):
        if os.path.exists(f): os.remove(f); print(f"  {f} removed")
    cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1901
                    AND census_household_num BETWEEN 1 AND 27 AND source LIKE %s""", (MINE,))
    print(f"  The Ropewalk rows that stand: {cur.fetchone()[0]}")
else:
    print("\n  preview only - pass --apply")
