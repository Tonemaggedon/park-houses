# -*- coding: utf-8 -*-
"""The whole 1861 Ropewalk, numbered by A. Hagues from the enumerator's run.

The 1861 walk descends the Ropewalk: 32a at schedule 113 down to 2a at 131,
with 16 already fixed at schedule 122 by Charles Buttery, who is there in 1871
and 1881 too. That one known point and the count of houses either side of it
settle every other schedule in the run.

Two dwellings in the run have no number on the page:

  schedule 129  a small building at the corner, still standing, holding
                William Hurst, solicitor, and three others. Held unnumbered.
  schedule 131  2a - the second of the pair at number 2, whose listing records
                it as "formerly 2no. townhouses c1835-40".

188 people were unfiled on this street in 1861, the largest single block in the
whole record. This closes it.
"""
import os, psycopg2

RUN = [
 (113, 329, "32a The Ropewalk", "Moritz Jacoby, lace merchant, born Germany"),
 (114, 328, "32 The Ropewalk",  "George Berrey, lace manufacturer"),
 (115, 327, "30 The Ropewalk",  "John Jackson, coachman"),
 (116, 326, "28 The Ropewalk",  "William Patterson, retired from business, born Scotland"),
 (117, 325, "26 The Ropewalk",  "Nathaniel Dickenson, pawnbroker"),
 (118, 324, "24 The Ropewalk",  "James Wallis, clothier"),
 (119, 323, "22 The Ropewalk",  "Francis Braithwaite, hosiery manufacturer - and 22 has Mary "
                                "Braithwaite in 1881, which corroborated the run before it was numbered"),
 (120, 322, "20 The Ropewalk",  "Edward Stegemann, lace manufacturer, born Germany"),
 (121, 321, "18 The Ropewalk",  "Richard Hall, landed proprietor"),
 # 38 falls out on its own: schedule 109 is the only household between 108 (40)
 # and 110 (36a), and 38 is the only number between them.
 (109, 332, "38 The Ropewalk",  "Jonathan Reckless, lace manufacturer - the only household between "
                                "schedules 108 at 40 and 110 at 36a, and 38 the only number between them"),
 (123, 319, "14 The Ropewalk",  "Thomas Shaw, lace manufacturer"),
 (124, 318, "12 The Ropewalk",  "Cuthbert Orlebar, clergyman"),
 (125, 317, "10 The Ropewalk",  "John Tom Yeatman, barrister at law"),
 (126, 316, "8 The Ropewalk",   "Frances Cook, householder"),
 (127, 315, "6 The Ropewalk",   "Luke S Mason, lace manufacturer"),
 (128, 314, "4 The Ropewalk",   "Edward Monk, landed proprietor"),
 (129, 430, "The Ropewalk (unnumbered, between 4 and 2)",
                                "William Hurst, solicitor - a small building at the corner that has no "
                                "number on the page and none in the record"),
 (130, 313, "2 The Ropewalk",   "John Scott Wells, hosiery manufacturer"),
 (131, 429, "2a The Ropewalk",  "Sarah Wise, schoolmistress - the second of the pair at number 2, and "
                                "the last schedule on the street"),
]
WHY = ("numbered by A. Hagues from the 1861 enumerator's run, which descends the Ropewalk from 32a to "
       "2a with 16 fixed at schedule 122 by Charles Buttery, who is at 16 in 1871 and 1881 as well")

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    total = 0
    for sched, pid, addr, who in RUN:
        cur.execute("""SELECT COUNT(*) FROM census_entries
                        WHERE census_year=1861 AND census_household_num=%s AND property_id IS NULL""", (sched,))
        n = cur.fetchone()[0]
        if not n:
            print(f"  schedule {sched}: nothing unfiled - skipped"); continue
        cur.execute("SELECT COUNT(*) FROM census_entries WHERE census_year=1861 AND property_id=%s", (pid,))
        assert cur.fetchone()[0] == 0, f"#{pid} already holds an 1861 household"
        cur.execute("""UPDATE census_entries SET property_id=%s, address=%s, unresolved_address=NULL,
                              source = source || %s
                        WHERE census_year=1861 AND census_household_num=%s AND property_id IS NULL""",
                    (pid, addr, f"; {who}; {WHY}", sched))
        print(f"  sched {sched:<4} -> #{pid:<4} {addr:<42} {cur.rowcount:2d} people")
        total += cur.rowcount
    cur.execute("""SELECT COUNT(*) FILTER (WHERE property_id IS NOT NULL),
                          COUNT(*) FILTER (WHERE property_id IS NULL), COUNT(*)
                     FROM census_entries WHERE census_year=1861""")
    print(f"\n  {total} people placed.  1861 filed/unfiled/total: {cur.fetchone()}")
    cur.execute("""SELECT COUNT(*) FROM census_entries WHERE census_year=1861 AND property_id IS NULL
                     AND unresolved_address ILIKE '%%ropewalk%%'""")
    print(f"  still unfiled on the Ropewalk in 1861: {cur.fetchone()[0]}")
    c.commit(); print("committed")

if __name__ == '__main__':
    main()
