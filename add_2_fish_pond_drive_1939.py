# -*- coding: utf-8 -*-
"""2 Fish Pond Drive, 1939 - schedule 26, and a number three books use.

**Schedule 26 is already used twice over**: by RMGC for *Castle Rising, 3 Lenton
Road* and by RMGA for *Rock House, Barrack Lane*. This is a third use of it, so
Fish Pond Drive is in a book the record still cannot name - as numbers 4 and 6
were at schedules 77 and 78. The book is left unstated rather than guessed.

**Saul Barnett supervises electrical cleaning and washing machines**, and his
two daughters are both in the gown trade - one selling, one dressing windows.

**The two daughters cannot both be Minnie's.** Betty was born 29 November 1916
and Freda 15 May 1917, less than six months apart, so one of them is a
stepdaughter, or a birth date on the page is wrong.

  railway run python3 add_2_fish_pond_drive_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NOBOOK = ("1939 Register, schedule {sched}, {addr} - read from the page by A. Hagues; sub number "
          "{sub}. THE ED LETTER CODE IS NOT KNOWN for this household: schedule {sched} is already "
          "used by the RMGC book for Clare Valley, so this is another book, and the record will "
          "not guess which")
RMGB = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
        "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
        "by A. Hagues; sub number {sub}")

HOUSES = [
 (373, 26, "2 Fish Pond Drive", NOBOOK, [
  (1, "Saul", "Barnett", "M", "1885-08-20", 54,
   "Supervisor, electrical cleaning and washing machines", "Married",
   "schedule 26 is used by RMGC for Castle Rising, 3 Lenton Road and by RMGA for Rock House, "
   "Barrack Lane, so this is a third book - and the record will not guess which"),
  (2, "Minnie", "Barnett", "F", "1892-04-02", 47, "Unpaid domestic duties", "Married",
   "seven years younger than Saul and sharing his surname, so his wife"),
  (3, "Betty", "Barnett", "F", "1916-11-29", 22, "Gown saleslady", "Single",
   "the index gives her as Sokoloff (Barnett); 22 and single in her parents' house, so Barnett "
   "on the night. SHE AND FREDA AT SUB NUMBER 4 ARE BORN LESS THAN SIX MONTHS APART - 29 "
   "November 1916 and 15 May 1917 - so they cannot both be Minnie's, and one is a stepdaughter "
   "or a birth date on the page is wrong"),
  (4, "Freda", "Barnett", "F", "1917-05-15", 22, "Window dresser, gowns", "Single",
   "the index gives her as Hoole (Barnett). Both daughters are in the gown trade, one selling "
   "and one dressing windows"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, tmpl, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        LATER = {'Betty': 'Sokoloff', 'Freda': 'Hoole'}
        for sub, fn, ln, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)
                              AND ce.age_at_census=%s""", (sched, fn, ln, age))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = tmpl.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
            if not APPLY:
                continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
            if fn in LATER:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name,
                                                        born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, LATER[fn], int(bd[:4]), fn, LATER[fn]))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, occupation_at_census, census_household_num,
                            marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, occ, sched, marital, src))
            rec = {"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                   "born_date": bd, "id": pid,
                   "census": [{"census_year": 1939, "age_at_census": age, "address": addr,
                               "occupation_at_census": occ, "census_household_num": sched,
                               "marital_status": marital, "source": src}]}
            if prop: rec["census"][0]["property_id"] = prop
            else: rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**2 Fish Pond Drive, schedule 26 of the 1939 Register.** The book is "
                           "not known: schedule 26 is used by RMGC for Castle Rising and by RMGA "
                           "for Rock House, so this is a third use of the number.",
                   "source": "1939 Register; the ED letter code for Fish Pond Drive is not known",
                   "people": out}, open('data/people_1939_2_fish_pond_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
