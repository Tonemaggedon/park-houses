# -*- coding: utf-8 -*-
"""9 Cavendish Crescent, 1939 - schedule 254, and a cook of 76 the record knows.

**Emma Radford, 76, widowed, cook.** She is the record's own Emma Radford,
born 1863 - a general servant at **1 Pelham Crescent** in 1901, married to
William Edward Radford the coachman, and housekeeper of that same house in 1911
when he headed it. He is gone and she is in service again at 76. Bound by
number. She is also the woman an import duplicated this morning, folded back
within the same day she turned up alive in 1939.

**Wilfred O Woodward is Ministry of Supply** - the page gives *Civil Servant
Minister Supply Area Officer Timber Control No 3*, which is **Timber Control**,
a wartime body. Another government post on the estate three weeks after war was
declared.

**The side is not given, and it cannot be settled from the record.** Neither 9
Cavendish Crescent North nor 9 Cavendish Crescent South holds a Woodward in any
earlier round, and the two are tangled: **9 North is one of the seven houses
schedule 193 could be**. If 193 is 9 North then this is 9 South, and the other
way about. So the household is unfiled.

  railway run python3 add_9_cavendish_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (None, 254, "9 Cavendish Crescent (the side is not given)", [
  (1, None, "Wilfred O", "Woodward", None, "M", "1886-06-05", 53,
   "Civil servant, Ministry of Supply - area officer, Timber Control No 3", "Married",
   "the page gives Civil Servant Minister Supply Area Officer Timber Control No 3. Timber "
   "Control was a wartime department of the Ministry of Supply, so he is another government "
   "post on the estate three weeks after war was declared"),
  (2, None, "Helen R", "Woodward", None, "F", "1922-02-22", 17,
   "Articled pupil, chartered accountants", "Single",
   "the page gives Articled Pupil Chat? Act Hig? & Company, the firm's name unread; articled "
   "pupil to a firm of chartered accountants is the reading. Seventeen and already articled"),
  (3, None, "Vera L", "Woodward", None, "F", "1890-07-11", 49, "Unpaid domestic duties", "Married",
   "four years younger than Wilfred O and sharing his surname, so his wife - which makes Helen R "
   "at sub number 2 their daughter, listed above her mother"),
  (4, None, "Marjorie E", "Slack", "Bingham, Barber", "F", "1911-09-18", 28, "Domestic", "Single",
   "the index gives her as Slack (Bingham) (Barber) and A. Hagues reads SLACK as the maiden "
   "name, so she was Slack on the night and married twice afterwards. The record holds Slacks "
   "at 25 Cavendish Crescent South and elsewhere, none of them hers so far as it can tell"),
  (5, 535, "Emma", "Radford", None, "F", "1863-05-21", 76, "Cook", "Widowed",
   "she is the record's Emma Radford, born 1863 - general servant at 1 Pelham Crescent in 1901 "
   "and housekeeper there in 1911, when her husband William Edward Radford, coachman, headed "
   "the house. He is gone by now and she is in service again at 76"),
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
                   "people": out}, open('data/people_1939_rmgb_9_cavendish_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
