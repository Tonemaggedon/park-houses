# -*- coding: utf-8 -*-
"""2 Lenton Avenue, 1939 - schedule 171, the Ashleys where the record left them.

All three are already in the record from 1921, in this house, and nothing about
them has changed but eighteen years. Thomas Stephenson Ashley is a chauffeur in
both rounds; Hilda Mary is a shoe shop assistant in both. So these are new rows
on people the record already holds, not new people.

The index prints the daughter as **Hild M Cobb (Ashley)**. The 1921 census gives
her in full as **Hilda Mary**, so Hild is a clipped reading; Ashley is the name
she bore on the night and Cobb is written in later.

**The book is RMGB.** Schedule 171 of RMGC is 26 The Ropewalk, so this is the
other book, and the RMGB walk has 173 at 4 Lenton Avenue, 177 at 8 and 178 at
10 - 171 at number 2 sits in front of them.

  railway run python3 add_2_lenton_avenue_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED, ADDR = 366, 171, "2 Lenton Avenue"
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}. THE BOOK IS RMGB because schedule 171 of RMGC is 26 The "
       "Ropewalk, and the RMGB walk has 173 at 4 Lenton Avenue, 177 at 8 and 178 at 10")
PEOPLE = [
 (1, 1543, "Thomas Stephenson", "Ashley", "1878-04-01", 61, "Chauffeur", "Married", None,
  "the same chauffeur the 1921 census has in this house, aged 43"),
 (2, 1544, "Edith Priscilla", "Ashley", "1877-12-07", 61, "Unpaid domestic duties", "Married", None,
  "his wife in 1921, in the same house"),
 (3, 1545, "Hilda Mary", "Ashley", "1902-03-03", 37, "Shop assistant, shoes", "Single", "Cobb",
  "the index clips her to Hild M; the 1921 census gives Hilda Mary, a shoe shop assistant in this "
  "house at 19. Entered as Cobb (Ashley), so Ashley on the night and Cobb written in later"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print(f"--- schedule {SCHED}, {ADDR} (#{PROP})")
    for sub, pid, fn, ln, bd, age, occ, marital, later, note in PEOPLE:
        cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                        AND census_household_num=%s AND person_id=%s""", (SCHED, pid))
        if cur.fetchone():
            print(f"  sub {sub} #{pid} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=SCHED, addr=ADDR, sub=sub) + '; ' + note
        print(f"  sub {sub} #{pid} {fn} {ln}, {age} - {occ}" + (f"  [later {later}]" if later else ""))
        if not APPLY: continue
        cur.execute("UPDATE people SET born_date=COALESCE(born_date,%s) WHERE id=%s", (bd, pid))
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
        out.append({"first_name": fn, "last_name": ln, "born_year": int(bd[:4]), "born_date": bd,
                    "id": pid,
                    "census": [{"census_year": 1939, "age_at_census": age, "address": ADDR,
                                "property_id": PROP, "occupation_at_census": occ,
                                "census_household_num": SCHED, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        json.dump({"note": "**2 Lenton Avenue, schedule 171 of the 1939 Register, ED letter code "
                           "RMGB.** The Ashleys, still in the house the 1921 census found them in - "
                           "Thomas a chauffeur in both rounds, Hilda Mary in shoes in both. New "
                           "rows on people the record already holds.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_2_lenton_avenue.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
