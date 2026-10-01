# -*- coding: utf-8 -*-
"""A sheet to fill in while looking at the 1939 pages, and nothing more to do.

Rather than re-sending documents, the cheapest way to mend the amended surnames
is a worklist with two blank columns. Fill in what the page shows and hand it
back; fix_1939_amended_names.py takes the rows straight from it.

Everybody in the 1939 round is listed, in the order the record received them -
house by house, schedule by schedule, in the order they were entered - so the
sheet can be worked straight down beside the pages instead of jumped around.

  railway run python3 amended_names_worksheet.py
"""
import os, json, psycopg2, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

OBSCURED = 'written under the amendment cannot be read'

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
P = {p['id']: p.get('address', '') for p in json.load(open('data/all_props.json'))}

cur.execute("""SELECT c.id, p.id, p.first_name, p.last_name, p.sex, c.property_id,
                      c.age_at_census, c.occupation_at_census, c.census_household_num,
                      c.relationship, p.maiden_name,
                      (c.source ILIKE %s) AS obscured
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                WHERE c.census_year = 1939
                ORDER BY c.id""", ('%' + OBSCURED + '%',))
rows = cur.fetchall()

BOLD = Font(bold=True)
FILL = PatternFill('solid', fgColor='FFF2CC')       # the two columns he fills in
RED  = PatternFill('solid', fgColor='FCE4D6')       # the surname is the amendment
WARM = PatternFill('solid', fgColor='FFF9E6')       # worth a glance
HEAD = ['row', 'person', 'name as recorded', 'house', 'schedule', 'in the household',
        'age', 'occupation', 'NAME ON THE NIGHT', 'AMENDED TO', 'what the record says']
WIDTH = (7, 9, 26, 34, 10, 16, 6, 28, 22, 22, 46)


def note_for(sex, age, maiden, obscured):
    if obscured:
        return 'the surname IS the amendment - the 1939 name is struck through under it'
    if maiden and maiden.strip():
        return f'carries a maiden name already: {maiden}'
    if sex == 'F' and age is not None and 12 <= age <= 50:
        return 'woman of marrying age - worth a glance for a strikethrough'
    return ''


def sheet(ws, data):
    ws.append(HEAD)
    for cell in ws[1]:
        cell.font = BOLD
    for cell in (ws['I1'], ws['J1']):
        cell.fill = FILL
    for cid, pid, fn, ln, sex, prop, age, occ, sched, rel, maiden, obscured in data:
        note = note_for(sex, age, maiden, obscured)
        ws.append([cid, pid, f'{fn} {ln}', P.get(prop) or '(unfiled)', sched, rel,
                   age, occ, '', '', note])
        row = ws[ws.max_row]
        row[8].fill = row[9].fill = FILL
        row[10].alignment = Alignment(wrap_text=True, vertical='top')
        if obscured:
            for cell in row[:8]:
                cell.fill = RED
        elif note:
            for cell in row[:8]:
                cell.fill = WARM
    for i, w in enumerate(WIDTH, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'


wb = openpyxl.Workbook()
sheet(wb.active, rows)
wb.active.title = 'Everybody, in order'
obscured = [r for r in rows if r[-1]]
sheet(wb.create_sheet('The obscured names'), obscured)

out = os.path.expanduser('~/Desktop/1939 names - fill in.xlsx')
wb.save(out)
women = [r for r in rows if r[4] == 'F' and r[6] is not None and 12 <= r[6] <= 50]
print(f'Written: {out}')
print(f'   sheet 1: all {len(rows)} people in the 1939 round, in the order they were added')
print(f'   sheet 2: the {len(obscured)} whose surname is the amendment - the 1939 name is lost under it')
print(f'   {len(women)} women aged 12 to 50 are tinted, as the ones a strikethrough is likely on')
