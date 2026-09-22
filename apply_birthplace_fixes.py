#!/usr/bin/env python3
"""
Write a birth place out in full where the record only has a county.

A. Hagues supplies these. They are nearly all the same shape: a 1911 row
carrying "Lincs" or "staffs" or "Middx" where the same person's 1901 or 1921 row
gives the town. A bare county geocodes to the middle of a shire and puts a pin
in a field; the town puts it where the person was born.

Two of them are not that shape and are corrections of fact:

  Mildred Jacklin   1891 reads "Denby, LINCOLNSHIRE". Denby is in Derbyshire.
  Elizabeth Phillips  the record disagrees with itself - 1901 says Dudley,
                      Staffordshire and 1921 says Dudley, Worcestershire. It is
                      Worcestershire: Dudley was a detached part of it until
                      1966, surrounded by Staffordshire but not in it.

A. Hagues asked whether Worcestershire would still be found, Dudley being in the
West Midlands now. It is not: the geocoder answers a spot in the COTSWOLDS,
having matched "Worcestershire (detached)" and ignored the town. Nor is Mitcham
found under Surrey, nor Liverpool under Lancashire - a road in Bagshot and a
canal at Rufford respectively. Where a town has left its historic county the
modern county wins, and it wins with something confidently wrong rather than
with nothing.

The record keeps the county the census wrote. The position comes from
data/geocode_manual.json, which is what that file is for - Acton, Middlesex has
been pinned there since it answered Acton, Massachusetts.

Keyed on person number, so no name matching can go wrong. It writes only where
the value differs, fills a blank people.born_place, and clears the coordinates
off every row it touches so the geocoder looks them up again.

Usage:
  railway run python3 apply_birthplace_fixes.py          # show what would change
  railway run python3 apply_birthplace_fixes.py --apply  # make the change
  railway run python3 apply_geocode_cache.py --apply     # then re-position them
"""

import os, sys
import psycopg2

APPLY = '--apply' in sys.argv

# person id -> the birth place in full, as A. Hagues gives it
FIXES = {
     933: 'Mitcham, Surrey',              # Frederick John Elborough
    1271: 'Stamford, Lincolnshire',       # Johanna Goodcliffe
     922: 'Grimsby, Lincolnshire',        # Ada Nicholson Green
     925: 'Nottingham, Nottinghamshire',  # Dorothy Green, born 1892
    4897: 'Nottingham, Nottinghamshire',  # Dorothy Green, born 1888 - see note
     923: 'Nottingham, Nottinghamshire',  # Jessie Green
    2229: 'Denby, Derbyshire',            # Mildred Jacklin - 1891 says Lincolnshire
     645: 'Liverpool, Lancashire',        # Edward Evans Lloyd
     598: 'Clackmannanshire, Scotland',   # Edward Palmer
     928: 'Birstall, Yorkshire',          # Samuel Walker Pemberton
    2255: 'Dudley, Worcestershire',       # Elizabeth Phillips - see note
    1277: 'Acton, Middlesex',             # Edwin Arthur Polley
}

# Every number here was checked against the surname it should carry before the
# table was trusted. That check earned its keep at once: the first version of
# this file had #2891 against Frederick John Elborough, and #2891 is Gustave
# Throsheim of Lenton Avenue - a number carried over from other work. Applied
# unchecked it would have moved a German lace merchant's birth to Surrey.

# There are TWO Dorothy Greens, born 1888 and 1892, and the correction names
# neither. Both are given Nottingham: the 1892 one because her own 1901 row
# already says so and her 1911 row says "staffs", the 1888 one because her only
# row says "Nottingham" and wants the county after it. Neither is a guess about
# which woman was meant.


def database_url():
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 '
                     + os.path.basename(__file__))


conn = psycopg2.connect(database_url())
cur = conn.cursor()

rows_changed = people_changed = 0
for pid, place in sorted(FIXES.items(), key=lambda x: x[1]):
    cur.execute('SELECT first_name, last_name, born_year, born_place FROM people WHERE id=%s', (pid,))
    who = cur.fetchone()
    if not who:
        print(f'  #{pid}: no such person - skipped')
        continue
    fn, ln, by, bp = who
    cur.execute("""SELECT id, census_year, birth_place FROM census_entries
                    WHERE person_id=%s ORDER BY census_year""", (pid,))
    rows = cur.fetchall()
    todo = [(rid, yr, old) for rid, yr, old in rows if (old or '').strip() != place]
    fill_person = not (bp or '').strip()
    if not todo and not fill_person:
        continue
    print(f'\n  #{pid} {fn} {ln}, born {by}  ->  {place}')
    for rid, yr, old in todo:
        print(f'      {yr}: {old!r}')
    if fill_person:
        print(f'      and the person record, which has no birth place at all')
    if APPLY:
        for rid, _, _ in todo:
            cur.execute("""UPDATE census_entries
                              SET birth_place=%s, birth_lat=NULL, birth_lng=NULL
                            WHERE id=%s""", (place, rid))
            rows_changed += 1
        if fill_person:
            cur.execute('UPDATE people SET born_place=%s WHERE id=%s', (place, pid))
            people_changed += 1
    else:
        rows_changed += len(todo)
        people_changed += 1 if fill_person else 0

print()
if APPLY:
    conn.commit()
    print(f'Written: {rows_changed} census rows, {people_changed} person records.')
    print('Their coordinates are cleared, so now run:')
    print('   railway run python3 geocode_birth_places.py')
    print('   railway run python3 apply_geocode_cache.py --apply')
else:
    print(f'{rows_changed} census rows and {people_changed} person records would change.')
    print('Nothing has been written. Run again with --apply.')

cur.close()
conn.close()
