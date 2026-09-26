# -*- coding: utf-8 -*-
"""Sunnyside was held twice. It is one house, and A. Hagues has identified the site.

#415, "Sunny Side, 12 Park Valley", was built on 24 September 2026 off two
enumerators' pages. #390, "Sunnyside, Park Terrace", came from Dougal de
Havilland's Park Map and from A. Hagues's knowledge of the ground.

They are the same house, and the disagreement was never really one. The house
stood on the cliff: Park Terrace along the top, Park Valley at the foot, Sun
Drive on the other side. One enumerator walked it from above and two from below,
and the people living in it gave a Park Valley postal address. On the Ordnance
Survey sheet the plot is Clinton House's ground, and the cliff-hugging
twentieth-century houses on Park Terrace stand on it now.

#390 survives, because it carries the Map label and the position A. Hagues set
himself. The number 12 is withdrawn: it was never on any page, only inferred
from where the enumerator turned from the odd side onto the even.
"""
import os, psycopg2

DROP, KEEP = 415, 390
ADDRESS = "Sunnyside, Park Terrace"
FILED = ("filed at Sunnyside on A. Hagues's identification of the site, "
         "26 September 2026, the house having stood on the cliff between "
         "Park Terrace and Park Valley")

SOURCE_FIXES = [
    # the number 12 was an inference from walk order, not a reading
    ("1939 Register, schedule 121, 12 Park Valley, written as Sunnyside",
     "1939 Register, schedule 121, Sunnyside, Park Valley"),
    ("the house is not identified in the record, so this row is left unfiled", FILED),
]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    cur.execute("UPDATE census_entries SET property_id=%s WHERE property_id=%s", (KEEP, DROP))
    print(f"  census rows moved #{DROP} -> #{KEEP}: {cur.rowcount}")

    # a resident of the folded house is a resident of the same house
    cur.execute("""UPDATE property_residents SET property_id=%s WHERE property_id=%s
                    AND NOT EXISTS (SELECT 1 FROM property_residents r2
                                     WHERE r2.property_id=%s AND r2.person_id=property_residents.person_id)""",
                (KEEP, DROP, KEEP))
    moved = cur.rowcount
    cur.execute("DELETE FROM property_residents WHERE property_id=%s", (DROP,))
    print(f"  residents moved: {moved}, duplicates dropped: {cur.rowcount}")

    cur.execute("UPDATE census_entries SET address=%s WHERE property_id=%s", (ADDRESS, KEEP))
    print(f"  address set on {cur.rowcount} rows: {ADDRESS}")

    for old, new in SOURCE_FIXES:
        cur.execute("UPDATE census_entries SET source=REPLACE(source,%s,%s) "
                    "WHERE property_id=%s AND source LIKE %s", (old, new, KEEP, '%'+old+'%'))
        print(f"  source clause rewritten on {cur.rowcount} rows")

    # the 1921 rows came in from the National Archives with no detail of their own
    cur.execute("""UPDATE census_entries SET source=%s
                    WHERE property_id=%s AND census_year=1921 AND source='National Archives 1921 Census'""",
                ("National Archives 1921 Census; the householders' own cover sheets give the "
                 "postal address as Sunnyside, Park Valley, Nottingham - registration district 430, "
                 "sub-district 1, enumeration district 16 - and are signed L. C. Ord and C. Parker, "
                 "two separate returns from the one house", KEEP))
    print(f"  1921 rows given their cover-sheet source: {cur.rowcount}")

    cur.execute("DELETE FROM property_data WHERE id=%s", (DROP,))
    print(f"  property_data row for #{DROP} removed: {cur.rowcount}")

    cur.execute("SELECT census_year, COUNT(*) FROM census_entries WHERE property_id=%s GROUP BY 1 ORDER BY 1", (KEEP,))
    print(f"\n  #{KEEP} now holds: {cur.fetchall()}")
    c.commit(); print("committed")

if __name__ == '__main__':
    main()
