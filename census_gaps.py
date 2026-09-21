#!/usr/bin/env python3
"""
The last head of each house before a gap in its census record.

A house the record holds in 1891 and again in 1911 has a hole in 1901, and the
useful thing to know about that hole is not that it exists - it is WHO WAS
LIVING THERE when the record last saw the house. A head's name and trade is
what finds the household on the next return: the family is usually still there,
or the directory names their successor.

So this walks every property the record holds anybody in, finds the census
years it is missing between the first and last year it DOES hold, and prints
the head of the household immediately before each gap, with the head after it
where there is one. A gap flanked by the same family is a transcription job; a
gap flanked by two different families is a move, and wants the directory.

It reads and changes nothing.

Usage:
  railway run python3 census_gaps.py                 # every gap, street by street
  railway run python3 census_gaps.py --year 1901     # only houses missing that year
  railway run python3 census_gaps.py --street "Lenton Road"
  railway run python3 census_gaps.py --xlsx          # also write it to the Desktop
"""

import os, re, sys, json, argparse
import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))

# The rounds this record is built on. 1861 and 1871 are held for a handful of
# houses only, and 1939 is a register rather than a census, so a house missing
# from those is not a gap in any meaningful sense - it is the ordinary state of
# the record. Gaps are measured across the five full rounds.
SPINE = [1881, 1891, 1901, 1911, 1921]
CONTEXT = [1861, 1871, 1939]


def database_url():
    """Railway injects the internal host, which only resolves inside Railway's
    own network. The public URL is the one that works from a laptop."""
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 '
                         + os.path.basename(__file__))
    return v


ap = argparse.ArgumentParser(add_help=False)
ap.add_argument('--year', type=int)
ap.add_argument('--street')
ap.add_argument('--xlsx', action='store_true')
ap.add_argument('-h', '--help', action='help')
args = ap.parse_args()

props = {p['id']: p for p in json.load(open(os.path.join(HERE, 'data', 'all_props.json')))}


def label(pid):
    p = props.get(pid)
    if not p:
        return f'#{pid}'
    return (p.get('address') or f"{p.get('no','')} {p.get('street','')}").strip() or f'#{pid}'


conn = psycopg2.connect(database_url())
conn.set_session(readonly=True)
cur = conn.cursor()

# One row per property per year: the head if the return names one, and the size
# of the household either way. DISTINCT ON takes the head where a year has one,
# because 'Head' sorts before every other relationship once nulls are last.
cur.execute("""
    SELECT ce.property_id, ce.census_year,
           COUNT(*) OVER (PARTITION BY ce.property_id, ce.census_year) AS n,
           p.id, p.first_name, p.last_name, ce.relationship, ce.occupation_at_census
      FROM census_entries ce
      JOIN people p ON p.id = ce.person_id
     WHERE ce.property_id IS NOT NULL
     ORDER BY ce.property_id, ce.census_year,
              (CASE WHEN LOWER(COALESCE(ce.relationship,'')) LIKE 'head%' THEN 0 ELSE 1 END),
              ce.id""")

houses = {}
for pid, year, n, person, fn, ln, rel, occ in cur.fetchall():
    slot = houses.setdefault(pid, {}).setdefault(year, None)
    if slot is None:
        houses[pid][year] = dict(n=n, person=person, name=f'{fn or ""} {ln or ""}'.strip(),
                                 rel=rel, occ=occ)

rows = []
for pid, years in houses.items():
    held = sorted(y for y in years if y in SPINE)
    if len(held) < 2:
        continue
    missing = [y for y in SPINE if held[0] < y < held[-1] and y not in years]
    for y in missing:
        before = max(h for h in held if h < y)
        after = min(h for h in held if h > y)
        b, a = years[before], years[after]
        same = (b['name'].split()[-1:] == a['name'].split()[-1:]) and b['name'] and a['name']
        rows.append(dict(
            pid=pid, house=label(pid),
            street=(props.get(pid, {}) or {}).get('street', ''),
            missing=y,
            before_year=before, before=b['name'], before_rel=b['rel'],
            before_occ=b['occ'] or '', before_n=b['n'],
            after_year=after, after=a['name'], after_n=a['n'],
            verdict='same family either side - very likely still there'
                    if same else 'different families either side - somebody moved',
            other=' '.join(str(c) for c in CONTEXT if c in years)))

if args.year:
    rows = [r for r in rows if r['missing'] == args.year]
if args.street:
    rows = [r for r in rows if args.street.lower() in (r['street'] or '').lower()]
rows.sort(key=lambda r: (r['missing'], r['street'] or '', r['pid']))

# A gap on one house is a job; the same gap on a whole street is a ROUND that
# was never transcribed, and that is the thing worth targeting. Group them.
blocks = {}
for r in rows:
    blocks.setdefault((r['street'] or '(no street)', r['before_year'], r['after_year']), []).append(r)
big = sorted((k, v) for k, v in blocks.items() if len(v) >= 3)
if big and not args.street:
    print('WHOLE STRETCHES OF ONE STREET, MISSING THE SAME ROUND')
    print('   These are enumerator rounds nobody has transcribed, not houses that went quiet.\n')
    for (street, b, a), v in sorted(big, key=lambda t: -len(t[1])):
        def housekey(n):
            m = re.match(r'(\d+)(.*)', n or '')
            return (0, int(m.group(1)), m.group(2)) if m else (1, 0, n or '')
        nums = ', '.join(sorted(((props.get(r['pid'], {}) or {}).get('no')
                                 or (props.get(r['pid'], {}) or {}).get('name') or '?'
                                 for r in v), key=housekey))
        print(f'   {street:<26} {len(v):>3} houses   last seen {b} -> next seen {a}')
        print(f'   {"":<26}     {nums}')
    print()

print(f'Houses with a hole in their census record: {len(rows)}'
      + (f"  (missing {args.year})" if args.year else '')
      + (f"  on {args.street}" if args.street else ''))
print('Measured across', ', '.join(str(y) for y in SPINE),
      '- a house is only counted where the record holds it both before and after.\n')

cur_year = None
for r in rows:
    if r['missing'] != cur_year:
        cur_year = r['missing']
        n = sum(1 for x in rows if x['missing'] == cur_year)
        print(f'\n──── MISSING {cur_year} ─── {n} house(s) ' + '─' * 34)
    print(f"\n  {r['house']}   (#{r['pid']})")
    print(f"      last seen {r['before_year']}: {r['before']}"
          + (f", {r['before_occ']}" if r['before_occ'] else '')
          + f"  — {r['before_n']} in the house")
    print(f"      next seen {r['after_year']}: {r['after']}  — {r['after_n']} in the house")
    print(f"      {r['verdict']}" + (f"   [also holds {r['other']}]" if r['other'] else ''))

if args.xlsx and rows:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook(); ws = wb.active; ws.title = 'Census gaps'
    heads = ['missing', 'house', 'property', 'last seen', 'head then', 'their trade',
             'size', 'next seen', 'head then', 'size', 'reading']
    ws.append(heads)
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='2F4858')
    for r in rows:
        ws.append([r['missing'], r['house'], f"#{r['pid']}", r['before_year'], r['before'],
                   r['before_occ'], r['before_n'], r['after_year'], r['after'], r['after_n'],
                   r['verdict']])
    for i, w in enumerate([9, 30, 10, 10, 26, 30, 7, 10, 26, 7, 46], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(vertical='top', wrap_text=True)
    ws.freeze_panes = 'A2'
    out = os.path.expanduser('~/Desktop/Census gaps.xlsx')
    wb.save(out)
    print(f'\nWritten: {out}')

cur.close()
conn.close()
