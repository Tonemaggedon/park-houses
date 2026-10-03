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
 (None, 113, "2 Hope Drive", [
   (1, "Francis", "Carner", None, "M", "1877-07-23", 62, "Master b- ; city councillor", "Married",
    "the index leaves the sex unknown; he is married to the woman at sub number 2 and the forename "
    "is Francis, so male is taken. The trade is written Master B and is cut short - master baker, "
    "butcher or builder cannot be told apart from it, and the city councillor is the part that "
    "will be findable"),
   (2, "Maud M", "Carner", None, "F", "1882-01-03", 57, "Unpaid domestic duties", "Married", None),
   (3, "Evelyn M", "Carner", None, "F", "1907-05-10", 32, "Confidential secretary", "Single", None),
   (4, "Gwen Hote", "Schofield", "Carner", "F", "1916-08-03", 23, "Ladies' hairdresser", "Single",
    "the forename is written Gwen Hote and is not a form the record holds. The name written over "
    "hers afterwards is Carner, which is the name of the household she is living in - the fourth "
    "woman on these pages to marry into the house she lodged in"),
   (5, "Dorothy M", "Carner", None, "F", "1911-01-30", 28, "Shop assistant, drapery", "Married", None),
   (6, "Eric R", "Carner", None, "M", "1909-07-17", 30,
    "Cost accounts clerk, Royal Ordnance Factory", "Married", None),
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
                   "people": out}, open('data/people_1939_rmgb_2_hope_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
