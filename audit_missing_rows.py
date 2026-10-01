# -*- coding: utf-8 -*-
"""Every census row an import file holds that the record has not got.

Written after a fold tool deleted rows instead of moving them. The import files
are the record's own account of what should be there, so this reads them back
and names anything missing - which is the only honest way to find out what a
destructive run cost.

  railway run python3 audit_missing_rows.py
"""
import os, glob, json, psycopg2

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
# A person the record has renamed is not a person the record has lost, so the
# names it answers to include every alias as well as the one it carries now.
cur.execute("""SELECT LOWER(TRIM(p.first_name)), LOWER(TRIM(p.last_name)), c.census_year,
                      c.property_id
                 FROM census_entries c JOIN people p ON p.id = c.person_id
               UNION ALL
               SELECT LOWER(TRIM(a.first_name)), LOWER(TRIM(a.last_name)), c.census_year,
                      c.property_id
                 FROM census_entries c JOIN person_alias a ON a.person_id = c.person_id
               UNION ALL
               SELECT LOWER(TRIM(p.first_name)), LOWER(TRIM(a.last_name)), c.census_year,
                      c.property_id
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                 JOIN person_alias a ON a.person_id = c.person_id""")
have = set()
for fn, ln, yr, prop in cur.fetchall():
    have.add((fn, ln, yr, prop))
    have.add((fn, ln, yr, None))          # unfiled or filed, either counts

missing = []
for f in sorted(glob.glob('data/people_*.json')):
    d = json.load(open(f))
    for x in d.get('people', d if isinstance(d, list) else []):
        if not isinstance(x, dict):
            continue
        fn = (x.get('first_name') or '').strip().lower()
        ln = (x.get('last_name') or '').strip().lower()
        if not fn or not ln:
            continue
        for ce in x.get('census', []):
            yr = ce.get('census_year')
            prop = ce.get('property_id')
            if (fn, ln, yr, prop) in have or (fn, ln, yr, None) in have:
                continue
            missing.append((f, x.get('first_name'), x.get('last_name'), yr, prop,
                            ce.get('age_at_census'), ce.get('address') or ce.get('unresolved_address')))

print(f"  {len(missing)} rows the files hold and the record has not")
for f, fn, ln, yr, prop, age, addr in missing:
    print(f"    {yr}  {fn} {ln}, aged {age} - house {prop} {addr or ''}   [{f.split('/')[-1]}]")
