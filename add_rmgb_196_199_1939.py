# -*- coding: utf-8 -*-
"""Schedules 196 to 199 of the RMGB book, 1939.

**The bracket in this batch holds the name the register was written in**, and the
surname printed in front of it is the name the woman came to later. Two children
prove it: Eileen Archer (Almond) is **twelve** and Helen U H Martlow (Yeomans)
is **fourteen**, and neither can be carrying a married name. So Eileen was
Almond on the night, in her parents' house, and Archer afterwards. That agrees
with A. Hagues's word that Bould is the maiden name at Hardwicke House.

Three of these four households were new to the record. The fourth is Mary E
Littlewood's: she kept 1 Cavendish Crescent North in 1921 with Sarah Coates and
Agnes Stanley, and the same two servants are still with her eighteen years
later, so all three are bound by number.

**Schedule 196 goes in unfiled.** The index gives the number 7 but not the side,
and schedule 194 is already 7 Cavendish Crescent North - so this is most likely
the South, but the page has not said so.

  railway run python3 add_rmgb_196_199_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (None, 196, "7 Cavendish Crescent (the side is not given; schedule 194 is already the North)", [
  (1, 2322, "Mary E", "Littlewood", None, "F", "1854-01-06", 85, "Unpaid domestic duties", None,
   "she kept 1 Cavendish Crescent North in 1921 with Sarah Coates and Agnes Stanley, the same two "
   "servants who are with her here eighteen years on; her birth year is 1856 on that round and "
   "1854 on this. So she moved between 1921 and 1939, and this is not the house she left"),
  (2, 2324, "Sarah", "Coates", None, "F", "1861-04-18", 78, "Parlour maid", "Single",
   "in Mary Littlewood's household in 1921 as well, aged 60, which agrees with this birth date"),
  (3, 2325, "Agnes", "Stanley", None, "F", "1873-11-17", 65, "Cook", "Single",
   "in Mary Littlewood's household in 1921 as well, aged 48, which agrees with this birth date"),
  (4, None, "Katherine", "Rowden", None, "F", "1908-09-05", 31, "Housemaid", None,
   "the only one of the four the record did not already hold"),
 ]),
 (231, 197, "8 North Road", [
  (1, None, "Elizabeth M", "Coulley", None, "F", "1871-02-19", 68, "Unpaid domestic duties", "Widowed",
   "head of the house at 68, with a married couple and a domestic under her roof"),
  (2, None, "John", "Featherstone", None, "M", "1899-04-26", 40, "Motor fitter", "Married",
   "the record holds Featherstones at 13 Park Valley and 34 The Ropewalk in this same round, "
   "none of an age to be him"),
  (3, None, "Ethel E J", "Featherstone", None, "F", "1902-10-19", 36, "Unpaid domestic duties", "Married",
   "the page gives her trade as Domestic Wife"),
  (4, None, "Agnes A", "Alexander", None, "F", "1900-04-14", 39, "Domestic", "Single",
   "the record holds an Edith Annie Alexander born the same year, but the forenames do not "
   "match well enough to bind her"),
 ]),
 (346, 198, "7 Western Terrace", [
  (1, None, "Elizah", "Almond", None, "M", "1880-05-15", 59, "Joiner", "Married",
   "the forename is written Elizah and is most likely Elijah"),
  (2, None, "May", "Almond", None, "F", "1888-06-06", 51, "Unpaid domestic duties", "Married",
   "the index gives her as May (Marjorie Ellen); she shares a birthday, the sixth of June, with "
   "her daughter at sub number 3, thirty-nine years apart"),
  (3, None, "Eileen", "Almond", "Archer", "F", "1927-06-06", 12, "At school", "Single",
   "the index gives her as Archer (Almond); she is twelve and in her parents' house, so Almond "
   "is the name the register was written in and Archer the name she came to later - which is "
   "what settles the direction of the bracket for this whole batch"),
  (4, None, "John W", "Stamp", None, "M", "1905-08-03", 34, "Unemployed", "Single",
   "one of very few in the record returned as unemployed"),
  (5, None, "James", "Wolfe", None, "M", "1891-02-15", 48, "Warehouse packer, lace", "Single", None),
 ]),
 (347, 199, "8 Western Terrace", [
  (1, None, "Robert A", "Lowe", None, "M", "1909-09-02", 30, "Clerk, tobacconist's", "Married", None),
  (2, None, "Marjorie L", "Lowe", "Barber", "F", "1912-03-06", 27, "Textile sanitaries", "Married",
   "the index gives her as Barber (Lowe); by the direction this batch's children settle, Lowe is "
   "the name the register was written in - so she is Robert A Lowe's wife and became Barber "
   "afterwards. Her trade is written Textile Saniteries and is most likely sanitary textiles"),
  (3, None, "May E I", "Pomerdy", None, "F", "1890-12-15", 48, "Piano teacher, retired", "Single",
   "the surname is written Pomerdy and may be Pomeroy"),
  (4, None, "Katherine A", "Powell", "Miller", "F", "1909-07-09", 30, "Housekeeper", "Single",
   "the index gives her as Katherine A (Catherine Bennie) Miller (Powell); she is single, so "
   "Powell is the name the register was written in, and Ann R Powell at sub number 5 is "
   "thirty-seven years older and most likely her mother"),
  (5, None, "Ann R", "Powell", None, "F", "1872-02-15", 67, "Housekeeper", "Widowed", None),
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
        json.dump({"note": "**Schedules 196 to 199 of the 1939 Register, ED letter code RMGB.** "
                           "8 North Road, 7 and 8 Western Terrace, and one household at a number 7 "
                           "on Cavendish Crescent whose side the index does not give, which is "
                           "therefore unfiled. The bracket in this batch holds the name the "
                           "register was written in: Eileen Archer (Almond) is twelve and in her "
                           "parents' house, which settles it.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_196_199.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
