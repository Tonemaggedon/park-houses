# -*- coding: utf-8 -*-
"""House names supplied by A. Hagues from Dougal de Havilland's map of the Park.

Matched on street and number together, never on name alone - matching on name
alone is what throws up Rock House on Barrack Lane against Rock House on
Peveril Drive, and three different houses called The Cottage.

Where a property already carries a different name, the old one is kept in
prev_house_name rather than overwritten.
"""
import json, sys, re
APPLY = '--apply' in sys.argv

NAMES = [
 ("Lenton Road", "43", "Sedgeley House", None),
 ("Lenton Road", "23", "Rutland House", None),
 ("Castle Grove", "1 Lenton Road", "Hine House", None),
 ("South Road", "1", "William House", None),
 ("South Road", "4", "The South House", None),
 ("Hamilton Drive", "16", "Morisco", None),
 ("Hamilton Drive", "9", "Wisteria House", None),
 ("Hamilton Drive", "1b", "Ivy Nook", None),
 ("Hamilton Drive", "1a", "Ivy Lodge", None),
 ("Cavendish Crescent South", "19", "Amelia House", None),
 ("Cavendish Crescent South", "21", "Albert Villas", None),
 ("Cavendish Crescent South", "23", "Holyrood House", None),
 ("Park Drive", "1", "Parkgate House", None),
 ("Park Drive", "3", "Castle View", None),
 ("Castle Grove", "4a", "Barbican House", None),

 ("Park Valley", "6", "Hollyhurst", None),
 ("Park Valley", "6a", "Stuart Cottage", None),
 ("Park Valley", "1", "Arundel House", None),
 ("Tattershall Drive", "5a", "Palisades", None),
 ("Pelham Crescent", "1", "Thornleigh", "a day and boarding school"),
 ("Cavendish Crescent North", "16a", "Crescent Lodge", None),
 ("Cavendish Crescent North", "14", "Park House", None),
 ("Cavendish Crescent North", "12", "Hazelwood", None),
 ("Cavendish Crescent North", "10", "Charnwood", None),
 ("Lenton Avenue", "33", "Newlands", None),
 ("Lenton Avenue", "31", "Greylands", None),
 ("Lenton Avenue", "25", "Arlington House", "formerly Homedale"),
 ("Lenton Avenue", "17", "Dundee House", None),
 ("Lenton Avenue", "3", "Cedar House", None),
 ("Lenton Avenue", "1", "Glenelg Villa", None),
]


def numbers(p):
    """Every house number a property's address claims, plus its whole address."""
    out = {str(p.get('address') or '').strip().lower()}
    if p.get('no'): out.add(str(p['no']).strip().lower())
    a = str(p.get('address') or '')
    for m in re.findall(r'\b(\d+[a-z]?)\b', a.lower()):
        out.add(m)
    return out


def main():
    P = json.load(open('data/all_props.json'))
    hits, misses, conflicts = [], [], []
    for street, no, name, extra in NAMES:
        cands = [p for p in P if str(p.get('street') or '').strip().lower() == street.lower()
                 and no.lower() in numbers(p)]
        if len(cands) != 1:
            misses.append((street, no, name, [c['id'] for c in cands]))
            continue
        p = cands[0]
        cur = (p.get('name') or '').strip()
        if cur and cur.lower() != name.lower():
            conflicts.append((street, no, name, p['id'], p.get('address'), cur))
        hits.append((p, name, extra, cur))
    print(f"=== matched on street and number: {len(hits)} ===")
    for p, name, extra, cur in hits:
        flag = f"   (already named {cur!r} - that name will be kept as a former name)" if cur and cur.lower() != name.lower() else ""
        print(f"  #{p['id']:<5} {(p.get('address') or ''):<44} -> {name}{(' (' + extra + ')') if extra else ''}{flag}")
    print(f"\n=== no single match: {len(misses)} ===")
    for street, no, name, ids in misses:
        print(f"  {no} {street:<26} {name:<22} candidates {ids}")
    print(f"\n=== name conflicts to look at: {len(conflicts)} ===")
    for street, no, name, pid, addr, cur in conflicts:
        print(f"  #{pid} {addr} is named {cur!r}, the map says {name!r}")
    if not APPLY:
        print("\n  preview only - pass --apply"); return
    for p, name, extra, cur in hits:
        if cur and cur.lower() != name.lower():
            prev = [x.strip() for x in str(p.get('prev_house_name') or '').split('\n') if x.strip()]
            if cur not in prev: prev.append(cur)
            p['prev_house_name'] = '\n'.join(prev)
        p['name'] = name
        p['house_name'] = name
        addr = str(p.get('address') or '')
        if not addr.lower().startswith(name.lower()):
            p['address'] = f"{name}, {addr}"
        if extra:
            p['history'] = (p.get('history') or '') + (
                f"\n\n**Named {name} on Dougal de Havilland's map of the Park** - {extra}.")
        else:
            p['history'] = (p.get('history') or '') + (
                f"\n\n**Named {name} on Dougal de Havilland's map of the Park.**")
    json.dump(P, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"\n  {len(hits)} houses named")


if __name__ == '__main__':
    main()
