#!/usr/bin/env python3
"""
St Mary, St Peter and St Nicholas are the parishes Nottingham was divided into
for the census, not places anybody was born in. This rewrites every one of them
to plain "Nottingham, Nottinghamshire", so that the Origins map puts those
people in the town they came from rather than against a church, or nowhere.

It touches ONLY spellings that name Nottingham. Ottery St Mary and Rugby St
Johns are real places and are left exactly as they are.

Usage:
  railway run python3 fix_nottingham_parishes.py          # show what would change
  railway run python3 fix_nottingham_parishes.py --apply  # make the change
"""

import os, sys, re
import psycopg2

TARGET = 'Nottingham, Nottinghamshire'
APPLY = '--apply' in sys.argv

# A parish spelling only counts when Nottingham is named alongside the saint.
PARISH = re.compile(
    r'^\s*(?:st[\.\s]+(?:mary|peter|nicholas|ann|anns|paul|james)(?:\'s)?\s*,?\s*nottingham'
    r'|nottingham\s*[,(]?\s*st[\.\s]+(?:mary|peter|nicholas|ann|anns|paul|james)(?:\'s)?\s*\)?)'
    r'\s*(?:,\s*nottinghamshire)?\s*$', re.I)

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
cur = conn.cursor()


def column_exists(table, column):
    cur.execute("""SELECT 1 FROM information_schema.columns
                    WHERE table_name=%s AND column_name=%s""", (table, column))
    return cur.fetchone() is not None


targets = [('census_entries', 'birth_place')]
if column_exists('people', 'born_place'):
    targets.append(('people', 'born_place'))

total = 0
for table, column in targets:
    cur.execute(f"""SELECT TRIM({column}) AS v, COUNT(*)
                      FROM {table}
                     WHERE {column} IS NOT NULL AND TRIM({column}) <> ''
                     GROUP BY TRIM({column})""")
    hits = [(v, n) for v, n in cur.fetchall() if PARISH.match(v)]
    if not hits:
        print(f'{table}.{column}: nothing to change')
        continue
    print(f'{table}.{column}:')
    for v, n in sorted(hits, key=lambda x: -x[1]):
        print(f'   {v!r:<40} {n:>4} rows  ->  {TARGET!r}')
        total += n
        if APPLY:
            cur.execute(f"UPDATE {table} SET {column}=%s WHERE TRIM({column})=%s",
                        (TARGET, v))

print()
if APPLY:
    conn.commit()
    print(f'Changed {total} rows.')
    # The old spellings leave dead geocode_cache entries behind. Drop them so
    # nothing keeps pointing at a church, and so a re-run of the geocoder is clean.
    # PARISH is anchored and only matches a spelling that names Nottingham
    # beside the saint. Anything looser catches East Kirkby and West Bridgford,
    # whose coordinates are right and must not be thrown away.
    cur.execute("SELECT place_text FROM geocode_cache")
    dead = [p for (p,) in cur.fetchall() if PARISH.fullmatch((p or '').strip())]
    for p in dead:
        cur.execute("DELETE FROM geocode_cache WHERE place_text=%s", (p,))
    conn.commit()
    print(f'Removed {len(dead)} stale geocode_cache entries for those spellings.')
    print('\nNow run:  railway run python3 geocode_birth_places.py')
else:
    print(f'{total} rows would change. Nothing has been written.')
    print('Run again with --apply to make the change.')

cur.close()
conn.close()
