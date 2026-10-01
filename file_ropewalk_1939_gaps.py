# -*- coding: utf-8 -*-
"""Two holes in the 1939 Ropewalk, both closed by A. Hagues.

Schedule 161 had no number on the page and was held "between 48 and 42". It is
**44 The Ropewalk**, which the record already has, and the walk agrees: 158 is
54, 159 is 52, 160 is 48, then this, then 42 and 40.

And 48 The Ropewalk was a person short. Sub number 4 was missing from a
household that runs 1, 2, 3, 5, 6 - **Elvina Lowe**, kitchen maid, born 29
December 1923, amended afterwards to Ward.

  railway run python3 file_ropewalk_1939_gaps.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'
RW44, RW48 = 335, 336

SRC48 = ("1939 Register, schedule 160, 48 The Ropewalk, ED letter code RMGC, Nottingham "
         "registration sub-district 3 - read from the page by A. Hagues; sub number 4; entered as "
         "Elvina Lowe, which is her name on the night; Ward is written over it in a later hand. "
         "She is the sub number the record was missing from this household")


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    d = json.load(open(DATA))

    cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                     JOIN people p ON p.id=c.person_id
                    WHERE c.census_year=1939 AND c.census_household_num=161""")
    rows = cur.fetchall()
    for cid, fn, ln in rows:
        print(f"  row {cid} {fn} {ln}: unfiled -> 44 The Ropewalk")

    cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                    WHERE c.census_year=1939 AND c.census_household_num=160
                      AND p.first_name='Elvina'""")
    have = cur.fetchone()
    print("  Elvina Lowe: already in the record" if have
          else "  sub 4 of schedule 160: Elvina Lowe, 15, kitchen maid - Ward kept as an alias")

    if not APPLY:
        print("\n  Nothing written. Add --apply.")
        return

    note = ("the house is 44 The Ropewalk - the page gives no number, and A. Hagues reads it from "
            "the sheet; the walk agrees, schedule 160 being 48 and 162 being 42")
    cur.execute("""UPDATE census_entries SET property_id=%s, address='44 The Ropewalk',
                     unresolved_address=NULL,
                     source = replace(source,
                       'the house is not identified in the record, so this row is left unfiled', %s)
                    WHERE census_year=1939 AND census_household_num=161""", (RW44, note))
    for _, fn, ln in rows:
        for x in d['people']:
            if (x['first_name'], x['last_name']) != (fn, ln):
                continue
            cur.execute("SELECT id FROM people WHERE first_name=%s AND last_name=%s", (fn, ln))
            got = cur.fetchall()
            if len(got) == 1:
                x['id'] = got[0][0]
            for ce in x['census']:
                if ce.get('census_household_num') != 161:
                    continue
                ce.pop('unresolved_address', None)
                ce['property_id'] = RW44
                ce['address'] = '44 The Ropewalk'
                ce['source'] = ce['source'].replace(
                    'the house is not identified in the record, so this row is left unfiled', note)

    if not have:
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES ('Elvina','Lowe','F',1923,'1923-12-29') RETURNING id""")
        pid = cur.fetchone()[0]
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       VALUES (%s,'Elvina','Ward',1923,'1939 amendment')""", (pid,))
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,%s,1939,'48 The Ropewalk',15,'Kitchen maid',160,'Single',%s)""",
                    (pid, RW48, SRC48))
        rec = {"first_name": "Elvina", "last_name": "Lowe", "sex": "F", "born_year": 1923,
               "born_date": "1923-12-29", "match_born_year": True,
               "census": [{"census_year": 1939, "property_id": RW48, "address": "48 The Ropewalk",
                           "marital_status": "Single", "age_at_census": 15,
                           "occupation_at_census": "Kitchen maid",
                           "census_household_num": 160, "source": SRC48}],
               "id": pid}
        at = next((i for i, x in enumerate(d['people'])
                   if any(ce.get('census_household_num') == 160 for ce in x['census'])), None)
        d['people'].insert(at + 1 if at is not None else len(d['people']), rec)
        print(f"        entered as #{pid}")

    json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
    c.commit()
    print("\n  committed")


if __name__ == '__main__':
    main()
