# -*- coding: utf-8 -*-
"""Schedule 245, 1939 - Sir Jesse Hind and Dame Lilian, and six domestics.

**A knight and a dame, with six servants** - the largest staff in this stretch
of the walk, and four of the six are teenagers.

Sir Jesse Hind, solicitor, and his wife Lilian Frances kept **39 Newcastle
Drive** in 1921 with five servants. They had left it by 1939 - that house now
holds the Fischers - and the index does not say where they went. **The household
goes in unfiled**: A. Hagues heads the page "207" and no property in the record
carries that number.

Both are bound by number, and both now carry the titles the register gives them.

  railway run python3 add_schedule_245_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (None, 245, "207 (the street is not given)", [
  (1, 1201, "Jesse William", "Hind", None, "M", "1866-08-29", 73, "Solicitor", "Married",
   "the index gives him as SIR Jessie Hind; he is the Jesse William Hind who kept 39 Newcastle "
   "Drive in 1921 aged 54 in the same trade, born 1867 on that round and August 1866 here. The "
   "knighthood is new to the record"),
  (2, 1202, "Lilian Frances", "Hind", None, "F", "1868-11-04", 70, "Private means", "Married",
   "the index gives her as DAME Lilian F; she was his wife at 39 Newcastle Drive in 1921 aged 52"),
  (3, None, "Mildred I", "Smith", None, "F", "1877-09-29", 62, "Domestic", "Single",
   "her birthday fell on the very day the register was taken, so she turned 62 that morning"),
  (4, None, "May", "Haxley", None, "F", "1912-11-13", 26, "Domestic", "Single", None),
  (5, None, "Ada", "Burton", None, "F", "1922-07-24", 17, "Domestic", "Single", None),
  (6, None, "Edith", "Newton", None, "F", "1923-11-09", 15, "Domestic", "Single",
   "fifteen years old and in service; she and Mary at sub number 7 share a surname and are "
   "nineteen months apart, so most likely sisters"),
  (7, None, "Mary", "Newton", None, "F", "1922-04-05", 17, "Domestic", "Single", None),
  (8, None, "Kathleen M", "Crookes", None, "F", "1924-04-18", 15, "Domestic", "Single",
   "the youngest person in service in this whole book, at fifteen"),
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
                   "people": out}, open('data/people_1939_rmgb_schedule_245.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
