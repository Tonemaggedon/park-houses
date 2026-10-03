# -*- coding: utf-8 -*-
"""The duplicates a wobbling birth year makes, folded by hand.

An import file that carries `match_born_year` needs the year to agree exactly,
and a birth year worked back from a census age moves by a year or two between
returns. So the importer finds nobody, makes a second person, and the two sit
side by side holding one household between them.

The post-import checklist names this fault and names two of these people -
Margaret Lewis and William Bowers - and the record has made them again. The
shape-matching fold does not catch them because the new row is unfiled and the
old one has a house, so they are folded here by hand.

**Each pair is the same person on the same night**: same surname, same forename,
same round, same age, and the same house once the unfiled address is read.

  railway run python3 fold_match_born_year_duplicates.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

# keep, fold away, why
PAIRS = [
 (3360, 8920, "Margaret Lewis, 37 in 1901 on Clare Valley - the new row calls the house Elmsdale "
               "and the old one 5 Clare Valley"),
 (3970, 8921, "William Bowers, 58 in 1901 on Lenton Avenue - the old row has the house as number 3"),
 (535,  8922, "Emma Radford, 37 in 1901 on Pelham Crescent - the old row has the house as number 1"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for keep, drop, why in PAIRS:
        cur.execute("SELECT first_name, last_name, born_year FROM people WHERE id=%s", (drop,))
        got = cur.fetchone()
        if not got:
            print(f"  #{drop}: already folded away"); continue
        print(f"  #{drop} {got[0]} {got[1]} (b.{got[2]})  ->  #{keep}")
        print(f"      {why}")
        if not APPLY:
            continue
        # anything the keeper has not got comes across; the rest is a true duplicate
        cur.execute("""UPDATE census_entries n SET person_id=%s
                        WHERE n.person_id=%s AND NOT EXISTS
                          (SELECT 1 FROM census_entries o
                            WHERE o.person_id=%s AND o.census_year=n.census_year)""",
                    (keep, drop, keep))
        cur.execute("DELETE FROM census_entries WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM property_residents WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
