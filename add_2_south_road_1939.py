# -*- coding: utf-8 -*-
"""2 South Road gets its first household, in any round.

The property has stood in the list empty - no census, no people, nothing - and
A. Hagues reads schedule 235 for it from the 1939 Register. It belongs to the
same batch as the rest of South Road and Cavendish Crescent South, which runs
229 to 237 and is numbered separately from the RMGC book the record holds in
full.

**Three women and no head.** Agnes L Foster is married and at sub number 1,
with a parlourmaid and a cook. Her husband is not on the page.

**One name is read two ways.** The index gives her as *Acho (Victoria) Wright
(Richardson)*. The record's settled reading of that bracket is that the
bracketed name is the name on the night and the one outside it is what was
written over it later, so she is entered as **Victoria Richardson** with Acho
Wright kept as an alias - and the source says plainly that the direction comes
from the pattern, not from this page.

  railway run python3 add_2_south_road_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_south_road.json'
PROP, SCHED, ADDR = 381, 235, '2 South Road'

BASE = ("1939 Register, schedule 235, 2 South Road - read from the page by A. Hagues; "
        "sub number {sub}; this schedule belongs to the South Road and Cavendish Crescent South "
        "run, numbered 229 to 237, and not to the RMGC book")

PEOPLE = [
 (1, "Agnes L", "Foster", None, "1901-11-23", 1901, 37, "Unpaid domestic duties", "Married",
  "sub number 1 and married, with a parlourmaid and a cook under her - her husband is not on "
  "the page"),
 (2, "Ethel", "Coke", None, "1905-11-29", 1905, 33, "Parlour maid", "Single", None),
 (3, "Victoria", "Richardson", ("Acho", "Wright"), "1897-09-17", 1897, 42, "Cook", "Single",
  "the index gives her as Acho (Victoria) Wright (Richardson). She is entered under the "
  "bracketed names as her names on the night, which is how this record reads that bracket "
  "elsewhere in the round - the direction comes from the pattern, not from this page, and "
  "Acho Wright is kept as a name she can be found under"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for sub, fn, ln, alias, bd, by, age, occ, marital, note in PEOPLE:
        cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                        WHERE c.census_year=1939 AND c.property_id=%s
                          AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                    (PROP, fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = BASE.format(sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}"
              + (f"  [{alias[0]} {alias[1]} kept as an alias]" if alias else ""))
        if not APPLY:
            continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES (%s,%s,'F',%s,%s) RETURNING id""", (fn, ln, by, bd))
        pid = cur.fetchone()[0]
        if alias:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           VALUES (%s,%s,%s,%s,'1939 amendment')""", (pid, alias[0], alias[1], by))
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                    (pid, PROP, ADDR, age, occ, SCHED, marital, src))
        rec = {"first_name": fn, "last_name": ln, "sex": "F", "born_year": by,
               "born_date": bd, "match_born_year": True,
               "census": [{"census_year": 1939, "property_id": PROP, "address": ADDR,
                           "marital_status": marital, "age_at_census": age,
                           "occupation_at_census": occ, "census_household_num": SCHED,
                           "source": src}],
               "id": pid}
        out.append(rec)
        print(f"        entered as #{pid}")

    if not APPLY:
        print("\n  Nothing written. Add --apply.")
        return
    json.dump({"note": "**2 South Road, schedule 235 of the 1939 Register.** The property had "
                       "stood in the list with no census in any round. A. Hagues reads the "
                       "household off the page: three women, no head, and one name the index "
                       "gives two ways.",
               "source": "1939 Register, South Road run, schedules 229 to 237",
               "people": out}, open(DATA, 'w'), indent=1, ensure_ascii=False)
    props = json.load(open('data/all_props.json'))
    for p in props:
        if p['id'] == PROP and not p.get('history'):
            p['history'] = ("**The record held this house empty until 1939.** No census in any "
                            "round named it, and the 1939 Register's South Road run gives it a "
                            "household at last: **Agnes L Foster**, 37, married, at sub number 1, "
                            "with **Ethel Coke**, 33, parlourmaid, and **Victoria Richardson**, "
                            "42, cook. **Her husband is not on the page.**")
    json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    c.commit()
    print("\n  committed")


if __name__ == '__main__':
    main()
