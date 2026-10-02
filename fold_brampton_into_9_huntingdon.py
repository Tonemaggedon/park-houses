# -*- coding: utf-8 -*-
"""Brampton is 9 Huntingdon Drive, and the record held the name all along.

The 1939 Register names a house on Huntingdon Drive that the property list had
not got, read first as *Brankston* and then, from A. Hagues, as **Brampton**. It
was made as its own property this morning. It should not have been: **9
Huntingdon Drive already carried Brampton as a former name**, and A. Hagues
confirms the house. So #439 folds into #151 and the name goes on the front of
the address, where the record puts a house name.

It holds **Leslie Fleetwood Bates**, who had the chair of physics at Nottingham
for twenty-eight years, with Winifred Frances Furze Bates.

  railway run python3 fold_brampton_into_9_huntingdon.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NEW, KEEP = 439, 151
ADDR = "Brampton House, 9 Huntingdon Drive"

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                 JOIN people p ON p.id = c.person_id WHERE c.property_id = %s""", (NEW,))
rows = cur.fetchall()
for cid, fn, ln in rows:
    print(f"  row {cid} {fn} {ln}: #{NEW} -> #{KEEP} {ADDR}")
print(f"  and #{NEW} is removed from the property list")

if APPLY:
    cur.execute("""UPDATE census_entries SET property_id=%s, address=%s,
                     source = replace(source,
                       'the house is Brampton, Huntingdon Drive, which the record now holds',
                       'the house is 9 Huntingdon Drive, which the record already held under the '
                       'name Brampton - A. Hagues settles it, and the 1939 page was read here '
                       'first as Brankston')
                   WHERE property_id=%s""", (KEEP, ADDR, NEW))
    cur.execute("UPDATE property_residents SET property_id=%s WHERE property_id=%s", (KEEP, NEW))
    cur.execute("DELETE FROM census_unoccupied WHERE property_id=%s", (NEW,))
    c.commit()

    props = [p for p in json.load(open('data/all_props.json')) if p['id'] != NEW]
    for p in props:
        if p['id'] == KEEP:
            p['address'] = ADDR
            p['name'] = p['house_name'] = 'Brampton House'
            p['history'] = ((p.get('history') or '') + (
                "\n\n**Brampton House.** The 1939 Register names the house where the property list "
                "had only a number - read on the page as *Brankston*, settled by A. Hagues as "
                "**Brampton**, and already carried here as a former name. It holds **Leslie "
                "Fleetwood Bates**, 42, professor of physics, with **Winifred Frances Furze "
                "Bates**. Bates held the chair of physics at Nottingham for twenty-eight years "
                "and made the place a centre for the study of magnetism.")).strip()
    json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)

    d = json.load(open('data/people_1939_rmgc_the_park.json'))
    for x in d['people']:
        for ce in x.get('census', []):
            if ce.get('property_id') == NEW:
                ce['property_id'] = KEEP
                ce['address'] = ADDR
                ce['source'] = ce['source'].replace(
                    'the house is Brampton, Huntingdon Drive, which the record now holds',
                    'the house is 9 Huntingdon Drive, which the record already held under the '
                    'name Brampton - A. Hagues settles it')
    json.dump(d, open('data/people_1939_rmgc_the_park.json', 'w'), indent=1, ensure_ascii=False)
    print("\n  committed")
else:
    print("\n  Nothing written. Add --apply.")
