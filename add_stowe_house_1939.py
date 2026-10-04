# -*- coding: utf-8 -*-
"""Stowe House, 1939 - schedule 225, and an eighteen-year-old V.A.D.

**The record holds no house called Stowe House**, so this household goes in
unfiled. The walk puts it next to Felixstowe and Holly Lodge, both on **Clumber
Road West**, so that is where to look.

**Joan M Ball, 18, is a V.A.D. at a general hospital** - a Voluntary Aid
Detachment nurse, and the first in this record. The register was taken on 29
September 1939, three weeks after war was declared; she had turned eighteen five
weeks before it.

A sixth line in this household is one the register will not open: *the record
for this person is officially closed*, which it says of anyone who may still
have been living. So the house held at least six and the record can name five.

**The bracket here is the name the woman came to later.** Doris M Sinclair
(Ball) is married to Arthur C **Ball** at sub number 1, so Ball is what she bore
on the night; Joan M Mitchell (Ball) is their daughter. Both are entered under
Ball.

  railway run python3 add_stowe_house_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (None, 225, "Stowe House", [
  (1, None, "Arthur C", "Ball", None, "M", "1898-01-10", 41, "Managing director", "Married",
   "the record holds no house called Stowe House; the walk puts it beside Felixstowe and Holly "
   "Lodge, both on Clumber Road West. What he was managing director of is not given"),
  (2, None, "Doris M", "Ball", "Sinclair", "F", "1897-10-14", 41, "Unpaid domestic duties", "Married",
   "the index gives her as Sinclair (Ball); she is married to Arthur C Ball at sub number 1, so "
   "Ball is the name she bore on the night and Sinclair the name she came to later"),
  (3, None, "Joan M", "Ball", "Mitchell", "F", "1921-08-22", 18, "V.A.D., general hospital", "Single",
   "the index gives her as Mitchell (Ball); she is Arthur C and Doris M's daughter, so Ball on "
   "the night. A VOLUNTARY AID DETACHMENT nurse at a general hospital, and the first in this "
   "record - she had turned eighteen five weeks before the register was taken, three weeks "
   "after war was declared"),
  (5, None, "Dora E", "Smith", "Townhill", "F", "1898-08-07", 41, "Nurse, domestic servant", "Single",
   "the index gives her as Townhill (Smith); single, so Smith is the name the register was "
   "written in. Sub number 4 is a line the register keeps closed, so the household had at "
   "least six people in it"),
  (6, None, "?", "Wright", None, "F", "1908-07-14", 31, "Cook, domestic servant", "Single",
   "the index cannot read her forename and prints it as a row of question marks, so she is "
   "entered with a question mark, which is what puts her on Names to Check"),
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
        json.dump({"note": "**Stowe House, schedule 225 of the 1939 Register, ED letter code "
                           "RMGB.** Unfiled: the record holds no house of that name, and the walk "
                           "puts it beside Felixstowe and Holly Lodge on Clumber Road West. Joan "
                           "M Ball, 18, is a V.A.D. at a general hospital, the first in the "
                           "record. A sixth line is a closed record.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_stowe_house.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
