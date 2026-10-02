# -*- coding: utf-8 -*-
"""One house, one spelling - everywhere the record writes a house name.

A house name is written in more places than anybody can hold in their head: the
property's `name`, its `house_name`, its `address`, its `prev_house_name`, the
address on every census row filed to it, and the unresolved address on every row
that is not. When those drift apart the house looks like two houses, and a
search for one of them finds half its people.

This gathers every form of every name and groups the ones that are nearly the
same, so the odd spelling shows up beside the right one.

  railway run python3 tools_house_name_consistency.py
"""
import os, json, re, difflib, collections, psycopg2

NOISE = re.compile(r'^(the|a)\s+', re.I)


def key(s):
    """What two spellings of one name have in common."""
    s = NOISE.sub('', (s or '').strip().lower())
    return re.sub(r'[^a-z]', '', s)


c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
props = json.load(open('data/all_props.json'))

# every house-name string the record holds, and where it holds it
forms = collections.defaultdict(set)      # name -> {where}
owner = {}                                 # name -> property id
for p in props:
    for field in ('name', 'house_name', 'prev_house_name'):
        for nm in (p.get(field) or '').split('\n'):
            nm = nm.strip()
            if nm and not nm[0].isdigit():
                forms[nm].add(f"#{p['id']} {field}")
                owner.setdefault(nm, p['id'])
    a = p.get('address') or ''
    if a and ',' in a and not a[0].isdigit():
        nm = a.split(',')[0].strip()
        if nm and not nm[0].isdigit():
            forms[nm].add(f"#{p['id']} address")
            owner.setdefault(nm, p['id'])

cur.execute("""SELECT DISTINCT COALESCE(address, unresolved_address) FROM census_entries
                WHERE COALESCE(address, unresolved_address) IS NOT NULL""")
for (a,) in cur.fetchall():
    a = a.strip()
    if not a or a[0].isdigit():
        continue
    nm = a.split(',')[0].strip()
    if nm and not nm[0].isdigit() and len(nm) > 3:
        forms[nm].add('census')

# group the near-identical
groups = collections.defaultdict(list)
for nm in forms:
    groups[key(nm)].append(nm)

print("  Names written more than one way in the record\n")
shown = 0
for k, names in sorted(groups.items()):
    if len(names) > 1:
        shown += 1
        print(f"  {' | '.join(sorted(names))}")
        for nm in sorted(names):
            print(f"      {nm:<34} {', '.join(sorted(forms[nm]))}")

# and the near misses that differ by a letter or two
seen = set()
near = []
keys = sorted(groups)
for i, a in enumerate(keys):
    for b in keys[i + 1:]:
        if abs(len(a) - len(b)) > 2 or (a, b) in seen:
            continue
        if len(a) > 5 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.88:
            seen.add((a, b))
            near.append((groups[a], groups[b]))
if near:
    print(f"\n  Names a letter or two apart - one house or two?\n")
    for ga, gb in near:
        pa, pb = owner.get(ga[0]), owner.get(gb[0])
        print(f"  {ga[0]} (#{pa})   vs   {gb[0]} (#{pb})")

print(f"\n  {shown} names written more than one way; {len(near)} pairs a letter or two apart")
