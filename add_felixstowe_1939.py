# -*- coding: utf-8 -*-
"""Felixstowe, Clumber Road West, 1939 - two households, and a refugee.

The house carries **two schedules**, 223 and 224, so it was shared by September
1939.

**Schedule 223 is one woman: Anna E Hirschfield, 62, widowed, "No Occupation -
Refugee"** - and the index carries the register's own flag, *Special interest
groups: Refugee*. She is **the first person in the record so marked**. The
register was taken on 29 September 1939, three weeks after war was declared.

**Schedule 224** is Helena G Firth, 69, with a cook, a parlourmaid and a
housemaid.

**She is NOT Helena Brownsword Dowson**, though that would have been the obvious
guess: the suffragist, city councillor and magistrate kept this very house in
1911 and 1921, and was returned in 1921 as *Town Councillor, Justice of the
Peace*. But the record has her born **23 November 1866** and dead in **1964**,
and this woman is born **29 April 1870**. Different dates, different women. The
Dowsons had gone and Helena Brownsword Dowson is somewhere else in the 1939
Register.

  railway run python3 add_felixstowe_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (394, 223, "Felixstowe, Clumber Road West", [
  (1, None, "Anna E", "Hirschfield", None, "F", "1876-11-22", 62, None, "Widowed",
   "the page writes the address Felexdive Chamber Road, which is Felixstowe, Clumber Road. Her "
   "occupation is given as NO OCCUPATION - REFUGEE and the index carries the register's own flag, "
   "Special interest groups: Refugee. She is the first person in this record so marked. Her line "
   "is RG101/6178A, item 21, line 24. She has a schedule to herself in a house whose other "
   "household is schedule 224, so she was lodging there as a separate household"),
 ]),
 (394, 224, "Felixstowe, Clumber Road West", [
  (1, None, "Helena G", "Firth", None, "F", "1870-04-29", 69, "Unpaid domestic duties", "Married",
   "returned married with no husband in the house. She is NOT Helena Brownsword Dowson, who kept "
   "this house in 1911 and 1921 and was its Town Councillor and Justice of the Peace: that "
   "Helena was born 23 November 1866 and died in 1964, and this one is born 29 April 1870"),
  (2, None, "Helen", "Anderson", None, "F", "1898-03-21", 41, "Cook", "Single", None),
  (3, None, "Phyllis", "Thompson", None, "F", "1897-08-30", 42, "Parlour maid", "Single", None),
  (4, None, "Margaret", "Brammer", None, "F", "1897-11-04", 41, "Housemaid", "Single",
   "the index gives her as Margaret (May), so she went by May"),
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
        json.dump({"note": "**Felixstowe, Clumber Road West, schedules 223 and 224 of the 1939 "
                           "Register, ED letter code RMGB.** Two households in one house. Anna E "
                           "Hirschfield has a schedule to herself and is flagged REFUGEE by the "
                           "register - the first in this record. Helena G Firth is not Helena "
                           "Brownsword Dowson, who kept the house in 1911 and 1921.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_felixstowe.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
