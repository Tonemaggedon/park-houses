#!/usr/bin/env python3
"""
Make data/geocode_manual.json win over a geocoder result that is wrong.

The server seeds that file at start-up, but deliberately will not overwrite a
place the geocoder marked 'found' - a guard meant to stop a good lookup being
clobbered. It also stops a BAD lookup being corrected, and Nominatim answers
with the best match in the world: Lincoln in Nebraska, Brighton in New Jersey,
Wellington in New Zealand. Those rows are 'found', so the file cannot touch them.

This writes the file's position over the cache row, and clears the coordinates
it had already put on the census rows so the next copy re-reads them.

It only touches places the file actually names. A place the file says nothing
about is left exactly as the geocoder left it.

Usage:
  railway run python3 force_geocode_manual.py          # show what would change
  railway run python3 force_geocode_manual.py --apply  # make the change
  railway run python3 apply_geocode_cache.py --apply   # then re-copy onto the rows
"""

import os, sys, json
import psycopg2

SRC = 'data/geocode_manual.json'
APPLY = '--apply' in sys.argv
# Coordinates rounded to four places are within about ten metres; anything
# closer than this is the same position and not worth rewriting.
TOL = 0.01


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


doc = json.load(open(SRC))
want = {}
for p in doc.get('places', []):
    try:
        want[p['place_text'].strip()] = (float(p['lat']), float(p['lng']),
                                         p.get('label'), p.get('note'))
    except (KeyError, TypeError, ValueError):
        print(f'skipping a malformed entry: {p!r}')

conn = psycopg2.connect(database_url())
cur = conn.cursor()
cur.execute("SELECT place_text, lat, lng, status FROM geocode_cache")
have = {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}

disagree, absent = [], []
for place, (lat, lng, label, note) in sorted(want.items()):
    if place not in have:
        absent.append(place)
        continue
    hlat, hlng, status = have[place]
    # A place the geocoder failed on is in the cache with no position at all.
    # Those are the ones this file exists to give one to, so they must survive
    # the comparison rather than be arithmetic on None.
    if hlat is None or hlng is None \
       or abs(float(hlat) - lat) > TOL or abs(float(hlng) - lng) > TOL:
        disagree.append((place, hlat, hlng, status, lat, lng, label))

print(f'{SRC} names {len(want)} places.')
print(f'   the cache disagrees about  : {len(disagree)}')
print(f'   not in the cache at all    : {len(absent)}  (the server seeds these on its own)')

if disagree:
    print('\nTHE CACHE WOULD BE OVERWRITTEN FOR THESE:')
    for place, hlat, hlng, status, lat, lng, label in disagree:
        print(f'   {place[:44]:<44} {status}')
        was = (f'{float(hlat):>9.4f}, {float(hlng):>9.4f}'
               if hlat is not None and hlng is not None else 'no position at all')
        print(f'   {"":<44} was  {was}')
        print(f'   {"":<44} now  {lat:>9.4f}, {lng:>9.4f}   {label or ""}')

if APPLY and disagree:
    rows_cleared = 0
    for place, hlat, hlng, status, lat, lng, label in disagree:
        cur.execute("""
            UPDATE geocode_cache
               SET lat=%s, lng=%s, formatted_address=%s,
                   status='manual', corrected_from=%s, queried_at=NOW()
             WHERE place_text=%s""", (lat, lng, label, SRC, place))
        # The wrong position is already on the census rows. Clear it so the
        # copy step reads the corrected one.
        cur.execute("""
            UPDATE census_entries
               SET birth_lat=NULL, birth_lng=NULL
             WHERE TRIM(birth_place)=%s""", (place,))
        rows_cleared += cur.rowcount
    conn.commit()
    print(f'\nCorrected {len(disagree)} cached places.')
    print(f'Cleared the old position from {rows_cleared} census rows.')
    print('\nNow run:  railway run python3 apply_geocode_cache.py --apply')
elif disagree:
    print('\nNothing written. Run again with --apply.')

cur.close()
conn.close()
