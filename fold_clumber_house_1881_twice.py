# -*- coding: utf-8 -*-
"""Clumber House was transcribed twice in 1881, and six Gregorys came of it.

One schedule - 160, Clumber House, Park Drive, RG11/3367 - and the record holds
**six of its people under two names each**, because a second pass read the
forenames shorter than the first:

    William Godfrey / William G      Ellen Augusta / Ellen A
    William Jr      / William        Charles Arthur / Charles A
    Harriett Jr     / Harriett       Frank Henry    / Frank Hy

The first pass is the family's own block of ids, with rows in 1881, 1891 and
1901. The second made six new people with one row apiece. Nothing matched them,
because a surname bucket cannot see that *Charles Arthur* and *Charles A* are
one boy.

**The second pass is the better transcription** - every one of its rows cites
RG11/3367, where five of the six first-pass rows carry no source at all, and it
gives Charles his trade as a fitter where the other leaves him blank. So the
**person** kept is the one with the fuller forename and the longer life in the
record, and the **row** kept is whichever of the two is sourced.

  railway run python3 fold_clumber_house_1881_twice.py            # preview
  railway run python3 fold_clumber_house_1881_twice.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

PAIRS = [(95, 7063), (97, 7064), (99, 7065), (100, 7066), (102, 7067), (103, 7068)]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for keep, drop in PAIRS:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (drop,))
        d = cur.fetchone()
        if not d:
            print(f"  #{drop}: already folded"); continue
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (keep,))
        k = cur.fetchone()
        cur.execute("""SELECT id, person_id, (source IS NOT NULL) FROM census_entries
                        WHERE person_id IN (%s,%s) AND census_year=1881 ORDER BY id""", (keep, drop))
        rows = cur.fetchall()
        if len(rows) != 2:
            print(f"  #{drop} -> #{keep}: {len(rows)} rows for 1881, left alone"); continue
        sourced = [r for r in rows if r[2]]
        best = sourced[0] if sourced else rows[0]
        other = [r for r in rows if r[0] != best[0]][0]
        print(f"  #{drop} {d[0]} {d[1]}  ->  #{keep} {k[0]} {k[1]}")
        print(f"      keeping row {best[0]} ({'sourced' if best[2] else 'no source'}), "
              f"dropping row {other[0]} ({'sourced' if other[2] else 'no source'})")
        if not APPLY:
            continue
        cur.execute("DELETE FROM census_entries WHERE id=%s", (other[0],))
        cur.execute("UPDATE census_entries SET person_id=%s WHERE id=%s", (keep, best[0]))
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
