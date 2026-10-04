# -*- coding: utf-8 -*-
"""29 and 31 Lenton Avenue were each transcribed twice in 1881.

One pass read the street without numbers - "1881 census, Lenton Avenue,
schedule 113/114 ... the house is not identified in the record" - and a later
pass read the same two schedules again from RG11/3367 and placed them at 29 and
31. Both passes are in the record, so seven people are held twice, under
spellings close enough that no tool bucketing on the surname can see them:

    Peppercorn / Pepperdine    McEwan / McBean    Maplethorpe / Maplesthorpe
    Jemmina / Jemmima          Piggins / Piggin

**There is only one schedule 113 and one schedule 114**, and each held exactly
these people, so the pairs cannot be different residents. Where the two passes
disagree on an age or a birthplace - Johanna at 26 and at 21, Henry at 22 and
27, Mary born Wellingore and born Welbourn - the disagreement is between two
readings of one line, not between two people.

The **lower-numbered person is kept**, because the rest of each household is
already on that block of ids. The **RG11/3367 row is kept**, because it names
the house and cites the piece; the unnumbered row goes. The spelling the other
pass used is left behind as an alias.

  railway run python3 fold_lenton_avenue_1881_twice.py            # preview
  railway run python3 fold_lenton_avenue_1881_twice.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

# keep, fold away
PAIRS = [
 (3903, 6887, "Reuben Peppercorn / Pepperdine, 31, head"),
 (3904, 6888, "Mary Peppercorn / Pepperdine, 32, wife - born Wellingore in one pass, Welbourn in the other"),
 (3905, 6889, "Herbert Peppercorn / Pepperdine, 3, son"),
 (3906, 6890, "Johanna McEwan / McBean, boarder - 26 in one pass, 21 in the other"),
 (3907, 6891, "Henry Maplethorpe / Maplesthorpe, boarder - 22 in one pass, 27 in the other"),
 (3897, 6885, "Jemmina / Jemmima E Thornley, 20, daughter"),
 (3902, 6886, "Frances Piggins / Piggin, 26, servant"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for keep, drop, why in PAIRS:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (drop,))
        d = cur.fetchone()
        if not d:
            print(f"  #{drop}: already folded"); continue
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (keep,))
        k = cur.fetchone()
        # which 1881 row is the fuller one
        cur.execute("""SELECT id, person_id, source FROM census_entries
                        WHERE person_id IN (%s,%s) AND census_year=1881""", (keep, drop))
        rows = cur.fetchall()
        better = [r for r in rows if r[2] and 'RG11/3367' in r[2]]
        weaker = [r for r in rows if not (r[2] and 'RG11/3367' in r[2])]
        print(f"  #{drop} {d[0]} {d[1]}  ->  #{keep} {k[0]} {k[1]}")
        print(f"      {why}")
        if len(better) != 1 or len(weaker) != 1:
            print(f"      LEFT ALONE - {len(better)} fuller row(s), {len(weaker)} weaker"); continue
        print(f"      keeping row {better[0][0]} (names the house, cites RG11/3367), "
              f"dropping row {weaker[0][0]}")
        if not APPLY:
            continue
        cur.execute("DELETE FROM census_entries WHERE id=%s", (weaker[0][0],))
        cur.execute("UPDATE census_entries SET person_id=%s WHERE id=%s", (keep, better[0][0]))
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name)
                       VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""", (keep, d[0], d[1]))
        cur.execute("DELETE FROM census_entries WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM property_residents WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM occupations WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
