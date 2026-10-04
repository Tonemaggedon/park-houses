# -*- coding: utf-8 -*-
"""Haddon House, Cavendish Crescent North, 1939 - schedule 192.

**Bernard Swanwick Wright, solicitor**, headed this house in 1921 aged 45 with
his daughter Kathleen Florence, 18, and two servants. He is here still at 63,
and **Kathleen F Cooper at sub number 3 is that daughter**, 37 and married since.
Both bound by number. His wife Florence M, 63, was not in the 1921 household and
is new to the record.

Before the Wrights the house was the **Smiths'** - three generations of lace
manufacturers, John, John Percy and John Leslie, from 1891 to 1911.

**Sub number 5 is a malformed row.** The index runs the forename and surname
columns together as *Ethel Hall (Annison) (Marks)* and gives the sex as **Male**
for a woman doing domestic duties. Two brackets, where this batch's rule says
one bracket holds the name the register was written in - so the reading taken
here is that the names run **Marks, then Annison, then Hall**, latest first, and
she was **Marks** on the night. That wants confirming against the page.

  railway run python3 add_haddon_house_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (37, 192, "Haddon House, Cavendish Crescent North", [
  (1, 2308, "Bernard Swanwick", "Wright", None, "M", "1876-04-09", 63,
   "Solicitor and colliery director", None,
   "the index gives him as Bernard S and his trade as Solicitor And Colliery ERECTOR, which is "
   "almost certainly Director - a solicitor on a colliery board is ordinary in this county, a "
   "solicitor erecting one is not. He headed this house in 1921 aged 45, a solicitor then too"),
  (2, None, "Florence M", "Wright", None, "F", "1875-10-13", 63, "Private means", None,
   "six months older than Bernard Swanwick and sharing his surname, so his wife; she was not in "
   "the 1921 household, which held only him, his daughter and two servants"),
  (3, 2309, "Kathleen Florence", "Wright", "Cooper", "F", "1902-07-11", 37,
   "Unpaid domestic duties", None,
   "the index gives her as Kathleen F COOPER; she is Bernard Swanwick Wright's daughter, 18 in "
   "this house in 1921 and born 1903 on that round against 1902 here, and she has married a "
   "Cooper since. Her father is at sub number 1, which is what identifies her"),
  (4, None, "Kate V", "Mosley", "Osborne", "F", "1901-11-12", 37, "Unpaid domestic duties", None,
   "the index gives her as Osborne (Mosley), so Mosley is the name the register was written in"),
  (5, None, "Ethel", "Marks", "Annison, Hall", "F", "1918-12-13", 20, "Unpaid domestic duties", None,
   "the index runs her name columns together as Ethel Hall (Annison) (Marks) and gives her sex as "
   "Male, which she is not. Two brackets where the rest of this batch has one: taken here as three "
   "names latest first, so Marks on the night, then Annison, then Hall. The row wants re-reading"),
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
        json.dump({"note": "**Haddon House, Cavendish Crescent North, schedule 192 of the 1939 "
                           "Register, ED letter code RMGB.** Bernard Swanwick Wright, solicitor, "
                           "who headed it in 1921, and his daughter Kathleen Florence, married "
                           "to a Cooper since. Sub number 5 is a malformed row.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_haddon_house.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
