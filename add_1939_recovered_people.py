# -*- coding: utf-8 -*-
"""People the 1939 import had to pass over, named at last.

The importer takes nobody without both a first and a last name, so a handful of
1939 people whose forenames were lost under repair strips were written into the
import file's note instead of being entered - a household, a birth date and a
trade, with no name to hang them on. As A. Hagues recovers each forename from
the Register's index, this puts the person into the record where they belong.

  railway run python3 add_1939_recovered_people.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'

# schedule, sub, forename(s), surname on the night, amended surname, sex,
# born_date, born_year, age, occupation, property, and what to say
PEOPLE = [
 (82, 4, "Annie Holland", "Hatton", "Longsdale", "F", "1914-04-13", 1914, 25,
  "Domestic servant", 64, "Grove House, Clare Valley",
  "the forename is from the Register's index; the page has it under a repair strip, which is "
  "why this record carried a servant with a birth date and no name. Entered as Annie Holland "
  "Hatton, which is her name on the night; Longsdale is written over it in a later hand, and "
  "was first read here as Lonsdale"),
 (125, 3, "Lucy", "Fox", "Harbord", "F", "1904-07-10", 1904, 35,
  "Cook general", 260, "4 Park Valley",
  "the forename is from the Register's index; the page has it under a repair strip, which is "
  "why this record carried a cook with a birth date and no name. Entered as Lucy Fox, which is "
  "her name on the night; Harbord is written over it in a later hand, and was first read here "
  "as Hargood"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    d = json.load(open(DATA))
    for (sched, sub, fn, was, later, sex, bd, by, age, occ, prop, addr, note) in PEOPLE:
        cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                        WHERE c.census_year=1939 AND c.census_household_num=%s
                          AND LOWER(p.first_name)=LOWER(%s)""", (sched, fn))
        if cur.fetchone():
            print(f"  {fn} {was}: already in the record"); continue
        print(f"  schedule {sched} sub {sub}: {fn} {was}, {addr}"
              + (f" - {later} kept as an alias" if later else ""))
        if not APPLY:
            continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, was, sex, by, bd))
        pid = cur.fetchone()[0]
        if later:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           VALUES (%s,%s,%s,%s,'1939 amendment')""", (pid, fn, later, by))
        src = (f"1939 Register, schedule {sched}, {addr}, ED letter code RMGC, Nottingham "
               f"registration sub-district 3 - read from the page by A. Hagues; sub number {sub}; "
               + note)
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, source)
                       VALUES (%s,%s,1939,%s,%s,%s,%s,%s)""",
                    (pid, prop, addr, age, occ, sched, src))
        rec = {"first_name": fn, "last_name": was, "sex": sex, "born_year": by,
               "born_date": bd, "match_born_year": True,
               "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                           "age_at_census": age, "occupation_at_census": occ,
                           "census_household_num": sched, "source": src}],
               "id": pid}
        at = next((i for i, x in enumerate(d['people'])
                   if any(ce.get('census_household_num') == sched for ce in x['census'])), None)
        d['people'].insert(at + 1 if at is not None else len(d['people']), rec)
        print(f"        entered as #{pid}")
    if APPLY:
        json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
