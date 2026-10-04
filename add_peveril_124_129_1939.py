# -*- coding: utf-8 -*-
"""Peveril Drive, 1939 - schedules 124 and 129, the last two of the run.

With these the RMGB walk down Peveril Drive is unbroken from 114 to 130:

    119  ABSENT - the Register records the household away on the night
    124  officially closed but for one line, Lilian A Butler
    129  Ada Vaugham, 83, widow, with a housekeeper

**Ada Vaugham is the head A. Hagues's index of the street named and the record
did not hold.** She is 83 and widowed, with Florence A Taylor, 47, keeping house
for her - and she sits between **Eskdale** at schedule 128 and **Parkdale** at
130, so her house is one of those two's neighbours.

Both go in **unfiled**: the index gives no house for either.

  railway run python3 add_peveril_124_129_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, Peveril Drive, ED letter code RMGB, Nottingham "
       "registration district 430-3, sub-district 26, The National Archives RG101/6178A - read "
       "from the page by A. Hagues; sub number {sub}")

PEOPLE = [
 (124, 1, "Lilian A", "Butler", "F", None, None, None, None,
  "SCHEDULE 124 IS OFFICIALLY CLOSED BUT FOR THIS ONE LINE - the rest of the household are "
  "records the register will not open, so the record cannot say how many were in the house or "
  "who headed it. The index gives her no birth date and no trade either. She is not in "
  "A. Hagues's index of Peveril Drive heads, which is consistent with her not being the head. "
  "The schedule falls between Ferndene at 123 and 125, so the house is on this drive"),
 (129, 1, "Ada", "Vaugham", "F", "1856-04-03", 83, "Unpaid domestic duties", "Widowed",
  "the one head in A. Hagues's index of Peveril Drive that the record did not hold. At 83 she "
  "is among the oldest people in this round. Her schedule sits between Eskdale at 128 and "
  "Parkdale at 130, so her house is one of their neighbours"),
 (129, 2, "Florence A", "Taylor", "F", "1892-08-31", 47, "Housekeeper", "Single",
  "thirty-six years younger than Ada Vaugham and of a different name, so she is keeping house "
  "for her rather than kin"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for sched, sub, fn, ln, sex, bd, age, occ, marital, note in PEOPLE:
        cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                        WHERE ce.census_year=1939 AND ce.census_household_num=%s
                          AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                          AND LOWER(p.last_name)=LOWER(%s)""", (sched, '%RMGB%', fn, ln))
        if cur.fetchone():
            print(f"  s{sched} sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=sched, sub=sub) + '; ' + note
        print(f"  s{sched} sub {sub} {fn} {ln}, {age if age is not None else '?'} - {occ or 'no trade given'}")
        if not APPLY:
            continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                    (fn, ln, sex, int(bd[:4]) if bd else None, bd))
        pid = cur.fetchone()[0]
        cur.execute("""INSERT INTO census_entries
                       (person_id, census_year, unresolved_address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,1939,'Peveril Drive (no number given)',%s,%s,%s,%s,%s)""",
                    (pid, age, occ, sched, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex,
                    "born_year": int(bd[:4]) if bd else None, "born_date": bd, "id": pid,
                    "census": [{"census_year": 1939,
                                "unresolved_address": "Peveril Drive (no number given)",
                                "age_at_census": age, "occupation_at_census": occ,
                                "census_household_num": sched, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        json.dump({"note": "**Peveril Drive, schedules 124 and 129 of the 1939 Register, ED letter "
                           "code RMGB.** The last two households of the run. 124 is officially "
                           "closed but for Lilian A Butler; 129 is Ada Vaugham, 83, the one head "
                           "in A. Hagues's index of the street the record did not hold. Schedule "
                           "119 is marked ABSENT and has no household at all.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_peveril_124_129.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
