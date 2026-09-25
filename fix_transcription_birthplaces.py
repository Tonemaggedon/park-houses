#!/usr/bin/env python3
"""
Birth places the transcriptions carried in with the wrong spelling or the wrong
county, rewritten to the forms A. Hagues supplied. Sixty came from the 1871 and
1881 rounds; seven more from the 1891 and 1939 rounds, which the geocoder either
could not place at all or placed in the wrong county.

The importer fills blanks and never overwrites, so a second import cannot mend
these - the value is already there. This is the only way to change them.

Sixty spellings, and one of them - plain "Nottingham" - stands for most of the
rows. Every change is an exact, whole-value match: "Nottingham" becomes
"Nottingham, Nottinghamshire", but "St Mary, Nottingham" and "The Park,
Nottingham" are left alone, because they are not the same value.

Two places are deliberately NOT in the list. "At sea" and "(not known)" name
nowhere. Their cache rows are marked 'nowhere' rather than deleted, because a
deleted row is simply looked up again - which is how they came back as a
street in Bonaire and an island in the Solomons.

Usage:
  railway run python3 fix_transcription_birthplaces.py          # show what would change
  railway run python3 fix_transcription_birthplaces.py --apply  # make the change
"""

import os, sys
import psycopg2

APPLY = '--apply' in sys.argv

REWRITE = {
    # ── the 1891 and 1939 rounds ──────────────────────────────────────────────
    # Bolnhurst, Bedfordshire was checked with these and is right as it stands.
    "Baston, Norfolk": "Bacton, Norfolk",                     # Baston is in Lincolnshire
    # Not England. The same enumerator wrote "London, Middlesex" against this
    # man's wife on the line above. Confirmed by A. Hagues as East London in the
    # Eastern Cape - the port, not the hamlet in Mpumalanga the geocoder chose.
    "London, South Africa": "East London, South Africa",
    "Braceby, Leicestershire": "Braceby, Lincolnshire",
    "Clyro, Radnorshire": "Clyro, Powys",
    "Kimpton, Leicestershire": "Knipton, Leicestershire",
    "Newball, Staffordshire": "Newhall, Staffordshire",
    "Stapleton near Darlington, Durham": "Stapleton, Yorkshire",
    "Yaxley, Lincolnshire": "Yaxley, Cambridgeshire",
    # ── the 1871 and 1881 rounds ──────────────────────────────────────────────
    "Appleknowle, Derbyshire": "Apperknowle, Derbyshire",
    "Appleton, Bolton Percy, Yorkshire": "Bolton Percy, Yorkshire",
    "Arlaston": "Arleston, Derbyshire",
    "Ashfordby, Leicestershire": "Asfordby, Leicestershire",
    "Ashley Lea, Derbyshire": "Lea, Derbyshire",
    "Ashton-under-Lyne, Lancashire": "Ashton-under-Lyne, Greater Manchester",
    "Barleythorpe, Lincolnshire": "Barleythorpe, Rutland",
    "Barnstone near Bingham, Nottinghamshire": "Barnstone, Nottinghamshire",
    "Belgaum, Bombay, India": "Belagavi, Karnataka, India",
    "Benares, East Indies": "Varanasi, India",
    "Bitton, Leicestershire": "Belton, Leicestershire",
    "Bole near Gainsborough, Nottinghamshire": "Bole, Nottinghamshire",
    "Bollington, Lancashire": "Bollington, Cheshire",
    "Bradburton, Yorkshire": "Brandesburton, Yorkshire",
    "Branston Lodge, Leicestershire": "Branston, Leicestershire",
    "Brinsley, Derbyshire": "Brinsley, Nottinghamshire",
    "Calcutta, India (British subject)": "Calcutta, India",
    "Carlton le Moorland, Nottinghamshire": "Carlton le Moorland, Lincolnshire",
    "Castle Field, Derbyshire": "Castlefields, Derbyshire",
    "Colgrave, Nottinghamshire": "Cotgrave, Nottinghamshire",
    "Coopers Bank, Staffordshire": "Cooper's Bank, Staffordshire",
    "Cosgrave, Nottinghamshire": "Cotgrave, Nottinghamshire",
    "Crofts, Leicester": "Croft, Leicester",
    "Eye Green, Northamptonshire": "Eye Green, Cambridgeshire",
    "Eyton, Yorkshire": "East Ayton, Yorkshire",
    "France (British subject)": "France",
    "France (naturalised British subject)": "France",
    "Freemanston": "Freemanston, Pembrokeshire, Wales",
    "Gayton, Nottinghamshire": "Gayton, Northamptonshire",
    "Germany (British subject)": "Germany",
    "Germany (naturalised British subject)": "Germany",
    "Great Gidding": "Great Gidding, Huntingdonshire",
    "Hanover, Germany (naturalised British subject)": "Hanover, Germany",
    "Hardwick Grange, Nottinghamshire": "Hardwick, Nottinghamshire",
    "Kimpton, Nottinghamshire": "Kimpton, Hertfordshire",
    "Knowlton, Nottinghamshire": "Kinoulton, Nottinghamshire",
    "Laxfield Vicarage, Suffolk": "Laxfield, Suffolk",
    "Mannheim, Germany (naturalised British subject)": "Mannheim, Germany",
    "Mehrungen, East Prussia": "Kreis Mohrungen, East Prussia",
    "Moor Green, Nottinghamshire": "Moorgreen, Nottinghamshire",
    "New York, USA (British subject)": "New York, USA",
    "Norton, Radnorshire": "Norton, Powys",
    "Nottingham": "Nottingham, Nottinghamshire",
    "Nottingham (British subject)": "Nottingham, Nottinghamshire",
    "Old Brinsley, Nottinghamshire": "Brinsley, Nottinghamshire",
    "Ostend, Belgium (British subject)": "Ostend, Belgium",
    "Paddington, Middlesex": "Paddington, London",
    "Petersfield": "Petersfield, Hampshire",
    "Pooley Bridge, Cumberland": "Pooley Bridge, Cumbria",
    "Prussia (British subject)": "Prussia",
    "Prussia (naturalised British subject)": "Prussia",
    "Puddimore, Somerset": "Podimore, Somerset",
    "Ranceby, Lincolnshire": "Ranby, Lincolnshire",
    "Sandiacre": "Sandiacre, Derbyshire",
    "Saxe-Weimar, Germany": "Thuringia, Germany",
    "Scalescombe, Sussex": "Sedlescombe, Sussex",
    "Shelton, Leicestershire": "Shelton, Nottinghamshire",
    "Shoreditch, Middlesex": "Shoreditch, London",
    "Smallford, Staffordshire": "Smallford, Hertfordshire",
    "Standard Hill, Nottinghamshire": "Nottingham, Nottinghamshire",
    "Thorney, Northamptonshire": "Thorney, Cambridgeshire",
    "Tottenham, Middlesex": "Tottenham, London",
    "Victoria, Australia (British subject)": "Victoria, Australia",
    "West Newham, Norfolk": "West Raynham, Norfolk",
    "Winwick, Lancashire": "Winwick, Cheshire"
}

NOWHERE = ['At sea', '(not known)']


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

total = 0
touched = set()
for table, column in (('census_entries', 'birth_place'), ('people', 'born_place')):
    rows = []
    for old, new in sorted(REWRITE.items()):
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE TRIM({column})=%s", (old,))
        n = cur.fetchone()[0]
        if n:
            rows.append((n, old, new))
    if not rows:
        continue
    print(f'\n{table}.{column}:')
    for n, old, new in sorted(rows, reverse=True):
        print(f'   {old!r:<46} {n:>4} rows  ->  {new!r}')
        total += n
        touched.add(old)
        if APPLY:
            # Clear the position first. A row renamed from "Baston, Norfolk" to
            # "Bacton, Norfolk" otherwise keeps the coordinates Baston was given,
            # and apply_geocode_cache fills blanks rather than overwriting, so a
            # wrong position would sit there for good.
            if table == 'census_entries':
                cur.execute("UPDATE census_entries SET birth_lat=NULL, birth_lng=NULL "
                            "WHERE TRIM(birth_place)=%s", (old,))
            cur.execute(f"UPDATE {table} SET {column}=%s WHERE TRIM({column})=%s", (new, old))

print()
if APPLY:
    conn.commit()
    print(f'Changed {total} rows.')
    # The old spellings leave geocode_cache entries that nothing points at any
    # more, and several of them hold a wrong position. Drop exactly those, and
    # the two that name nowhere at all.
    dead = 0
    for p in sorted(touched):
        cur.execute("DELETE FROM geocode_cache WHERE place_text=%s", (p,))
        dead += cur.rowcount
    # These two name nowhere. Deleting the row only invites the geocoder to look
    # them up again and answer with the best match in the world, so mark them
    # instead and strip any position they already carry.
    for p in NOWHERE:
        cur.execute("""UPDATE geocode_cache SET lat=NULL, lng=NULL, status='nowhere',
                              formatted_address='names nowhere - never to be positioned'
                        WHERE place_text=%s""", (p,))
        cur.execute("UPDATE census_entries SET birth_lat=NULL, birth_lng=NULL WHERE TRIM(birth_place)=%s", (p,))
    conn.commit()
    print(f'Removed {dead} stale geocode_cache entries, and marked {len(NOWHERE)} that name nowhere.')
    print('\nNow run, in this order:')
    print('   railway run python3 apply_geocode_cache.py --apply   # positions rows from places already known')
    print('   railway run python3 geocode_birth_places.py          # looks up what is left')
    print('   railway run python3 check_geocode_sanity.py          # Nominatim answers with the best match in the world')
else:
    print(f'{total} rows would change. Nothing has been written.')
    print('Run again with --apply to make the change.')

cur.close()
conn.close()
