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
 (288, 208, "19 Pelham Crescent", [
   (1, "William", "Hanley", None, "M", "1888-04-11", 51, "Engineer salesman", "Married", None),
   (2, "Lucy Dena", "Hanley", None, "F", "1895-12-31", 43, "Guest house proprietor", "Married",
    "the trade is written Prop Guest House and an index reads the first word as Reef"),
   (3, "William B", "Hanley", None, "M", "1921-05-01", 18, "Student, electrical engineering", "Single",
    "the page gives May 1921 without a day"),
   (4, "Dennis Anthony", "Hanley", None, "M", "1925-12-11", 13, "At school", "Single", None),
   (5, "Charles K", "Leask", None, "M", "1913-03-21", 26, "Bank clerk, commercial", "Single", None),
   (6, "Dorothy", "Aldridge", None, "F", "1890-06-20", 49, "Clerical, Ministry of Labour", "Single", None),
   (7, "Annie", "Clarskon", None, "F", "1880-10-26", 58, "Civil servant, clerical", "Single",
    "the surname is written Clarskon and is likely Clarkson"),
   (8, "Violet M", "Woolmer", None, "F", "1891-09-08", 48, "Civil servant, clerical", "Single", None),
   (9, "Mary E", "Mackenzie", None, "F", "1882-08-10", 57, "Unpaid domestic duties", "Single", None),
   (10, "Annie D", "Mackenzie", None, "F", "1889-11-07", 49,
    "Civil servant, higher executive", "Single",
    "she and the woman at sub number 9 share a surname and are seven years apart, so they are "
    "most likely sisters lodging together"),
   (11, "Elizabeth B", "McDonald", None, "F", "1894-05-23", 45,
    "Civil service audit, travelling", "Single", None),
   (12, "Eric Hallem", "Hogg", None, "M", "1897-11-18", 41, "Chartered accountant", "Single",
    "the middle name is written Hallem here and Hallam on the page image"),
   (13, "Harry D", "Haddon", None, "M", "1889-10-08", 49, "Traveller, bakeries", "Widowed", None),
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
                   "people": out}, open('data/people_1939_rmgb_19_pelham_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
