# -*- coding: utf-8 -*-
"""7 and 9 Hope Drive, 1939 - schedules 67 and 69 of the RMGC book.

At number 9, **Louis Millett and his son Bernard are both returned *Partner,
clothing outfitter*** - the same firm, father at 53 and son at 23. A fourth line
of that household is a record the register keeps closed.

At number 7, a secretary and organiser of 52 and his wife of 32, herself a
typist and secretary - one of the few married women in this round with a trade
of her own.

The odd side of Hope Drive runs 1, 3, 5, 7, 9 at schedules 63, 64, 65, 67 and
69, so **66 and 68 are two more households on this street** that have not come
through yet.

  railway run python3 add_hope_drive_67_69_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code {book}, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

# property, schedule, address, book, people
HOUSES = [
 (354, 67, "7 Hope Drive", [
  (1, None, "Frederick", "Parker", None, "M", "1886-12-03", 52, "Secretary and organiser", "Married",
   "what he was secretary of is not given"),
  (2, None, "Myrtle J", "Parker", None, "F", "1907-01-17", 32, "Typist and secretary", "Married",
   "twenty years younger than Frederick and sharing his surname, so his wife - and one of the "
   "few married women in this round returned with a trade of her own rather than domestic duties"),
 ]),
 (355, 69, "9 Hope Drive", [
  (1, None, "Louis", "Millett", None, "M", "1886-05-15", 53,
   "Partner, clothing outfitters", "Married", None),
  (2, None, "Anna", "Millett", None, "F", "1887-10-21", 51, "Unpaid domestic duties", "Married",
   "a year younger than Louis and sharing his surname, so his wife"),
  (3, None, "Bernard", "Millett", None, "M", "1916-01-29", 23,
   "Partner, clothing outfitters", "Single",
   "returned in the same words as Louis at sub number 1 - thirty years younger and sharing his "
   "surname, so his son and his partner in the same firm"),
  (5, None, "Lilian E", "Underwood", None, "F", "1899-07-05", 40, "Housemaid, domestic", "Single",
   "sub number 4 is a line the register keeps closed, so the house held at least five"),
 ]),
]
BOOK = {67: 'RMGC', 69: 'RMGC'}


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
                                AND source ILIKE %s""", (sched, exist, f'%{BOOK[sched]}%'))
            else:
                cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                                WHERE ce.census_year=1939 AND ce.census_household_num=%s
                                  AND ce.source ILIKE %s
                                  AND LOWER(p.first_name)=LOWER(%s)
                                  AND LOWER(p.last_name)=LOWER(%s)""",
                            (sched, f'%{BOOK[sched]}%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub, book=BOOK[sched]) + (('; ' + note) if note else '')
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
                   "people": out}, open('data/people_1939_rmgc_hope_drive_67_69.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
