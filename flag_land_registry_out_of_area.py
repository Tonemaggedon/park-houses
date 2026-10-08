# -*- coding: utf-8 -*-
"""Forty-five rows in the Land Registry harvest are not in The Park.

The harvest was taken by street name and town NOTTINGHAM. Several of the
record's 44 street names exist elsewhere in the same postal town, so the query
brought back houses from Hucknall, Beeston, West Bridgford, Long Eaton and
Kirkby. Nothing marked them, and three had already been written into research
questions as names in The Park wanting a house.

The Park is NG7 1xx; Park Row, Park Terrace and The Ropewalk are NG1 5 and
NG1 6. Everything else is flagged rather than deleted, so the harvest stays
whole and the reason is recorded against each row.
"""
import json
d = json.load(open('data/land_registry_names.json'))
n = 0
for r in d['addresses']:
    pc = str(r.get('postcode') or '')
    inpark = pc.startswith('NG7 1') or pc.startswith('NG1 5') or pc.startswith('NG1 6')
    r['in_the_park'] = bool(inpark)
    if not inpark:
        n += 1
        r['out_of_area_note'] = (
            "Not in The Park. Caught by the street name in another part of the NOTTINGHAM postal "
            "town." if pc else "No postcode in the price paid data, so not placeable.")
d['note'] = d['note'].rstrip() + (
    " **Forty-five of these rows are not in The Park.** The query matched on street name and town, "
    "and several of the record's street names exist elsewhere in the same postal town - Derby Road "
    "runs out to Kirkby and Long Eaton, and there are a Park Drive in Hucknall, a North Road in "
    "West Bridgford, a South Road in Beeston, a Hardwick Road in Sherwood and a Park Terrace at "
    "NG12. Each row now carries `in_the_park`; The Park is NG7 1xx, and Park Row, Park Terrace and "
    "The Ropewalk are NG1 5 and NG1 6.")
d['count_in_the_park'] = sum(1 for r in d['addresses'] if r['in_the_park'])
json.dump(d, open('data/land_registry_names.json', 'w'), indent=1, ensure_ascii=False)
print(f"  {n} rows flagged out of area; {d['count_in_the_park']} of {d['count']} are in The Park")
