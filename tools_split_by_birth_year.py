#!/usr/bin/env python3
"""
Split people whose census rows cannot all belong to one person.

The importer matches on a name, so a grandfather and a grandson with the same
name become one man who is 56 in 1881 and 6 in 1891. The welds that shared a
house were pulled apart by tools_split_welded_people.py; these are the ones
that did not, and they are only visible in the arithmetic.

Two tests, because one is not enough - and a list of people the tests get wrong.

First, the rows are grouped by the birth year each age implies. Rows within
GRACE years of one another are the same person - census ages wander, and a
servant who is 24 in one round and 32 in the next is still one woman. A group
that sits further off is somebody else.

Second, the calendar. Nobody ages nineteen years in ten. Where the step between
two rounds outruns the years between them, the rows are two people however
close their implied birth years look.

But the calendar test only proves that SOMETHING is wrong, not what. George
Shepperley is 40 in 1881 and 59 in 1891 - and he is one chemist at one address
on Western Terrace, with the same son beside him, whose age was written down
wrong. Eight of the nine the calendar test first found were that, not welds.
So anyone checked and found to be one person goes in
data/age_conflicts_checked.json, and is skipped here.

The largest group keeps the original person, because that is where the
biography, the links and the notability mark already are. Every new person
carries the birth year their own rows imply, so nothing re-welds.

Usage:
  railway run python3 tools_split_by_birth_year.py            # show what would happen
  railway run python3 tools_split_by_birth_year.py --apply    # do it
  railway run python3 tools_split_by_birth_year.py --gap 10   # only the wilder ones
"""

import os, sys, json
import psycopg2

APPLY = '--apply' in sys.argv
GRACE = 5          # years of census wandering allowed inside one person
MIN_GAP = 10       # only split where the groups are at least this far apart
CALENDAR = 3       # how much faster than the calendar a person may appear to age
if '--gap' in sys.argv:
    MIN_GAP = int(sys.argv[sys.argv.index('--gap') + 1])


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

# Ageing faster than the calendar means one of two things, and the arithmetic
# cannot tell them apart: two people welded together, or one person whose age
# was written down wrong. The household around them tells you which, and where
# somebody has looked and found one person, they are listed here so this does
# not keep offering to invent a second.
CHECKED = {c['person_id']: c['why']
           for c in json.load(open('data/age_conflicts_checked.json'))['checked']}
conn = psycopg2.connect(database_url())
cur = conn.cursor()

cur.execute("""
  SELECT p.id, p.first_name, p.last_name, p.significant, COALESCE(LENGTH(p.bio),0)
    FROM people p JOIN census_entries c ON c.person_id=p.id
   WHERE c.age_at_census IS NOT NULL
   GROUP BY 1,2,3,4,5
  HAVING MAX(c.census_year-c.age_at_census) - MIN(c.census_year-c.age_at_census) > %s
   ORDER BY p.last_name, p.first_name""", (GRACE,))
people = cur.fetchall()

split = newrows = 0
for pid, fn, ln, sig, biolen in people:
    if pid in CHECKED:
        continue
    cur.execute("""SELECT id, census_year, age_at_census, property_id, relationship, occupation_at_census
                     FROM census_entries WHERE person_id=%s ORDER BY census_year, id""", (pid,))
    rows = cur.fetchall()
    dated = [r for r in rows if r[2] is not None]
    # Walk the rows in birth-year order and start a new group wherever the step
    # is bigger than the wander a census can explain.
    dated.sort(key=lambda r: r[1] - r[2])
    groups, cur_g = [], [dated[0]]
    for r in dated[1:]:
        if (r[1] - r[2]) - (cur_g[-1][1] - cur_g[-1][2]) <= GRACE:
            cur_g.append(r)
        else:
            groups.append(cur_g); cur_g = [r]
    groups.append(cur_g)
    # Second test, and the one that catches what grouping cannot. Nobody ages
    # nineteen years in ten. Where a group's rows show a step that outruns the
    # calendar, the group is two people however close their birth years look -
    # George Shepperley is 40 in 1881 and 59 in 1891, and the two implied birth
    # years are only nine apart, which slips under MIN_GAP.
    # Second test, and the one grouping cannot do. Nobody ages nineteen years in
    # ten. Where a group's own rows show a step that outruns the calendar, that
    # group is two people however close their implied birth years look - George
    # Shepperley is 40 in 1881 and 59 in 1891, and those birth years are only
    # nine apart, which slips under MIN_GAP.
    # Does the person's own run of rounds contain a step no one can take? That
    # is asked of the rows in census order, before any grouping, because the
    # grouping may already have put the two rounds in different groups - which
    # is exactly what happens to George Shepperley, 40 in 1881 and 59 in 1891.
    inorder = sorted(dated, key=lambda r: r[1])
    calendar_fired = any((b[2] - a[2]) - (b[1] - a[1]) > CALENDAR
                         for a, b in zip(inorder, inorder[1:]))
    broken = []
    for g in groups:
        byyear = sorted(g, key=lambda r: r[1])
        run = [byyear[0]]
        for a, b in zip(byyear, byyear[1:]):
            if (b[2] - a[2]) - (b[1] - a[1]) > CALENDAR:
                broken.append(run); run = [b]
            else:
                run.append(b)
        broken.append(run)
    groups = broken
    if len(groups) < 2:
        continue
    born = lambda g: round(sum(r[1] - r[2] for r in g) / len(g))
    # MIN_GAP guards the first test against splitting one person whose age
    # merely wandered. It has no business guarding the second: an impossible
    # step is impossible at any distance.
    if not calendar_fired and max(born(g) for g in groups) - min(born(g) for g in groups) < MIN_GAP:
        continue
    groups.sort(key=lambda g: (-len(g), born(g)))
    keeper, others = groups[0], groups[1:]
    undated = [r for r in rows if r[2] is None]
    print(f"\n  #{pid} {fn} {ln}" + (f"   [notable]" if sig else "") + (f"   [{biolen}ch of life written]" if biolen else ""))
    print(f"      keeps   b.{born(keeper)}   " + ', '.join(f"{r[1]}:{r[2]}" for r in sorted(keeper, key=lambda r: r[1])))
    if undated:
        print(f"      and the {len(undated)} row(s) with no age, which nothing can place")
    for g in others:
        print(f"      splits  b.{born(g)}   " + ', '.join(f"{r[1]}:{r[2]} {props.get(r[3],'(unfiled)')[:24]}" for r in sorted(g, key=lambda r: r[1])))
        split += 1; newrows += len(g)
        if APPLY:
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year)
                           SELECT first_name, last_name, sex, %s FROM people WHERE id=%s
                        RETURNING id""", (born(g), pid))
            new = cur.fetchone()[0]
            cur.execute("UPDATE census_entries SET person_id=%s WHERE id = ANY(%s)", (new, [r[0] for r in g]))
            for r in g:
                if not r[3]:
                    continue
                cur.execute("SELECT 1 FROM census_entries WHERE person_id=%s AND property_id=%s", (pid, r[3]))
                if cur.fetchone():
                    continue
                cur.execute("""UPDATE property_residents SET person_id=%s
                                WHERE person_id=%s AND property_id=%s
                                  AND NOT EXISTS (SELECT 1 FROM property_residents z
                                                   WHERE z.person_id=%s AND z.property_id=%s)""",
                            (new, pid, r[3], new, r[3]))
                cur.execute("DELETE FROM property_residents WHERE person_id=%s AND property_id=%s", (pid, r[3]))
            print(f"              -> new person #{new}")
    if APPLY:
        cur.execute("UPDATE people SET born_year=COALESCE(born_year,%s) WHERE id=%s", (born(keeper), pid))

print()
if APPLY:
    conn.commit()
    print(f"Made {split} people and moved {newrows} census rows.")
else:
    print(f"{split} people would be made and {newrows} rows moved. Nothing written.")
    print(f"(grace {GRACE} years inside one person, split only where the groups sit {MIN_GAP}+ apart)")
    print("Run again with --apply.")

cur.close()
conn.close()
