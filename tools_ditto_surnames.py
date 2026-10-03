# -*- coding: utf-8 -*-
"""The surnames that are really ditto marks, traced back to the head of the house.

An enumerator writes the family name against the head of the household and
rules it down the column. A transcription that reads the mark as a value puts
people into the record with their **middle initial** standing where the family
name should be - *Ellen T.*, *Frank B.*, *Jane A. B.* - and they are invisible
everywhere on the site except Names to Check.

Nineteen came in with the 1901 gap round. The initial is not noise: it is the
person's middle initial, and the family name is the one the head of their
household carries. So this moves the initial into the forename, where it
belongs, and takes the surname from the head.

A household is read as everyone at the same address in the same year, which is
how these rows are gathered - most of them have no schedule number.

  railway run python3 tools_ditto_surnames.py            # preview
  railway run python3 tools_ditto_surnames.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
MARK = r'^([A-Za-z]\.?|["'']+|-+|do\.?|ditto)$'


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT p.id, p.first_name, p.last_name, ce.census_year, ce.relationship,
                          COALESCE(NULLIF(ce.address,''), ce.unresolved_address) AS addr
                     FROM people p JOIN census_entries ce ON ce.person_id=p.id
                    WHERE trim(p.last_name) ~ %s ORDER BY ce.census_year, 6, p.id""", (MARK,))
    todo = cur.fetchall()
    done = skipped = 0
    for pid, first, last, year, rel, addr in todo:
        # the head of the same house in the same year carries the family name
        cur.execute("""SELECT p2.id, p2.first_name, p2.last_name
                         FROM census_entries c2 JOIN people p2 ON p2.id=c2.person_id
                        WHERE c2.census_year=%s
                          AND COALESCE(NULLIF(c2.address,''), c2.unresolved_address) = %s
                          AND lower(c2.relationship) = 'head'
                          AND trim(p2.last_name) !~ %s""", (year, addr, MARK))
        heads = cur.fetchall()
        surnames = {h[2] for h in heads}
        if len(surnames) != 1:
            print(f"  #{pid} {first} {last!r:<8} {rel:<9} {addr}")
            print(f"      LEFT ALONE - {len(heads)} head(s) at that address: "
                  f"{', '.join(sorted(surnames)) or 'none found'}")
            skipped += 1
            continue
        surname = surnames.pop()
        initial = last.strip().rstrip('.')
        new_first = f"{first} {initial}".strip() if initial.isalpha() else first
        print(f"  #{pid} {first} {last!r}  ->  {new_first} {surname}"
              f"   ({rel.lower()} at {addr}, head is {heads[0][1]} {surname})")
        if APPLY:
            cur.execute("UPDATE people SET first_name=%s, last_name=%s WHERE id=%s",
                        (new_first, surname, pid))
        done += 1
    print(f"\n  {done} to put right, {skipped} left alone")
    if APPLY:
        c.commit(); print("  committed")
    else:
        print("  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
