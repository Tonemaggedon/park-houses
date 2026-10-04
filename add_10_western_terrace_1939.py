# -*- coding: utf-8 -*-
"""10 Western Terrace, 1939 - the Goddards, who moved from 8 Park Terrace.

Schedule 201. **Three of the four are already in the record** and entering them
as the index writes them would have made a second copy of the whole family.

Arthur Raymond Goddard, dental surgeon, headed **8 Park Terrace** in 1921 aged
34 with his wife Ernestine and their baby daughter. Eighteen years later the
same three are at 10 Western Terrace: the index gives him as Arthur R, her as
**Ernetine** - which is Ernestine - and the daughter as **Joan T Perkins
(Goddard)**, which is the Theodore Joan Goddard who was one year old in 1921.
She is twenty, single and an insurance clerk, so Goddard is the name the
register was written in and Perkins the name she came to later.

Only William H, born 1922, is new, because he was born after the 1921 round.

  railway run python3 add_10_western_terrace_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (349, 201, "10 Western Terrace", [
  (1, 1808, "Arthur Raymond", "Goddard", None, "M", "1886-10-24", 52, "Dental surgeon", "Married",
   "the index gives him as Arthur R; he headed 8 Park Terrace in 1921 aged 34 in the same trade, "
   "and his birth year is 1887 on that round and 1886 here"),
  (2, 1809, "Ernestine", "Goddard", None, "F", "1893-12-05", 45, "Unpaid domestic duties", "Married",
   "the index writes her forename Ernetine; she was his wife at 8 Park Terrace in 1921 aged 27"),
  (3, 1810, "Theodore Joan", "Goddard", "Perkins", "F", "1919-07-05", 20, "Insurance clerk", "Single",
   "the index gives her as Joan T Perkins (Goddard); she is the Theodore Joan Goddard who was a "
   "year old at 8 Park Terrace in 1921, and being twenty and single here, Goddard is the name "
   "the register was written in"),
  (4, None, "William H", "Goddard", None, "M", "1922-05-04", 17, "Clerk, tobacco", "Single",
   "born after the 1921 round, so the record did not hold him"),
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
            if later:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, later, int(bd[:4]), fn, later))
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
            if prop:
                rec["census"][0]["property_id"] = prop
            else:
                rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**10 Western Terrace, schedule 201 of the 1939 Register, ED letter "
                           "code RMGB.** The Goddard family, who kept 8 Park Terrace in 1921 - "
                           "Arthur Raymond the dental surgeon, his wife Ernestine, and the "
                           "daughter the index calls Joan T, who is their Theodore Joan. Three of "
                           "the four are bound by number.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_10_western_terrace.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
