# -*- coding: utf-8 -*-
"""Jesse Boot at Gardenhurst, 5 South Road, in 1905.

A. Hagues, from Dougal de Havilland's map of the Park. The record already holds
the house and the man, and had never joined them.

**The house.** 5 South Road has carried *Gardenhurst* in its house_name field
and in its history all along - "Also known as Gardenhurst" - but its `name` was
empty, so it showed as a numbered house with no name. Now named.

**The man.** Sir Jesse Boot, 1850-1931, is in the record for 1911 and 1921,
both times at **St Helier, Clumber Road East**, with his Wikipedia page against
him - and **not marked notable**, which for the founder of Boots and the
benefactor who gave Nottingham its university campus is an oversight worth
putting right. His wife Florence was not marked either.

**Why it is a resident link and not a census row.** 1905 falls between the 1901
and 1911 rounds, and the record holds no round for 5 South Road before 1911 -
by which time the house is the Haddens' and the Boots are on Clumber Road East.
So nothing in the census could ever show him here. This is the same shape as
Margaret Stote Glen Bott at 2 Newcastle Circus in 1916.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
GARDENHURST, JESSE, FLORENCE = 304, 2840, 2841
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT id,title,first_name,last_name,significant FROM people WHERE id IN (%s,%s)", (JESSE, FLORENCE))
for r in cur.fetchall(): print("  ", r)
cur.execute("SELECT count(*) FROM property_residents WHERE property_id=%s AND person_id=%s", (GARDENHURST, JESSE))
print("  resident link already there:", cur.fetchone()[0])

if apply:
    cur.execute("""UPDATE people SET significant=TRUE, significant_by='A. Hagues',
                          significance_note='Founder of Boots the Chemists, and the benefactor who gave Nottingham its university campus'
                    WHERE id=%s AND significant IS NOT TRUE""", (JESSE,))
    print(f"\n  Jesse Boot marked notable: {cur.rowcount}")
    cur.execute("""UPDATE people SET significant=TRUE, significant_by='A. Hagues',
                          significance_note='Director of Boots, and a benefactor of Nottingham in her own right'
                    WHERE id=%s AND significant IS NOT TRUE""", (FLORENCE,))
    print(f"  Florence Boot marked notable: {cur.rowcount}")
    cur.execute("""UPDATE people
                      SET bio = bio || E'\\n\\nDougal de Havilland''s map of the Park has him at '
                            '**Gardenhurst, 5 South Road, in 1905** - six years before the census '
                            'finds him at St Helier, and in a gap no census round can reach.'
                    WHERE id=%s AND bio NOT ILIKE '%%Gardenhurst%%'""", (JESSE,))
    cur.execute("""INSERT INTO property_residents (property_id, person_id, from_year, notes)
                   SELECT %s,%s,1905,'At Gardenhurst in 1905, on Dougal de Havilland''s map of the '
                          'Park. Recorded as a resident rather than a census row: 1905 falls '
                          'between the 1901 and 1911 rounds, and the record holds no round for this '
                          'house before 1911, by which time it is the Haddens'' and the Boots are at '
                          'St Helier, Clumber Road East. Whether his wife Florence and their three '
                          'children were here with him is not recorded.'
                     FROM (SELECT 1) t
                    WHERE NOT EXISTS (SELECT 1 FROM property_residents
                                       WHERE property_id=%s AND person_id=%s)""",
                (GARDENHURST, JESSE, GARDENHURST, JESSE))
    print(f"  resident link written: {cur.rowcount}")
    c.commit()
    P = json.load(open('data/all_props.json'))
    for p in P:
        if p['id'] == GARDENHURST:
            p['name'] = 'Gardenhurst'
            p['house_name'] = 'Gardenhurst'
            if not str(p.get('address') or '').lower().startswith('gardenhurst'):
                p['address'] = 'Gardenhurst, 5 South Road'
            if 'Jesse Boot' not in (p.get('history') or ''):
                p['history'] = (p.get('history') or '') + (
                  "\n\n**Sir Jesse Boot was living here in 1905**, on Dougal de Havilland's map of "
                  "the Park - the founder of Boots the Chemists, later Lord Trent, and the "
                  "benefactor who gave Nottingham the ground its university stands on. The census "
                  "cannot show it: 1905 falls between the 1901 and 1911 rounds, and by 1911 the "
                  "house is Henry Charles Hadden's and the Boots are at St Helier on Clumber Road "
                  "East. The house had carried the name Gardenhurst in the record all along, in a "
                  "field nothing displayed.")
            print(f"  {p['address']}")
    json.dump(P, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
else:
    print("\n  preview only - pass --apply")
