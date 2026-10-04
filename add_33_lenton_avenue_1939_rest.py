# -*- coding: utf-8 -*-
"""33 Lenton Avenue, 1939 - three more households in one house.

Schedules 187 to 190, which join schedule 186 already in the record. Five
separate schedules at one address means the house was **divided into flats or
let out in rooms** by 1939: a garage proprietor, a warp knitter in artificial
silk and his wife nursing, a tailor's shop assistant and his wife, a young
medical man on his own, and a manufacturer of ladies' wear on his own.

Five households of two, two, two, one and one - eight people where the 1921
round held ten in a single family.

  railway run python3 add_33_lenton_avenue_1939_rest.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (173, 187, "33 Lenton Avenue", [
   (1, "Alan J", "McClatchie", None, "M", "1908-08-20", 31, "Warp knitter, artificial silk", None,
    "the page gives Warp Knitter Art Silk"),
   (2, "Doris S", "McClatchie", None, "F", "1910-05-21", 29, "Auxiliary nurse", None,
    "two years younger than the man at sub number 1 and sharing his surname, so most likely his wife"),
 ]),
 (173, 188, "33 Lenton Avenue", [
   (1, "Vernon E E", "Cramphorn", None, "M", "1910-09-27", 29, "Shop assistant, tailor's", None,
    "his birthday fell two days before the register was taken"),
   (2, "Nora N", "Cramphorn", None, "F", "1916-02-11", 23, "Unpaid domestic duties", None, None),
 ]),
 (173, 189, "33 Lenton Avenue", [
   (1, "H William", "Forsyth", None, "M", "1913-02-14", 26, "Registered medical", None,
    "the trade is written Reg Medical Te and the next word is unread, so what he was registered "
    "as is not known; his line is RG101/6178A, item 18, line 11, and the page gives his address "
    "in full as 33 Lenton Avenue, Nottingham"),
 ]),
 (173, 190, "33 Lenton Avenue", [
   (1, "Charles N", "Dorrington", None, "M", "1899-01-21", 40,
    "Manufacturer, ladies' wear", None,
    "his line is RG101/6178A, item 18, line 12, immediately below H William Forsyth, and the page "
    "gives his address in full as 33 Lenton Avenue, Nottingham"),
 ]),
]


def main():
    props = {p.get('address'): p['id'] for p in json.load(open('data/all_props.json'))}
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        prop = prop or props.get(addr)
        if not prop:
            print(f"  {addr}: not in the property list"); continue
        print(f"--- schedule {sched}, {addr} (#{prop})")
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                            WHERE c.census_year=1939 AND c.property_id=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                        (prop, fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
            if not APPLY:
                continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, int(bd[:4]) if bd else None, bd))
            pid = cur.fetchone()[0]
            names = [x.strip() for x in (later or '').split(',') if x.strip()]
            for i, one in enumerate(names):
                label = ('1939 amendment' if len(names) < 2 else
                         f"1939 amendment ({'latest' if i == len(names)-1 else 'first'} married name)")
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,%s FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, one, int(bd[:4]) if bd else None, label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]) if bd else None,
                        "born_date": bd, "match_born_year": bool(bd),
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "marital_status": marital, "age_at_census": age,
                                    "occupation_at_census": occ, "census_household_num": sched,
                                    "source": src}], "id": pid})
    if APPLY:
        json.dump({"note": "**33 Lenton Avenue, schedules 187 to 190 of the 1939 Register, ED "
                           "letter code RMGB.** Three households joining schedule 186 at the "
                           "same address, five in all, so the house was divided by 1939. H "
                           "William Forsyth's trade is written Reg Medical Te with the next "
                           "word unread.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_33_lenton_avenue_rest.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
