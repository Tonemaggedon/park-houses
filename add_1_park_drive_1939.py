# -*- coding: utf-8 -*-
"""1 Park Drive, 1939 - schedule 264, a plain net director.

**The book is taken as RMGB** on the evidence of the walk: schedule 257 of that
book is 3 Cavendish Crescent North and 269 is 11a Fish Pond Drive, so 264 falls
between two confirmed RMGB schedules - and unlike the Fish Pond Drive households
at 26, 77 and 78, **no other book uses the number 264 at all.**

**Plain net** is the Nottingham lace trade: net made without a pattern, the
plain ground that patterned lace is worked on. The record holds two other plain
net men - Herbert Smith at 7 Park Drive in 1921 and the Herbert Smith who keeps
Clumber House in this very round.

The house had been **Edward Wynne Humphreys's**, Official Receiver in
Bankruptcy, in 1911 and 1921; he is at Fern Lodge, 9 Lenton Road by 1939.

  railway run python3 add_1_park_drive_1939.py --apply
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
 (232, 264, "1 Park Drive", RMGB, [
  (1, "Leo E", "Folman", "M", "1900-03-16", 39, "Company director, plain net", "Married",
   "the page gives C Director (Plain Net). PLAIN NET is the Nottingham trade - net made without "
   "a pattern, the ground that patterned lace is worked on. The record holds no Folman, and the "
   "book is taken as RMGB because schedule 257 of it is 3 Cavendish Crescent North and 269 is "
   "11a Fish Pond Drive, with no other book using 264 at all"),
  (2, "Pauline D E", "Folman", "F", "1916-02-23", 23, "Unpaid domestic duties", "Married",
   "sixteen years younger than Leo E and sharing his surname, so his wife"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, tmpl, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        LATER = {}
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
        json.dump({"note": "**1 Park Drive, schedule 264 of the 1939 Register, ED letter code "
                           "RMGB.** Leo E Folman, company director in plain net. The book is taken "
                           "from the walk: 257 is 3 Cavendish Crescent North and 269 is 11a Fish "
                           "Pond Drive, and no other book uses 264.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_1_park_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
