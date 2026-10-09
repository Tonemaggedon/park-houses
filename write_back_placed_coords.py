# -*- coding: utf-8 -*-
"""Ten positions were put right on the map. The seed file still holds the old ones.

`coords` is what the site draws and `data/all_props.json` is only a seed, so
nothing on the site is wrong - but the file is the thing every script of mine
reads, and it now disagrees with the map for ten more houses. That gap is
already a question of its own; this closes ten of it rather than widening it.

Each one also gets its position source rewritten, because several were created
with a calculated point and carried a note saying so. They are not calculated
any more.
"""
import os, sys, json, math, psycopg2

apply = '--apply' in sys.argv
d = json.load(open('data/all_props.json'))
P = {p['id']: p for p in d}
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT id, lat, lng, placed_at FROM coords
                WHERE placed_at > NOW() - INTERVAL '12 hours' ORDER BY placed_at""")
rows = cur.fetchall()
NOTE = ("Taken from the OpenStreetMap building this house matches, checked and applied by "
        "A. Hagues on the positions page, 9 October 2026. Not calculated, not read off a map "
        "by eye: the footprint of the building itself.")

def m(a, b):
    return math.hypot((a[0]-b[0])*110540, (a[1]-b[1])*111320*math.cos(math.radians(a[0])))

n = 0
for pid, lat, lng, at in rows:
    p = P.get(pid)
    if not p:
        print(f"  #{pid} is not in the file"); continue
    old = (p.get('lat'), p.get('lng'))
    gap = m((float(lat), float(lng)), (float(old[0]), float(old[1]))) if old[0] else None
    print(f"  #{pid:<4} {str(p.get('address'))[:40]:<42} seed moves {gap:.0f} m" if gap is not None
          else f"  #{pid:<4} {p.get('address')} had no seed position")
    if not apply:
        continue
    p['lat'], p['lng'] = round(float(lat), 7), round(float(lng), 7)
    s = p.get('sources')
    if isinstance(s, dict):   s['position'] = NOTE
    elif isinstance(s, list): p['sources'] = [x for x in s if 'osition' not in str(x)[:12]] + ['Position: ' + NOTE]
    else:                     p['sources'] = {'position': NOTE}
    n += 1

if apply:
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"\n  {n} written back, each with where the position came from")
else:
    print("\n  preview only - pass --apply")
