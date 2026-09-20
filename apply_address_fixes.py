#!/usr/bin/env python3
"""
Carry corrected unfiled addresses from the data files into the record.

The importer fills blanks and never overwrites, which is right: a file should
not be able to quietly rewrite what somebody has entered by hand. But it also
means a correction made in a file AFTER that file was imported never arrives.

That is the case here. The 1901 files went in carrying the enumerator's linking
words as addresses - "Next", "First schedule" - along with stray quote marks,
bare house names, and Rd where the record writes Road. All of it was mended in
the files afterwards. None of it reached the database.

This matches each census row to its person and year and writes the address the
file now holds. It only touches rows with no property_id, so nothing filed is
disturbed, and only where the two actually differ.

Usage:
  railway run python3 apply_address_fixes.py          # show what would change
  railway run python3 apply_address_fixes.py --apply  # make the change
"""

import os, sys, glob, json, collections
import psycopg2

APPLY = '--apply' in sys.argv
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def database_url():
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 '
                         + os.path.basename(__file__))
    return v


# What the files say an unfiled row's address should be, keyed on the person's
# name, the census year and the schedule - which together identify a row
# closely enough without depending on ids the files may not carry.
wanted = {}
for path in sorted(glob.glob(os.path.join(DATA, 'people_*.json'))):
    try:
        doc = json.load(open(path))
    except Exception:
        continue
    for person in doc.get('people', []):
        fn = (person.get('first_name') or '').strip().lower()
        ln = (person.get('last_name') or '').strip().lower()
        if not fn and not ln:
            continue
        for c in (person.get('census') or []):
            if c.get('property_id'):
                continue
            addr = (c.get('unresolved_address') or '').strip()
            if not addr:
                continue
            key = (fn, ln, c.get('census_year'), c.get('census_household_num'))
            wanted[key] = addr

conn = psycopg2.connect(database_url())
cur = conn.cursor()
cur.execute("""
    SELECT ce.id, ce.census_year, ce.census_household_num,
           TRIM(COALESCE(ce.unresolved_address, '')),
           LOWER(TRIM(COALESCE(p.first_name, ''))), LOWER(TRIM(COALESCE(p.last_name, '')))
      FROM census_entries ce
      JOIN people p ON p.id = ce.person_id
     WHERE ce.property_id IS NULL""")

changes, unmatched = [], 0
for row_id, year, hh, current, fn, ln in cur.fetchall():
    want = wanted.get((fn, ln, year, hh))
    if want is None:
        unmatched += 1
        continue
    if want != current:
        changes.append((row_id, year, f'{fn} {ln}'.title(), current, want))

pairs = collections.Counter((c[3], c[4]) for c in changes)
print(f'Unfiled rows whose address the files have since corrected: {len(changes)}')
print(f'   ({unmatched} unfiled rows have no matching row in any file - untouched)')
if pairs:
    print('\nWHAT WOULD CHANGE:')
    for (old, new), n in pairs.most_common():
        print(f'   {old[:44]!r:<46} -> {new[:44]!r:<46} {n:>4}')

if APPLY and changes:
    for row_id, _, _, _, want in changes:
        cur.execute('UPDATE census_entries SET unresolved_address=%s WHERE id=%s',
                    (want, row_id))
    conn.commit()
    print(f'\nWritten: {len(changes)} rows.')
elif changes:
    print('\nNothing written. Run again with --apply.')

cur.close()
conn.close()
