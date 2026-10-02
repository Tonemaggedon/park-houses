# -*- coding: utf-8 -*-
"""One house, one address - on the property and on every row filed to it.

A census row carries its own address string, and over eight rounds those strings
drift: *Western House, 30 The Ropewalk* against *30 The Ropewalk*, *Broxtowe
House, Park Terrace* against *Broxtowe House, The Park*, *8 Pelham Terrace (now
31 Newcastle Drive)* against *31 Newcastle Drive*. The house then reads as two
houses depending on which page you are on.

The property's address is the record's answer, so every filed row is made to
agree with it. **Nothing is lost**: the page's own wording is already in each
row's source sentence, and any house name a row carried that the property did
not is reported here to be put on the property rather than thrown away.

  railway run python3 tools_normalise_house_addresses.py          # show
  railway run python3 tools_normalise_house_addresses.py --apply  # do it
"""
import os, re, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NUM = re.compile(r'^\s*\d')

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
props = {p['id']: p for p in json.load(open('data/all_props.json'))}


def names_in(addr):
    """House names inside an address string - the parts that are not a number."""
    out = []
    for part in re.split(r'[,()/]', addr or ''):
        part = part.strip(' .')
        if (part and not NUM.match(part) and len(part) > 3
                and not re.fullmatch(r'(now|and|the Park|as the page writes it)', part, re.I)
                and ' ' in part):
            out.append(part)
    return out


cur.execute("""SELECT property_id, address, COUNT(*) FROM census_entries
                WHERE property_id IS NOT NULL AND address IS NOT NULL
                  AND TRIM(address) <> '' GROUP BY 1,2""")
drift, lost = [], {}
for pid, addr, n in cur.fetchall():
    want = (props.get(pid) or {}).get('address')
    if not want or addr.strip() == want.strip():
        continue
    drift.append((pid, addr, want, n))
    known = ' '.join(filter(None, [want, (props.get(pid) or {}).get('name'),
                                   (props.get(pid) or {}).get('house_name'),
                                   (props.get(pid) or {}).get('prev_house_name')])).lower()
    for nm in names_in(addr):
        if nm.lower() not in known and nm.lower() not in want.lower():
            lost.setdefault(pid, set()).add(nm)

for pid, addr, want, n in sorted(drift, key=lambda r: -r[3]):
    print(f"  {n:>4}  #{pid} {want[:44]:<46} <- {addr[:56]}")
print(f"\n  {sum(d[3] for d in drift)} rows in {len(drift)} forms would be made to agree")

if lost:
    print("\n  House names that live only on a census row, and not on the property:")
    for pid, nms in sorted(lost.items()):
        print(f"    #{pid} {props[pid]['address']:<42} {', '.join(sorted(nms))}")

if APPLY:
    for pid, addr, want, n in drift:
        cur.execute("""UPDATE census_entries SET address=%s
                        WHERE property_id=%s AND address=%s""", (want, pid, addr))
    cur.execute("""UPDATE census_entries c SET address = %s
                    WHERE FALSE""", ('',))      # keep the shape explicit
    c.commit()
    print("\n  committed")
else:
    print("\n  Nothing written. Add --apply.")
