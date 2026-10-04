# -*- coding: utf-8 -*-
"""1a Peveril Drive, 1939 - schedule 61, thirteen people and nine trades.

**The record holds no 1a Peveril Drive**, so this household is unfiled. The
street has 1, 2, 2a, 3 to 8, 10, 11, 12, Eskdale, Parkdale and Peveril House,
and no 1a among them.

**It is a lodging house for working people, and nothing like the rest of the
estate.** Thomas F Cooper is a **coal miner, a timberer** - the man who sets the
props that hold a roadway up - and his lodgers are a plumber, a milling machine
operator, an engineer's mate, an **asbestos sheeter** and an iron shaper. His own
children pack soap, examine needlework and clean buses. Two further lines are
records the register keeps closed, so the house held at least thirteen.

**The book is RMGC.** Schedule 61 falls just before 1 Hope Drive at 63, and
63 to 75 of that book are Hope Drive, which Peveril Drive runs into.

**The brackets are settled by the two youngest.** Hilda Fowler (Cooper) is 19
and Daisy Cullen (Cooper) is 15, both single in their parents' house, so Cooper
is what they bore on the night.

  railway run python3 add_1a_peveril_drive_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule 61, 1a Peveril Drive, ED letter code RMGC, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

PEOPLE = [
 (1, "Thomas F", "Cooper", None, "M", "1889-12-16", 49, "Coal miner, timberer", "Married",
  "a TIMBERER set the props that held a roadway up underground - skilled and dangerous work, and "
  "the only coal miner in this record's 1939 round. The record holds no 1a Peveril Drive, so this "
  "household is unfiled"),
 (2, "Mary E", "Cooper", None, "F", "1885-09-27", 54, "Unpaid domestic duties", "Married",
  "four years older than Thomas F and sharing his surname, so his wife; her birthday fell two "
  "days before the register was taken"),
 (3, "Thomas F", "Cooper", None, "M", "1916-01-31", 23, "Bus cleaner", "Single",
  "the index prints him as Thomas F (MINNIE) Cooper while giving his sex as Male, which does not "
  "sit together - and a Minnie Goldrich stands at the next sub number, so the bracket may have "
  "slipped from her row. He carries his father's name"),
 (4, "Minnie", "Goldrich", None, "F", "1912-04-23", 27, "Domestic", "Married", None),
 (5, "Hilda", "Cooper", "Fowler", "F", "1920-03-29", 19, "Soap packer", "Single",
  "the index gives her as Fowler (Cooper); 19 and single in her parents' house, so Cooper on the "
  "night - which with her sister at the next sub number settles the bracket for this page"),
 (6, "Daisy", "Cooper", "Cullen", "F", "1924-06-24", 15, "Needlework examiner", "Single",
  "FIFTEEN and already examining needlework"),
 (7, "Alex", "Russell", None, "M", "1906-04-21", 33, "Plumber", "Single", None),
 (8, "Arthur", "Broadbent", None, "M", "1913-04-21", 26, "Milling machine operator", "Single",
  "he shares a birthday, the twenty-first of April, with the plumber at sub number 7, seven "
  "years apart"),
 (9, "Ernest", "Davis", None, "M", "1882-07-14", 57, "Engineer's mate, heating and domestic", "Married",
  "sub numbers 10 and 11 are lines the register keeps closed, so the house held at least thirteen"),
 (12, "Arthur", "Watson", None, "M", "1910-04-27", 29, "Sheeter, asbestos", "Married",
  "an ASBESTOS SHEETER cut and fixed asbestos sheeting; the record holds nobody else at that work"),
 (13, "Harry", "Steele", None, "M", "1877-07-08", 62, "Iron shaper", "Married",
  "the oldest of the lodgers, still at a shaping machine at 62"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print("--- schedule 61, 1a Peveril Drive [UNFILED]")
    for sub, fn, ln, later, sex, bd, age, occ, marital, note in PEOPLE:
        cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                        WHERE ce.census_year=1939 AND ce.census_household_num=61
                          AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                          AND LOWER(p.last_name)=LOWER(%s)
                          AND ce.age_at_census=%s""", ('%RMGC%', fn, ln, age))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
        if not APPLY:
            continue
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
                       (person_id, census_year, unresolved_address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,1939,'1a Peveril Drive',%s,%s,61,%s,%s)""",
                    (pid, age, occ, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                    "born_date": bd, "id": pid,
                    "census": [{"census_year": 1939, "unresolved_address": "1a Peveril Drive",
                                "age_at_census": age, "occupation_at_census": occ,
                                "census_household_num": 61, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        json.dump({"note": "**1a Peveril Drive, schedule 61 of the 1939 Register, ED letter code "
                           "RMGC.** A lodging house of thirteen headed by a coal miner, with nine "
                           "trades between them. UNFILED: the record holds no 1a on that street.",
                   "source": "1939 Register, ED letter code RMGC, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgc_1a_peveril_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
