# -*- coding: utf-8 -*-
"""16 and 14 Pelham Crescent, 1939 - schedules 213 and 214.

**Schedule 214 came without an address, and Thomas Hugh Carrington is what
names it.** He was a grandson at **14 Pelham Crescent** in 1911 aged 19 and a
son there in 1921 aged 29, and he is in this household at 47 - the same way
Henry Holliwell named 7 Cavendish Crescent North. With him is **Nellie A
Pearson**, who is his mother: Nellie Annie Carrington, head of that house in
1921, remarried since to **Frederick Pearson**, company director, 81.

So the record now holds 14 Pelham Crescent across four rounds and three
generations: Mary Ann Mann, 71, heading it in 1911 with her daughter and
grandson; Nellie heading it in 1921; and in 1939 Nellie, her new husband and
her son, who has never left.

**16 Pelham Crescent** is the Williams family - and the index gives the wife's
surname as *William*, without the s, where her husband and daughter are both
Williams.

  railway run python3 add_rmgb_213_214_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (285, 213, "16 Pelham Crescent", [
  (1, None, "Bertha", "Williams", None, "F", "1889-04-25", 50, "Unpaid domestic duties", "Married",
   "the index gives her surname as WILLIAM, without the s, where her husband at sub number 3 and "
   "her daughter at sub number 2 are both Williams; she is entered under the family's spelling"),
  (2, None, "Jean", "Williams", "Burton", "F", "1920-11-13", 18, "Shorthand typist", "Single",
   "the index gives her as Jean (Jeane) Burton (Williams); she is eighteen and single in her "
   "parents' house, so Williams is the name the register was written in and Burton the name she "
   "came to later - the same shape as Eileen Archer (Almond) at 7 Western Terrace"),
  (3, None, "Alfred C", "Williams", None, "M", "1890-02-05", 49, "Agent, clothiers", "Married", None),
  (4, None, "Lucy", "Forbes", None, "F", "1858-07-17", 81, "Retired", "Widowed",
   "thirty-one years older than Bertha and of a different name, so most likely her mother or a "
   "lodger; the record holds no other Forbes"),
 ]),
 (283, 214, "14 Pelham Crescent", [
  (1, 552, "Nellie Annie", "Carrington", "Pearson", "F", "1872-12-01", 66,
   "Unpaid domestic duties", "Married",
   "the index gives her as Nellie A PEARSON; she is the Nellie Annie Carrington who was Mary Ann "
   "Mann's daughter in this house in 1911 aged 38 and its head in 1921 aged 47, and she has "
   "married Frederick Pearson since. Her son by her first marriage is at sub number 3"),
  (2, None, "Frederick", "Pearson", None, "M", "1858-04-07", 81, "Company director", "Married",
   "fourteen years older than Nellie Annie; the record holds no Pearson who could be him - the "
   "Park Valley Pearsons are a different family"),
  (3, 553, "Thomas Hugh", "Carrington", None, "M", "1891-11-22", 47, "Display manager", "Single",
   "the index gives him as Thomas H; he is what identifies this house - a grandson here in 1911 "
   "aged 19 and a son in 1921 aged 29, a chemist's assistant and then a department manager. Born "
   "1892 on those rounds and November 1891 here, which agrees with both ages"),
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
        json.dump({"note": "**Schedules 213 and 214 of the 1939 Register, ED letter code RMGB.** "
                           "16 Pelham Crescent, where the index drops the s from the wife's "
                           "Williams, and 14 Pelham Crescent, which came without an address and "
                           "is named by Thomas Hugh Carrington - a grandson there in 1911 and a "
                           "son in 1921, with his mother remarried to Frederick Pearson.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_213_214.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
