# -*- coding: utf-8 -*-
"""Split welded people by the house they were in, not by the row's number.

tools_split_welded_people.py names the census rows to move by their id, and that
stops working the moment a re-import recreates a row with a new id - which is
why half its entries report "expected 1 rows, found 0" and the same welds keep
coming back. A person, a round and a house are stable; a row id is not.

Each entry below says: this person is holding rows for more than one house in
one round, and these ones belong to somebody else. The someone-else is made
fresh, with a birth year worked out from the age on the row, so the two are told
apart afterwards by more than a name.

Every split here is read off the record: two different ages, two different
birthplaces, or a daughter of nineteen and a wife of forty-three.

Usage:
  railway run python3 tools_split_by_house.py          # show
  railway run python3 tools_split_by_house.py --apply  # do it
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

# (person, [(round, property_id), ...] to move away, why)
SPLITS = [
 # The two Elizabeth Browns are NOT a weld - they are two people who each hold
 # BOTH women's rows, so the fix is a duplicate row removed from each, not a split.
 # See fix_elizabeth_brown.py.
 (4124, [(1881, 182), (1891, 179)], "the cork cutter's wife, born Tewkesbury - 51 at 8 Lenton Road and 61 at 6 Lenton Road"),
 (3794, [(1881, 182), (1891, 179), (1901, None)], "William Lewis the cork cutter, born Nottingham - a different man from the hosiery manufacturer of 3 Pelham Crescent, who was born at Tewkesbury"),
 (28,   [(1881, 286)], "Emily S Johnson, wife of the Town Clerk at 17 Pelham Crescent, 43 and born Middlesex - not the daughter of 19 at Lenton House, born London"),
 (3142, [(1891, 44)],  "a stepdaughter of 24 at 15 Cavendish Crescent South - not the scholar of 10 at 8 Lenton Avenue"),
 (7114, [(1881, 365)], "George Parr the solicitor, 35 and born Gotham, at 33 Lenton Road - not Samuel Parr's son of 21, a clerk in a soda factory"),
 (6808, [(1881, 43)],  "a housemaid of 23 born Linton at 11 Cavendish Crescent South - not the housemaid of 22 born Nottingham at 4 Clinton Terrace"),
 (7116, [(1881, 241)], "a domestic housekeeper of 55 born Walesby at 1 Park Terrace - not the daughter of 22 at Fairlawn"),
 (7119, [(1881, 175)], "a servant and cook of 28 born Tipton at 2 Lenton Road - not the servant of 18 born Ruddington at 121 Derby Road, whose birth year #7119 already carries"),
]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    made = moved = 0
    for pid, houses, why in SPLITS:
        cur.execute("SELECT first_name, last_name, sex FROM people WHERE id=%s", (pid,))
        who = cur.fetchone()
        if not who: print(f"  #{pid}: no such person - skipped"); continue
        fn, ln, sex = who
        rows = []
        for yr, prop in houses:
            cur.execute("""SELECT id, age_at_census, birth_place FROM census_entries
                            WHERE person_id=%s AND census_year=%s AND property_id IS NOT DISTINCT FROM %s""",
                        (pid, yr, prop))
            rows += [(r[0], yr, prop, r[1], r[2]) for r in cur.fetchall()]
        if not rows:
            print(f"  #{pid} {fn} {ln}: nothing left to move - already split"); continue
        # the person must still be holding more than one house in one of those rounds,
        # or this is not a weld and moving the row would be a mistake
        yrs = {r[1] for r in rows}
        for yr in yrs:
            cur.execute("SELECT COUNT(*) FROM census_entries WHERE person_id=%s AND census_year=%s", (pid, yr))
            if cur.fetchone()[0] < 2:
                print(f"  #{pid} {fn} {ln}: only one row for {yr} - skipped, nothing assumed")
                rows = [r for r in rows if r[1] != yr]
        if not rows: continue
        age = next((r[3] for r in rows if r[3] is not None), None)
        born = (rows[0][1] - age) if age is not None else None
        bp = next((r[4] for r in rows if r[4]), None)
        print(f"  #{pid} {fn} {ln}  ->  a new person, born about {born}")
        print(f"      {why}")
        for rid, yr, prop, a, b in rows:
            print(f"      row {rid}  {yr}  house {prop}  aged {a}")
        if APPLY:
            cur.execute("""INSERT INTO people (first_name,last_name,sex,born_year,born_place)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, born, bp))
            new = cur.fetchone()[0]
            for rid, yr, prop, a, b in rows:
                cur.execute("UPDATE census_entries SET person_id=%s WHERE id=%s", (new, rid))
                cur.execute("""UPDATE property_residents SET person_id=%s
                                WHERE person_id=%s AND property_id IS NOT DISTINCT FROM %s
                                  AND NOT EXISTS (SELECT 1 FROM property_residents r2
                                                   WHERE r2.person_id=%s AND r2.property_id=%s)""",
                            (new, pid, prop, new, prop))
                moved += 1
            print(f"      -> new person #{new}")
            made += 1
    print(f"\n  {made} people made, {moved} rows moved" if APPLY else "\n  Nothing written. Add --apply.")
    if APPLY:
        cur.execute("SELECT COUNT(*) FROM (SELECT person_id,census_year FROM census_entries GROUP BY 1,2 HAVING COUNT(*)>1) t")
        print(f"  people in two places in one round: {cur.fetchone()[0]}")
        c.commit(); print("committed")

if __name__ == '__main__':
    main()
