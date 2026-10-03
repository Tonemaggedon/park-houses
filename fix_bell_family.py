# -*- coding: utf-8 -*-
"""The Bell family of 19 Park Valley, and a Frank hung on the boy next door.

Found by the variant-spelling check after the 1891 Cavendish Crescent South
round. William Bell, draper, kept 19 Park Valley in 1881 with his second wife,
his daughter Florence by his first, and three small sons. By 1891 he is dead,
his widow heads 15 Cavendish Crescent South on her own means, and Florence is
her **stepdaughter** - which is what identifies her.

Two things are wrong, and both are arithmetic rather than judgement.

**Florence is in the record twice.** 14 in 1881 and 24 in 1891 both work back to
1867, she is born in Nottingham on both returns, and her brothers Henry and
Frank are in both houses. The 1891 round made a second Florence because the
1881 one carries no birth year for the matcher to agree with.

**The 1891 Frank Bell row is on the wrong Frank.** Two boys of that name were
returned next door to each other in 1881: Frank Bell of 19 Park Valley,
schedule 217, aged 2 and born in Nottingham, and Frank Bell of 21 Park Valley,
schedule 216, aged 7 and born in New York. The 1891 row gives Frank Bell aged
12, which is the first boy grown up - the second would be 17. It is on the
second. So it moves to his brother, in the household his brother's family
actually heads.

  railway run python3 fix_bell_family.py            # preview
  railway run python3 fix_bell_family.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    # --- Florence, held twice -------------------------------------------------
    cur.execute("SELECT first_name, last_name, born_year FROM people WHERE id=8923")
    if cur.fetchone():
        print("Florence: #8923 Florence Bell (1891, stepdaughter, 24) folds into")
        print("          #6215 Florence E Bell (1881, daughter, 14) - both work back to 1867")
        if APPLY:
            cur.execute("""UPDATE census_entries SET person_id=6215
                            WHERE person_id=8923 AND NOT EXISTS
                              (SELECT 1 FROM census_entries o
                                WHERE o.person_id=6215 AND o.census_year=census_entries.census_year)""")
            cur.execute("DELETE FROM census_entries WHERE person_id=8923")
            cur.execute("DELETE FROM property_residents WHERE person_id=8923")
            # the name the 1891 round used is worth keeping, so a re-import finds her
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year)
                           VALUES (6215, 'Florence', 'Bell', 1867)
                           ON CONFLICT DO NOTHING""")
            cur.execute("DELETE FROM people WHERE id=8923")
            # 1881 and 1891 agree on the year, so it can be written down
            cur.execute("UPDATE people SET born_year=1867 WHERE id=6215 AND born_year IS NULL")
    else:
        print("Florence: already folded")

    # --- Frank, on the wrong brother -----------------------------------------
    cur.execute("""SELECT id, age_at_census FROM census_entries
                    WHERE person_id=6207 AND census_year=1891""")
    row = cur.fetchone()
    if row:
        print(f"\nFrank:    the 1891 row (aged {row[1]}) moves from")
        print("          #6207 Frank Bell, 7 in 1881 at 21 Park Valley, born New York - he would be 17")
        print("          #6217 Frank Bell, 2 in 1881 at 19 Park Valley, born Nottingham - he is 12")
        if APPLY:
            cur.execute("UPDATE census_entries SET person_id=6217 WHERE id=%s", (row[0],))
            cur.execute("UPDATE people SET born_year=1879 WHERE id=6217 AND born_year IS NULL")
    else:
        print("\nFrank:    already moved")

    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
