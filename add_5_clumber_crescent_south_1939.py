# -*- coding: utf-8 -*-
"""5 Clumber Crescent South, 1939 - schedule 242, and a second war volunteer.

**Joyce M Crane, 24, is a British Red Cross volunteer** - the second woman in
this round found volunteering three weeks after war was declared, after Joan M
Ball, the eighteen-year-old V.A.D. at Stowe House.

Her father William is a **builder and contractor**, which is a trade the estate
had rather than housed: most heads in this stretch are lace, tobacco, law or
land.

**The two domestics are almost certainly sisters.** Daisy **Cameron** Mariwitt,
30 and married, and Lily **Cameron** Caunt, 32 and single, share a middle name
that is itself a surname. Read together with Lily's own entry - the index gives
her as Caunt (White), so Caunt is the name she bore on the night - the pair read
as two Caunt sisters, one of whom had married a Mariwitt.

The house was **John Thorpe Perry's**, solicitor, in 1911.

  railway run python3 add_5_clumber_crescent_south_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (79, 242, "5 Clumber Crescent South", [
  (1, None, "William", "Crane", None, "M", "1874-06-06", 65, "Builder and contractor", "Married",
   "the record holds no other Crane. The walk identifies the house: schedules 238 and 241 are "
   "6 South Road and 244 is Gwedon, 9 Clumber Crescent South, so this stretch is on Clumber "
   "Crescent - A. Hagues confirmed it"),
  (2, None, "Gladys E", "Crane", None, "F", "1890-02-18", 49, "Unpaid domestic duties", "Married",
   "sixteen years younger than William and sharing his surname, so his wife"),
  (3, None, "Joyce M", "Crane", None, "F", "1915-04-05", 24, "British Red Cross volunteer", "Single",
   "the page gives British Red Cross Vol. The second woman in this round found volunteering "
   "three weeks after war was declared, after Joan M Ball, the eighteen-year-old V.A.D. at "
   "Stowe House"),
  (4, None, "Daisy Cameron", "Mariwitt", None, "F", "1909-06-27", 30, "Domestic", "Married",
   "she and the woman at sub number 5 share the middle name Cameron, which is itself a surname, "
   "and both are domestics here - so they are most likely sisters, Daisy having married a "
   "Mariwitt. The surname wants the page; the record holds nothing like it"),
  (5, None, "Lily Cameron", "Caunt", "White", "F", "1907-05-09", 32, "Domestic", "Single",
   "the index gives her as Caunt (White); she is single, so Caunt is the name the register was "
   "written in and White the name she came to later. If she and Daisy Cameron are sisters, "
   "Caunt is the family name and Daisy was a Caunt before she married"),
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
                   "people": out}, open('data/people_1939_rmgb_5_clumber_crescent_south.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
