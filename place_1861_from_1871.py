# -*- coding: utf-8 -*-
"""The 1861 round placed by walking it against 1871.

The 1861 enumerator wrote street names and no numbers, which left 385 of the
round's 432 people unfiled - the largest single block in the record. 1871 gives
numbers for the same ground, so where a household stands in both rounds the
1871 number places the 1861 one.

Two things came out of laying the walks side by side.

  Park Terrace climbs in both rounds. 1861 schedule 85 is the one house the
  page does number - "6 Park Terrace" - and Robert Hoyles is there, with Robert
  Hoyle at 6 in 1871. From there the two runs keep step.

  The Ropewalk runs the other way. 1861 descends the numbers where 1871 climbs
  them, which is why the schedule numbers move in opposite directions: 56, 40,
  36a, 36, 34 ... 16 as 1861 goes on.

Only households whose head is in both rounds, on the same street, are placed.
Somebody who moved between the two is not evidence of a house.
"""
import os, psycopg2

# 1861 schedule, property, address, why
PLACE = [
 (85,  246, "6 Park Terrace",
  'the page itself writes "6 Park Terrace" against this schedule, and Robert Hoyles is here; '
  'Robert Hoyle is at 6 Park Terrace in 1871'),
 (88,  248, "8 Park Terrace",
  'Martha Clarke, boarding house keeper, heads this house in 1861 and 8 Park Terrace in 1871'),
 (93,  252, "12 Park Terrace",
  'Henry Wing, solicitor, heads this house in 1861 and 12 Park Terrace in 1871 and 1881'),
 (95,  378, "13 Park Terrace",
  'Catherine Turner heads this house in 1861 and 13 Park Terrace in 1871'),
 (96,  253, "14 Park Terrace",
  'William Gibson, hosiery manufacturer, heads this house in 1861 and 14 Park Terrace in 1871'),
 (105, 339, "56 The Ropewalk",
  'Joseph Smith heads this house in 1861 and 56 The Ropewalk in 1871'),
 (108, 333, "40 The Ropewalk",
  'William Henry Blackmer heads this house in 1861 and 40 The Ropewalk in 1871'),
 (110, 418, "36a The Ropewalk",
  'Samuel Newham heads this house in 1861 and 36a The Ropewalk in 1871'),
 (111, 331, "36 The Ropewalk",
  'placed by the walk rather than by a name: a gardener with two in the house, standing between '
  '36a and 34 in the 1861 run exactly as Edward Woolley, gardener, with two in the house, stands '
  'between them in 1871'),
 (112, 330, "34 The Ropewalk",
  'Thomas Herbert heads this house in 1861 and 34 The Ropewalk in 1871'),
 (122, 320, "16 The Ropewalk",
  'Charles Buttery, retired druggist, heads this house in 1861 and 16 The Ropewalk in 1871'),
]
NOTE = " - placed 27 September 2026 by walking the 1861 round against 1871"

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    total = 0
    for sched, pid, addr, why in PLACE:
        cur.execute("""SELECT COUNT(*) FROM census_entries
                        WHERE census_year=1861 AND census_household_num=%s AND property_id IS NULL""", (sched,))
        n = cur.fetchone()[0]
        if not n:
            print(f"  schedule {sched}: nothing unfiled - skipped"); continue
        cur.execute("""SELECT COUNT(*) FROM census_entries WHERE census_year=1861 AND property_id=%s""", (pid,))
        assert cur.fetchone()[0] == 0, f"#{pid} already holds an 1861 household"
        cur.execute("""UPDATE census_entries
                          SET property_id=%s, address=%s, unresolved_address=NULL,
                              source = source || %s
                        WHERE census_year=1861 AND census_household_num=%s AND property_id IS NULL""",
                    (pid, addr, "; " + why + NOTE, sched))
        print(f"  schedule {sched:<4} -> #{pid:<4} {addr:<18} {cur.rowcount} people")
        total += cur.rowcount
    cur.execute("""SELECT COUNT(*) FILTER (WHERE property_id IS NOT NULL),
                          COUNT(*) FILTER (WHERE property_id IS NULL), COUNT(*)
                     FROM census_entries WHERE census_year=1861""")
    print(f"\n  {total} people placed.  1861 filed/unfiled/total now: {cur.fetchone()}")
    c.commit(); print("committed")

# --------------------------------------------------------------------------
# And two 1871 households placed the same way, by elimination along the walk.

PLACE_1871 = [
 (125, 251, "11 Park Terrace",
  'the only Park Terrace house between 1 and 17 with no 1871 household, and the only 1871 Park '
  'Terrace household with no house - one to one. The walk reaches it between 12 and 13, and 11 '
  'stands about three metres from 12, so 12, 11, 13 is the natural order on the ground. '
  'William Knight, timber merchant, and seven others'),
 (113, 406, "Broxtowe House, Park Terrace",
  'a Bradley household standing immediately before 1 Park Terrace in the 1871 walk, exactly where '
  'Broxtowe House stands in the 1891 walk, and Broxtowe House is held by Alfred Bradley in 1891, '
  '1901 and 1911 but has nothing for 1871. The head is on the previous page; the schedule opens '
  'with his daughter'),
]

def place_1871():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for sched, pid, addr, why in PLACE_1871:
        cur.execute("""SELECT COUNT(*) FROM census_entries
                        WHERE census_year=1871 AND census_household_num=%s AND property_id IS NULL""", (sched,))
        n = cur.fetchone()[0]
        if not n:
            print(f"  1871 schedule {sched}: nothing unfiled - skipped"); continue
        cur.execute("SELECT COUNT(*) FROM census_entries WHERE census_year=1871 AND property_id=%s", (pid,))
        assert cur.fetchone()[0] == 0, f"#{pid} already holds an 1871 household"
        cur.execute("""UPDATE census_entries SET property_id=%s, address=%s, unresolved_address=NULL,
                              source = source || %s
                        WHERE census_year=1871 AND census_household_num=%s AND property_id IS NULL""",
                    (pid, addr, "; " + why + " - placed 27 September 2026 by walking 1871 against the rounds either side", sched))
        print(f"  1871 schedule {sched:<4} -> #{pid:<4} {addr:<30} {cur.rowcount} people")
    cur.execute("""SELECT COUNT(*) FILTER (WHERE property_id IS NOT NULL),
                          COUNT(*) FILTER (WHERE property_id IS NULL) FROM census_entries WHERE census_year=1871""")
    print(f"  1871 filed/unfiled now: {cur.fetchone()}")
    c.commit(); print("committed")


if __name__ == '__main__':
    import sys
    if '--1871' in sys.argv: place_1871()
    else: main()
