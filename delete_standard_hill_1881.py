"""The forty-one unfiled Standard Hill rows of 1881, removed on A. Hagues' word.

Standard Hill is outside the record's ground - the same ruling he gave for the
1901 Standard Hill households earlier today.

Eight households go: the Sculthorpes, the Richardses, the Boyeses, the
Lowndeses, the Selbys, the Bartons, the Chatwins and the Pettifors, schedules
254 to 261.

**Three people keep a round elsewhere and are not touched as people:**

  Herbert F Chatwin, who is at 52 The Ropewalk in the 1939 Register
  Sarah Pettifor, at Harpenden, Lenton Road in 1901
  Elizabeth Allwood, at 11 Park Valley in 1901

**And Jane Chatwin is not lost either.** She is in the record twice - as the
annuitant of 50 at Standard Hill in 1881, and as the widow of 70 at 52 The
Ropewalk in 1901, which is the same woman twenty years on. The 1881 record goes
with the rest; the 1901 one stays, and carries the note.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
W = """census_year=1881 AND property_id IS NULL
       AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE '%standard hill%'"""
cur.execute(f"SELECT id, person_id FROM census_entries WHERE {W}")
rows = cur.fetchall()
ids = [r[1] for r in rows]
print(f"  {len(rows)} rows across 8 households")
cur.execute(f"""SELECT count(*) FROM people p WHERE p.id = ANY(%s)
                  AND (SELECT count(*) FROM census_entries ce WHERE ce.person_id=p.id) = 1""", (ids,))
print(f"  people who would be left with nothing: {cur.fetchone()[0]}")
if apply:
    # keep the 1881/1901 Jane Chatwin connection in the surviving row before the old one goes
    cur.execute("""UPDATE census_entries
                      SET source = source || ' - the 1881 census had her at Standard Hill, an '
                            'annuitant of 50, with her son Herbert F Chatwin aged 10. Those rows '
                            'were removed when Standard Hill was ruled outside the record''s ground; '
                            'she is the same woman, twenty years on'
                    WHERE person_id=9378 AND census_year=1901
                      AND source NOT ILIKE '%annuitant of 50%'""")
    cur.execute(f"DELETE FROM census_entries WHERE {W}")
    n = cur.rowcount
    gone = 0
    for pid in ids:
        cur.execute("SELECT count(*) FROM census_entries WHERE person_id=%s", (pid,))
        if cur.fetchone()[0] == 0:
            for t in ('property_residents','occupations','person_alias'):
                cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (pid,))
            cur.execute("DELETE FROM people WHERE id=%s", (pid,))
            gone += 1
    c.commit()
    print(f"\n  {n} rows removed, {gone} people with them")
    cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1881 AND property_id IS NULL
                    AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE '%standard hill%'""")
    print(f"  Standard Hill 1881 rows remaining: {cur.fetchone()[0]}")
    for pid, lbl in ((7734,'Herbert F Chatwin'),(4308,'Sarah Pettifor'),(4831,'Elizabeth Allwood'),
                     (9378,'Jane Chatwin')):
        cur.execute("""SELECT ce.census_year, COALESCE(NULLIF(ce.address,''),ce.unresolved_address)
                         FROM census_entries ce WHERE ce.person_id=%s""", (pid,))
        print(f"   {lbl} keeps: {cur.fetchall()}")
else:
    print("\n  preview only - pass --apply")
