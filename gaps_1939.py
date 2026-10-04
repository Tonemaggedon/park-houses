# -*- coding: utf-8 -*-
"""What the 1939 Register still owes the record, in lists a person can work.

Four sheets, each a different kind of gap:

  Houses with no 1939   - the real work. A house the record holds in 1911 or
                          1921 and has nothing for in 1939, with the last
                          household it saw there, which is what to look for on
                          the page.
  Schedule gaps         - numbers missing from each book's run. A gap here is
                          either a household not yet sent or a schedule that
                          never existed.
  Unfiled 1939 rows     - people transcribed but not yet put in a house.
  Rows naming no book   - 1939 rows whose source does not say RMGB or RMGC, so
                          the schedule-gap lists cannot see them.
  Houses the Register
  names                 - an address the 1939 Register gives that the property
                          list does not hold. These are houses to ADD, not
                          households to find: the people are already in the
                          record, waiting on a house.
  Marked empty in 1939  - houses the record says nobody was in. These are NOT
                          counted as gaps. Nine of them rest on a stub note
                          saying only "1939 census", and one such mark was
                          found wrong: 21 Lenton Avenue was marked empty and
                          holds schedule 176, five people, properly sourced.

  railway run python3 gaps_1939.py
"""
import os, re, json, psycopg2, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

HEAD = Font(bold=True, color='FFFFFF')
BAR = PatternFill('solid', fgColor='2F5D3A')
SUB = Font(bold=True)


def sheet(wb, title, cols, rows, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    ws.append(cols)
    for i, cell in enumerate(ws[1], start=1):
        cell.font, cell.fill = HEAD, BAR
        cell.alignment = Alignment(vertical='center')
    for r in rows:
        ws.append(r)
    for i, w in enumerate(cols, start=1):
        width = max([len(str(w))] + [len(str(r[i-1])) for r in rows[:400] if len(r) >= i]) + 2
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = min(width, 60)
    ws.freeze_panes = 'A2'
    return ws


def main():
    ps = json.load(open('data/all_props.json'))
    props = {p['id']: p for p in ps}
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    cur.execute("""SELECT property_id, census_year, COUNT(*) FROM census_entries
                    WHERE property_id IS NOT NULL GROUP BY 1,2""")
    held = {}
    for pid, yr, n in cur.fetchall():
        held.setdefault(pid, {})[yr] = n
    # a house the Register marks EMPTY is not a gap - it is an answer
    cur.execute("SELECT property_id, notes FROM census_unoccupied WHERE census_year=1939")
    empty = {pid: (notes or '') for pid, notes in cur.fetchall()}

    def street(a):
        return re.sub(r'^[\d/a-zA-Z]+\s+', '', a).split(',')[-1].strip()

    gap_rows = []
    for pid, years in held.items():
        if 1939 in years or pid in empty:
            continue
        last = max(years)
        if last < 1891:
            continue
        addr = props.get(pid, {}).get('address', f'property {pid}')
        cur.execute("""SELECT p.first_name || ' ' || p.last_name, ce.occupation_at_census
                         FROM census_entries ce JOIN people p ON p.id=ce.person_id
                        WHERE ce.property_id=%s AND ce.census_year=%s
                          AND lower(COALESCE(ce.relationship,'')) IN ('head','head (widow)')
                        LIMIT 1""", (pid, last))
        h = cur.fetchone()
        gap_rows.append([street(addr), addr, pid, last, years[last],
                         h[0] if h else '', (h[1] if h else '') or ''])
    gap_rows.sort(key=lambda r: (r[0], r[1]))

    wb = openpyxl.Workbook()
    sheet(wb, 'Houses with no 1939',
          ['Street', 'House', 'Property', 'Last round held', 'People then',
           'Head of the house then', 'and his or her trade'],
          gap_rows, first=True)

    sched = []
    for book in ('RMGB', 'RMGC'):
        cur.execute("""SELECT DISTINCT census_household_num FROM census_entries
                        WHERE census_year=1939 AND source ILIKE %s
                          AND census_household_num IS NOT NULL ORDER BY 1""", (f'%{book}%',))
        have = [r[0] for r in cur.fetchall()]
        if not have:
            continue
        run = None
        for n in range(min(have), max(have) + 1):
            if n not in have and run is None:
                run = n
            elif n in have and run is not None:
                sched.append([book, run, n - 1, n - run]); run = None
        if run is not None:
            sched.append([book, run, max(have), max(have) - run + 1])
    sheet(wb, 'Schedule gaps', ['Book', 'From', 'To', 'How many'], sched)

    cur.execute("""SELECT COALESCE(ce.unresolved_address,'(no address at all)'),
                          ce.census_household_num, p.id, p.first_name || ' ' || p.last_name,
                          ce.age_at_census, ce.occupation_at_census
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.census_year=1939 AND ce.property_id IS NULL
                    ORDER BY 1, ce.id""")
    sheet(wb, 'Unfiled 1939 rows',
          ['Address as the page gives it', 'Schedule', 'Person', 'Name', 'Age', 'Trade'],
          [list(r) for r in cur.fetchall()])

    cur.execute("""SELECT ce.census_household_num, p.id, p.first_name || ' ' || p.last_name,
                          COALESCE(NULLIF(ce.address,''), ce.unresolved_address), LEFT(ce.source, 80)
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.census_year=1939
                      AND (ce.source IS NULL OR (ce.source NOT ILIKE '%RMGB%'
                                                 AND ce.source NOT ILIKE '%RMGC%'))
                    ORDER BY ce.census_household_num, ce.id""")
    sheet(wb, 'Rows naming no book',
          ['Schedule', 'Person', 'Name', 'House', 'What the source says'],
          [list(r) for r in cur.fetchall()])

    cur.execute("""SELECT property_id, notes FROM census_unoccupied WHERE census_year=1939
                    ORDER BY property_id""")
    emp = []
    for pid, notes in cur.fetchall():
        notes = notes or ''
        emp.append([props.get(pid, {}).get('address', f'property {pid}'), pid,
                    'cites the page' if len(notes) > 60 else 'STUB - no evidence given',
                    notes[:200]])
    sheet(wb, 'Marked empty in 1939',
          ['House', 'Property', 'How well evidenced', 'What the note says'], emp)

    # houses the Register names that the property list does not hold
    cur.execute("""SELECT ce.unresolved_address, COUNT(*), MIN(ce.census_household_num),
                          STRING_AGG(DISTINCT CASE WHEN ce.source ILIKE '%RMGA%' THEN 'RMGA'
                                                   WHEN ce.source ILIKE '%RMGB%' THEN 'RMGB'
                                                   WHEN ce.source ILIKE '%RMGC%' THEN 'RMGC'
                                                   ELSE '?' END, '/'),
                          STRING_AGG(DISTINCT p.first_name || ' ' || p.last_name, ', ')
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.census_year=1939 AND ce.property_id IS NULL
                      AND ce.unresolved_address IS NOT NULL
                    GROUP BY 1 ORDER BY 1""")
    known = [str(p.get('address', '')).lower() for p in ps]
    nothouse = []
    for a, n, schednum, book, who in cur.fetchall():
        core = re.sub(r'\s*\(.*?\)\s*', ' ', a).strip().rstrip(',')
        # the first distinctive word - a house name, or a number
        word = next((w for w in re.split(r'[ ,]+', core) if len(w) > 3), core).lower()
        seen = any(word in k for k in known)
        nothouse.append([a, schednum, book or '?', n,
                         'the list has something like it' if seen else 'NOT IN THE PROPERTY LIST',
                         (who or '')[:120]])
    sheet(wb, 'Houses the Register names',
          ['Address as the page gives it', 'Schedule', 'Book', 'People',
           'In the property list?', 'Who is in it'], nothouse)

    out = os.path.expanduser('~/Desktop/1939 - what is left.xlsx')
    wb.save(out)
    print(f"  {len(gap_rows)} houses with no 1939 round")
    print(f"  {len(sched)} runs of missing schedule numbers")
    print(f"  written to {out}")


if __name__ == '__main__':
    main()
