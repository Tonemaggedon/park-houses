# -*- coding: utf-8 -*-
"""White Gates is 8 Huntingdon Drive and Ravenswood is 6, as A. Hagues settles them.

The 1939 run named the street's empty houses for the first time and left two
names between two numbers. This puts them where they belong, folds the
Ravenswood property made this morning into the house it turns out to be, and
takes the name off number 7, which the record had wrong.

  railway run python3 place_huntingdon_names.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
RAVEN_NEW, SIX, EIGHT, SEVEN = 440, 148, 150, 149
ADDR = "Ravenswood, 6 Huntingdon Drive"

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                 JOIN people p ON p.id = c.person_id WHERE c.property_id=%s""", (RAVEN_NEW,))
rows = cur.fetchall()
for cid, fn, ln in rows:
    print(f"  row {cid} {fn} {ln}: #{RAVEN_NEW} -> #{SIX} {ADDR}")
print(f"  #{RAVEN_NEW} removed; White Gates goes on #{EIGHT}; the name comes off #{SEVEN}")

if APPLY:
    cur.execute("""UPDATE census_entries SET property_id=%s, address=%s,
                     source = replace(source,
                       'the house is Ravenswood, Huntingdon Drive, which the record now holds',
                       'the house is 6 Huntingdon Drive - A. Hagues settles Ravenswood here and '
                       'White Gates at 8, which the register takes empty the schedule before. '
                       'The record had carried Ravenswood as a former name of number 7, and 7 has '
                       'its own schedule that night, ticked and left blank')
                   WHERE property_id=%s""", (SIX, ADDR, RAVEN_NEW))
    cur.execute("UPDATE property_residents SET property_id=%s WHERE property_id=%s", (SIX, RAVEN_NEW))
    cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes)
       SELECT %s, 1939, 'White Gates, 8 Huntingdon Drive, schedule 88 - the Register marks it '
              'empty, and the index writes the name Whale Yates. A. Hagues reads it White Gates '
              'and settles the house. 1939 Register, ED letter code RMGC.'
        WHERE NOT EXISTS (SELECT 1 FROM census_unoccupied WHERE property_id=%s AND census_year=1939)""",
                (EIGHT, EIGHT))
    c.commit()

    props = [p for p in json.load(open('data/all_props.json')) if p['id'] != RAVEN_NEW]
    for p in props:
        if p['id'] == SIX:
            p['address'] = ADDR
            p['name'] = p['house_name'] = 'Ravenswood'
            p['prev_house_name'] = 'Avoca'
            p['history'] = ((p.get('history') or '') + (
                "\n\n**Ravenswood is this house.** The 1939 Register takes it at schedule 89 and it "
                "holds **Fred Noble Smith**, 56, civil engineer in the water department, with "
                "**Violet Amy B Smith**. The record had carried Ravenswood as a former name of "
                "**number 7** - one house out, which is the commonest kind of error there is, and "
                "the register rules it out by giving 7 its own schedule that night, ticked and "
                "left blank.")).strip()
        if p['id'] == EIGHT:
            p['address'] = 'White Gates, 8 Huntingdon Drive'
            p['name'] = p['house_name'] = 'White Gates'
            p['history'] = ((p.get('history') or '') + (
                "\n\n**White Gates is this house.** It had no recorded name of any kind until the "
                "1939 Register named the street's empty houses - schedule 88, between Brampton at "
                "9 and Ravenswood at 6, marked empty. The index writes it *Whale Yates*; "
                "A. Hagues reads it White Gates.")).strip()
        if p['id'] == SEVEN:
            p['prev_house_name'] = ''
            p['history'] = ((p.get('history') or '') + (
                "\n\n**This house is not Ravenswood.** The record carried that name here and it "
                "belongs to **6 Huntingdon Drive**, next door. The 1939 Register settles it: 7 has "
                "its own schedule, 90, ticked and left blank, on the night Ravenswood holds a "
                "household.")).strip()
    json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)

    d = json.load(open('data/people_1939_rmgc_the_park.json'))
    for x in d['people']:
        for ce in x.get('census', []):
            if ce.get('property_id') == RAVEN_NEW:
                ce['property_id'] = SIX
                ce['address'] = ADDR
    json.dump(d, open('data/people_1939_rmgc_the_park.json', 'w'), indent=1, ensure_ascii=False)
    print("\n  committed")
else:
    print("\n  Nothing written. Add --apply.")
