#!/usr/bin/env python3
"""
Split people the importer welded together.

The importer matches on a name. Where two households in one round each had a
servant called Mary Shaw, it decided they were one woman - so she is recorded
as living in three houses on the same night. This is the opposite of a
duplicate and much harder to see, because nothing looks wrong until you notice
the same name in two places.

Each entry below names the census rows to take OFF a person and give to a new
one. The person keeps whatever is not listed. The born_year on the new person
is worked out from the age on the row, so the two are told apart afterwards by
something more than a name.

Every split here was read off the page: a wife of 65 and a cook of 22 are not
the same woman, and a solicitor born at Gotham is not a soda-factory clerk born
in Nottingham.

Usage:
  railway run python3 tools_split_welded_people.py          # show what would happen
  railway run python3 tools_split_welded_people.py --apply  # do it
"""

import os, sys, json
import psycopg2

APPLY = '--apply' in sys.argv

# (person_id, [census row ids to move away], why)
SPLITS = [
    (6170, [8867], "a cook of 22 at 15 Cavendish Crescent South, born Kimberley - not Charles Shaw's wife of 65"),
    (6170, [7900], "a cook of 36 at 4 Park Drive, born Rowsley - a third woman again"),
    (4124, [8095], "Henry Lewis's wife at The Chestnuts, 38, born Nottingham"),
    (4124, [7831, 4523], "the cork cutter's wife, born Tewkesbury - 51 at 8 Lenton Road in 1881 and 61 at 6 Lenton Road in 1891"),
    (3794, [7830, 4522, 5689, 976], "William Lewis the cork cutter, born Nottingham - a different man from the hosiery manufacturer of 3 Pelham Crescent, who was born at Tewkesbury"),
    (871,  [8162], "George P Parr, Samuel Parr's son, a clerk of 21 in a soda factory at Oakhurst - not the solicitor of 35 at 33 Lenton Road"),
    (28,   [8258], "Emily S Johnson, wife of Samuel George Johnson the Town Clerk at 17 Pelham Crescent, 43 - not the daughter of 19 at Lenton House, who is Samuel Waite Johnson's"),
    (5226, [8305], "a daughter of 22 at Fairlawn - not the housekeeper of 55 at 1 Park Terrace, who was born at Walesby"),
    (617,  [8706], "a lady's maid of 44 at 9 Pelham Crescent, born Bramcote"),
    (617,  [8203], "a servant of 18 at 4 Western Terrace, born Southwell"),
    (6135, [8600], "a servant of 18 at 121 Derby Road, born Ruddington - not the cook of 28 at 2 Lenton Road, born Tipton"),
]


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


props = {p['id']: p.get('address', '') for p in json.load(open('data/all_props.json'))}
conn = psycopg2.connect(database_url())
cur = conn.cursor()

made = moved = links = 0
for pid, rows, why in SPLITS:
    cur.execute("SELECT first_name, last_name, sex FROM people WHERE id=%s", (pid,))
    who = cur.fetchone()
    if not who:
        print(f"  #{pid} is not there any more - skipped")
        continue
    fn, ln, sex = who
    cur.execute("""SELECT id, census_year, property_id, relationship, age_at_census, occupation_at_census
                     FROM census_entries WHERE id = ANY(%s) AND person_id=%s""", (rows, pid))
    take = cur.fetchall()
    if len(take) != len(rows):
        print(f"  #{pid}: expected {len(rows)} rows, found {len(take)} - skipped, nothing assumed")
        continue
    born = next((r[1] - r[4] for r in take if r[4] is not None), None)
    print(f"\n  #{pid} {fn} {ln}  ->  a new person, born about {born or '?'}")
    print(f"      {why}")
    for r in take:
        print(f"      row {r[0]}  {r[1]}  {props.get(r[2], '(unfiled)')[:38]:<38} {r[3] or '':<12} {r[4]}  {r[5] or ''}")
    if not APPLY:
        made += 1; moved += len(take)
        continue
    cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year)
                   VALUES (%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, born))
    new = cur.fetchone()[0]
    made += 1
    cur.execute("UPDATE census_entries SET person_id=%s WHERE id = ANY(%s)", (new, rows))
    moved += cur.rowcount
    # A resident link the person keeps for a house they were never in is the same
    # fault one step removed. Move it only where no census row of theirs is left
    # in that house.
    for r in take:
        if not r[2]:
            continue
        cur.execute("""SELECT 1 FROM census_entries WHERE person_id=%s AND property_id=%s""", (pid, r[2]))
        if cur.fetchone():
            continue
        cur.execute("""UPDATE property_residents SET person_id=%s
                        WHERE person_id=%s AND property_id=%s
                          AND NOT EXISTS (SELECT 1 FROM property_residents z
                                           WHERE z.person_id=%s AND z.property_id=%s)""",
                    (new, pid, r[2], new, r[2]))
        links += cur.rowcount
        cur.execute("DELETE FROM property_residents WHERE person_id=%s AND property_id=%s", (pid, r[2]))
    print(f"      -> new person #{new}")

print()
if APPLY:
    conn.commit()
    print(f"Made {made} people, moved {moved} census rows and {links} resident links.")
    print("None of the originals lost a row that was theirs.")
else:
    print(f"{made} new people would be made and {moved} census rows moved. Nothing written.")
    print("Run again with --apply.")

cur.close()
conn.close()
