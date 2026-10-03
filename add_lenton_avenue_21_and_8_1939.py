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
 (167, 176, "21 Lenton Avenue", [
   (1, "Wilfred H", "Wilson", None, "M", "1893-05-02", 46,
    "Managing director, bleaching and finishing", "Married",
    "**the third man on this street in the bleaching trade.** Leonard S Penticost at number 9 is a "
    "bleacher, dyer and finisher, and the man at sub number 2 here is this firm's assistant manager"),
   (2, "Francis R S", "de la Cour", None, "M", "1894-09-23", 45,
    "Assistant manager, bleaching and finishing", "Single",
    "the index runs the name together as Dela Cour; the page image has it as DE LA COUR"),
   (3, "Dora A", "Rooth", None, "F", "1879-12-21", 59, "Cook", "Married", None),
   (4, "Madge", "Thorpe", "Hancock", "F", "1916-09-21", 23, "Parlour maid", "Single",
    "**A. Hagues has not said which way the bracket runs on this schedule.** The index writes her "
    "Hancock (Thorpe); the page image has HANCOCK written above the line in a later hand, which "
    "makes Thorpe the name on the night. Entered as Thorpe with Hancock kept as the married name, "
    "and open to correction"),
   (5, "Bernard", "Wright", None, "M", "1914-06-08", 25, "Butler", "Single",
    "a butler of 25 - the record holds one other in this round, William James Reynolds at "
    "Allendale, who is 66 and had been butler at 5 Park Valley in 1911"),
 ]),
 (369, 177, "8 Lenton Avenue", [
   (1, "Doris G", "Bates", None, "F", "1892-02-15", 47, "Dressmaker", "Single", None),
   (2, "Nora A", "Bates", None, "F", "1908-12-23", 30, "Clerk, commercial, textiles", "Single",
    "the trade is written En Clerk Commercial Tex and is cut short; the first word cannot be read"),
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
                        (fn, ln, sex, int(bd[:4]) if bd else None, bd))
            pid = cur.fetchone()[0]
            names = [x.strip() for x in (later or '').split(',') if x.strip()]
            for i, one in enumerate(names):
                label = ('1939 amendment' if len(names) < 2 else
                         f"1939 amendment ({'latest' if i == len(names)-1 else 'first'} married name)")
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,%s FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, one, int(bd[:4]) if bd else None, label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]) if bd else None,
                        "born_date": bd, "match_born_year": bool(bd),
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "marital_status": marital, "age_at_census": age,
                                    "occupation_at_census": occ, "census_household_num": sched,
                                    "source": src}], "id": pid})
    if APPLY:
        json.dump({"note": "**Hope Drive, schedules 100 and 101 of the 1939 Register, ED letter "
                           "code RMGB.** A street of gun and aero workers six days after the "
                           "register was taken.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_lenton_avenue_21_and_8.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
