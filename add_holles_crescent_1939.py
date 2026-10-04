# -*- coding: utf-8 -*-
"""1 and 3 Holles Crescent, 1939 - schedules 262 and 260.

**The book is taken as RMGB** on the walk: 263 is 3 Park Drive and 264 is 1 Park
Drive, both RMGB, and Holles Crescent runs into Park Drive. No other book uses
either number. The enumerator is working down the odd side - 3 Holles at 260,
1 Holles at 262, then 3 and 1 Park Drive - with 261 still unaccounted for.

Both houses had nothing at all for 1939 until now. The record knew 1 Holles
Crescent in 1891, 1911 and 1921, and 3 Holles Crescent in 1911 and 1921.

**Margaret J Wright** is entered under the name she bore on the night. The index
prints her as *Back (Wright)*, which is the Register's own way of showing a
married name written in later, so Wright is the 1939 name and Back is kept as a
variant - the same reading as Florence Northern, who becomes Verner.

  railway run python3 add_holles_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
RMGB = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
        "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
        "by A. Hagues; sub number {sub}")

HOUSES = [
 (128, 260, "3 Holles Crescent", RMGB, [
  (1, "Rosemarie L E", "Morgan", "F", "1903-06-02", 36, "Private means", "Married", None,
   "the index prints the forename as Rosrmarie, which is a misread Rosemarie"),
  (2, "Joseph D", "Morgan", "M", "1901-05-17", 38, "Agent inspector, insurance", "Married", None,
   "listed second but two years the elder, and sharing her surname, so her husband"),
 ]),
 (127, 262, "1 Holles Crescent", RMGB, [
  (1, "Vernon C", "Wright", "M", "1890-10-30", 48, "Shop proprietor, tobacconist", "Married", None,
   "the record already holds three men called Bernard Wright in 1939, all different; this is a "
   "fourth Wright household and no relation is implied"),
  (2, "Marie E", "Wright", "F", "1892-12-31", 46, "Unpaid domestic duties", "Married", None, None),
  (3, "Margaret J", "Wright", "F", "1919-12-06", 19, "Civil service, clerical assistant", "Single",
   "Back", "the index prints her as Back (Wright); Wright is the name she bore on the night and "
   "Back is written in later, so Back is held as a variant"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, tmpl, people in HOUSES:
        print(f"--- schedule {sched}, {addr} (#{prop})")
        for sub, fn, ln, sex, bd, age, occ, marital, later, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)
                              AND ce.age_at_census=%s""", (sched, fn, ln, age))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = tmpl.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}" + (f"  [later {later}]" if later else ""))
            if not APPLY: continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
            if later:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, later, int(bd[:4]), fn, later))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, occ, sched, marital, src))
            rec = {"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                   "born_date": bd, "id": pid,
                   "census": [{"census_year": 1939, "age_at_census": age, "address": addr,
                               "property_id": prop, "occupation_at_census": occ,
                               "census_household_num": sched, "marital_status": marital,
                               "source": src}]}
            out.append(rec)
    if APPLY:
        json.dump({"note": "**1 and 3 Holles Crescent, schedules 262 and 260 of the 1939 Register, "
                           "ED letter code RMGB.** The book is taken from the walk - 263 is 3 Park "
                           "Drive and 264 is 1 Park Drive, both RMGB - and no other book uses "
                           "either number. Both houses had nothing at all for 1939 before this.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_holles_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
