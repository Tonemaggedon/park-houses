# -*- coding: utf-8 -*-
"""8 Barrack Lane, 1939 - schedule 18, a retired pawnbroker who moved next door.

**John H Clarke and his wife Charlotte B kept 8a Barrack Lane in 1921**, where
he was returned *Director of Limited Co*. In 1939 they are at **8**, next door,
and the register says plainly what the company was: he is a **pawnbroker,
retired**, at 72.

Both are bound by number. The 1921 round holds 8 and 8a as separate houses, with
William Thomas Harris, surveyor, in number 8 - so the move is real rather than
two readings of one address, though the page would settle it.

  railway run python3 add_8_barrack_lane_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGA, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6177J - read from the page "
       "by A. Hagues; sub number {sub}")

PEOPLE = [
 (1, 1169, "John H", "Clarke", None, "M", "1867-01-23", 72, "Pawnbroker, retired", "Married",
  "he and his wife kept 8A Barrack Lane in 1921, where he was returned Director of Limited Co "
  "and the record could not say of what. This entry says: pawnbroking. His birth year is 1867 on "
  "both rounds. The 1921 round holds 8 and 8a as separate houses, number 8 being William Thomas "
  "Harris the surveyor's, so the Clarkes moved next door between the two"),
 (2, 1170, "Charlotte B", "Clarke", None, "F", "1871-08-08", 68, "Unpaid domestic duties", "Married",
  "his wife at 8a Barrack Lane in 1921, born 1872 on that round and August 1871 here"),
 (3, None, "Margaret", "Griffiths", None, "F", "1910-06-30", 29, "Domestic servant", "Single",
  "no relation the record can see to the Marelina Griffiths who was housemaid at 9 Pelham "
  "Crescent in this same round, nine years her junior"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print("--- schedule 18, 8 Barrack Lane (#6)")
    for sub, exist, fn, ln, later, sex, bd, age, occ, marital, note in PEOPLE:
        if exist:
            cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                            AND census_household_num=18 AND person_id=%s
                            AND source ILIKE %s""", (exist, '%RMGA%'))
        else:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=18
                              AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                              AND LOWER(p.last_name)=LOWER(%s)""", ('%RMGA%', fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=18, addr="8 Barrack Lane", sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}  [{f'bound to #{exist}' if exist else 'new'}]")
        if not APPLY:
            continue
        if exist:
            pid = exist
            cur.execute("""UPDATE people SET born_date=COALESCE(born_date,%s),
                             born_year=COALESCE(born_year,%s) WHERE id=%s""", (bd, int(bd[:4]), pid))
        else:
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
        if later:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,%s,'1939 Register, the other form of her surname'
                             FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a
                             WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                               AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                        (pid, fn, later, int(bd[:4]), fn, later))
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,6,1939,'8 Barrack Lane',%s,%s,18,%s,%s)""",
                    (pid, age, occ, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                    "born_date": bd, "id": pid,
                    "census": [{"census_year": 1939, "property_id": 6, "address": "8 Barrack Lane",
                                "age_at_census": age, "occupation_at_census": occ,
                                "census_household_num": 18, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        json.dump({"note": "**8 Barrack Lane, schedule 18 of the 1939 Register, ED letter code "
                           "RMGA, RG101/6177J.** John H Clarke, retired pawnbroker, and his wife "
                           "Charlotte B, who kept 8a next door in 1921. Both bound by number.",
                   "source": "1939 Register, ED letter code RMGA, The National Archives RG101/6177J",
                   "people": out}, open('data/people_1939_rmga_8_barrack_lane.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
