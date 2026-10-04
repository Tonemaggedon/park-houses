# -*- coding: utf-8 -*-
"""Barrack Lane, 1939 - schedules 204 and 205.

**1 Barrack lane** holds a gardener and his wife, and a third line the register
keeps shut: *the record for this person is officially closed*, which is what the
1939 Register says of anyone who may still have been living when it was opened.
So the house held three people and the record can name two.

**Pelham Cottage, Barrack Lane** holds a widowed certified teacher and her two
daughters, aged 18 and 17, one a GPO telegraphist and the other a clerk. The
record has no property of that name, so the household goes in unfiled - though
an Onion was living at 1 Barrack lane in 1921, so the family was already on this
lane.

Florence M Onion's birth day is unread on the page: June 1899 is all it gives.

  railway run python3 add_barrack_lane_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (2, 204, "1 Barrack lane", [
  (1, None, "Frederick George", "Wisher", None, "M", "1904-03-09", 35, "Gardener", "Married",
   "a third person in this household is one the register will not name - the index returns only "
   "that the record for them is officially closed, which it does for anyone who may still have "
   "been living. So the house held at least three"),
  (2, None, "Sarah O", "Wisher", None, "F", "1905-06-03", 34, "Domestic", "Married",
   "fifteen months younger than Frederick George and sharing his surname, so his wife"),
 ]),
 (None, 205, "Pelham Cottage, Barrack Lane", [
  (1, None, "Florence M", "Onion", None, "F", "1899", 40,
   "Unpaid domestic duties; certified teacher", "Widowed",
   "the page gives only June 1899 for her birth, the day being unread, and her trade as Unpaid "
   "Domestic Certified Teacher - so she had qualified as a teacher and was keeping house. The "
   "record holds no Pelham Cottage, but a Winifred Onion, insurance agent, was at 1 Barrack lane "
   "in 1921, so the family was already on this lane"),
  (2, None, "Winifred M", "Onion", "Marshall", "F", "1920-11-05", 18, "GPO telegraphist", "Single",
   "the index gives her as Marshall (Onion), so Onion is the name the register was written in; "
   "she shares her forename with the Winifred Onion of 1 Barrack lane, born 1888"),
  (3, None, "Gladys E", "Onion", "Gell", "F", "1922-05-30", 17, "Clerk, chemist's", "Single",
   "the index gives her as Gell (Onion); her trade is written Clark (Book Chemist), so she kept "
   "the books for a chemist"),
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
        json.dump({"note": "**Barrack Lane, schedules 204 and 205 of the 1939 Register, ED letter "
                           "code RMGB.** 1 Barrack lane, where a third household member is a "
                           "record the register keeps closed, and Pelham Cottage, which is not "
                           "in the property list and so is unfiled.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_barrack_lane.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
