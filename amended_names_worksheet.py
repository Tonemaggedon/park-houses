# -*- coding: utf-8 -*-
"""A sheet to fill in while looking at the 1939 pages, and nothing more to do.

Rather than re-sending documents, the cheapest way to mend the amended surnames
is a worklist with two blank columns. Fill in what the page shows and hand it
back; fix_1939_amended_names.py takes the rows straight from it.

  railway run python3 amended_names_worksheet.py
"""
import os, json, psycopg2, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
P = {p['id']: p.get('address', '') for p in json.load(open('data/all_props.json'))}

cur.execute("""SELECT p.id, p.first_name, p.last_name, p.sex, c.property_id, c.age_at_census,
                      c.occupation_at_census, c.census_household_num,
                      CASE WHEN c.source ILIKE '%%written under the amendment cannot be read%%'
                           THEN 'amendment noted - the 1939 name is under it'
                           WHEN p.maiden_name IS NOT NULL AND TRIM(p.maiden_name) <> ''
                           THEN 'carries a maiden name already: ' || p.maiden_name
                           ELSE '' END AS flag
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                WHERE c.census_year = 1939 AND p.sex = 'F' AND c.age_at_census BETWEEN 12 AND 50
                ORDER BY (CASE WHEN c.source ILIKE '%%written under the amendment cannot be read%%' THEN 0
                               WHEN p.maiden_name IS NOT NULL THEN 1 ELSE 2 END),
                         c.property_id NULLS LAST, p.last_name""")
rows = cur.fetchall()

wb = openpyxl.Workbook(); ws = wb.active; ws.title = "1939 amended surnames"
ws.append(['person', 'name as recorded', 'house', 'schedule', 'age', 'occupation',
           'NAME ON THE NIGHT', 'AMENDED TO', 'already flagged?'])
for cell in ws[1]: cell.font = Font(bold=True)
fill = PatternFill('solid', fgColor='FFF2CC')
for cell in (ws['G1'], ws['H1']): cell.fill = fill
flagged = 0
for pid, fn, ln, sex, prop, age, occ, sched, flag in rows:
    ws.append([pid, f"{fn} {ln}", P.get(prop) or '(unfiled)', sched, age, occ, '', '', flag])
    if flag: flagged += 1
for i, w in enumerate((9, 28, 34, 10, 6, 30, 22, 22, 42), 1):
    ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
ws.freeze_panes = 'A2'
for row in ws.iter_rows(min_row=2):
    row[6].fill = fill; row[7].fill = fill
    row[8].alignment = Alignment(wrap_text=True, vertical='top')

out = os.path.expanduser('~/Desktop/1939 amended surnames - fill in.xlsx')
wb.save(out)
print(f"Written: {out}")
print(f"   {len(rows)} women aged 12 to 50 in the 1939 round")
print(f"   {flagged} of them already carry a flag - do those first")
print(f"   {len(rows)-flagged} are unflagged: only worth a look if the page shows a strikethrough")
