# -*- coding: utf-8 -*-
"""10 and 12 Barrack Lane, 1939 - schedules 17 and 16 of the RMGA book.

**Barrack Lane is turning out to be a street of managers and clerks**, where
the record had always had it as a mews. George F Houfton at number 10 is a
production manager and director of a mechanical engineering works; George Lynch
at number 12 is a bank cashier. Each keeps domestic servants.

**Number 10 settles its own bracket.** Gladys A is given as *Cunnington (Gibson)
(Loomes)* and is single at 39; **Ada E Cunnington at the next sub number has no
bracket at all**. Two Cunningtons in service in one house are sisters, so
Cunnington is the birth name and the surname in front is what they were born
with - Gibson and Loomes are marriages she made afterwards.

That is the opposite direction from Sylvia Woyciehouski at number 4, four
schedules away, where the bracket holds the birth name. **The register has no
rule, and each household has to be read on its own.**

  railway run python3 add_barrack_lane_16_17_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGA, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6177J - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (7, 17, "10 Barrack Lane", [
  (1, "George F", "Houfton", None, "M", "1903-12-01", 35,
   "Production manager and director, mechanical engineering works", "Married",
   "the page gives Production Manager & Dire Mechanical Engineering W, cut off at both ends. "
   "The record holds one other Houfton, a housemaid of 1891, and nothing to connect them. The "
   "house itself had been the Derrys' - a groom in 1881 and a jobbing gardener in 1901"),
  (2, "Muriel B", "Houfton", None, "F", "1904-07-05", 35, "Unpaid domestic duties", "Married",
   "seven months younger than George F and sharing his surname, so his wife"),
  (3, "Gladys A", "Cunnington", "Gibson, Loomes", "F", "1900-07-19", 39, "Domestic servant", "Single",
   "the index gives her as Cunnington (Gibson) (Loomes). She is single at 39 and ADA E "
   "CUNNINGTON at the next sub number carries no bracket at all, so Cunnington is the name the "
   "two were born with and the two brackets are marriages Gladys made afterwards"),
  (4, "Ada E", "Cunnington", None, "F", "1903-06-06", 36, "Domestic servant", "Single",
   "three years younger than Gladys A and sharing her surname, so most likely her sister - and "
   "it is her plain entry that fixes the direction of Gladys's brackets"),
 ]),
 (8, 16, "12 Barrack Lane", [
  (1, "George", "Lynch", None, "M", "1887-07-02", 52, "Bank cashier", "Married",
   "the page gives Bank Cashier Mille Ban, the bank's name unread - Midland is the likeliest "
   "thing it stands for, and the page should settle it"),
  (2, "Ethel M", "Lynch", None, "F", "1885-09-13", 54, "Unpaid domestic duties", "Married",
   "twenty-two months older than George and sharing his surname, so his wife"),
  (3, "Alice", "Wakefield", "Boyes", "F", "1916-10-26", 22, "Domestic service", "Single",
   "the index gives her as Wakefield (Boyes). Nothing in this household settles which way the "
   "bracket runs, so she is entered under the surname in front, as the Cunnington sisters at "
   "number 10 are - but Boyes may be the birth name instead, and both are held"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr} (#{prop})")
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                              AND LOWER(p.last_name)=LOWER(%s)""", (sched, '%RMGA%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
            if not APPLY:
                continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, int(bd[:4]), bd))
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
                            (pid, fn, one, int(bd[:4]), label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                        "born_date": bd, "id": pid,
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "age_at_census": age, "occupation_at_census": occ,
                                    "census_household_num": sched, "marital_status": marital,
                                    "source": src}]})
    if APPLY:
        json.dump({"note": "**10 and 12 Barrack Lane, schedules 17 and 16 of the 1939 Register, "
                           "ED letter code RMGA, RG101/6177J.** A production manager and a bank "
                           "cashier, each with servants - Barrack Lane in 1939 is not the mews the "
                           "record has had it as.",
                   "source": "1939 Register, ED letter code RMGA, The National Archives RG101/6177J",
                   "people": out}, open('data/people_1939_rmga_barrack_lane_16_17.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
