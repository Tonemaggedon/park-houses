# -*- coding: utf-8 -*-
"""3 Clumber Crescent South and Clumber House, 1939 - schedules 252 and 253.

**Clumber House settles the bracket for its own page.** The index gives sub
number 3 twice over, under two renderings of one woman:

    Phyllis F  Hodges (Smith)
    Phyllis F  Lane (Hodges, Smith)

Same birth date, same sub number, same trade. Read together they give the whole
chain - **Smith, then Hodges, then Lane** - with the surname in front being the
latest and the brackets running back. She is 27, single, and Herbert and Lily M
**Smith** head the house, so **Smith** is what she bore on the night. By the
same direction, Hilda Milward (Beaskell) was **Beaskell**.

The house had been the **Gregorys'**, lace manufacturers, from 1881 to 1901 at
least - William Godfrey Gregory with eight children.

  railway run python3 add_rmgb_252_253_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (78, 252, "3 Clumber Crescent South", [
  (1, None, "Herbert V", "Turner", None, "M", "1888-08-07", 51, "Craftsman, colliery", "Married",
   "the trade is written Cragsman Col E, which is not a trade; craftsman at a colliery is the "
   "likeliest reading of it and the page should settle it. No relation the record can see to "
   "the Frank S Turner who drives at The Cottage, Lincoln Circus"),
  (2, None, "Milden O", "Turner", None, "F", "1896-06-06", 43, "Unpaid domestic duties", "Married",
   "the forename is written Milden, which is most likely Mildred; eight years younger than "
   "Herbert V and sharing his surname, so his wife"),
  (3, None, "Mabel E", "Gill", None, "F", "1884-08-13", 55, "Private means", "Single",
   "of private means in a craftsman's household, and of a different name - so a lodger rather "
   "than family, unless she is one of their mothers under a remarried name"),
 ]),
 (239, 253, "Clumber House, Park Drive", [
  (1, None, "Herbert", "Smith", None, "M", "1883-08-03", 56, "Net manufacturer", "Married",
   "net rather than lace, in a house the Gregorys kept as lace manufacturers from 1881"),
  (2, None, "Lily M", "Smith", None, "F", "1885-02-12", 54, "Unpaid domestic duties", "Married",
   "the register gives her occupation simply as Wife"),
  (3, None, "Phyllis F", "Smith", "Hodges, Lane", "F", "1912-08-25", 27, "Secretary", "Single",
   "the index prints her TWICE, as Hodges (Smith) and as Lane (Hodges, Smith) - same birth date, "
   "same sub number, same trade. The two together give the chain: Smith, then Hodges, then Lane, "
   "latest in front. She is 27 and single in Herbert and Lily M Smith's house, so Smith is what "
   "she bore on the night"),
  (4, None, "Mary", "Laurence", None, "F", "1876-12-05", 62, "Cook", "Single", None),
  (5, None, "Hilda", "Beaskell", "Milward", "F", "1918-06-26", 21, "Parlour maid", "Single",
   "the index gives her as Milward (Beaskell); by the direction sub number 3 settles on this very "
   "page, the bracket is the earlier name, so she was Beaskell on the night. Beaskell is not a "
   "name the record holds elsewhere"),
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
                   "people": out}, open('data/people_1939_rmgb_252_253.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
