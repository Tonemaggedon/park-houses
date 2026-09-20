#!/usr/bin/env python3
"""
Copy coordinates the record already knows onto the census rows that lack them.

Every birth place is looked up once and kept in geocode_cache; the coordinates
are then copied onto each census row carrying that place. The copy is the last
step of geocode_birth_places.py, after its lookup loop - so when that script
cannot reach the database, or is stopped part way, imports since the last
successful run are left with birth places that the cache can already place.

That is the state this mends, and it needs no network at all. It writes only
where a row has no coordinates, so a position set by hand is never disturbed.

Usage:
  railway run python3 apply_geocode_cache.py          # show what would change
  railway run python3 apply_geocode_cache.py --apply  # make the change
"""

import os, sys
import psycopg2

APPLY = '--apply' in sys.argv


def database_url():
    """Railway injects the internal host, which only resolves inside Railway's
    own network. The public URL is the one that works from a laptop."""
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 '
                         + os.path.basename(__file__))
    return v


conn = psycopg2.connect(database_url())
cur = conn.cursor()

MATCH = """
      FROM census_entries ce
      JOIN geocode_cache gc ON TRIM(ce.birth_place) = gc.place_text
     WHERE gc.status IN ('found', 'manual')
       AND gc.lat IS NOT NULL AND gc.lng IS NOT NULL
       AND (ce.birth_lat IS NULL OR ce.birth_lng IS NULL)
"""

cur.execute("SELECT COUNT(*) " + MATCH)
would = cur.fetchone()[0]

cur.execute("""
    SELECT TRIM(ce.birth_place), COUNT(*)
""" + MATCH + """
    GROUP BY TRIM(ce.birth_place)
    ORDER BY COUNT(*) DESC
    LIMIT 20""")
top = cur.fetchall()

print(f'Census rows that can take coordinates from the cache: {would}')
if top:
    print('\nThe commonest of them:')
    for place, n in top:
        print(f'   {place[:50]:<50} {n:>5}')

if APPLY and would:
    cur.execute("""
        UPDATE census_entries ce
           SET birth_lat = gc.lat, birth_lng = gc.lng
          FROM geocode_cache gc
         WHERE TRIM(ce.birth_place) = gc.place_text
           AND gc.status IN ('found', 'manual')
           AND gc.lat IS NOT NULL AND gc.lng IS NOT NULL
           AND (ce.birth_lat IS NULL OR ce.birth_lng IS NULL)""")
    print(f'\nPositioned {cur.rowcount} census rows.')
    conn.commit()
elif would:
    print('\nNothing written. Run again with --apply.')

# What is left is a real gap: a place nobody has looked up, or one that could
# not be found. Those are geocode_birth_places.py's business.
cur.execute("""
    SELECT COUNT(DISTINCT TRIM(ce.birth_place))
      FROM census_entries ce
     WHERE ce.birth_place IS NOT NULL AND TRIM(ce.birth_place) <> ''
       AND ce.birth_lat IS NULL
       AND NOT EXISTS (SELECT 1 FROM geocode_cache gc
                        WHERE gc.place_text = TRIM(ce.birth_place)
                          AND gc.status IN ('found', 'manual')
                          AND gc.lat IS NOT NULL)""")
print(f'\nBirth places still needing a lookup: {cur.fetchone()[0]}')
print('Those are for:  railway run python3 geocode_birth_places.py')

cur.close()
conn.close()
