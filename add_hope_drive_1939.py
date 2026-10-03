# -*- coding: utf-8 -*-
"""Hope Drive, 1939 - two households off the RMGB book, and a street of gun workers.

Schedules 100 and 101. Between them they hold five men building guns and
aeroplanes six days after the register was taken: three engineers at the gun
factory, an aero engine rigger, a fitter and a travelling inspector of
armaments. Hope Drive had a single round in the record before this.

  railway run python3 add_hope_drive_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (143 if False else 142, 100, "26 Hope Drive", [
   (1, "George H", "Garner", None, "M", "1884-09-09", 55, "Licensee, unemployed", "Married", None),
   (2, "Alice Maud", "Garner", None, "F", "1885-09-07", 54, "Domestic duties", "Married", None),
   (3, "Iris I", "Cranshaw", "Garner", "F", "1910-08-27", 29, "Domestic duties", "Single",
    "the name written over hers afterwards is Garner, which is the name of the couple keeping "
    "this house - and a John Cranshaw of 35 is lodging at 2 Hamilton Drive the same night"),
   (4, "Laurie G", "Clarke", None, "M", "1895-05-29", 44, "Engineer, gun factory", "Single",
    "the index gives the forename as Lawrence G as well as Laurie G"),
   (5, "Jack", "Frith", None, "M", "1910-02-26", 29, "Engineer, gun factory", "Married", None),
   (6, "John A", "Whitfield", None, "M", "1913-12-10", 25, "Aero engine rigger", "Single", None),
   (7, "R", "Gosnell", None, "M", "1914-05-17", 25, "Engineer, gun factory", "Single",
    "the page gives no forename beyond the initial R"),
 ]),
 (None, 101, "24 Hope Drive", [
   (1, "Fred", "Taylor", None, "M", "1915-11-05", 23,
    "Fitter, Royal Ordnance Factory", "Married", None),
   (2, "Kathleen", "Taylor", None, "F", "1914-12-08", 24, "Unpaid domestic duties", "Married", None),
   (3, "John G", "Richardson", None, "M", "1900-02-25", 39,
    "Travelling inspector of armaments", "Married", None),
   (4, "Irene", "Richardson", None, "F", "1899-05-05", 40, "Unpaid domestic duties", "Married", None),
 ]),
]


def main():
    props = {p.get('address'): p['id'] for p in json.load(open('data/all_props.json'))}
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        prop = prop or props.get(addr)
        if not prop:
            print(f"  {addr}: not in the property list"); continue
        print(f"--- schedule {sched}, {addr} (#{prop})")
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                            WHERE c.census_year=1939 AND c.property_id=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                        (prop, fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
            if not APPLY:
                continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
            if later:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment' FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, later, int(bd[:4]), fn, later))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                        "born_date": bd, "match_born_year": True,
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "marital_status": marital, "age_at_census": age,
                                    "occupation_at_census": occ, "census_household_num": sched,
                                    "source": src}], "id": pid})
    if APPLY:
        json.dump({"note": "**Hope Drive, schedules 100 and 101 of the 1939 Register, ED letter "
                           "code RMGB.** A street of gun and aero workers six days after the "
                           "register was taken.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_hope_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
