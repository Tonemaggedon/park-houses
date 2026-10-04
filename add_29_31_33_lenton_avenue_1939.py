# -*- coding: utf-8 -*-
"""The top of Lenton Avenue, 1939 - numbers 29, 31 and 33, off the RMGB book.

Schedules 184, 185 and 186, three small households at the far end of the street
where the record had no 1939 at all. A company director and his son the
commercial artist; an engineering director and his wife; a garage proprietor and
the woman keeping house for him.

Nobody here was in the record under any of these names.

  railway run python3 add_29_31_33_lenton_avenue_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (171, 184, "29 Lenton Avenue", [
   (1, "George S", "Anderson", None, "M", "1871-03-28", 68,
    "Company director and secretary", None,
    "the trade is written Company Director Secretary, which is one office or two"),
   (2, "Albert G", "Anderson", None, "M", "1919-06-10", 20, "Commercial artist", None,
    "forty-eight years younger than the man at sub number 1 and sharing his surname, so most "
    "likely his son"),
 ]),
 (172, 185, "31 Lenton Avenue", [
   (1, "James A", "Linday", None, "M", "1887-07-20", 52, "Engineering director", None,
    "the employer is written Soals, a firm the record does not otherwise hold; the surname is "
    "written Linday and the record holds a Lindley and a Lindey family at 14 Park Terrace, "
    "though under different forenames"),
   (2, "Theodora", "Linday", None, "F", "1889-03-06", 50, "Unpaid domestic duties", None,
    "the page gives Domestic Duties"),
 ]),
 (173, 186, "33 Lenton Avenue", [
   (1, "Arthur Eric", "Roe", None, "M", "1903-05-30", 36, "Garage proprietor", None, None),
   (2, "Irene Doris", "Horney", "Roe", "F", "1904-02-16", 35, "Unpaid domestic duties", None,
    "the index gives her as Horney (Roe), and the bracket in this register carries no fixed "
    "meaning; she is entered here under the name the register was written in, with Roe as the "
    "amendment, because Arthur Eric Roe heads the house and a woman already married to him "
    "would have been written Roe - but this wants confirming against the page"),
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
        json.dump({"note": "**29, 31 and 33 Lenton Avenue, schedules 184 to 186 of the 1939 Register, "
                           "ED letter code RMGB.** The far end of the street, where the record held "
                           "no 1939 round. Irene Doris Horney at 33 is given by the index as Horney "
                           "(Roe); she is entered under the register name with Roe as the amendment, "
                           "which wants confirming against the page.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_29_31_33_lenton_avenue.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
