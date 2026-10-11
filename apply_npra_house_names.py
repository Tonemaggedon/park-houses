# -*- coding: utf-8 -*-
"""House names from the NPRA membership registry, applied to houses already here.

A. Hagues supplied 104 building names drawn from the residents' association's
own addresses - names only, no members. The instruction was plain: **put them on
properties the record already holds, and create nothing.**

Matching is on street **and** number, because a name is not an identifier here -
four houses carry Rock, three are The Cottage, and two different houses are
called Peveril House on two different streets. And an existing name is never
overwritten: where the record already says something, the new one goes into
`prev_house_name` beside it if it is different, or is left alone if it agrees.
"""
import json, re, sys
apply = '--apply' in sys.argv

NPRA = json.load(open('/tmp/npra.json'))
props = json.load(open('data/all_props.json'))

# "The South House" and "South House" are one name.
def norm(s):     return re.sub(r'^the', '', re.sub(r'[^a-z0-9]', '', (s or '').lower()))
def street(s):   return norm(s).replace('the', '')
def numkey(s):   return (s or '').strip().lower().replace(' ', '')

# Every name a property is already known by, and the numbers it answers to -
# including the ones inside brackets, because "3 Clinton Terrace (131 Derby
# Road)" answers to both.
def names_of(p):
    out = set()
    for k in ('name', 'house_name', 'prev_house_name'):
        for part in str(p.get(k) or '').split('\n'):
            if part.strip(): out.add(norm(part))
    return out
def numbers_of(p):
    out = {numkey(p.get('no'))} - {''}
    for m in re.finditer(r'(\d+[a-z]?)\s*(?:[-–]\s*\d+[a-z]?)?', str(p.get('address') or ''), re.I):
        out.add(numkey(m.group(1)))
    return out

by_street = {}
for p in props:
    by_street.setdefault(street(p.get('street')), []).append(p)

# The spreadsheet says what kind of thing each name is. Most types name the
# building - a flat inside a named building still tells you the building's name -
# but two do not, and they are the two that would do damage.
SKIP_TYPE = {'flat (descriptive name)'}
applied, already, ambiguous, nomatch, no_number = [], [], [], [], []
clashes, skipped, elsew = [], [], []
for row in NPRA:
    nm, no, st = row['name'], row['no'], row['street']
    if (row.get('type') or '') in SKIP_TYPE or (row.get('conf') or '') == 'Low':
        skipped.append((nm, st, row.get('type'), row.get('conf'))); continue
    cands = by_street.get(street(st), [])
    hit = None
    # 1. the record already knows the name on that street
    same_name = [p for p in cands if norm(nm) in names_of(p)]
    if same_name:
        already.append((nm, st, same_name[0])); continue
    # 2. the number on that street
    if no is not None and str(no).strip():
        byno = [p for p in cands if numkey(no) in numbers_of(p)]
        if len(byno) == 1: hit = byno[0]
        elif len(byno) > 1: ambiguous.append((nm, st, byno)); continue
    if hit:
        cur = (hit.get('house_name') or hit.get('name') or '').strip()
        # The record already calls it something else. That is two buildings, or a
        # disagreement, and neither is mine to settle silently.
        if cur and norm(cur) != norm(nm):
            clashes.append((nm, row.get('type'), hit, cur))
        else:
            # The same name already sits on a different street. Two houses can
            # share a name - but "Parkgate House, 1 Park Drive" and "Parkgate
            # House, 1 Peveril Drive" is too neat to take on trust.
            elsewhere = [q for q in props
                         if norm(nm) in names_of(q) and street(q.get('street')) != street(st)]
            if elsewhere:
                elsew.append((nm, st, hit, elsewhere[0]))
            else:
                applied.append((nm, hit))
    elif no is None or not str(no).strip():
        no_number.append((nm, st))
    else:
        nomatch.append((nm, no, st))

print(f"  {len(already):>3} already known to the record")
print(f"  {len(applied):>3} can be applied to a numbered house")
print(f"  {len(no_number):>3} have no number, so nothing to match on")
print(f"  {len(nomatch):>3} have a number the record has not got")
print(f"  {len(ambiguous):>3} ambiguous")
print(f"  {len(clashes):>3} where the record already says something else")
print(f"  {len(skipped):>3} not a building name at all")
print(f"  {len(elsew):>3} where that name is already on another street\n")
if elsew:
    print("  LEFT ALONE - the record has this name on a different street:")
    for nm, st, hit, other in elsew:
        print(f"    {nm}: NPRA says #{hit['id']} {hit.get('address')}, "
              f"record already has #{other['id']} {other.get('address')}")
    print()
if clashes:
    print("  LEFT ALONE - the record has another name for it:")
    for nm, ty, p, cur in clashes:
        print(f"    #{p['id']:<4} {str(p.get('address'))[:38]:<40} record: {cur:<22} NPRA: {nm} ({ty})")
    print()
if skipped:
    print("  NOT A BUILDING NAME:")
    for nm, st, ty, cf in skipped: print(f"    {nm} — {st} ({ty}, {cf} confidence)")
    print()
print("  TO APPLY:")
for nm, p in applied:
    cur = p.get('house_name') or p.get('name') or ''
    print(f"    #{p['id']:<4} {str(p.get('address'))[:40]:<42} {nm}" + (f"   (record says {cur})" if cur else ""))

if not apply:
    print("\n  preview only - pass --apply")
    sys.exit()

byid = {p['id']: p for p in props}
n = 0
for nm, p in applied:
    cur = (p.get('house_name') or '').strip()
    if cur: continue
    p['house_name'] = nm
    if not (p.get('name') or '').strip(): p['name'] = nm
    addr = p.get('address') or ''
    if not addr.lower().startswith(nm.lower()):
        p['address'] = f"{nm}, {addr}"
    s = p.get('sources')
    note = ("Name: from the Nottingham Park Residents' Association membership addresses, "
            "supplied by A. Hagues. A name in use now, so a lead on the house's older name "
            "rather than a source for it.")
    if isinstance(s, dict): s['name'] = note
    elif isinstance(s, list): p['sources'] = s + [note]
    else: p['sources'] = {'name': note}
    n += 1
json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
print(f"\n  {n} properties named")
