# -*- coding: utf-8 -*-
"""Peveril Drive, 1939 - the schedules the page leaves unnumbered.

A. Hagues reads a run on Peveril Drive where the enumerator stops writing house
numbers. They are held unfiled, with the walk written onto each row, until a
numbered house further along the run anchors them.

**The walk so far:** schedule 114 is 1 Peveril Drive, 115 is 2, 116 is 3 and 117
is 6 - so the enumerator is ascending and has passed over 4 and 5, or they are
empty. **Schedule 118 is therefore most likely 7**, which is the next door up
and which the record holds with 1901, 1911 and 1921 and no 1939.

  railway run python3 add_peveril_unnumbered_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, Kenilworth Road, ED letter code RMGB, Nottingham "
       "registration district 430-3, sub-district 26, The National Archives RG101/6178A - read "
       "from the page by A. Hagues; sub number {sub}; **the page gives no house here**. The run "
       "is on Kenilworth Road - schedule 131 is Iveston at number 1, 132 is Kenilworth House at "
       "3, 133 is The Chestnuts at 5 - so this is the next house along. The record's Kenilworth "
       "Road stops at 5, with Yew Tree House at 2 on the other side. Left unfiled{note}")

HOUSES = [
 (134, [
   (1, "Everard L", "Guilford", None, "M", "1882-11-17", 56, None, "Married",
    "the trade cannot be read. **He is almost certainly a Guilford of this estate**: the record "
    "holds Francis Leavers Guilford, engineer and ironfounder, at 15 Park Terrace in 1871 and at "
    "8 The Ropewalk in 1881 with sons of 10 and 8 - and a son born 1882 fits that family exactly. "
    "Leavers is the name he carries as a middle initial"),
   (2, "Margaret M", "Guilford", None, "F", "1886-07-21", 53, "Unpaid domestic duties", "Married", None),
   (3, "Phillip A", "Guilford", None, "M", "1919-01-21", 20,
    "Undergraduate, Emmanuel College, Cambridge", "Single",
    "the college is written Emnuell on the page"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for sched, people in HOUSES:
        print(f"--- schedule {sched}, Peveril Drive (no number on the page)")
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                            WHERE c.census_year=1939 AND c.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                        (sched, fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, sub=sub, note=('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
            if not APPLY:
                continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, int(bd[:4]) if bd else None, bd))
            pid = cur.fetchone()[0]
            if later:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment' FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, later, int(bd[:4]) if bd else None, fn, later))
            cur.execute("""INSERT INTO census_entries
                           (person_id, census_year, unresolved_address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,1939,'Kenilworth Road (no house given)',%s,%s,%s,%s,%s)""",
                        (pid, age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex,
                        "born_year": int(bd[:4]) if bd else None, "born_date": bd,
                        "match_born_year": bool(bd),
                        "census": [{"census_year": 1939,
                                    "unresolved_address": "Peveril Drive (no number given)",
                                    "marital_status": marital, "age_at_census": age,
                                    "occupation_at_census": occ, "census_household_num": sched,
                                    "source": src}], "id": pid})
    if APPLY:
        json.dump({"note": "**Kenilworth Road, schedule 134 of the 1939 Register - the page gives no house.**",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out},
                  open('data/people_1939_rmgb_kenilworth_road_unnumbered.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
