# -*- coding: utf-8 -*-
"""13 Lenton Avenue, 1939 - schedule 169, three women and no head.

A. Hagues sent "13 Lenton avenue" and then the household, which is how he has
labelled every other house today. So 13 is taken as the address, and the empty
mark put on it an hour earlier - when the same words were read as the answer to
a different question - is removed. A house cannot be empty and full in the same
round.

**The walk holds.** The RMGB odd side runs 163 at number 1, 164 at 3, 165 at 5,
166 at 7, 167 at 9, and then 169 at 13 with 168 left for 11 - which sits in the
record at schedule 123, from another book, and wants looking at. After 13 come
15, 17, 19 and 23, all four ticked and left blank, for which 170, 172, 174 and
175 are free.

**Doneathy is the married name**, on A. Hagues' word, so Newton is the name
Doris bore on the night.

  railway run python3 add_13_lenton_avenue_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED, ADDR = 163, 169, "13 Lenton Avenue"
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")
PEOPLE = [
 (1, "Doris M", "Newton", "F", "1911-09-10", 28, "Domestic servant", "Single", "Doneathy",
  "entered as Doris (M) Doneathy (Newton). DONEATHY IS THE MARRIED NAME, on A. Hagues' word, so "
  "Newton is the name she bore on the night and Doneathy is written in later"),
 (2, "Vera A", "Jackson", "F", "1897-09-12", 42, "Domestic servant", "Single", None,
  "the forename initial is bracketed on the page as Vera (A)"),
 (3, "Williamina G", "Seedbury", "F", "1896-03-09", 43, "Unpaid domestic duties", "Married", None,
  "the only married woman of the three and the only one not in service, so most likely the head - "
  "though no head is marked, and no husband is entered with her"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print(f"--- schedule {SCHED}, {ADDR} (#{PROP})")
    cur.execute("SELECT notes FROM census_unoccupied WHERE property_id=%s AND census_year=1939", (PROP,))
    e = cur.fetchone()
    if e: print(f"  NOTE: this house is currently marked empty for 1939 - that mark will be removed")
    for sub, fn, ln, sex, bd, age, occ, marital, later, note in PEOPLE:
        cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                        WHERE ce.census_year=1939 AND ce.census_household_num=%s
                          AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                    (SCHED, fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=SCHED, addr=ADDR, sub=sub) + '; ' + note
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
                    (pid, PROP, ADDR, age, occ, SCHED, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                    "born_date": bd, "id": pid,
                    "census": [{"census_year": 1939, "age_at_census": age, "address": ADDR,
                                "property_id": PROP, "occupation_at_census": occ,
                                "census_household_num": SCHED, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        cur.execute("DELETE FROM census_unoccupied WHERE property_id=%s AND census_year=1939", (PROP,))
        print(f"  empty mark removed ({cur.rowcount} row)")
        json.dump({"note": "**13 Lenton Avenue, schedule 169 of the 1939 Register, ED letter code "
                           "RMGB.** Three women, no head marked - two domestic servants and "
                           "Williamina G Seedbury, married, at unpaid domestic duties.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_13_lenton_avenue.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
