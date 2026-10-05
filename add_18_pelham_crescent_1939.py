# -*- coding: utf-8 -*-
"""18 Pelham Crescent, 1939 - schedule 13, the last gap on the street.

**Alfred M Pike is already in the record.** The 1921 census has Alfred Pike, 54,
hosiery underwear manufacturer, at **20 Barrack Lane** with his wife Fanny, his
son Ernest Henry and his daughters Gladys Winifred and Evelyn Nora. The Register
gives him born 13 August 1866, which makes him 54 in June 1921 - the same man.
By 1939 he is **widowed** and keeps house with a housekeeper and one lodger, so
Fanny died between the rounds and the children had gone.

**The book is not known.** Schedule 13 is free in every book the record holds,
and nothing places it:

  * RMGC has 12 and 14 on North Road, so 13 of that book would be a North Road
    house, not Pelham Crescent;
  * RMGA runs down Barrack Lane - 16 at number 12, 17 at 10, 18 at 8, 20 at 4 -
    so 13 of that book would be further up the same lane;
  * the rest of Pelham Crescent is RMGB, at schedules 208 to 221, which is a
    long way from 13.

So the citation says plainly that the ED letter code is not known, rather than
guessing one. See the question written on this.

  railway run python3 add_18_pelham_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED, ADDR = 287, 13, "18 Pelham Crescent"
SRC = ("1939 Register, schedule {sched}, {addr} - read from the page by A. Hagues; sub number "
       "{sub}. THE ED LETTER CODE IS NOT KNOWN for this household. Schedule 13 is unused in every "
       "book the record holds, and none of them reaches Pelham Crescent at that number: RMGC has "
       "12 and 14 on North Road, RMGA is walking down Barrack Lane, and the rest of Pelham "
       "Crescent is RMGB at schedules 208 to 221")
PEOPLE = [
 (1, 8354, "Alfred M", "Pike", "M", "1866-08-13", 73, "Hosiery manufacturer", "Widowed",
  "the 1921 census has Alfred Pike, 54, hosiery underwear manufacturer, at 20 Barrack Lane with "
  "his wife Fanny and three grown children. The birth year agrees, and he is widowed by 1939, so "
  "Fanny died between the rounds. Entered in the record as Alfred; the Register gives Alfred M"),
 (2, None, "Edith", "Munton", "F", "1901-09-29", 38, "Housekeeper", "Single", None),
 (3, None, "Charles E", "Huthwaite", "M", "1901-05-07", 38, "Bank clerk", "Married",
  "married, but no wife is entered with him, so a lodger"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print(f"--- schedule {SCHED}, {ADDR} (#{PROP})")
    for sub, pid, fn, ln, sex, bd, age, occ, marital, note in PEOPLE:
        if pid:
            cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                            AND census_household_num=%s AND person_id=%s""", (SCHED, pid))
        else:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                        (SCHED, fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=SCHED, addr=ADDR, sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}" + (f"  [#{pid}, already in the record]" if pid else ""))
        if not APPLY: continue
        if pid:
            cur.execute("""UPDATE people SET born_date=COALESCE(born_date,%s),
                                             born_year=COALESCE(born_year,%s) WHERE id=%s""",
                        (bd, int(bd[:4]), pid))
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,%s,'A. Hagues' FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                              AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                        (pid, fn, ln, int(bd[:4]), fn, ln))
        else:
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
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
        json.dump({"note": "**18 Pelham Crescent, schedule 13 of the 1939 Register.** Alfred M "
                           "Pike, hosiery manufacturer, widowed, who was at 20 Barrack Lane in "
                           "1921 with his wife Fanny. The ED letter code is not known - schedule "
                           "13 is unused in every book and none of them reaches Pelham Crescent.",
                   "source": "1939 Register, book not identified",
                   "people": out}, open('data/people_1939_18_pelham_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
