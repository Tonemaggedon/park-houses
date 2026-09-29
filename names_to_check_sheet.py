# -*- coding: utf-8 -*-
"""A spreadsheet of names the transcriber flagged, one round at a time.

Every source line that says a name was hard to read, or that an amendment
written over it could not be made out, is a name somebody could settle by
looking at the page again. They are scattered through the record and invisible
until gathered.

The 1939 Register has two kinds. A name simply hard to read, and a name with a
LATER name written over it - the Register was kept up to date for decades, so a
woman who married after 1939 has her married name written across the original.
The two want different treatment, so they get a sheet each.

Usage:
  railway run python3 names_to_check_sheet.py --year 1939
"""
import os, re, sys, json, argparse
import psycopg2, openpyxl
from openpyxl.styles import Font, Alignment

ap = argparse.ArgumentParser()
ap.add_argument('--year', type=int, default=1939)
args = ap.parse_args()
YEAR = args.year

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
PROPS = {p['id']: p.get('address', '') for p in json.load(open('data/all_props.json'))}

cur.execute("""SELECT p.id, p.first_name, p.last_name, c.property_id, c.age_at_census,
                      c.occupation_at_census, c.census_household_num, c.source, c.birth_place
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                WHERE c.census_year = %s
                  AND (c.source ILIKE '%%hard to read%%' OR c.source ILIKE '%%cannot be read%%'
                       OR c.source ILIKE '%%could not be read%%'
                       OR p.first_name ILIKE '%%unknown%%' OR p.last_name ILIKE '%%unknown%%')
                ORDER BY c.property_id NULLS LAST, p.last_name, p.first_name""", (YEAR,))

def flag(src, fn, ln):
    if 'unknown' in (fn + ln).lower(): return 'broken'
    if re.search(r'written under the amendment cannot be read', src or '', re.I): return 'amendment'
    return 'hard to read'

def clause(src):
    """the bit of the source that says what is wrong, not the whole provenance"""
    bits = [b.strip() for b in (src or '').split(';')]
    keep = [b for b in bits if re.search(r'hard to read|cannot be read|could not be read', b, re.I)]
    return '; '.join(keep) or (src or '')[:90]

SHEETS = {'hard to read': 'Name hard to read',
          'amendment':    'Amendment over the name',
          'broken':       'No forename at all'}
buckets = {k: [] for k in SHEETS}
for pid, fn, ln, prop, age, occ, sched, src, bp in cur.fetchall():
    buckets[flag(src, fn or '', ln or '')].append(
        [pid, f"{fn} {ln}".strip(), PROPS.get(prop) or '(unfiled)', sched, age, occ, bp, clause(src)])

wb = openpyxl.Workbook(); wb.remove(wb.active)
HEAD = ['person', 'name as transcribed', 'house', 'schedule', 'age', 'occupation', 'birth place', 'what the note says']
for key, title in SHEETS.items():
    rows = buckets[key]
    ws = wb.create_sheet(f"{title} ({len(rows)})"[:31])
    ws.append(HEAD)
    for cell in ws[1]: cell.font = Font(bold=True)
    for r in rows: ws.append(r)
    for i, w in enumerate((9, 30, 36, 10, 7, 30, 26, 60), 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    for row in ws.iter_rows(min_row=2):
        row[7].alignment = Alignment(wrap_text=True, vertical='top')

out = os.path.expanduser(f'~/Desktop/{YEAR} names to check.xlsx')
wb.save(out)
print(f"Written: {out}")
for key, title in SHEETS.items():
    print(f"   {title:<26} {len(buckets[key])}")
