# -*- coding: utf-8 -*-
"""Write the record's person id into every import file entry it can match.

This is the root of the welds. An import file names a person; the importer
matches on that name; and the moment the record corrects a name the file stops
pointing at anybody, so the next import makes a second person and hangs the
household's rows on whoever else shares the name.

That is what happened this morning: a hundred and twenty-eight 1939 names were
put right in the record and the files still carried the old ones.

An id survives a rename, a corrected birth year and a split. So each file entry
is matched - by the name it carries, or by any alias the record holds for that
name - and the id written in. **A name that matches more than one person is left
alone and reported**, because binding the wrong one is worse than binding none.

  railway run python3 tools_bind_import_files_by_id.py          # show
  railway run python3 tools_bind_import_files_by_id.py --write  # do it
"""
import os, sys, glob, json, psycopg2

WRITE = '--write' in sys.argv

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT id, LOWER(TRIM(first_name)), LOWER(TRIM(last_name)) FROM people")
by_name = {}
for pid, fn, ln in cur.fetchall():
    by_name.setdefault((fn, ln), []).append(pid)
cur.execute("""SELECT a.person_id, LOWER(TRIM(a.first_name)), LOWER(TRIM(a.last_name)),
                      LOWER(TRIM(p.first_name))
                 FROM person_alias a JOIN people p ON p.id = a.person_id""")
by_alias = {}
for pid, afn, aln, pfn in cur.fetchall():
    by_alias.setdefault((afn, aln), []).append(pid)
    by_alias.setdefault((pfn, aln), []).append(pid)     # old surname, current forename

# What each person actually holds. A name match is only trusted when the file's
# own census rows agree with it - otherwise binding would freeze a weld in place
# rather than prevent one.
cur.execute("SELECT person_id, census_year, property_id FROM census_entries")
holds = {}
for pid, yr, prop in cur.fetchall():
    holds.setdefault(pid, set()).add((yr, prop))

bound = already = ambiguous = unmatched = mismatched = 0
amb, un, mm = [], [], []
for f in sorted(glob.glob('data/people_*.json')):
    d = json.load(open(f))
    people = d.get('people', d if isinstance(d, list) else [])
    changed = False
    for x in people:
        if not isinstance(x, dict):
            continue
        if x.get('id'):
            already += 1
            continue
        fn = (x.get('first_name') or '').strip().lower()
        ln = (x.get('last_name') or '').strip().lower()
        if not fn or not ln:
            continue
        hits = by_name.get((fn, ln)) or by_alias.get((fn, ln)) or []
        hits = sorted(set(hits))
        # A file row with no property_id is one the record has since filed, so the
        # house cannot be compared and the year has to carry the match on its own.
        want, want_years = set(), set()
        for ce in x.get('census', []):
            yr, prop = ce.get('census_year'), ce.get('property_id')
            (want.add((yr, prop)) if prop else want_years.add(yr))
        if want or want_years:
            fits = [h for h in hits
                    if (holds.get(h, set()) & want)
                    or (want_years & {y for y, _ in holds.get(h, set())})]
            if fits:
                hits = fits
            elif hits:
                mismatched += 1
                mm.append((f.split('/')[-1], x.get('first_name'), x.get('last_name'), hits))
                continue
        if len(hits) == 1:
            x['id'] = hits[0]
            bound += 1
            changed = True
        elif len(hits) > 1:
            ambiguous += 1
            amb.append((f.split('/')[-1], x.get('first_name'), x.get('last_name'), hits))
        else:
            unmatched += 1
            un.append((f.split('/')[-1], x.get('first_name'), x.get('last_name')))
    if changed and WRITE:
        json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)

print(f"  bound by id : {bound}")
print(f"  already had : {already}")
print(f"  ambiguous   : {ambiguous}  (left alone - more than one person of that name)")
print(f"  no match    : {unmatched}  (not in the record under that name or any alias)")
print(f"  rows disagree: {mismatched}  (left alone - the name matches somebody who does not hold these rows)")
if amb:
    print("\n  ambiguous, a sample:")
    for a in amb[:12]:
        print(f"    {a[1]} {a[2]}  ->  {a[3]}   [{a[0]}]")
if mm:
    print("\n  the name matches somebody who holds none of these rows - a weld waiting to happen:")
    for a in mm[:15]:
        print(f"    {a[1]} {a[2]}  ->  {a[3]}   [{a[0]}]")
if un:
    print("\n  no match, a sample:")
    for a in un[:12]:
        print(f"    {a[1]} {a[2]}   [{a[0]}]")
print("\n  Nothing written. Add --write." if not WRITE else "\n  written")
