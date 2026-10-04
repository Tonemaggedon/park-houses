# -*- coding: utf-8 -*-
"""Two leftovers in the Robinson household at 21 Lenton Avenue, 1901.

Both surfaced while the ditto-mark surnames were being traced. The house was
transcribed twice - once as "21 Lenton Avenue" and once as schedule 140, "No
21" - and two people survived in both copies.

**Minnie carries the wrong surname.** The schedule-140 copy gives her as
*Minnie B Parker*, aged 1, daughter; the record holds *Minnie B. Robinson*,
aged 1, daughter, born Nottingham, in the same house in the same round. There
is no Parker in the household. The ditto that swallowed her brother Lisle's
surname gave her a neighbour's.

**Ethel is in twice over.** *Ethel Dora Hardstaff* and *Ethel M. Hardstaff* are
both 22, both servants, both nurses (domestic), both born Hucknall Torkard, both
at 21 Lenton Avenue in 1901, and both from the same transcription. Only the
middle name differs. One of them is a second pass at the same line.

  railway run python3 fix_21_lenton_avenue.py            # preview
  railway run python3 fix_21_lenton_avenue.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

PAIRS = [
 (2917, 4291, "Minnie B Parker, 1, daughter - the record's Minnie B. Robinson, 1, daughter, "
               "born Nottingham, same house, same round; no Parker lives there"),
 (943, 3081,  "Ethel M. Hardstaff, 22, servant - identical to Ethel Dora Hardstaff in age, trade, "
               "birthplace, house and source; the middle name is all that differs"),
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
        print(f"  #{drop} {d[0]} {d[1]}  ->  #{keep} {k[0]} {k[1]}")
        print(f"      {why}")
        if not APPLY:
            continue
        cur.execute("""UPDATE census_entries k SET
                          birth_place = COALESCE(k.birth_place, d.birth_place),
                          marital_status = COALESCE(k.marital_status, d.marital_status),
                          occupation_at_census = COALESCE(k.occupation_at_census, d.occupation_at_census)
                         FROM census_entries d
                        WHERE k.person_id=%s AND d.person_id=%s AND d.census_year=k.census_year""",
                    (keep, drop))
        cur.execute("""UPDATE census_entries n SET person_id=%s
                        WHERE n.person_id=%s AND NOT EXISTS
                          (SELECT 1 FROM census_entries o WHERE o.person_id=%s
                             AND o.census_year=n.census_year)""", (keep, drop, keep))
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""", (keep, d[0], d[1]))
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
