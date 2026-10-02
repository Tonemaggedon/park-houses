# -*- coding: utf-8 -*-
"""7 Hamilton Drive, 1939 - a boarding house of eight, and a woman put back in it.

The page settles what two schedule 83s had left in doubt. **The run is ED letter
code RMGB**, a second book covering Hamilton Drive, and its schedule 83 is **7
Hamilton Drive** - so it is not the RMGC schedule 83 at Ribble Lodge at all.

**Muriel Langtree belongs here**, not at Ribble Lodge, where she had been posted
from an index on the strength of a schedule number that belongs to the other
book. Her birth year stands: the page reads 7 March 1918, and she is 21.

The household is A. Hagues's reading; the house and the district are read off
the page header and the address column.

  railway run python3 add_7_hamilton_drive_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED, ADDR = 120, 83, '7 Hamilton Drive'
SRC = ("1939 Register, schedule 83, 7 Hamilton Drive, ED letter code RMGB, Nottingham "
       "registration district 430-3, sub-district 26 - read from the page by A. Hagues; "
       "sub number {sub}")

# sub, forename, surname, amended surname, sex, born_date, age, occupation, marital, note
PEOPLE = [
 (1, "Horatio", "Nelson", None, "M", "1878-02-15", 61, "Boarding house keeper", "Married", None),
 (2, "Helen", "Nelson", None, "F", "1878-10-30", 60, "Domestic duties", "Married",
  "the index gives the forename as Ellen as well as Helen"),
 (3, "Florence M", "Hill", None, "F", "1895-10-25", 43, "Shorthand typist, civil service", "Single", None),
 (4, "Alexander", "Scott", None, "M", "1893-06-01", 46, "Export despatch clerk, textile", "Single", None),
 (5, "William", "Fraser", None, "M", "1908-11-12", 30,
  "Companion secretary, Trent Navigation", "Married", None),
 (6, "Betty D", "Williams", None, "F", "1908-02-09", 31, "Supervisor, ladies' fashion", "Married",
  "the line carries more than one surname and the page is written over here"),
 (7, "Ronald H", "Cotter", None, "M", "1914-11-15", 24, "Binder, system export", "Single", None),
]
MOVE = (7557, 8, "Muriel", "Langtree", "School teacher",
        "entered as Muriel Langtree, which is her name on the night; Cotter is written over it in "
        "a later hand, and sub number 7 of this schedule is Ronald H Cotter, single and the same "
        "age. The record had her at Ribble Lodge on Clare Valley, posted there from an index on a "
        "schedule number that belongs to the other book")


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for sub, fn, ln, later, sex, bd, age, occ, marital, note in PEOPLE:
        cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                        WHERE c.census_year=1939 AND c.property_id=%s
                          AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                    (PROP, fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
        if not APPLY:
            continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
        pid = cur.fetchone()[0]
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                    (pid, PROP, ADDR, age, occ, SCHED, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                    "born_date": bd, "match_born_year": True,
                    "census": [{"census_year": 1939, "property_id": PROP, "address": ADDR,
                                "marital_status": marital, "age_at_census": age,
                                "occupation_at_census": occ, "census_household_num": SCHED,
                                "source": src}], "id": pid})
        print(f"        entered as #{pid}")

    pid, sub, fn, ln, occ, note = MOVE
    cur.execute("SELECT id, property_id FROM census_entries WHERE person_id=%s AND census_year=1939", (pid,))
    row = cur.fetchone()
    if row and row[1] != PROP:
        print(f"  sub {sub} {fn} {ln}: moved from house {row[1]} to {ADDR}, and given her trade")
        if APPLY:
            cur.execute("""UPDATE census_entries SET property_id=%s, address=%s,
                             occupation_at_census=%s, source=%s
                            WHERE id=%s""",
                        (PROP, ADDR, occ, SRC.format(sub=sub) + '; ' + note, row[0]))
    elif row:
        print(f"  sub {sub} {fn} {ln}: already at {ADDR}")

    if APPLY:
        json.dump({"note": "**7 Hamilton Drive, schedule 83 of the 1939 Register, ED letter code "
                           "RMGB.** A boarding house of eight. The whole of Hamilton Drive had only "
                           "a 1921 round in the record until this page.",
                   "source": "1939 Register, ED letter code RMGB, district 430-3, sub-district 26",
                   "people": out}, open('data/people_1939_rmgb_hamilton_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
