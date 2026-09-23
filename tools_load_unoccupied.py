#!/usr/bin/env python3
"""
Load data/census_unoccupied.json into the census_unoccupied table.

A house in that file is one the enumerator wrote down as standing empty. That is
an ANSWER, not a gap: without it the gap tools keep offering the same empty house
round after round, and somebody keeps looking for a household that was never there.

Safe to run twice - it will not duplicate a house already recorded for that year.

Usage:
  railway run python3 tools_load_unoccupied.py          # show what would change
  railway run python3 tools_load_unoccupied.py --apply  # write it
"""

import os, sys, json
import psycopg2

APPLY = '--apply' in sys.argv


def database_url():
    """Railway injects the internal host, which only resolves inside Railway's own
    network. The public URL is the one that works from a laptop."""
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 ' +
                         os.path.basename(__file__))
    return v


houses = json.load(open('data/census_unoccupied.json'))['houses']
props = {p['id']: p.get('address', '') for p in json.load(open('data/all_props.json'))}

conn = psycopg2.connect(database_url())
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS census_unoccupied (
                 property_id INTEGER, census_year INTEGER, notes TEXT)""")
conn.commit()

added = already = 0
for h in houses:
    pid, yr = h['property_id'], h['census_year']
    cur.execute("SELECT 1 FROM census_unoccupied WHERE property_id=%s AND census_year=%s", (pid, yr))
    if cur.fetchone():
        already += 1
        continue
    added += 1
    print(f"  {yr}  #{pid:<4} {props.get(pid, '?')}")
    if APPLY:
        cur.execute("INSERT INTO census_unoccupied (property_id, census_year, notes) VALUES (%s,%s,%s)",
                    (pid, yr, h.get('notes')))

print()
if APPLY:
    conn.commit()
    print(f'Recorded {added} empty houses. {already} were already there.')
else:
    print(f'{added} would be recorded, {already} already there. Nothing written.')
    print('Run again with --apply.')

cur.close()
conn.close()
