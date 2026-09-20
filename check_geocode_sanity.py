#!/usr/bin/env python3
"""
Find birth places the geocoder has put somewhere improbable.

Nominatim returns the best match in the world, not the best match in England.
A census birth place with no county - "Bedford", "Clifton" - or one whose county
the search does not weight, can come back in Pennsylvania, New Jersey or
Ontario. On the Origins map that is a pin on the wrong continent, and nothing
about the row looks wrong until somebody notices.

This reports; it changes nothing. What it finds belongs in
data/geocode_manual.json, positioned by hand.

Usage:
  railway run python3 check_geocode_sanity.py
"""

import os, re, sys
import psycopg2

# Great Britain and Ireland. The eastern edge is drawn at Lowestoft rather
# than out into the Channel, or Calais and Boulogne fall inside it.
UK = dict(lat=(49.8, 61.0), lng=(-11.0, 1.8))

# A birth place naming somewhere abroad is expected to sit abroad.
ABROAD = re.compile(
    r'\b(germany|france|belgium|holland|netherlands|denmark|sweden|norway|russia|poland|'
    r'austria|hungary|switzerland|italy|spain|portugal|greece|turkey|saxony|prussia|bavaria|'
    r'schleswig|berlin|hamburg|frankfurt|munich|paris|brussels|vienna|moscow|'
    r'u\.?s\.?a|america|united states|new york|boston|philadelphia|chicago|st louis|'
    r'canada|ontario|quebec|australia|sydney|melbourne|new zealand|napier|'
    r'india|bombay|calcutta|madras|ceylon|china|shanghai|japan|siam|bangkok|'
    r'africa|cape|natal|johannesburg|egypt|malta|gibraltar|jamaica|barbados|'
    r'curacao|d\.w\.i|west indies|brazil|argentina|chile|peru|mexico|'
    r'yemen|aden|malaysia|selangor|kuala lumpur|singapore|ukraine|lithuania|latvia|'
    r'estonia|finland|romania|bulgaria|serbia|croatia|slovenia|bohemia|moravia|'
    r'channel islands|jersey|guernsey|alderney|sark|isle of man|'
    r'new south wales|victoria, australia|tasmania|queensland)\b', re.I)


# Boston is in Lincolnshire and Melbourne in Derbyshire before they are anywhere
# else. Where the text names an English county or nation, take it at its word.
HOME_COUNTY = re.compile(
    r'\b(nottinghamshire|lincolnshire|derbyshire|leicestershire|yorkshire|lancashire|'
    r'staffordshire|warwickshire|cheshire|shropshire|worcestershire|gloucestershire|'
    r'northamptonshire|huntingdonshire|cambridgeshire|bedfordshire|buckinghamshire|'
    r'hertfordshire|oxfordshire|berkshire|wiltshire|somerset|dorset|devon|cornwall|'
    r'hampshire|surrey|sussex|kent|essex|suffolk|norfolk|rutland|durham|northumberland|'
    r'cumberland|westmorland|middlesex|monmouthshire|england|scotland|wales|ireland)\b',
    re.I)

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


conn = psycopg2.connect(database_url())
conn.set_session(readonly=True)
cur = conn.cursor()

cur.execute("""
    SELECT gc.place_text, gc.lat, gc.lng, gc.status, gc.formatted_address,
           (SELECT COUNT(*) FROM census_entries ce
             WHERE TRIM(ce.birth_place) = gc.place_text) AS rows
      FROM geocode_cache gc
     WHERE gc.lat IS NOT NULL AND gc.lng IS NOT NULL
     ORDER BY rows DESC, gc.place_text""")

offshore, far_north, suspicious = [], [], []
for place, lat, lng, status, formatted, rows in cur.fetchall():
    lat, lng = float(lat), float(lng)
    inside = UK['lat'][0] <= lat <= UK['lat'][1] and UK['lng'][0] <= lng <= UK['lng'][1]
    names_abroad = bool(ABROAD.search(place)) and not HOME_COUNTY.search(place)
    if not inside and not names_abroad:
        offshore.append((place, lat, lng, status, formatted, rows))
    elif inside and names_abroad:
        # The reverse mistake: "Berlin, Germany" placed in England.
        suspicious.append((place, lat, lng, status, formatted, rows))


def show(title, items, explain):
    print(f'\n{title} — {len(items)} place(s), {sum(i[5] for i in items)} census row(s)')
    if explain:
        print(f'   {explain}')
    for place, lat, lng, status, formatted, rows in items:
        print(f'   {place[:46]:<46} {rows:>4} rows  {lat:>9.4f}, {lng:>9.4f}  {status}')
        if formatted:
            print(f'   {"":<46}        {formatted[:90]}')


show('OUTSIDE THE BRITISH ISLES, BUT NOT NAMING ANYWHERE ABROAD', offshore,
     'Almost certainly the wrong place — the same name somewhere else in the world.')
show('INSIDE THE BRITISH ISLES, BUT NAMING SOMEWHERE ABROAD', suspicious,
     'The opposite mistake, and rarer.')

total = len(offshore) + len(suspicious)
print(f'\n{total} place(s) worth a look.')
if total:
    print('None of this has been changed. To correct one, add it to')
    print('data/geocode_manual.json with a lat/lng and a note, and it is applied')
    print('at the next deploy — the file always wins over a geocoder result.')

cur.close()
conn.close()
