#!/usr/bin/env python3
"""
Look up every birth place the record has never looked up before.

It asks Nominatim, OpenStreetMap's geocoder, which needs no key and allows one
request a second - so this takes about a second per NEW place and nothing at
all for the rest. Answers are kept in geocode_cache so no place is ever looked
up twice, and the coordinates are copied onto the census rows at the end.

It has no dry run: it writes as it goes. That is safe, because it only touches
places with no answer yet and never overwrites one.

Run apply_geocode_cache.py FIRST - it costs nothing and needs no network, and
it clears out every row this would otherwise have to ask about.

Then run check_geocode_sanity.py AFTER, because Nominatim answers with the best
match in the world: Lincoln in Nebraska, Boston in Massachusetts, Wellington in
New Zealand.

Usage:
  railway run python3 geocode_birth_places.py
"""

import os, time, urllib.request, urllib.parse, json, ssl
import psycopg2

# Bypass SSL verification (macOS Python certificate issue)
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE


def database_url():
    """Railway injects the internal host, which only resolves inside Railway's own
    network. Run from a laptop it fails with "could not translate host name
    postgres.railway.internal". The public URL is the one that works from here, so
    prefer it and fall back to the internal one when running on Railway itself."""
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 ' +
                         os.path.basename(__file__))
    return v


conn = psycopg2.connect(database_url())
cur  = conn.cursor()

# Get all distinct birth places not yet in cache
cur.execute("""
    SELECT DISTINCT TRIM(birth_place) AS bp
    FROM census_entries
    WHERE birth_place IS NOT NULL AND TRIM(birth_place) != ''
      AND TRIM(birth_place) NOT IN (SELECT place_text FROM geocode_cache)
    ORDER BY bp
""")
places = [r[0] for r in cur.fetchall()]
print(f"Places to geocode: {len(places)}")

not_found = []
found = 0

for place in places:
    # Skip obvious junk
    if place in ('?', '1') or len(place) < 2:
        cur.execute("INSERT INTO geocode_cache (place_text, status) VALUES (%s,'not_found') ON CONFLICT DO NOTHING", (place,))
        not_found.append(place)
        conn.commit()
        continue

    encoded = urllib.parse.quote(place)
    # Use Nominatim (OpenStreetMap) — no key required, 1 req/sec limit
    url = (f"https://nominatim.openstreetmap.org/search"
           f"?q={encoded}&format=json&limit=1&addressdetails=0")
    headers = {'User-Agent': 'Nottspark/1.0 (ahagues75@icloud.com)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as resp:
            results = json.loads(resp.read())
    except Exception as e:
        print(f"  ERROR fetching {place}: {e}")
        continue

    if results:
        r = results[0]
        lat = float(r['lat'])
        lng = float(r['lon'])
        fmt = r.get('display_name', place)
        cur.execute("""
            INSERT INTO geocode_cache (place_text, lat, lng, status, formatted_address)
            VALUES (%s, %s, %s, 'found', %s)
            ON CONFLICT (place_text) DO UPDATE
              SET lat=EXCLUDED.lat, lng=EXCLUDED.lng,
                  status='found', formatted_address=EXCLUDED.formatted_address
        """, (place, lat, lng, fmt))
        found += 1
        print(f"  ✓ {place} → {lat:.4f}, {lng:.4f}")
    else:
        cur.execute("""
            INSERT INTO geocode_cache (place_text, status)
            VALUES (%s, 'not_found')
            ON CONFLICT (place_text) DO UPDATE SET status='not_found'
        """, (place,))
        not_found.append(place)
        print(f"  ✗ {place} — not found")

    conn.commit()
    time.sleep(1.1)  # Nominatim requires max 1 req/sec

# Update census_entries with lat/lng from cache
cur.execute("""
    UPDATE census_entries ce
    SET birth_lat = gc.lat, birth_lng = gc.lng
    FROM geocode_cache gc
    WHERE TRIM(ce.birth_place) = gc.place_text
      AND gc.status = 'found'
      AND (ce.birth_lat IS NULL OR ce.birth_lng IS NULL)
""")
print(f"\nUpdated {cur.rowcount} census entries with coordinates")
conn.commit()

print(f"\n── Summary ──────────────────────────────")
print(f"Geocoded:    {found}")
print(f"Not found:   {len(not_found)}")

if not_found:
    print(f"\n── Places needing manual coordinates ───")
    print("Recommended site: https://www.latlong.net  or  https://visionofbritain.org.uk/place/")
    print("For each place below, find the lat/lng and run:")
    print("  UPDATE geocode_cache SET lat=<lat>, lng=<lng>, status='manual'")
    print("  WHERE place_text = '<place>';")
    print("Then re-run this script to apply coordinates to census entries.\n")
    for p in not_found:
        print(f"  '{p}'")

cur.close()
conn.close()
