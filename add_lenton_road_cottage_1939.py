# -*- coding: utf-8 -*-
"""The gardener's cottage on Lenton Road, 1939 - a couple the record already holds.

Schedule 96 of RMGB is a cottage on Lenton Road with a gardener and his wife.
They are not new: **John George Stell**, gardener, and **Sarah Ann Stell** are at
**11 Lenton Road** in 1921, he 47 and she 51, and the birth dates agree. So the
rows are bound to the people the record has rather than minting a second pair.

**The surname is Stell.** A. Hagues suggested it might be Still; the 1921 round
was read from the enumerator's page and says Stell, which is a better witness
than an index, and the 1939 index says Stell too.

**The house is not identified.** The page says only a cottage on Lenton Road.
The record holds *The Stables, Lenton Road*, a *Fern Cottage* unfiled from 1891,
and 10 Lenton Road under the former name *The Bungalow* - and the Stells
themselves were at number 11 eighteen years before.

  railway run python3 add_lenton_road_cottage_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SCHED = 96
ADDR = "Cottage, Lenton Road"
SRC = ("1939 Register, schedule 96, a cottage on Lenton Road, ED letter code RMGB, Nottingham "
       "registration district 430-3, sub-district 26, The National Archives RG101/6178A - read "
       "from the page by A. Hagues; sub number {sub}; the house is not identified in the record, "
       "so this row is left unfiled. {note}")

PEOPLE = [
 (1447, 1, "1874-03-18", 65, "Gardener", "Married",
  "He is the John George Stell who is gardener at 11 Lenton Road in 1921, aged 47 - the same man "
  "eighteen years on, still gardening. The surname reads Stell on the 1921 page as well as in "
  "this index; A. Hagues raised Still as a possibility and the earlier round argues against it."),
 (1448, 2, "1869-02-22", 70, "Unpaid domestic duties", "Married",
  "She is the Sarah Ann Stell at 11 Lenton Road in 1921, aged 51."),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for pid, sub, bd, age, occ, marital, note in PEOPLE:
        cur.execute("""SELECT 1 FROM census_entries WHERE person_id=%s AND census_year=1939""", (pid,))
        if cur.fetchone():
            print(f"  #{pid}: already has a 1939 row"); continue
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (pid,))
        fn, ln = cur.fetchone()
        print(f"  sub {sub} #{pid} {fn} {ln}, {age} - {occ}")
        if not APPLY:
            continue
        cur.execute("""INSERT INTO census_entries
                       (person_id, census_year, unresolved_address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,1939,%s,%s,%s,%s,%s,%s)""",
                    (pid, ADDR, age, occ, SCHED, marital, SRC.format(sub=sub, note=note)))
        cur.execute("UPDATE people SET born_date=%s WHERE id=%s AND born_date IS NULL", (bd, pid))
    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
