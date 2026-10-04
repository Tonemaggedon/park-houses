# -*- coding: utf-8 -*-
"""Rockville and Rock House, Barrack Lane, 1939 - and a THIRD book.

**These are the record's first rows from the RMGA book, and from piece
RG101/6177J.** Every other 1939 row it holds cites RG101/**6178A**, under the
letter codes RMGB and RMGC. So The Park was enumerated across at least three
districts and at least two pieces, and a third of it has not been looked at.

Both houses are **unfiled**: the property list holds neither a Rockville nor a
Rock House on Barrack Lane. It does hold **Rock House, 37 Lenton Road**, which
is a different house on a different street, and **Rocky Mount, Derby Road**.

Three people, all in their sixties: a widow on private means, and a manager and
traveller in the pipes trade with his wife.

  railway run python3 add_barrack_lane_rmga_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGA, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6177J - read from the page "
       "by A. Hagues; sub number {sub}. This is a DIFFERENT PIECE from the RMGB and RMGC books "
       "the rest of the record's 1939 rows come from, which are RG101/6178A")

HOUSES = [
 (None, 25, "Rockville, Barrack Lane", [
  (1, "Harry", "Smith", None, "M", "1871-12-31", 67, "Manager and traveller, pipes trade", "Married",
   "born on the last day of 1871. The record holds no Rockville, so this household is unfiled"),
  (2, "Elizabeth H", "Smith", None, "F", "1870-08-06", 69, "Unpaid domestic duties", "Married",
   "sixteen months older than Harry and sharing his surname, so his wife"),
 ]),
 (None, 26, "Rock House, Barrack Lane", [
  (1, "Gertrude L", "Ford", None, "F", "1873-03-11", 66, "Private means", "Widowed",
   "alone in the house. The page writes the address in quotation marks - \'rock House\' Barrack "
   "Lane - and her line is RG101/6177J, item 3, line 25. The record holds a ROCK HOUSE, 37 "
   "LENTON ROAD, which is a different house on a different street, and a Rocky Mount on Derby "
   "Road; it holds no Rock House on Barrack Lane and no Ford at all"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                              AND LOWER(p.last_name)=LOWER(%s)""", (sched, '%RMGA%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age if age is not None else '?'} - {occ}")
            if not APPLY:
                continue
            yr = int(bd[:4]) if bd else None
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, yr, bd if bd and len(bd) > 4 else None))
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
                            (pid, fn, one, yr, label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, occupation_at_census, census_household_num,
                            marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": yr,
                        "born_date": bd if bd and len(bd) > 4 else None, "id": pid,
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "age_at_census": age, "occupation_at_census": occ,
                                    "census_household_num": sched, "marital_status": marital,
                                    "source": src}]})
    if APPLY:
        json.dump({"note": "**Rockville and Rock House, Barrack Lane, schedules 25 and 26 of the "
                           "1939 Register, ED letter code RMGA, RG101/6177J.** The record's first "
                           "rows from a third book and a second piece. Both unfiled: the property "
                           "list holds neither house.",
                   "source": "1939 Register, ED letter code RMGA, The National Archives RG101/6177J",
                   "people": out}, open('data/people_1939_rmga_barrack_lane.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
