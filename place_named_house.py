# -*- coding: utf-8 -*-
"""A house the 1939 Register names, which the property list has not got.

Eighteen houses in the 1939 round carry a name and no number, and the record
could only hold their households unfiled. Where A. Hagues confirms the house,
this makes the property and files the schedule into it - in the database and in
the import file, bound by person id, so a full import cannot undo it.

The position is provisional in every case: it follows the enumerator's run and
nothing else. Say so in the history, and put it on the walking list.

  railway run python3 place_named_house.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'

# property id, name, street, schedule, provisional position, why that position
RUN = ("the enumerator takes 1, 3 and 5 Tattershall Drive in order at schedules 30, 31 and 32 "
       "and runs straight on through Lynwood, St Ives and Elmsdale at 33, 34 and 35 before the "
       "book leaves the street altogether - so this is house {n} of that walk, past number 5")

HOUSES = [
 (433, "Lynwood",  "Tattershall Drive", 33, 52.95090, -1.15990, RUN.format(n="four")),
 (434, "St Ives",  "Tattershall Drive", 34, 52.95105, -1.15995, RUN.format(n="five")),
 (435, "Elmsdale", "Tattershall Drive", 35, 52.95120, -1.16000, RUN.format(n="six")),
 (436, "The Lodge", "Tattershall Drive", 38, 52.95345, -1.16570,
  "schedule 38 sits between 2 Albury Square and 10 Cavendish Crescent North, which puts this "
  "house at the **north** end of the drive and nowhere near the 1 to 5 run. Carnoustie Lodge "
  "stands there too, but it is separately enumerated at schedule 8, so this is a second lodge "
  "at that end"),
 (437, "Cedar Lodge", "Tunnel Road", 56, 52.95205, -1.16455,
  "schedule 56 comes immediately before The Cottage on the same street, and the book then runs "
  "on to Allendale and out to Penrhyn Cottage on Cavendish Road East - so Cedar Lodge is the "
  "house west of The Cottage, at the far end of the walk"),
 (438, "Allendale", "Tunnel Road", 58, 52.95235, -1.16380,
  "schedule 58 falls between The Cottage and Penrhyn Cottage on Cavendish Road East, so "
  "Allendale stands east of The Cottage, between it and Gees Lodge"),
 (439, "Brampton", "Huntingdon Drive", 87, 52.95088, -1.15872,
  "the enumerator comes down Huntingdon Drive - The Cottage at 14 is schedule 85, then Brampton, "
  "then Ravenswood, and then 5, 4, 3 and 2 in order - so Brampton stands between number 14 and "
  "the 6 to 10 run. The record's Huntingdon Drive has no 11, 12 or 13"),
 (440, "Ravenswood", "Huntingdon Drive", 89, 52.95095, -1.15900,
  "the enumerator comes down Huntingdon Drive - The Cottage at 14, then Brampton, then "
  "Ravenswood, then 5, 4, 3 and 2 in order - so Ravenswood is the next door below Brampton and "
  "the last before the numbered run begins"),
]


def household(cur, sched):
    cur.execute("""SELECT c.id, p.first_name, p.last_name, c.age_at_census,
                          c.occupation_at_census, c.marital_status
                     FROM census_entries c JOIN people p ON p.id = c.person_id
                    WHERE c.census_year = 1939 AND c.census_household_num = %s
                    ORDER BY c.id""", (sched,))
    return cur.fetchall()


def history(name, street, rows, why):
    body = (f"**{name} is named by the 1939 Register and by nothing else in the record.** "
            f"Its household on 29 September 1939:\n\n| | |\n|---|---|\n")
    for _, fn, ln, age, occ, mar in rows:
        age_s = f", {age}" if age is not None else ""
        body += f"| **{fn} {ln}**{age_s} | {occ or 'no trade given'} |\n"
    body += (f"\n**The position is provisional.** {why.capitalize()}. Nothing in the record fixes "
             f"it. See [[house-names-live-in-prose]].")
    if street == 'Tattershall Drive':
        body = body.replace("See [[house-names-live-in-prose]].",
                            "The house may well be one the list holds under a number: Tattershall "
                            "Drive runs 1 to 5 and then jumps to 17a, which leaves exactly the "
                            "room the three named houses would need. See "
                            "[[named-houses-on-tattershall-drive-and-where-they-sit]].")
    return body


def main():
    props = json.load(open('data/all_props.json'))
    have = {p['id'] for p in props}
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    d = json.load(open(DATA))
    by_name = {(x['first_name'], x['last_name']): x for x in d['people']}

    for pid, name, street, sched, lat, lng, why in HOUSES:
        rows = household(cur, sched)
        if not rows:
            print(f"  {name}: schedule {sched} holds nobody"); continue
        addr = f"{name}, {street}"
        print(f"  #{pid} {addr} - schedule {sched}, {len(rows)} people")
        for _, fn, ln, age, occ, _m in rows:
            print(f"        {fn} {ln}, {age} - {occ}")
        if not APPLY:
            continue
        if pid not in have:
            props.append({"id": pid, "name": name, "street": street, "no": "",
                          "address": addr, "desc": "", "history": history(name, street, rows, why),
                          "date_built": "", "listed": "No", "census_only": True,
                          "house_name": name, "lat": lat, "lng": lng})
        cur.execute("""UPDATE census_entries
                          SET property_id = %s, unresolved_address = NULL, address = %s,
                              source = replace(source,
                                'the house is not identified in the record, so this row is left unfiled',
                                'the house is ' || %s || ', which the record now holds')
                        WHERE census_year = 1939 AND census_household_num = %s""",
                    (pid, addr, addr, sched))
        for _, fn, ln, *_ in rows:                      # and in the import file
            rec = by_name.get((fn, ln))
            if not rec:
                print(f"        ! {fn} {ln} not found in {DATA}"); continue
            for ce in rec['census']:
                if ce.get('census_household_num') == sched:
                    ce.pop('unresolved_address', None)
                    ce['property_id'] = pid
                    ce['address'] = addr
                    ce['source'] = ce['source'].replace(
                        'the house is not identified in the record, so this row is left unfiled',
                        f'the house is {addr}, which the record now holds')
            cur.execute("SELECT id FROM people WHERE first_name=%s AND last_name=%s", (fn, ln))
            got = cur.fetchall()
            if len(got) == 1:
                rec['id'] = got[0][0]

    if APPLY:
        props.sort(key=lambda p: p['id'])
        json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
        json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
        c.commit()
        print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
