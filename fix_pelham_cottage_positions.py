# -*- coding: utf-8 -*-
"""The three Pelham Cottages were placed by arithmetic. OpenStreetMap has the buildings.

Created from the 1939 Register, 1, 2 and 3 Pelham Cottage were given positions
eight ten-thousandths of a degree apart in a straight line - the signature of a
generated point, and exactly the fault
[[a-guessed-position-is-indistinguishable-from-a-surveyed-one]] was written
about this morning. To its credit the record said so, in the description:
*the position is read off the map to about twenty metres and wants dragging
into place*. Neither cottage has a row in `coords`, so the file's numbers are
what the site draws.

OpenStreetMap holds all three as buildings on a street of their own -
**Pelham Cottages**, parent street Pelham Crescent, postcode NG7 1AQ - and the
map A. Hagues supplied shows the same terrace in the same order, west to east,
with Journey's End beyond the third.
"""
import os, sys, json, math
apply = '--apply' in sys.argv
OSM = {449: (52.9517934, -1.1684539), 450: (52.9517746, -1.1683096), 451: (52.9517467, -1.1681983)}
SRC = ("Position: OpenStreetMap building footprint, where the house is held on a street of its "
       "own - Pelham Cottages, parent street Pelham Crescent, postcode NG7 1AQ. Corroborated by "
       "the map A. Hagues supplied, which shows the three in the same order west to east. It "
       "replaces an arithmetical point: three positions set an equal distance apart in a straight "
       "line when the properties were created from the 1939 Register.")
d = json.load(open('data/all_props.json'))
byid = {p['id']: p for p in d}
for pid, (la, ln) in OSM.items():
    p = byid[pid]
    m = math.hypot((p['lat'] - la) * 111320, (p['lng'] - ln) * 111320 * math.cos(math.radians(la)))
    print(f"  #{pid} {p['address']:<34} moves {m:5.1f} m")
    if not apply:
        continue
    p['lat'], p['lng'] = la, ln
    s = p.get('sources')
    if isinstance(s, list):
        p['sources'] = s + [SRC]
    elif isinstance(s, dict):
        s['position'] = SRC
    else:
        p['sources'] = [SRC]
    p['desc'] = (p.get('desc') or '').replace(
        " **The position is read off the map to about twenty metres and wants dragging into place.**",
        " The position is now the building's own footprint.")
if apply:
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print("  written")
else:
    print("\n  preview only - pass --apply")
