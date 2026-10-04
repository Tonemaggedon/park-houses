# -*- coding: utf-8 -*-
"""7 Pelham Crescent, 1939 - schedule 217, the Cartwright women.

**The same house, eighteen years on.** Thomas William Cartwright kept 7 Pelham
Crescent in 1921 with his wife Kathleen Christina, 42, and their daughters Mary
Elizabeth Kathleen, 13, and Patience Christina, 8. In 1939 Thomas William is
dead, **Kathleen is widowed at 60 and still in the house**, and both daughters
are back in it, married, with two small boys. Three servants keep it. All three
women are bound by number.

**The surnames in this paste were put right by A. Hagues** so that every name a
woman carried is written down, the one she bore on the night in front and the
others in brackets. That is how they are entered here:

  May E K **Barber** - Mary Elizabeth Kathleen Cartwright, whose sons Robert A
  and Peter John are at sub numbers 4 and 5, which fixes Barber as her name in
  September 1939 beyond doubt.

  Patience **Goddard** (Cartwright) (Perkins) - Cartwright is her maiden name,
  so Goddard and Perkins are two marriages, and Goddard is taken as the one she
  bore on the night.

  railway run python3 add_7_pelham_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (277, 217, "7 Pelham Crescent", [
  (1, 1088, "Kathleen Christina", "Cartwright", None, "F", "1879-01-21", 60,
   "Unpaid domestic duties", "Widowed",
   "the index gives her as Kathleen Cc; she was Thomas William Cartwright's wife in this house "
   "in 1921 aged 42, and is widowed here at 60 and still in it"),
  (2, 1089, "Mary Elizabeth Kathleen", "Cartwright", "Barber", "F", "1908-06-17", 31,
   "Unpaid domestic duties", "Married",
   "the index gives her as May E K BARBER, which is her three forenames and her married name; "
   "she was thirteen in this house in 1921. Her sons Robert A and Peter John are at sub numbers "
   "4 and 5, which settles Barber as her name on the night"),
  (3, 1090, "Patience Christina", "Cartwright", "Goddard, Perkins", "F", "1912-07-06", 27,
   "Unpaid domestic duties", "Married",
   "the index gives her as Patience Goddard (Cartwright) (Perkins); she was eight in this house "
   "in 1921, born 1913 on that round and July 1912 here. Cartwright is her maiden name, so "
   "Goddard and Perkins are two marriages - Goddard taken as the name she bore in September "
   "1939, on the strength of her sister's entry in the same household, where the surname in "
   "front is the one borne on the night. Worth confirming against the page"),
  (4, None, "Robert A", "Barber", None, "M", "1934-10-26", 4, "At school", "Single",
   "Mary Elizabeth Kathleen's son, in his grandmother's house"),
  (5, None, "Peter John", "Barber", None, "M", "1937-11-13", 1, "Under school age", "Single",
   "his brother, and the youngest person in this stretch of the walk"),
  (6, None, "Dorothy", "Chapman", "Crocker", "F", "1918-01-15", 21, "Domestic servant", "Single", None),
  (7, None, "Joan M", "Benton", "Alcock", "F", "1921-09-28", 18, "Domestic servant", "Single",
   "her eighteenth birthday fell the day before the register was taken"),
  (8, None, "Louisa", "Dale", None, "F", "1906-05-08", 33, "Domestic servant", "Single", None),
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
        json.dump({"note": "**7 Pelham Crescent, schedule 217 of the 1939 Register, ED letter code "
                           "RMGB.** The Cartwright women - Kathleen Christina widowed at 60 in the "
                           "house she kept with her husband in 1921, and both daughters back in "
                           "it, married, with two small boys. Three bound by number.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_7_pelham_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
