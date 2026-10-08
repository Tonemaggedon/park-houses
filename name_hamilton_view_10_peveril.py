# -*- coding: utf-8 -*-
"""Hamilton View is 10 Peveril Drive, and Harlech House is its older name.

A. Hagues found it on a property price site that carries a photograph and a
Street View alongside the sale record, so the name, the number and the building
are tied together in one place.

That closes the Peveril Drive half of the Land Registry list: Rock Cottage is
3a, Hamilton View is 10.
"""
import sys, json
apply = '--apply' in sys.argv
d = json.load(open('data/all_props.json'))
p = [x for x in d if x['id'] == 295][0]
print(f"  #295 {p['address']}  house_name={p.get('house_name')!r}  prev={p.get('prev_house_name')!r}")
if apply:
    p['house_name'] = 'Hamilton View'
    p['name'] = 'Hamilton View'
    p['address'] = 'Hamilton View, 10 Peveril Drive'
    p['prev_house_name'] = 'Harlech House'
    s = p.get('sources')
    note = ("Name: Hamilton View, with Harlech House as the older name, found by A. Hagues on a "
            "property price record for Hamilton View, Peveril Drive, NG7 1DE, which carries a "
            "photograph and a street view of the building alongside the sale.")
    if isinstance(s, dict):
        s['name'] = note
    elif isinstance(s, list):
        p['sources'] = s + [note]
    else:
        p['sources'] = [note]
    p['history'] = (p.get('history') or '').rstrip() + (
        "\n\n**The house is Hamilton View, and was Harlech House before that.** The record held "
        "the number alone. Hamilton View is a name that describes a position, and this is the "
        "house it describes: 10 Peveril Drive looks across at Hamilton Drive.")
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"  -> {p['address']}, formerly {p['prev_house_name']}")
else:
    print("\n  preview only - pass --apply")
