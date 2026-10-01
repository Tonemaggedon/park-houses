# -*- coding: utf-8 -*-
"""Two things A. Hagues has settled: East Lodge, and 15 Park Terrace.

The Lodge on Park Terrace folds into **East Lodge, Park Row (#413)** - the
reading the record had argued for and would not assert on its own: the right
order in the book, eight metres away on the ground, listed with Tower House,
and no household of its own this round.

And schedule 150 is **15 Park Terrace**, not the 38 the back-of-book amendment
sheet gives. The enumerator's own column reads 15, and the walk agrees - 148 is
13 and 151 is 16.

  railway run python3 fold_lodge_and_file_15pt.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'
LODGE, EAST, PT15 = 441, 413, 254


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    d = json.load(open(DATA))
    props = json.load(open('data/all_props.json'))

    cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                     JOIN people p ON p.id=c.person_id WHERE c.property_id=%s""", (LODGE,))
    for cid, fn, ln in cur.fetchall():
        print(f"  row {cid} {fn} {ln}: The Lodge, Park Terrace -> East Lodge, Park Row")
    cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                     JOIN people p ON p.id=c.person_id
                    WHERE c.census_year=1939 AND c.census_household_num=150""")
    pt = cur.fetchall()
    for cid, fn, ln in pt:
        print(f"  row {cid} {fn} {ln}: unfiled -> 15 Park Terrace")
    if not APPLY:
        print("\n  Nothing written. Add --apply.")
        return

    cur.execute("""UPDATE census_entries SET property_id=%s, address='East Lodge, Park Row',
                     source = replace(source,
                       'the house is The Lodge, Park Terrace, as the page writes it, which the '
                       'record now holds under that name - it may be East Lodge on Park Row and '
                       'is not named so here',
                       'the page writes it The Lodge, Park Terrace; A. Hagues settles it as East '
                       'Lodge on Park Row, which stands beside Tower House and is listed with it. '
                       'The same page writes Tower House as Park Terrace too')
                    WHERE property_id=%s""", (EAST, LODGE))
    cur.execute("""UPDATE census_entries SET property_id=%s, address='15 Park Terrace',
                     unresolved_address=NULL,
                     source = replace(source,
                       'the house is not identified in the record, so this row is left unfiled',
                       'the house is 15 Park Terrace - the enumerator''s own column reads 15, the '
                       'walk agrees (schedule 148 is 13 and 151 is 16), and A. Hagues settles it '
                       'against the back-of-book amendment sheet, which gives 38')
                    WHERE census_year=1939 AND census_household_num=150""", (PT15,))
    cur.execute("""UPDATE census_entries SET source = source ||
                     '; the house is still not identified: the walk puts it between 13 Park '
                     'Terrace at schedule 148 and 16 at schedule 151, and 14 Park Terrace is '
                     'taken by schedule 204, so it is most likely a second household at 15'
                    WHERE census_year=1939 AND census_household_num=149
                      AND source NOT LIKE '%%the walk puts it between%%'""")

    for x in d['people']:
        for ce in x['census']:
            if ce.get('property_id') == LODGE:
                ce['property_id'] = EAST
                ce['address'] = 'East Lodge, Park Row'
            if ce.get('census_year') == 1939 and ce.get('census_household_num') == 150:
                ce.pop('unresolved_address', None)
                ce['property_id'] = PT15
                ce['address'] = '15 Park Terrace'
                ce['source'] = ce['source'].replace(
                    'the house is not identified in the record, so this row is left unfiled',
                    "the house is 15 Park Terrace - the enumerator's own column reads 15 and the "
                    "walk agrees, against the back-of-book amendment sheet, which gives 38")
    props = [p for p in props if p['id'] != LODGE]
    for p in props:
        if p['id'] == EAST and 'Bert Geddes' not in (p.get('history') or ''):
            p['history'] = (p.get('history') or '') + (
                " In 1939 the register writes this house **The Lodge, Park Terrace** and it holds "
                "**Bert Geddes**, 47, chauffeur, with **Hannah Geddes**, 48. The enumerator takes "
                "the General Hospital's lodge, then this house, then **Tower House** - which the "
                "same page also calls Park Terrace, and which is 53 Park Row, next door. "
                "A. Hagues settles the two as one.")
    json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
    c.commit()
    print("\n  committed")


if __name__ == '__main__':
    main()
