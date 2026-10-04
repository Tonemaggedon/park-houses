# -*- coding: utf-8 -*-
"""11 and 15 Hope Drive, 1939 - schedule 70, and a third woman volunteering.

**Irene Medd, 23, is a casualty ambulance driver.** She is the third woman this
book has turned up volunteering three weeks after war was declared, after Joan M
Ball, the eighteen-year-old V.A.D. at Stowe House, and Joyce M Crane of the
British Red Cross at 5 Clumber Crescent South. She was born on **29 February
1916**, so she had had five birthdays.

Number 11 is not a family but a **shared house**: two Downeys, Irene Medd, a
typewriter mechanic, and a married couple in their sixties, all under one
schedule and no two of them related so far as the record can tell.

**John Murden is a problem the page will have to settle.** A. Hagues heads him
**15 Hope Drive**, and the index row carries **schedule 70 sub number 7** -
which is number 11's schedule. One of the two is wrong: either he is the seventh
person at number 11, or he is at number 15 under a schedule of his own. He is
filed at 15 Hope Drive, where A. Hagues put him, with the clash written into his
source line.

  railway run python3 add_hope_drive_70_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code {book}, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

# property, schedule, address, book, people
HOUSES = [
 (356, 70, "11 Hope Drive", [
  (1, None, "Marion", "Downey", None, "F", "1906-08-29", 33,
   "Domestic science instructor, now personnel", "Single",
   "the page gives (Ea) Domestic Science Instructor Now Personnel - so she had taught domestic "
   "science and had moved into personnel work by September 1939"),
  (2, None, "James J", "Downey", None, "M", "1908-05-06", 31, "Tailor's cutter", "Single",
   "the index row is malformed, his birth date having slipped into the sex column; two years "
   "younger than Marion and sharing her surname, so most likely her brother"),
  (3, None, "Irene", "Medd", "Lowes", "F", "1916-02-29", 23,
   "Casualty ambulance driver", "Single",
   "the index gives her as Lowes (Medd) and A. Hagues reads MEDD as the maiden name; she is "
   "single at 23, so Medd is what she bore on the night. A CASUALTY AMBULANCE DRIVER - the "
   "third woman in this book found volunteering. Born on 29 February 1916, so she had had "
   "five birthdays"),
  (4, None, "James F", "Morton", None, "M", "1914-12-20", 24, "Typewriter mechanic", "Single", None),
  (5, None, "Edith E", "Cullis", None, "F", "1874-12-04", 64, "Dressmaker", "Married",
   "one of the oldest women in this round still at a trade"),
  (6, None, "Wallace H", "Cullis", None, "M", "1875-03-10", 64, "Timber traveller", "Married",
   "three months older than Edith E and sharing her surname, so her husband"),
 ]),
 (358, 70, "15 Hope Drive", [
  (7, None, "John", "Murden", None, "M", "1878-04-04", 61,
   "Railway ganger, maintenance", "Married",
   "A. HAGUES HEADS HIM 15 HOPE DRIVE AND THE INDEX ROW CARRIES SCHEDULE 70 SUB NUMBER 7, which "
   "is 11 Hope Drive's schedule. One of the two must be wrong: either he is the seventh person "
   "at number 11 or he is at number 15 under a schedule of his own. He is filed at 15 on "
   "A. Hagues's word, and this wants the page. A railway ganger led the gang that kept a length "
   "of track in repair"),
 ]),
]
BOOK = {70: 'RMGC'}


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
                   "people": out}, open('data/people_1939_rmgc_hope_drive_70.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
