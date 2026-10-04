# -*- coding: utf-8 -*-
"""1 Pelham Crescent and Holly Lodge, 1939 - schedules 221 and 222.

**Ernest F Bradley is the record's Ernest J Bradley** - a J read as an F. He
headed 1 Pelham Crescent in 1921 aged 49 as a leather manufacturer, and was at
15 Pelham Crescent in 1901 aged 29 in his father Frederick James Bradley's
house, another leather manufacturer. He is here at 67, retired managing director
and widowed. Bound by number.

**Cicily L Butler (Bradley)**, 32 and single, keeps house for him. She is
entered as **Bradley**, the name the register was written in - she cannot be a
Butler by birth and single while the bracket gives Bradley, and the household
she is keeping is a Bradley's. Most likely his daughter.

**Holly Lodge** on Clumber Road West holds the Broadheads, none of them in the
record. The house has carried better-known people: Samuel H Sands, bank
director, in 1881, and in 1901 **Frederic Stanley Kipping, professor of
chemistry**.

  railway run python3 add_rmgb_221_222_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (274, 221, "1 Pelham Crescent", [
  (1, None, "Elsie", "Lus", None, "F", "1913-04-14", 26, "Domestic servant", "Single",
   "the surname is written Lus, which the page should settle - Lees, Luce and Lusk are all "
   "likelier than Lus"),
  (2, None, "Alice May", "Smith", None, "F", "1901-06-04", 38, "Domestic servant", "Single", None),
  (3, None, "Cicily L", "Bradley", "Butler", "F", "1907-02-13", 32, "Housekeeper", "Single",
   "the index gives her as Butler (Bradley); she is single and the house is Ernest Bradley's, so "
   "Bradley is the name the register was written in and Butler the name she came to later. "
   "Thirty-five years younger than him, so most likely his daughter keeping house for her "
   "widowed father - though the register records no relationships and does not say so"),
  (4, 2241, "Ernest J", "Bradley", None, "M", "1872-03-07", 67,
   "Managing director, leather manufacturer, retired", "Widowed",
   "the index gives him as Ernest F; the record has him as Ernest J, born 1872, leather "
   "manufacturer, heading THIS house in 1921 aged 49 - and at 15 Pelham Crescent in 1901 aged 29 "
   "in the house of Frederick James Bradley, leather manufacturer, who is most likely his father"),
 ]),
 (86, 222, "Holly Lodge, Clumber Road West", [
  (1, None, "Frank A", "Broadhead", None, "M", "1887-07-11", 52,
   "Surveyor, land and probate", "Married",
   "the trade is written Article Surveyor (Land & Prob), so he most likely valued land and "
   "estates for probate; the first word wants the page"),
  (2, None, "Constance A", "Broadhead", None, "F", "1885-10-26", 53, "Unpaid domestic duties", "Married",
   "twenty months older than Frank A and sharing his surname, so his wife"),
  (3, None, "John Mac", "Broadhead", None, "M", "1919-04-08", 20, "Student, agriculture", None,
   "the forename is written John Mac, which may be a surname used as a middle name"),
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
        json.dump({"note": "**1 Pelham Crescent and Holly Lodge, Clumber Road West, schedules 221 "
                           "and 222 of the 1939 Register, ED letter code RMGB.** Ernest F Bradley "
                           "is the record's Ernest J, who headed 1 Pelham Crescent in 1921; his "
                           "housekeeper Cicily is a Bradley by the register and most likely his "
                           "daughter. The Broadheads of Holly Lodge are all new.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_221_222.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
