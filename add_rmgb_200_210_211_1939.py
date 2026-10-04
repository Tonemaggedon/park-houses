# -*- coding: utf-8 -*-
"""Schedules 200, 210 and 211 - 9 Western Terrace and two of Pelham Crescent.

**9 Western Terrace holds three single women, all doing domestic work, and no
head at all.** The family was out on the night of 29 September 1939 and the
register took the staff. One of the three is a find: **Francis M Wing, 73,
light domestic**, is **Frances Mary Wing**, daughter of *Henry Wing, solicitor*,
of 12 Park Terrace - a scholar of five there in 1871, at home with her parents
in 1891 and 1901, and a joint tenant of 2 Park Terrace on *private means* in
1911. At 73 she is in somebody else's house doing light domestic work.

**13 Pelham Crescent** is the Reverend **Henry Burgess Lee**, Hon Canon of
Southwell, who kept 6 Lenton Road in 1921, with his wife Ida Marian. Both bound.

**15 Pelham Crescent** holds Marion A Dunhill, widow of 61, alone - where Kate
Thorpe, 84, and a household of six had been in 1921.

  railway run python3 add_rmgb_200_210_211_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (348, 200, "9 Western Terrace", [
  (1, None, "Olive", "Randall", "Kew", "F", "1917-07-18", 22, "Domestic duties", "Single",
   "the index gives her as Kew (Randall) and A. Hagues reads Randall as the maiden name; she is "
   "single at 22, so Randall is the name the register was written in"),
  (2, None, "Ivy", "Truswell", "Hardwick", "F", "1913-05-23", 26, "Domestic duties", "Single",
   "the index gives her as Hardwick (Truswell); by the same reading Truswell is the maiden name "
   "and she is single, so it is the name the register was written in"),
  (3, 3649, "Frances Mary", "Wing", None, "F", "1865-10-11", 73, "Light domestic", "Single",
   "the index gives her as Francis M Wing, which is exactly how the 1871 page spelt her: she is "
   "Henry Wing the solicitor's daughter of 12 Park Terrace, five years old there in 1871, at "
   "home in 1891 and 1901, and a joint tenant of 2 Park Terrace on private means in 1911 aged "
   "45 - which agrees with this birth date of October 1865. The record held her twice, as "
   "Francis M and as Frances Mary, and the two were joined on 4 October 2026"),
 ]),
 (284, 210, "15 Pelham Crescent", [
  (1, None, "Marion A", "Dunhill", None, "F", "1877-10-31", 61, "Unpaid domestic duties", "Widowed",
   "alone in the house, where Kate Thorpe, 84, her sister, two cousins and two servants had been "
   "in 1921; the record holds no other Dunhill"),
 ]),
 (282, 211, "13 Pelham Crescent", [
  (1, 1454, "Henry Burgess", "Lee", None, "M", "1874-12-26", 64, "Clerk in Holy Orders", "Married",
   "the index gives him as Harry B and his trade as Clerk Holy Orders Sac Bond Of F, the last "
   "words unread; he is the Henry Burgess Lee who kept 6 Lenton Road in 1921, returned there as "
   "Clerk in Holy Orders, Hon Canon of Southwell"),
  (2, 1455, "Ida Marian", "Lee", None, "F", "1875-01-03", 64, "Unpaid domestic duties", "Married",
   "the index gives her as Ida M; she was his wife at 6 Lenton Road in 1921, 46 to his 46"),
  (3, None, "Alice", "Cliff", None, "F", "1881-02-17", 58, "Cook, domestic", "Single",
   "the page gives Unpaid Domestic Cook, which for a single woman in another family's house is "
   "most likely a paid place written down loosely"),
  (4, None, "Susanna H", "Brown", None, "F", "1896-02-13", 43, "Domestic servant", "Single", None),
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
        json.dump({"note": "**Schedules 200, 210 and 211 of the 1939 Register, ED letter code "
                           "RMGB.** 9 Western Terrace, taken from the staff with the family out; "
                           "15 and 13 Pelham Crescent. Frances Mary Wing, a solicitor's daughter "
                           "of 12 Park Terrace, is doing light domestic work at 73, and the "
                           "Reverend Henry Burgess Lee has moved from 6 Lenton Road.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_200_210_211.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
