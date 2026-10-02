# -*- coding: utf-8 -*-
"""The baseline: what the record is still missing, in lists a person can work.

Six sheets, each one a kind of work rather than a kind of subject, so a morning
can be spent on one of them without jumping about:

  Summary              - the shape of what is left
  Missing census       - a house the record holds either side of a round it has not got
  No census at all     - a property with no household in any round
  Houses to find       - the addresses the census gives that the property list has not
  Missing house names  - properties carrying a number and no name
  Open questions       - all of them, by area

  railway run python3 baseline_report.py
"""
import os, json, collections, psycopg2, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

YEARS = [1861, 1871, 1881, 1891, 1901, 1911, 1921, 1939]
BOLD = Font(bold=True)
HEAD = PatternFill('solid', fgColor='E8E8E8')

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
P = {p['id']: p for p in json.load(open('data/all_props.json'))}

cur.execute("""SELECT property_id, census_year, COUNT(*) FROM census_entries
                WHERE property_id IS NOT NULL GROUP BY 1,2""")
held = collections.defaultdict(dict)
for pid, yr, n in cur.fetchall():
    held[pid][yr] = n

# the head of each house when the record last saw it, which is what finds the family
cur.execute("""SELECT c.property_id, c.census_year, p.first_name || ' ' || p.last_name
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                WHERE c.property_id IS NOT NULL AND c.relationship ILIKE 'head'""")
heads = {}
for pid, yr, nm in cur.fetchall():
    heads[(pid, yr)] = nm

wb = openpyxl.Workbook()


def sheet(title, headers, rows, widths):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = BOLD
        cell.fill = HEAD
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    ws.freeze_panes = 'A2'
    return ws


# --- missing census, only where the record holds the house either side --------
gaps = []
for pid, rounds in held.items():
    ys = sorted(rounds)
    for y in YEARS:
        if y in rounds:
            continue
        before = [a for a in ys if a < y]
        after = [b for b in ys if b > y]
        if not (before and after):
            continue
        gaps.append([P.get(pid, {}).get('address', f'#{pid}'), y,
                     heads.get((pid, before[-1]), ''), before[-1],
                     heads.get((pid, after[0]), ''), after[0],
                     'the same family' if heads.get((pid, before[-1])) and
                     heads.get((pid, before[-1])) == heads.get((pid, after[0]))
                     else ''])
gaps.sort(key=lambda r: (r[1], r[0]))

# --- no census at all ---------------------------------------------------------
nocensus = sorted(
    ([p['address'], p.get('street', ''), 'yes' if p.get('census_only') else '',
      (p.get('history') or '')[:90]] for p in P.values() if p['id'] not in held),
    key=lambda r: r[0])

# --- houses to find: the addresses the census gives and the list has not -------
cur.execute("""SELECT COALESCE(unresolved_address, '(no address on the page)'),
                      census_year, COUNT(*)
                 FROM census_entries WHERE property_id IS NULL GROUP BY 1,2""")
unfiled = collections.defaultdict(dict)
for addr, yr, n in cur.fetchall():
    unfiled[addr][yr] = n
tofind = sorted(([a, sum(v.values()), ', '.join(f'{y} ({n})' for y, n in sorted(v.items()))]
                 for a, v in unfiled.items()), key=lambda r: -r[1])

# --- missing house names ------------------------------------------------------
noname = sorted(([p['address'], p.get('street', ''), len(held.get(p['id'], {})),
                  ', '.join(str(y) for y in sorted(held.get(p['id'], {})))]
                 for p in P.values()
                 if not (p.get('name') or p.get('house_name') or p.get('prev_house_name'))),
                key=lambda r: (r[1], r[0]))

# --- the questions ------------------------------------------------------------
Q = json.load(open('data/research_questions.json'))['questions']
qs = [[q.get('area', ''), q.get('priority', ''), q['title'], q['slug']]
      for q in Q if q.get('area') != 'Answered']

summary = [
    ['Properties in the record', len(P)],
    ['  of them with no census in any round', len(nocensus)],
    ['  of them carrying no house name', len(noname)],
    ['Rounds a house is missing but is held either side', len(gaps)],
    ['Addresses the census gives that the list has not', len(tofind)],
    ['Census rows not yet filed to a house',
     sum(sum(v.values()) for v in unfiled.values())],
    ['Open questions', len(qs)],
    ['  answered', len(Q) - len(qs)],
]
for a in ('Missing census', 'Houses to find', 'Street numbering', 'House names',
          'Names to settle', 'People', 'Birthplaces and maps', 'The record itself', 'On foot'):
    summary.append([f'    {a}', sum(1 for q in qs if q[0] == a)])

sheet('Summary', ['', ''], summary, (56, 10))
sheet('Missing census', ['house', 'round missing', 'head when last seen', 'that round',
                         'head when next seen', 'that round', 'same family either side?'],
      gaps, (40, 14, 28, 12, 28, 12, 22))
sheet('No census at all', ['house', 'street', 'census-only record?', 'what is known'],
      nocensus, (40, 24, 18, 90))
sheet('Houses to find', ['the address as the page writes it', 'people', 'rounds'],
      tofind, (62, 9, 40))
sheet('Missing house names', ['house', 'street', 'rounds held', 'which'],
      noname, (40, 24, 12, 40))
sheet('Open questions', ['area', 'priority', 'question', 'slug'],
      qs, (22, 9, 100, 46))
del wb['Sheet']
for ws in wb.worksheets:
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical='top', wrap_text=False)

out = os.path.expanduser('~/Desktop/Park Houses - the baseline.xlsx')
wb.save(out)
print(f"Written: {out}")
for k, v in summary:
    print(f"  {k:<52} {v}")
