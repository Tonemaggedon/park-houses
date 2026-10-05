"""The Castlethorpe household of 1881 is in the record twice over for three of
its people - the head, his elder daughter and his younger son.

Each pair is one person transcribed on two occasions. The older entry carries
the birth year and the later census rounds but its 1881 row has **no schedule
number and no source at all**; the newer entry has the proper citation -
schedule 155, Castlethorpe, Newcastle Circus - but nothing else.

So the fuller person is kept and the better row is kept, which is not the same
record in either case:

  #7032 John H Brownsword, 45, silk merchant  ->  #46 John Hind Brownsword
  #7033 Edith M Brownsword, 12                ->  #48 Edith Mary Brownsword
  #7034 John A Brownsword, 9                  ->  #50 John Anthony Brownsword

Elizabeth Fletcher, the cook, has a birth year of 1885 against an age of 25 in
1881, which cannot be. It is cleared rather than guessed at.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
PAIRS = [(7032, 46, 'John Hind'), (7033, 48, 'Edith Mary'), (7034, 50, 'John Anthony')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for drop, keep, name in PAIRS:
    cur.execute("""SELECT id, census_household_num, source IS NOT NULL
                     FROM census_entries WHERE person_id=%s AND census_year=1881""", (drop,))
    good = cur.fetchall()
    cur.execute("""SELECT id, census_household_num, source IS NOT NULL
                     FROM census_entries WHERE person_id=%s AND census_year=1881""", (keep,))
    bad = cur.fetchall()
    print(f"  #{drop} -> #{keep} {name}")
    print(f"     sourced row kept:   {good}")
    print(f"     unsourced row gone: {bad}")
if apply:
    for drop, keep, name in PAIRS:
        # the unsourced 1881 row on the person we keep goes; the sourced one moves onto them
        cur.execute("""DELETE FROM census_entries WHERE person_id=%s AND census_year=1881
                        AND (source IS NULL OR source='')""", (keep,))
        cur.execute("""UPDATE census_entries SET person_id=%s WHERE person_id=%s""", (keep, drop))
        for t in ('property_residents', 'occupations'):
            cur.execute(f"""UPDATE {t} SET person_id=%s WHERE person_id=%s
                             AND NOT EXISTS (SELECT 1 FROM {t} b WHERE b.person_id=%s
                                               AND b.property_id IS NOT DISTINCT FROM {t}.property_id)""",
                        (keep, drop, keep)) if t == 'property_residents' else \
            cur.execute(f"UPDATE {t} SET person_id=%s WHERE person_id=%s", (keep, drop))
        cur.execute("DELETE FROM property_residents WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM person_alias WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    cur.execute("UPDATE people SET born_year=NULL WHERE id=7132 AND born_year=1885")
    print(f"\n  three folded; Elizabeth Fletcher's impossible birth year cleared: {cur.rowcount}")
    c.commit()
    cur.execute("""SELECT p.id,p.first_name,p.last_name,p.born_year,ce.age_at_census,ce.relationship,
                          ce.census_household_num
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.property_id=206 AND ce.census_year=1881 ORDER BY ce.id""")
    print("\n  Castlethorpe 1881 now:")
    for r in cur.fetchall(): print(f"     #{r[0]:<5} {r[1]} {r[2]:<12} b.{r[3]} age{r[4]} {r[5]} hh{r[6]}")
else:
    print("\n  preview only - pass --apply")
