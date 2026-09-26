# -*- coding: utf-8 -*-
"""Two wrong rows on the 1891 household at 5 Clare Valley.

Schedule 146 was transcribed twice, years apart, and the second pass hung two of
its rows on the wrong people. Both are certain; the Elizabeth G Lewis tangle
found alongside them is not, and is left for the pages.
"""
import os, psycopg2

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    # 1. The wife's row landed on a different Margaret Lewis: the five-year-old
    #    daughter of Henry Lewis at The Chestnuts, 5 Kenilworth Road, in 1881.
    #    She keeps her own row; the Clare Valley row is already held correctly
    #    by person 3360, so this one is simply a second copy in the wrong hands.
    cur.execute("SELECT person_id, property_id, age_at_census FROM census_entries WHERE id=9266")
    assert cur.fetchone() == (7169, 63, 30), "row 9266 is not what was checked"
    cur.execute("SELECT COUNT(*) FROM census_entries WHERE person_id=3360 AND census_year=1891 AND property_id=63")
    assert cur.fetchone()[0] == 1, "the wife's row is not held by person 3360"
    cur.execute("DELETE FROM census_entries WHERE id=9266")
    cur.execute("DELETE FROM property_residents WHERE person_id=7169 AND property_id=63")
    print("  Margaret Lewis: the Clare Valley row taken off the 1881 child of The Chestnuts")

    # 2. "Iuna Holen Lewis" is Gwendolen Lewis misread. The 1901 round has her at
    #    the same house, aged 14 to this row's 4, which settles the name.
    cur.execute("SELECT COUNT(*) FROM census_entries WHERE person_id=7281")
    assert cur.fetchone()[0] == 1, "person 7281 holds more than the one row"
    cur.execute("SELECT COUNT(*) FROM census_entries WHERE person_id=3362 AND census_year=1891 AND property_id=63")
    assert cur.fetchone()[0] == 1, "Gwendolen's own 1891 row is missing"
    cur.execute("DELETE FROM census_entries WHERE person_id=7281")
    cur.execute("DELETE FROM property_residents WHERE person_id=7281")
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   SELECT 3362,'Iuna Holen','Lewis',1887,'merge' FROM (SELECT 1) t
                    WHERE NOT EXISTS (SELECT 1 FROM person_alias a
                                       WHERE a.person_id=3362 AND a.first_name='Iuna Holen')""")
    cur.execute("DELETE FROM people WHERE id=7281")
    print("  Iuna Holen Lewis folded into Gwendolen Lewis, alias kept")

    cur.execute("SELECT COUNT(*) FROM census_entries WHERE property_id=63 AND census_year=1891")
    print(f"\n  5 Clare Valley now holds {cur.fetchone()[0]} people for 1891 - the page shows 8")
    c.commit(); print("committed")

if __name__ == '__main__':
    main()
