# -*- coding: utf-8 -*-
"""Parkgate House is 1 Peveril Drive. The record had it on 1 Park Drive.

A. Hagues settled it outright. The name came into the record from a list of
house names he gave earlier in the week, read as Park Drive, and the residents'
association's own addresses put it on Peveril Drive - which is what made the
matcher refuse to apply it and raise the pair instead.

**Only the name moves.** Both houses have households of their own under their own
numbers - #232 across five rounds as 1 Park Drive, #289 in 1911 and 1939 as 1
Peveril Drive - and every one of those stays exactly where it is. This is a name
on the wrong door, not people in the wrong house.
"""
import json, sys
apply = '--apply' in sys.argv
d = json.load(open('data/all_props.json'))
P = {p['id']: p for p in d}
old, new = P[232], P[289]
print(f"  #232 {old['address']}  -> loses the name, keeps its five rounds")
print(f"  #289 {new['address']}  -> becomes Parkgate House")
if not apply:
    print("\n  preview only - pass --apply"); sys.exit()

NOTE = ("Name: Parkgate House, settled by A. Hagues. The record carried it on 1 Park Drive; "
        "the Nottingham Park Residents' Association's own addresses put it here, and he "
        "confirms it. Only the name moved - both houses keep the households filed under their "
        "own numbers.")
old['name'] = ''
old['house_name'] = None
old['address'] = '1 Park Drive'
old['history'] = (old.get('history') or '').rstrip() + (
    "\n\n**The record called this Parkgate House until 11 October 2026.** It is not: "
    "Parkgate House is 1 Peveril Drive, which A. Hagues has confirmed. The households below "
    "were always filed under the number and are unaffected.")

new['name'] = 'Parkgate House'
new['house_name'] = 'Parkgate House'
new['address'] = 'Parkgate House, 1 Peveril Drive'
s = new.get('sources')
if isinstance(s, dict):   s['name'] = NOTE
elif isinstance(s, list): new['sources'] = s + [NOTE]
else:                     new['sources'] = {'name': NOTE}
json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
print("\n  moved")
