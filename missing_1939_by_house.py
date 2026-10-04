"""One row per house, for every property with nothing for 1939.

A house counts as done if it has a 1939 census row OR a 1939 entry in
census_unoccupied - an empty house is written into the Register and ticked,
so a blank is a record, not a gap.
"""
import os, json, re, psycopg2
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

P = json.load(open('data/all_props.json'))
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

cur.execute("""SELECT property_id, census_year FROM census_entries
                WHERE property_id IS NOT NULL GROUP BY 1,2""")
years = {}
for pid, y in cur.fetchall(): years.setdefault(pid, set()).add(y)

cur.execute("SELECT property_id, census_year, notes FROM census_unoccupied")
empty, empty39 = {}, {}
for pid, y, n in cur.fetchall():
    empty.setdefault(pid, set()).add(y)
    if y == 1939: empty39[pid] = n or ''

# who the record last knew in the house, to give each row a handle
cur.execute("""SELECT property_id, MAX(census_year) FROM census_entries
                WHERE property_id IS NOT NULL GROUP BY 1""")
last = dict(cur.fetchall())
cur.execute("""SELECT ce.property_id, ce.census_year, p.first_name||' '||p.last_name
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id IS NOT NULL ORDER BY ce.id""")
heads = {}
for pid, y, nm in cur.fetchall():
    if last.get(pid) == y: heads.setdefault(pid, nm)

# schedules already spoken for, so a row can say what is left in its street
cur.execute("""SELECT DISTINCT census_household_num,
                      CASE WHEN source ILIKE '%RMGA%' THEN 'RMGA' WHEN source ILIKE '%RMGB%' THEN 'RMGB'
                           WHEN source ILIKE '%RMGC%' THEN 'RMGC' ELSE '' END
                 FROM census_entries WHERE census_year=1939 AND census_household_num IS NOT NULL""")
taken = {(s, b) for s, b in cur.fetchall()}

rows = []
for p in sorted(P, key=lambda x: (str(x.get('street') or ''), str(x.get('address') or ''))):
    pid = p['id']
    if 1939 in years.get(pid, set()) or pid in empty39:
        continue
    got = sorted(years.get(pid, set()) | (empty.get(pid, set()) - {1939}))
    rows.append({
        'Street': p.get('street') or '',
        'House': p.get('address') or p.get('name') or f"property {pid}",
        'House name': p.get('name') or '',
        'id': pid,
        'Census years the record has': ', '.join(str(y) for y in got) or 'none at all',
        'Last household known': f"{heads.get(pid,'')}{' (' + str(last[pid]) + ')' if pid in last else ''}",
        'Marked empty in': ', '.join(str(y) for y in sorted(empty.get(pid, set()))) or '',
    })

wb = Workbook(); ws = wb.active; ws.title = "Missing 1939"
cols = ['Street','House','House name','id','Census years the record has','Last household known','Marked empty in']
ws.append(cols)
for col in ws[1]:
    col.font = Font(bold=True, color="FFFFFF")
    col.fill = __import__('openpyxl').styles.PatternFill("solid", fgColor="1F4E46")
    col.alignment = Alignment(vertical='center')
for r in rows: ws.append([r[k] for k in cols])
ws.freeze_panes = "A2"
ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows)+1}"
for i, w in enumerate([22,42,18,7,30,32,16], 1):
    ws.column_dimensions[get_column_letter(i)].width = w

out = os.path.expanduser('~/Desktop/1939 - houses with nothing.xlsx')
wb.save(out)
print(f"{len(rows)} houses with no 1939 at all")
print(out)
by = {}
for r in rows: by[r['Street']] = by.get(r['Street'], 0) + 1
for s, n in sorted(by.items(), key=lambda kv: -kv[1]):
    print(f"   {n:>3}  {s or '(no street)'}")
