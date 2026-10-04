# -*- coding: utf-8 -*-
"""The Cottage, Barrack Lane, 1939 - schedule 1, a charwoman and her daughter.

**Emma Mee, 63, widowed, charwoman**, and Ida, 41, a **hosiery flat locker** -
a flat-lock machine is what joins knitted seams, and it was Nottingham's own
trade. Two working women alone in a cottage.

The record holds no house called The Cottage on Barrack Lane: only **Barrack
Yard** and the three **Pelham Cottages**. So the household is unfiled.

**The book is taken as RMGA** because both of A. Hagues's other Barrack Lane
households - Rockville at schedule 25 and Rock House at 26 - are RMGA, and
because neither RMGB nor RMGC numbers a schedule 1 at all: RMGB runs from 80 and
RMGC from 5. The record does hold one other 1939 schedule 1, at Derby House,
1 Derby Terrace, but that row names no book.

  railway run python3 add_the_cottage_barrack_lane_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGA, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6177J - read from the page "
       "by A. Hagues; sub number {sub}. This is a DIFFERENT PIECE from the RMGB and RMGC books "
       "the rest of the record's 1939 rows come from, which are RG101/6178A")

HOUSES = [
 (None, 1, "The Cottage, Barrack Lane", [
  (1, "Emma", "Mee", None, "F", "1876-04-01", 63, "Charwoman", "Widowed",
   "the record holds no Mee at all, and no house called The Cottage on Barrack Lane - only "
   "Barrack Yard and the three Pelham Cottages - so this household is unfiled. The book is "
   "taken as RMGA because both other Barrack Lane households A. Hagues has sent are RMGA, and "
   "neither RMGB nor RMGC numbers a schedule 1"),
  (2, "Ida", "Mee", None, "F", "1898-05-17", 41, "Hosiery flat locker", "Single",
   "twenty-two years younger than Emma and sharing her surname, so most likely her daughter. A "
   "flat-lock machine joins knitted seams; locking was skilled hosiery work and Nottingham's "
   "own trade"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                              AND LOWER(p.last_name)=LOWER(%s)""", (sched, '%RMGA%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age if age is not None else '?'} - {occ}")
            if not APPLY:
                continue
            yr = int(bd[:4]) if bd else None
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, yr, bd if bd and len(bd) > 4 else None))
            pid = cur.fetchone()[0]
            names = [x.strip() for x in (later or '').split(',') if x.strip()]
            for i, one in enumerate(names):
                label = ('1939 amendment (married name)' if len(names) < 2 else
                         f"1939 amendment ({'latest' if i == len(names)-1 else 'first'} married name)")
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,%s FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, one, yr, label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, occupation_at_census, census_household_num,
                            marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": yr,
                        "born_date": bd if bd and len(bd) > 4 else None, "id": pid,
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "age_at_census": age, "occupation_at_census": occ,
                                    "census_household_num": sched, "marital_status": marital,
                                    "source": src}]})
    if APPLY:
        json.dump({"note": "**The Cottage, Barrack Lane, schedule 1 of the 1939 Register, ED letter "
                           "code RMGA, RG101/6177J.** Emma Mee, charwoman, and her daughter Ida, a "
                           "hosiery flat locker. Unfiled: the record holds no house of that name "
                           "on the lane.",
                   "source": "1939 Register, ED letter code RMGA, The National Archives RG101/6177J",
                   "people": out}, open('data/people_1939_rmga_the_cottage_barrack_lane.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
