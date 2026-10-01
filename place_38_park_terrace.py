# -*- coding: utf-8 -*-
"""38 Park Terrace, which the enumerator's own column insists on.

Park Terrace runs 1 to 20 in the record and the 1939 page writes **38** for
schedule 149, between 13 at schedule 148 and 15 at schedule 150. A. Hagues has
read the column: it goes 12, 13, **38**, 15. So the number is on the page and
not a transcription fault, and the house stands where 14 would be - except that
14 Park Terrace is separately enumerated at schedule 204.

  railway run python3 place_38_park_terrace.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED = 442, 149


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT c.id, p.first_name, p.last_name, c.age_at_census, c.occupation_at_census
                     FROM census_entries c JOIN people p ON p.id = c.person_id
                    WHERE c.census_year = 1939 AND c.census_household_num = %s ORDER BY c.id""",
                (SCHED,))
    rows = cur.fetchall()
    for cid, fn, ln, age, occ in rows:
        print(f"  row {cid} {fn} {ln}, {age} - {occ}  ->  38 Park Terrace")
    if not APPLY:
        print("\n  Nothing written. Add --apply.")
        return

    props = json.load(open('data/all_props.json'))
    if not any(p['id'] == PROP for p in props):
        props.append({
          "id": PROP, "name": "", "street": "Park Terrace", "no": "38",
          "address": "38 Park Terrace", "desc": "",
          "history": "**A number Park Terrace has not got anywhere else.** The street runs 1 to 20 "
                     "in the record, and the 1939 Register writes **38** for schedule 149. "
                     "A. Hagues has read the enumerator's column along the run: it goes 12, 13, "
                     "**38**, 15. The number is on the page.\n\n"
                     "It holds **Edwin M Ratcliffe**, 48, commercial engineer, **Audrey "
                     "Ratcliffe**, 32, and **William B Callow**, 53, commercial manager - sub "
                     "numbers 1, 2 and 4, so a fourth person sits behind the closed band.\n\n"
                     "**It stands where 14 would be, and 14 is taken.** 14 Park Terrace is "
                     "separately enumerated at schedule 204, the Lindley household, which also "
                     "shows the register visits Park Terrace twice. So 38 is not a misreading of "
                     "14. See [[park-terrace-has-a-number-38]].\n\n"
                     "**The position is provisional**, set between 13 and 15 because that is "
                     "where the walk puts it.",
          "date_built": "", "listed": "No", "census_only": True,
          "lat": 52.95239, "lng": -1.15869})
        props.sort(key=lambda p: p['id'])
        json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)

    note = ("the house is 38 Park Terrace, which the record now holds - A. Hagues has read the "
            "enumerator's address column along the run, 12, 13, 38, 15, so the number is on the "
            "page. Park Terrace has no other 38, and 14 is taken by schedule 204")
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, unresolved_address=NULL, address='38 Park Terrace',
                          source = regexp_replace(source,
                            '; the house is still not identified.*$', '')
                      WHERE census_year=1939 AND census_household_num=%s""", (PROP, SCHED))
    cur.execute("""UPDATE census_entries SET source = replace(source,
                     'the house is not identified in the record, so this row is left unfiled', %s)
                    WHERE census_year=1939 AND census_household_num=%s""", (note, SCHED))

    d = json.load(open('data/people_1939_rmgc_the_park.json'))
    for _, fn, ln, *_ in rows:
        for x in d['people']:
            if (x['first_name'], x['last_name']) != (fn, ln):
                continue
            cur.execute("SELECT id FROM people WHERE first_name=%s AND last_name=%s", (fn, ln))
            got = cur.fetchall()
            if len(got) == 1:
                x['id'] = got[0][0]
            for ce in x['census']:
                if ce.get('census_household_num') != SCHED:
                    continue
                ce.pop('unresolved_address', None)
                ce['property_id'] = PROP
                ce['address'] = '38 Park Terrace'
                ce['source'] = ce['source'].replace(
                    'the house is not identified in the record, so this row is left unfiled', note)
    json.dump(d, open('data/people_1939_rmgc_the_park.json', 'w'), indent=1, ensure_ascii=False)
    c.commit()
    print("\n  committed")


if __name__ == '__main__':
    main()
