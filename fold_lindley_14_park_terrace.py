# -*- coding: utf-8 -*-
"""Tinsley Lindley and his wife, each held twice at 14 Park Terrace.

The post-import checklist names **Lindey beside Lindley** as one of the five
variant-spelling duplicates the 1901 gap round made, and the record still has
it - with a second pair made the same way by the 1939 round.

**The husband.** #1819 Tinsley Lindley, born 1865, barrister at law, heads 14
Park Terrace in 1901, 1911 and 1921, and carries the biography: His Honour
Tinsley Lindley, OBE, 27 October 1865 to 31 March 1940, the England footballer
and county court judge. #7889 *Finlay* Lindley, born 1865, **barrister at law**,
is at **14 Park Terrace** in 1939, aged 73. A T read as an F. He died six months
after the register was taken, so the 1939 line is his last.

**The wife.** #1820 Constance Agnes **Lindey**, born 1865, is the wife at the
same house in 1911 and 1921; #7890 Constance Agnes **Lindley**, born 1865, is
the wife there in 1901 and in 1939. Neither pair overlaps in any round, so
nothing has to be chosen between.

She takes the spelling her husband carries. The names the other copies used are
left behind as aliases, so a re-import finds them.

  railway run python3 fold_lindley_14_park_terrace.py            # preview
  railway run python3 fold_lindley_14_park_terrace.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

PAIRS = [
 (1819, 7889, None, "Finlay Lindley, 73, barrister at law at 14 Park Terrace in 1939 - "
                    "Tinsley Lindley with a T read as an F"),
 (1820, 7890, ("Constance Agnes", "Lindley"),
              "Constance Agnes Lindley, wife at 14 Park Terrace in 1901 and 1939 - the same woman "
              "the record holds as Lindey in 1911 and 1921; she takes her husband's spelling"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for keep, drop, rename, why in PAIRS:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (drop,))
        d = cur.fetchone()
        if not d:
            print(f"  #{drop}: already folded"); continue
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (keep,))
        k = cur.fetchone()
        # nothing may overlap, or a round would end up held twice
        cur.execute("""SELECT census_year FROM census_entries WHERE person_id=%s
                        INTERSECT SELECT census_year FROM census_entries WHERE person_id=%s""",
                    (keep, drop))
        clash = [r[0] for r in cur.fetchall()]
        print(f"  #{drop} {d[0]} {d[1]}  ->  #{keep} {k[0]} {k[1]}")
        print(f"      {why}")
        if clash:
            print(f"      LEFT ALONE - both hold {clash}"); continue
        if rename:
            print(f"      and #{keep} is renamed {rename[0]} {rename[1]}")
        if not APPLY:
            continue
        cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=%s", (keep, drop))
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year)
                       VALUES (%s,%s,%s,1865) ON CONFLICT DO NOTHING""", (keep, d[0], d[1]))
        if rename:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year)
                           VALUES (%s,%s,%s,1865) ON CONFLICT DO NOTHING""", (keep, k[0], k[1]))
            cur.execute("UPDATE people SET first_name=%s, last_name=%s WHERE id=%s",
                        (rename[0], rename[1], keep))
        cur.execute("DELETE FROM property_residents WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM occupations WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
