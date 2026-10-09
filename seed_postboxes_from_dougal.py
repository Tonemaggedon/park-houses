# -*- coding: utf-8 -*-
"""Six post boxes are drawn on Dougal de Havilland's map. A. Hagues read them off.

All six are placed. The sixth - 68 The Ropewalk - had no house to hang a point on,
because the record's Ropewalk stops at 56; A. Hagues found it on the map opposite
Tower House, which does have a point.

So the hunt does not start from nothing after all. These go in with **no cypher**,
because the map shows where a box is and not what is cast into it - which makes
the walk's job the good half: go and read it.

**Every position here is the position of the house named, not of the box.** A box
is in a wall or on a post a few metres from the door, and nothing in the record
knows which few metres. Each row says so, and the first person to stand in front
of one will replace the point with their own.

  railway run python3 seed_postboxes_from_dougal.py          # preview
  railway run python3 seed_postboxes_from_dougal.py --apply
"""
import os, sys, json, psycopg2

apply = '--apply' in sys.argv
P = {p['id']: p for p in json.load(open('data/all_props.json'))}

# (anchor property, where_note, box's own property_id or None)
BOXES = [
    (183, "Outside 9 Lenton Road, as Dougal de Havilland's map draws it.", 183),
    (193, "Outside 27 Lenton Road - Lenton House - as Dougal's map draws it.", 193),
    (205, "On Newcastle Circus, opposite Burton House, as Dougal's map draws it. "
          "The point is Burton House itself; the box is across the road from it.", None),
    (323, "22a The Ropewalk. The record holds 22 and not 22a, so the point is number 22 "
          "and the box is a door or two along.", None),
    (2,   "Opposite the top of Barrack Lane, as Dougal's map draws it. Which end of the "
          "lane is not certain from the map - the point is 1 Barrack Lane, at the Derby "
          "Road end.", None),
    # Found on a second look: A. Hagues placed it from the map on 9 October.
    (395, "By number 68 The Ropewalk, opposite Tower House. The record's Ropewalk stops "
          "at 56, so there is no house at 68 to hang the point on - this is Tower House, "
          "and the box is across the road from it on the Ropewalk side.", None),
]
MISSING = None

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for pid, note, own in BOXES:
    p = P[pid]
    print(f"  {p['address']:<42} {p['lat']:.6f}, {p['lng']:.6f}")
    print(f"      {note}")
if MISSING: print(f"\n  NOT PLACED: {MISSING}")

if not apply:
    print("\n  preview only - pass --apply")
    sys.exit()

n = 0
for pid, note, own in BOXES:
    p = P[pid]
    cur.execute("""SELECT id FROM postboxes
                    WHERE ABS(lat-%s) < 0.00018 AND ABS(lng-%s) < 0.0003""", (p['lat'], p['lng']))
    if cur.fetchone():
        print(f"  already there: {p['address']}"); continue
    cur.execute("""INSERT INTO postboxes (lat, lng, where_note, property_id, found_by)
                   VALUES (%s,%s,%s,%s,%s)""",
                (p['lat'], p['lng'], note, own,
                 "Dougal de Havilland's map, read by A. Hagues"))
    n += 1
c.commit()
print(f"\n  {n} boxes seeded, none with a cypher - that is what the walk is for")
