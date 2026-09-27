# -*- coding: utf-8 -*-
"""Five 1871 Ropewalk households placed off the now-numbered 1861 run.

The 1861 Ropewalk was numbered from the enumerator's page on 27 September 2026.
The 1871 numbers are read straight off their own page, and the 1871 walk jumps
about rather than running in order - 18, then 16, then 24 - so the walk itself
places nothing. What does place these five is the head being the same person,
or the same family, in the 1861 house.

Checked against 1881 in every case, and the three rounds agree where they
overlap: Buttery at 16 and Smith at 56 in all three, Herbert at 34 in 1861 and
1871 and his widow there in 1881.
"""
import os, psycopg2

PLACE = [
 (204, 322, "20 The Ropewalk",
  "Edward Stegeman, shipping merchant - Edward Stegemann, lace manufacturer, born Germany, is at 20 "
  "in 1861. The house has Mary M Whitty by 1881, so he had gone"),
 (205, 323, "22 The Ropewalk",
  "Joseph Braithwaite, magistrate - Francis Braithwaite, hosiery manufacturer, is at 22 in 1861 and "
  "Mary Braithwaite is there in 1881. Three rounds of Braithwaites in the one house"),
 (208, 326, "28 The Ropewalk",
  "William Patterson, retired silk merchant - William Patterson, retired from business, born "
  "Scotland, is at 28 in 1861. Not to be confused with the William A Patterson of schedule 196, a "
  "magistrate and silk throwster, who is left unfiled"),
 (209, 329, "32a The Ropewalk",
  "Violet Jacoby - Moritz Jacoby, lace merchant, born Germany, is at 32a in 1861. The schedule is "
  "addressed only 'The Park', with no house named"),
 (197, 314, "4 The Ropewalk",
  "Edward Munk, retired merchant - Edward Monk, landed proprietor, is at 4 in 1861, the spelling "
  "differing by a letter. Note that 1881 has William A Patterson at 4, so the house changed hands "
  "between the rounds"),
]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    total = 0
    for sched, pid, addr, why in PLACE:
        cur.execute("""SELECT COUNT(*) FROM census_entries
                        WHERE census_year=1871 AND census_household_num=%s AND property_id IS NULL""", (sched,))
        n = cur.fetchone()[0]
        if not n:
            print(f"  schedule {sched}: nothing unfiled - skipped"); continue
        cur.execute("SELECT COUNT(*) FROM census_entries WHERE census_year=1871 AND property_id=%s", (pid,))
        assert cur.fetchone()[0] == 0, f"#{pid} already holds an 1871 household"
        cur.execute("""UPDATE census_entries SET property_id=%s, address=%s, unresolved_address=NULL,
                              source = source || %s
                        WHERE census_year=1871 AND census_household_num=%s AND property_id IS NULL""",
                    (pid, addr, "; " + why + " - placed 27 September 2026 against the numbered 1861 run", sched))
        print(f"  sched {sched} -> #{pid:<4} {addr:<18} {cur.rowcount:2d} people")
        total += cur.rowcount
    cur.execute("""SELECT COUNT(*) FILTER (WHERE property_id IS NOT NULL),
                          COUNT(*) FILTER (WHERE property_id IS NULL) FROM census_entries WHERE census_year=1871""")
    print(f"\n  {total} people placed.  1871 filed/unfiled: {cur.fetchone()}")
    cur.execute("""SELECT COUNT(*) FROM census_entries WHERE census_year=1871 AND property_id IS NULL
                     AND unresolved_address ILIKE '%%ropewalk%%'""")
    print(f"  still unfiled on the Ropewalk in 1871: {cur.fetchone()[0]}")
    c.commit(); print("committed")

if __name__ == '__main__':
    main()
