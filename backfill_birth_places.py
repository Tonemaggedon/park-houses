#!/usr/bin/env python3
"""
Backfill birth_place in census_entries from the 1911 and 1921 spreadsheets.
Matches by first_name + last_name + census_year.
"""

import os, psycopg2, openpyxl

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

updated = 0
skipped = 0
not_found = []

SKIP_NAMES = {'first name(s)', 'last name', 'family', 'name', 'birth place', 'born', 'bl 1921', 'bl'}

def is_junk(val):
    if not val: return True
    s = str(val).strip()
    if not s or s in ('None', '-', ''): return True
    # Skip header rows
    if s.lower() in SKIP_NAMES: return True
    # Skip purely numeric strings (totals)
    try: float(s); return True
    except ValueError: pass
    return False

def update_birth_place(first, last, year, birth_place):
    global updated, skipped
    if is_junk(first) or is_junk(last): return
    if not birth_place or str(birth_place).strip() in ('', 'None', '-'): return
    bp = str(birth_place).strip()
    fn = str(first).strip()
    ln = str(last).strip()

    # Exact first name match
    cur.execute("""
        UPDATE census_entries ce
        SET birth_place = %s
        FROM people p
        WHERE ce.person_id = p.id
          AND ce.census_year = %s
          AND LOWER(TRIM(p.first_name)) = LOWER(%s)
          AND LOWER(TRIM(p.last_name)) = LOWER(%s)
          AND ce.birth_place IS NULL
    """, (bp, year, fn, ln))
    if cur.rowcount > 0:
        updated += cur.rowcount
        return

    # Fallback: match on first word of first name + exact last name
    # Only update if exactly one census entry matches (avoids false matches)
    first_word = fn.split()[0]
    cur.execute("""
        SELECT ce.id FROM census_entries ce
        JOIN people p ON p.id = ce.person_id
        WHERE ce.census_year = %s
          AND LOWER(TRIM(p.first_name)) = LOWER(%s)
          AND LOWER(TRIM(p.last_name)) = LOWER(%s)
          AND ce.birth_place IS NULL
    """, (year, first_word, ln))
    rows = cur.fetchall()
    if len(rows) == 1:
        cur.execute("UPDATE census_entries SET birth_place = %s WHERE id = %s", (bp, rows[0][0]))
        updated += 1
    else:
        not_found.append(f"{year} | {fn} {ln} | {bp}")
        skipped += 1

# ── 1911 sheets ──────────────────────────────────────────────────────────────
print("Reading 1911 spreadsheet…")
wb11 = openpyxl.load_workbook('1911censusmasterlinzij.xlsx', read_only=True, data_only=True)
SHEETS_11 = ['Park Drive', 'Peveril Drive', 'southrd p 168', 'Kenilworthrd p 259', 'North Rd']

for sheet in SHEETS_11:
    if sheet not in wb11.sheetnames:
        continue
    ws = wb11[sheet]
    for row in ws.iter_rows(min_row=3, values_only=True):
        last  = row[4]   # Col E: Family
        first = row[5]   # Col F: Name
        born  = row[29]  # Col AD: birth place text (col 28 is a binary flag)
        if not first or not last:
            continue
        update_birth_place(first, last, 1911, born)

# ── 1921 simple sheets (col layout: 0=first, 1=last, 6=birthplace) ──────────
print("Reading 1921 spreadsheet…")
wb21 = openpyxl.load_workbook('1921censuspark.xlsx', read_only=True, data_only=True)

SHEETS_21_SIMPLE = ['1921CCN', '1921pelhamcres', '1921WT',
                    '1921LC', '1921NC', '1921PkD', '1921peD']

for sheet in SHEETS_21_SIMPLE:
    if sheet not in wb21.sheetnames:
        continue
    ws = wb21[sheet]
    for row in ws.iter_rows(min_row=2, values_only=True):
        first = row[0]  # Col A: First name(s)
        last  = row[1]  # Col B: Last name
        born  = row[6]  # Col G: Birth place
        if not first or not last:
            continue
        update_birth_place(first, last, 1921, born)

# ── Sheets with layout: 6=last, 7=first, 31=born (1921bl, 1921ccntemplate) ──
for sheet, born_col in [('1921bl', 31), ('1921ccntemplate', 37)]:
    if sheet not in wb21.sheetnames:
        continue
    ws = wb21[sheet]
    for row in ws.iter_rows(min_row=2, values_only=True):
        last  = row[6]         # Col G: Family
        first = row[7]         # Col H: Name
        born  = row[born_col]
        update_birth_place(first, last, 1921, born)

conn.commit()
cur.close()
conn.close()

print(f"\nUpdated:   {updated}")
print(f"Not found: {skipped}")
if not_found:
    print("\nNot matched (name may differ between spreadsheet and DB):")
    for nf in not_found[:40]:
        print(f"  {nf}")
