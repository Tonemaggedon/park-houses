# -*- coding: utf-8 -*-
"""The Cottage, Lincoln Circus, 1939 - schedule 246, a chauffeur and his wife.

**Two people, no servants, and a chauffeur at the head** - which is what picks
the house. Lincoln Circus has three properties in the record: **Gladstone
House** and **Lincoln House**, both large and both kept with staff, and **The
Cottage**, which was the gardener's. Edward Palmer, domestic gardener, had it in
1901 with his wife and five children and still in 1911.

A chauffeur in 1939 is the same kind of household in the same kind of house: the
service dwelling of the Circus, with the motor car where the garden had been.

**This rests on the sort of house it is, not on evidence of the Turners
themselves** - the record holds neither of them. If the page says otherwise it
is one line to move.

  railway run python3 add_the_cottage_lincoln_circus_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (414, 246, "The Cottage, Lincoln Circus", [
  (1, None, "Frank S", "Turner", None, "M", "1874-04-10", 65, "Chauffeur", "Married",
   "A. Hagues gives the street as Lincoln Circus without a house. It is taken as The Cottage "
   "because that is the Circus's service dwelling - Edward Palmer, domestic gardener, kept it in "
   "1901 and 1911 - and a chauffeur with no servants of his own is a service household, where "
   "Gladstone House and Lincoln House were both kept with staff. This rests on the kind of house "
   "it is and not on the Turners, neither of whom the record holds"),
  (2, None, "Elizabeth", "Turner", None, "F", "1873-07-30", 66, "Unpaid domestic duties", "Married",
   "eight months older than Frank S and sharing his surname, so his wife"),
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
                   "people": out}, open('data/people_1939_rmgb_the_cottage_lincoln_circus.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
