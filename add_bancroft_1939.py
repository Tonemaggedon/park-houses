# -*- coding: utf-8 -*-
"""Bancroft, Barrack Lane, 1939 - schedule 24, two schoolmistresses.

**The record holds no house called Bancroft**, on Barrack Lane or anywhere, so
the household goes in unfiled.

And the walk does not help as it usually does. Schedule 24 sits between **8 Park
Drive** at s23 and **4 Park Drive** at s25, with 2 Park Drive at s21 and
Castle Rising, 3 Lenton Road at s26 - so this stretch of the RMGC book is
working Park Drive and Lenton Road, not Barrack Lane. A. Hagues reads the street
off the page as Barrack Lane, which is what the record follows; the walk is
noted because it disagrees.

Two single women in their fifties and sixties, both teachers - one of them
**formerly** a music teacher, which is the Register's way of saying retired.

  railway run python3 add_bancroft_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGC, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (None, 24, "Bancroft, Barrack Lane", [
  (1, "Ethel E", "Woollatt", None, "F", "1874-04-29", 65, "Music teacher, retired", "Single",
   "the page gives FORMERLY Music Teacher, which is how the Register wrote a trade given up. "
   "The record holds no Woollatt at all. Bancroft is not in the property list, so this household "
   "is unfiled - and the walk disagrees with the street: schedule 24 sits between 8 Park Drive "
   "and 4 Park Drive, with Castle Rising, 3 Lenton Road two schedules later"),
  (2, "Dorothy G H", "Gem", None, "F", "1885-10-26", 53, "Teacher", "Single",
   "the page gives Teacher (Scheme), the bracket unexplained - it may be a teaching scheme she "
   "was employed under. Eleven years younger than Ethel E and of a different name, so the two "
   "shared the house rather than being kin. The record holds no Gem either"),
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
                              AND LOWER(p.last_name)=LOWER(%s)""", (sched, '%RMGC%', fn, ln))
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
        json.dump({"note": "**Bancroft, Barrack Lane, schedule 24 of the 1939 Register, ED letter "
                           "code RMGC.** Two single schoolmistresses. UNFILED: the record holds no "
                           "house called Bancroft, and the walk puts schedule 24 among Park Drive "
                           "houses rather than on Barrack Lane.",
                   "source": "1939 Register, ED letter code RMGC, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgc_bancroft.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
