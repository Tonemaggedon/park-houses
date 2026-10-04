# -*- coding: utf-8 -*-
"""5 and 3 Pelham Crescent, 1939 - schedules 219 and 220.

**Samuel R Trotman at number 3 was the City Analyst**, retired by 1939 at 70 -
a public office, and the chemist a city trusts with its food, its water and its
poisons. Nobody of that name was in the record before. With him are his wife
Mary G, 64, his son John, 31, a supervisor at a tobacco works, and a cook.

Number 5 is John B G Northcott, electrical engineer, 53, his wife Dorothy O, and
a girl of sixteen in domestic service.

None of the seven was in the record. Number 5 had been Katherine Elizabeth
Flersheim's at 79 in 1911 and Joseph William Wright's in 1921; number 3 the
Lewises', hosiery manufacturers, across both rounds.

  railway run python3 add_rmgb_219_220_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (276, 219, "5 Pelham Crescent", [
  (1, None, "John B G", "Northcott", None, "M", "1886-08-14", 53, "Electrical engineer", "Married", None),
  (2, None, "Dorothy O", "Northcott", None, "F", "1891-08-02", 48, "Unpaid domestic duties", "Married",
   "five years younger than John B G and sharing his surname, so his wife"),
  (3, None, "Gladys M", "Essack", "Nuttall", "F", "1922-12-29", 16, "Domestic service", "Single",
   "the index gives her as Essack (Nuttall); she is sixteen and single, so Essack is the name "
   "the register was written in and Nuttall the name she came to later. She is the youngest "
   "person in service in this stretch of the walk. No relation the record can see to the Gladys "
   "S Nuttall of 12 Pelham Crescent, who is eighteen years older"),
 ]),
 (275, 220, "3 Pelham Crescent", [
  (1, None, "Samuel R", "Trotman", None, "M", "1869-03-21", 70, "City analyst, retired", "Married",
   "the CITY ANALYST is a public office - the chemist a corporation appoints to test its food, "
   "its water and its poisons under the Sale of Food and Drugs Acts. He is retired by 1939 and "
   "the record held no Trotman at all, so when he held the post and for how long is open"),
  (2, None, "Mary G", "Trotman", None, "F", "1875-05-01", 64, "Unpaid domestic duties", "Married", None),
  (3, None, "John", "Trotman", None, "M", "1908-03-15", 31, "Supervisor, tobacco works", "Married",
   "thirty-nine years younger than Samuel R and sharing his surname, so his son; he is returned "
   "married but no wife is in the house"),
  (4, None, "Elizabeth", "Martin", None, "F", "1895-09-06", 44, "Cook", "Single",
   "the record holds several Martins on the estate but none born in 1895"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        for sub, exist, fn, ln, later, sex, bd, age, occ, marital, note in people:
            # by NAME within this book's schedule - a person_id guard misses anyone new,
            # and the other 1939 book numbers its schedules over the same range
            # a bound person is checked by NUMBER, because the index's forename need not
            # match the record's - "Mary E Littlewood" against the record's "Mary" slipped
            # past a name guard and put her row in twice
            if exist:
                cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                                AND census_household_num=%s AND person_id=%s
                                AND source ILIKE %s""", (sched, exist, '%RMGB%'))
            else:
                cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                                WHERE ce.census_year=1939 AND ce.census_household_num=%s
                                  AND ce.source ILIKE %s
                                  AND LOWER(p.first_name)=LOWER(%s)
                                  AND LOWER(p.last_name)=LOWER(%s)""",
                            (sched, '%RMGB%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}  [{f'bound to #{exist}' if exist else 'new'}]")
            if not APPLY:
                continue
            if exist:
                pid = exist
                cur.execute("""UPDATE people SET born_date=COALESCE(born_date,%s),
                                 born_year=COALESCE(born_year,%s) WHERE id=%s""",
                            (bd, int(bd[:4]), pid))
            else:
                cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                            (fn, ln, sex, int(bd[:4]), bd))
                pid = cur.fetchone()[0]
            # a woman may have more than one later name, written here latest last
            for i, one in enumerate([x.strip() for x in (later or '').split(',') if x.strip()]):
                nlater = len([x for x in (later or '').split(',') if x.strip()])
                label = ('1939 amendment (married name)' if nlater < 2 else
                         f"1939 amendment ({'latest' if i == nlater-1 else 'first'} married name)")
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,%s
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, one, int(bd[:4]), label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, occupation_at_census, census_household_num,
                            marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, occ, sched, marital, src))
            rec = {"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                   "born_date": bd if len(bd) > 4 else None, "id": pid,
                   "census": [{"census_year": 1939, "age_at_census": age, "address": addr,
                               "occupation_at_census": occ, "census_household_num": sched,
                               "marital_status": marital, "source": src}]}
            if prop:
                rec["census"][0]["property_id"] = prop
            else:
                rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**5 and 3 Pelham Crescent, schedules 219 and 220 of the 1939 Register, "
                           "ED letter code RMGB.** Samuel R Trotman at number 3 was the City "
                           "Analyst, a public office, and the record held no Trotman before. None "
                           "of the seven was in it.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_219_220.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
