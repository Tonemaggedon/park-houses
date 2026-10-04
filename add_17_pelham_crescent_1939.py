# -*- coding: utf-8 -*-
"""17 Pelham Crescent, 1939 - schedule 209, and a family the record lost sight of.

A widow of 81 and her two unmarried daughters, all three of private means, with
two cooks. **The three Ellises are already in the record** - as the household of
**Francis R. Ellis, colliery director**, who kept *Gardenwood, Clumber Road* in
1901 with his wife Katharine A. and their daughters Alice M., 14, and Christabel
M., 13.

Thirty-eight years on, Francis is gone, Katharine is widowed, and the two girls
are 52 and 51 and still at home. The 1901 household is **unfiled** - the house
name was read uncertainly - so this does not identify Gardenwood, but it does
pick the family up again. All three are bound by number.

The index writes the daughter the record calls Christabel M. as **Mary C
(Christabel)**, so her name is most likely Mary Christabel and the record has
her initials the wrong way round.

  railway run python3 add_17_pelham_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (286, 209, "17 Pelham Crescent", [
  (1, 4163, "Katharine A.", "Ellis", None, "F", "1858-06-28", 81, "Private means", "Widowed",
   "the index gives her as Katherine Ann; she is the Katharine A. Ellis who was Francis R. "
   "Ellis's wife at Gardenwood, Clumber Road in 1901, aged 42 - born 1859 on that round and 1858 "
   "here. Francis, a colliery director, is not in the house, and she is returned widowed"),
  (2, 4164, "Alice M.", "Ellis", None, "F", "1886-10-20", 52, "Private means", "Single",
   "fourteen years old at Gardenwood in 1901, born 1887 on that round and 1886 here"),
  (3, 4165, "Christabel M.", "Ellis", None, "F", "1887-12-27", 51, "Private means", "Single",
   "thirteen at Gardenwood in 1901. The index gives her as Mary C (Christabel), so her name is "
   "most likely MARY CHRISTABEL and the record has her initials reversed - worth settling"),
  (4, None, "Emma", "Banett", None, "F", "1882-03-01", 57, "Cook, domestic", "Single",
   "the surname is written Banett and is most likely Barnett or Bennett; the record holds "
   "several of both but none that fits this birth year"),
  (5, None, "Ada", "Tongue", None, "F", "1884-11-03", 54, "Cook, domestic", "Single",
   "two cooks in one household of five, which is unusual - one of the two may be a housekeeper "
   "the register has written down by her former place"),
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
            if later:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, later, int(bd[:4]), fn, later))
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
        json.dump({"note": "**17 Pelham Crescent, schedule 209 of the 1939 Register, ED letter "
                           "code RMGB.** Katharine A. Ellis, widowed, and her two unmarried "
                           "daughters - the family of Francis R. Ellis, colliery director, of "
                           "Gardenwood, Clumber Road in 1901. All three bound by number.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_17_pelham_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
