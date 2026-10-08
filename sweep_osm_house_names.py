# -*- coding: utf-8 -*-
"""Ask OpenStreetMap for every named building in The Park, and match it against the record.

**The match has to look inside the address.** Many properties carry their name only in
`address` - *Castle Bank, 5 Lenton Road* - with `house_name` empty, so a match on the
name fields alone reports them as names the record has not got. It also has to allow a
trailing s: Albert Villa and Albert Villas are one house.

This replaces the hand-read list taken off six map screenshots. One Overpass
query round the middle of the estate returns every building carrying an
addr:housename, with its street, number and position, which is the sweep
[[osm-house-names-are-a-source-the-record-has-not-mined]] asked for.

A name in use now is a lead, not a record: under this record's rule none
becomes a property until a census household is found at it. And a name that
matches is not automatically the same house - two houses can carry one name in
different eras, so the match is reported with its street beside it.
"""
import json, re, math
STREETS = set("""Albury Square Alexander Road Barrack Lane Castle Grove Cavendish Crescent North
Cavendish Crescent South Cavendish Road East Cavendish Road West Clare Valley Clifton Terrace
Clumber Crescent North Clumber Crescent South Clumber Road East Clumber Road West Duke William Mount
Fiennes Crescent Fishpond Drive Hamilton Drive Hardwick Road Hermitage Walk Holles Crescent
Hope Drive Huntingdon Drive Kenilworth Road Lenton Avenue Lenton Road Lincoln Circus Maxtoke Road
Newcastle Circus Newcastle Drive Newcastle Terrace North Road Ogle Drive Park Drive Park Ravine
Park Terrace Park Valley Pelham Cottages Pelham Crescent Peveril Drive South Road Tattershall Drive
Tennis Drive The Ropewalk Tunnel Road Western Terrace""".split('\n'))
STREETS = {s.strip() for line in STREETS for s in [line] if s.strip()}
STREETS = set(' '.join(STREETS.__iter__()).split('  ')) if False else {
 l.strip() for l in """Albury Square|Alexander Road|Barrack Lane|Castle Grove|Cavendish Crescent North|
Cavendish Crescent South|Cavendish Road East|Cavendish Road West|Clare Valley|Clifton Terrace|
Clumber Crescent North|Clumber Crescent South|Clumber Road East|Clumber Road West|Duke William Mount|
Fiennes Crescent|Fishpond Drive|Hamilton Drive|Hardwick Road|Hermitage Walk|Holles Crescent|
Hope Drive|Huntingdon Drive|Kenilworth Road|Lenton Avenue|Lenton Road|Lincoln Circus|Maxtoke Road|
Newcastle Circus|Newcastle Drive|Newcastle Terrace|North Road|Ogle Drive|Park Drive|Park Ravine|
Park Terrace|Park Valley|Pelham Cottages|Pelham Crescent|Peveril Drive|South Road|Tattershall Drive|
Tennis Drive|The Ropewalk|Tunnel Road|Western Terrace""".replace('\n','').split('|')}

osm = json.load(open('/tmp/park_osm.json'))
seen, rows = set(), []
for e in osm['elements']:
    t = e.get('tags', {})
    nm, st = t.get('addr:housename', '').strip(), t.get('addr:street', '').strip()
    if not nm or st not in STREETS:
        continue
    no = (t.get('addr:housenumber') or t.get('addr:flats') or '').strip()
    k = (nm.lower(), st.lower(), no.lower())
    if k in seen: continue
    seen.add(k)
    c = e.get('center') or {'lat': e.get('lat'), 'lon': e.get('lon')}
    rows.append({"name": nm, "number": no, "street": st,
                 "lat": c.get('lat'), "lng": c.get('lon'),
                 "postcode": t.get('addr:postcode', '')})

P = json.load(open('data/all_props.json'))
def norm(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
held, leads = [], []
for r in rows:
    n = norm(r['name'])
    match = None
    for p in P:
        names = {norm(x) for k in ('name', 'house_name', 'prev_house_name', 'address')
                 for x in str(p.get(k) or '').split('\n') if x.strip()}
        # the address carries the name for many properties, so match the name inside it too,
        # and let a trailing s differ - Albert Villa and Albert Villas are one house
        hit = (n in names or n+'s' in names or n.rstrip('s') in names
               or any(n in a or n+'s' in a for a in names))
        if hit:
            match = p
            if norm(p.get('street')) == norm(r['street']):
                break
    if match:
        r['property_id'] = match['id']
        r['property'] = match.get('address')
        r['same_street'] = norm(match.get('street')) == norm(r['street'])
        held.append(r)
    else:
        leads.append(r)
out = {"note": ("Every building in The Park that OpenStreetMap gives a house name, from one Overpass "
 "query, matched against the property list. A name in use now is a LEAD, not a record: under this "
 "record's rule none becomes a property until a census household is found at it. And a name that "
 "matches is not automatically the same house - see "
 "[[two-houses-can-share-a-name-in-different-eras]] - so `same_street` is given with each match."),
 "source": "OpenStreetMap via the Overpass API, buildings and nodes carrying addr:housename",
 "read_on": "2026-10-08",
 "counts": {"named_buildings_in_the_park": len(rows), "matched": len(held), "leads": len(leads)},
 "leads": sorted(leads, key=lambda r: (r['street'], r['number'], r['name'])),
 "matched": sorted(held, key=lambda r: (r['street'], r['number'], r['name']))}
json.dump(out, open('data/map_osm_unmatched.json', 'w'), indent=1, ensure_ascii=False)
print(f"  {len(rows)} named buildings on Park streets | {len(held)} matched | {len(leads)} leads")
for r in out['leads']:
    print(f"    {r['street'][:26]:<28} {r['number'][:12]:<14} {r['name']}")
print("\n  matched but on a DIFFERENT street in the record:")
for r in out['matched']:
    if not r['same_street']:
        print(f"    {r['name']:<24} map: {r['street']:<26} record: {r['property']}")
