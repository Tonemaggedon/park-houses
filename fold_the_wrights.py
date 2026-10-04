# -*- coding: utf-8 -*-
"""The Wrights of 24 Barrack Lane, Haddon House and 2 Park Drive - one family, held six ways.

A. Hagues warned that the 1939 round holds **three different Bernard Wrights**,
and it does: a butler of 25 at 21 Lenton Avenue, a solicitor of 63 at Haddon
House, and a solicitor of 34 at 2 Park Drive. But checking that warning showed
that two of the three are **father and son**, and that the record was holding
three members of the family twice over.

**24 Barrack Lane in 1911** held them all: Bernard Swanwick Wright, his wife
Florence Mary, his daughter Kathleen Florence and his son **Bernard Joseph
Maxwell**, with three servants. By 1921 they were at Haddon House.

| held twice | and as |
|---|---|
| **#7400 Bernard John Wright**, 1939, solicitor, 2 Park Drive | **#3252 Bernard Joseph Maxwell Wright**, the son at 24 Barrack Lane. The index gives him *Bernard J M*, which is what names him |
| **#9020 Florence M Wright**, 1939, Haddon House | **#3251 Florence Mary Wright**, the wife, in the record from 1901 and at 24 Barrack Lane in 1911 |
| **#8589 Margaret Edn Wright**, 1939, 2 Park Drive | **#7403 Margaret Edna Fraxer**, same birth date, same schedule, same house |

  railway run python3 fold_the_wrights.py            # preview
  railway run python3 fold_the_wrights.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

PAIRS = [
 (3252, 7400, None,
  "Bernard Joseph Maxwell Wright - the index gives him as Bernard J M, and the record held him "
  "as a boy at 24 Barrack Lane in 1911 and as Bernard JOHN Wright, solicitor, at 2 Park Drive "
  "in 1939. Son of Bernard Swanwick Wright of Haddon House, also a solicitor"),
 (3251, 9020, None,
  "Florence Mary Wright - Bernard Swanwick Wright's wife, in the record from 1901 and at 24 "
  "Barrack Lane in 1911, and entered again as new at Haddon House in 1939"),
 (7403, 8589, None,
  "Margaret Edna Fraxer - the same woman twice in one schedule, once under her own name and "
  "once as Wright. The index renders her surname Frzer and cannot read her forename at all, "
  "which the record supplies"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for keep, drop, _rename, why in [(a, b, c_, d) for a, b, c_, d in PAIRS]:
        cur.execute("SELECT first_name, last_name, born_date FROM people WHERE id=%s", (drop,))
        d = cur.fetchone()
        if not d:
            print(f"  #{drop}: already folded"); continue
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (keep,))
        k = cur.fetchone()
        cur.execute("""SELECT census_year FROM census_entries WHERE person_id=%s
                        INTERSECT SELECT census_year FROM census_entries WHERE person_id=%s""",
                    (keep, drop))
        clash = [r[0] for r in cur.fetchall()]
        print(f"  #{drop} {d[0]} {d[1]}  ->  #{keep} {k[0]} {k[1]}")
        print(f"      {why}")
        if clash:
            print(f"      both hold {clash} - the duplicate row goes, the keeper's stays")
        if not APPLY:
            continue
        # anything the keeper lacks comes across first
        cur.execute("""UPDATE people SET born_date=COALESCE(born_date,%s),
                         born_year=COALESCE(born_year,%s) WHERE id=%s""",
                    (d[2], int(d[2][:4]) if d[2] else None, keep))
        cur.execute("""UPDATE census_entries n SET person_id=%s
                        WHERE n.person_id=%s AND NOT EXISTS
                          (SELECT 1 FROM census_entries o WHERE o.person_id=%s
                             AND o.census_year=n.census_year)""", (keep, drop, keep))
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
