# -*- coding: utf-8 -*-
"""Lincoln House, Lincoln Circus, 1939 - schedule 247, ten under one roof.

**Harry Laurence Birkin and Olive Isabel are already in the record**, in this
same house, in 1921 - he a lace manufacturer of 49, she 38, with six servants
between them. The Register gives him born 17 March 1872 and her 23 July 1882,
which agrees with both ages. So these are new rows on people the record held.

**The book is RMGB** on the walk: 245 is Newcastle Court, 246 is The Cottage,
Lincoln Circus, and 248 and 249 are Newcastle Circus, so 247 falls inside a run
the record already has - and this is the Lincoln House **on Lincoln Circus**,
not the other one, which the property list warns against confusing it with.

**Jean M Dulley (Dudley).** The bracket has meant the 1939 name all day, so
Dudley is entered and Dulley kept as a variant - but unlike the other bracketed
names in this round the two differ by a single letter, so this may be a
spelling rather than a marriage. Both are held, and the People search now reads
variants, so she is findable either way.

  railway run python3 add_lincoln_house_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED, ADDR = 403, 247, "Lincoln House, Lincoln Circus"
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}. THE BOOK IS RMGB on the walk: 245 is Newcastle Court, 246 "
       "is The Cottage on Lincoln Circus, and 248 and 249 are Newcastle Circus")
PEOPLE = [
 (1, 1187, "Harry Laurence", "Birkin", "M", "1872-03-17", 67, "Company director", "Married", None,
  "the 1921 census has him in this house at 49, a lace manufacturer, with six servants"),
 (2, 1188, "Olive Isabel", "Birkin", "F", "1882-07-23", 57, "Unpaid domestic duties", "Married", None,
  "his wife in 1921, in the same house, then 38"),
 (3, None, "Annie E", "Woolrich", "F", "1876-10-17", 62, "Cook housekeeper", "Single", None, None),
 (4, None, "James M", "Birkin", "M", "1912-04-23", 27, None, "Single", None,
  "the occupation column is a dash"),
 (5, None, "David L", "Birkin", "M", "1914-11-12", 24, "Convalescent after an operation", "Single", None,
  "see the question written on whether this is David Lloyd Birkin"),
 (6, None, "Doris M", "Worthington", "F", "1901-05-31", 38, "Housemaid", "Single", None, None),
 (7, None, "Edna V", "May", "F", "1913-11-19", 25, "Maid", "Single", None, None),
 (8, None, "Joyce", "Pearson", "F", "1924-04-05", 15, "Maid", "Single", None, None),
 (9, None, "Francis I", "Raynor", "F", "1920-11-20", 18, "Maid", "Single", None, None),
 (10, None, "Jean M", "Dudley", "F", "1921-05-21", 18, "Maid", "Single", "Dulley",
  "entered as Jean M Dulley (Dudley). The bracket has meant the name borne on the night all "
  "round, so Dudley is taken as that and Dulley as the later form - but the two differ by one "
  "letter, so this may be a spelling rather than a marriage"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print(f"--- schedule {SCHED}, {ADDR} (#{PROP})")
    for sub, pid, fn, ln, sex, bd, age, occ, marital, later, note in PEOPLE:
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
        print(f"  sub {sub:>2} {fn} {ln}, {age} - {occ or '(no occupation given)'}"
              + (f"  [#{pid}, already in the record]" if pid else "")
              + (f"  [later {later}]" if later else ""))
        if not APPLY: continue
        if pid:
            cur.execute("UPDATE people SET born_date=COALESCE(born_date,%s) WHERE id=%s", (bd, pid))
        else:
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
        if later:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                             FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
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
        json.dump({"note": "**Lincoln House, Lincoln Circus, schedule 247 of the 1939 Register, ED "
                           "letter code RMGB.** Harry Laurence Birkin, company director, and Olive "
                           "Isabel, who were in this house in 1921 with six servants; two young "
                           "Birkin men, a cook-housekeeper and four maids.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_lincoln_house.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
