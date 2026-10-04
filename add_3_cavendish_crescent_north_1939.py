# -*- coding: utf-8 -*-
"""3 Cavendish Crescent North, 1939 - schedule 257, and a second Yeomans house.

**The side is settled by elimination.** 3 Cavendish Crescent **South** already
has its 1939 round - schedule 95, early in this same book - and 3 Cavendish
Crescent **North** has none at all. So this is the North, and it comes off the
list of houses schedule 193 could be.

**Albert E Yeomans, office manager in tobacco**, is almost certainly kin to
**George E Yeomans, tobacco manufacturer**, two doors up at 5 Cavendish Crescent
North - schedule 195 of this book. Eight years between them, the same trade, the
same side of the same crescent. The record held no Yeomans family at all before
today.

**The bracket on this page is the name borne on the night**, proved by the two
daughters: Kathleen M A Widdowson (Yeomans) and Audrey Vaulkhard (Yeomans) are
21 and 20, single, in Albert E and Florence M **Yeomans's** house. So Florence A
Hart (Vines) was **Vines**.

  railway run python3 add_3_cavendish_crescent_north_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (22, 257, "3 Cavendish Crescent North", [
  (1, None, "Albert E", "Yeomans", None, "M", "1888-06-16", 51, "Office manager, tobacco", "Married",
   "eight years younger than the George E Yeomans who keeps 5 Cavendish Crescent North at "
   "schedule 195, and in the same trade - so almost certainly his brother, though the register "
   "records no relationships between households"),
  (2, None, "Florence M", "Yeomans", None, "F", "1893-12-16", 45, "Unpaid domestic duties", "Married", None),
  (3, None, "Kathleen M A", "Yeomans", "Widdowson", "F", "1918-03-11", 21,
   "Unpaid domestic duties", "Single",
   "the index gives her as Widdowson (Yeomans); she is 21 and single in her parents' house, so "
   "Yeomans is what she bore on the night"),
  (4, None, "Audrey", "Yeomans", "Vaulkhard", "F", "1919-04-12", 20, "Artist", None,
   "the index gives her as Vaulkhard (Yeomans) and her sex as UNKNOWN, which Audrey and her "
   "place in this household both answer. An artist at twenty. VAULKHARD is a Nottingham name "
   "and the record holds one already, a person whose forename it cannot read"),
  (5, None, "Florence A", "Vines", "Hart", "F", "1880-01-27", 59, "Domestic", "Single",
   "the index gives her as Hart (Vines); by the direction the two daughters settle on this very "
   "page, the bracket is the name borne on the night, so she was Vines. The record holds "
   "several Harts and no Vines at all"),
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
        json.dump({"note": "**5 Clumber Crescent South, schedule 242 of the 1939 Register, ED "
                           "letter code RMGB.** William Crane, builder and contractor, his wife "
                           "and his daughter Joyce M, a British Red Cross volunteer, with two "
                           "domestics who are most likely sisters. None of the five was in the "
                           "record.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_3_cavendish_crescent_north.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
