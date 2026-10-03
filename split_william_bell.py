# -*- coding: utf-8 -*-
"""Two William Bells, held as one: a draper and a coachman.

The record has #3138 keeping 19 Park Valley as a **draper**, aged 41, in 1881,
and heading a house on the even side of Lenton Avenue as a **coachman**, aged
40, in 1891. A man does not get a year younger in ten, and the even side of
Lenton Avenue was the mews - five of its six heads that year were coachmen,
living over the yards that stabled the horses of houses like 19 Park Valley.

The two households share nothing but the name. The draper's wife is Jemma M,
born Grantham, with Florence, Henry, Frank and a newborn son; the coachman's
wife is Mary, born nine years earlier, with Annie, Nellie and a different
Florence. The 1881 import bound its head by name alone and found the coachman.

So the draper becomes his own person. #3138 keeps the 1891 row and the birth
year that agrees with it; the 1881 row, the Park Valley house and the Draper
trade go to the new man. The Coachman trade, recorded five times over, is
reduced to one.

  railway run python3 split_william_bell.py            # preview
  railway run python3 split_william_bell.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT id, census_year, age_at_census, occupation_at_census, property_id
                     FROM census_entries WHERE person_id=3138 ORDER BY census_year""")
    rows = cur.fetchall()
    if len(rows) < 2:
        print("  #3138 holds one round only - already split"); return
    for r in rows:
        print(f"  #3138 holds {r[1]}, aged {r[2]}, {r[3]} (prop {r[4]})")
    print("\n  the 1881 draper becomes a new person; #3138 keeps 1891, the coachman")
    if not APPLY:
        print("\n  Nothing written. Add --apply."); return

    cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_place, bio)
                   VALUES ('William', 'Bell', 'M', 1840, NULL, %s) RETURNING id""",
                ("Draper, of 19 Park Valley, where he was returned as head in 1881 aged 41 with his "
                 "wife Jemma M, his daughter Florence by an earlier marriage, three young sons and "
                 "three servants. Separated from the William Bell who was coachman on Lenton Avenue "
                 "in 1891: the 1881 import bound its head by name alone and found him instead.",))
    new = cur.fetchone()[0]
    cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=3138 AND census_year=1881",
                (new,))
    cur.execute("UPDATE property_residents SET person_id=%s WHERE person_id=3138 AND property_id=270",
                (new,))
    # the Draper trade is his; it is the only one of that name on the old record
    cur.execute("UPDATE occupations SET person_id=%s WHERE person_id=3138 AND occupation='Draper'",
                (new,))
    # and the coachman's trade, written in five times, becomes one
    cur.execute("""DELETE FROM occupations WHERE person_id=3138 AND occupation='Coachman'
                    AND id NOT IN (SELECT MIN(id) FROM occupations
                                    WHERE person_id=3138 AND occupation='Coachman')""")
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year)
                   VALUES (%s, 'William', 'Bell', 1840) ON CONFLICT DO NOTHING""", (new,))
    c.commit()
    print(f"\n  the draper is now #{new}; #3138 is the coachman")
    print(f"  put #{new} into data/people_1881_standard_hill_part2.json for the 19 Park Valley head")


if __name__ == '__main__':
    main()
