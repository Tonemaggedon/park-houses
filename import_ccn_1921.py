#!/usr/bin/env python3
"""
Import 1921CCN template sheet into Railway PostgreSQL.
Run with: DATABASE_URL='postgres://...' python3 import_ccn_1921.py
"""
import os, sys, openpyxl, psycopg2

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1921censuspark.xlsx')
SHEET = '1921ccntemplate'

# Map house number → property_id (from all_props.json CCN entries)
HOUSE_TO_PROP = {
    1: 21, 3: 22, 5: 23, 7: 24, 9: 25, 10: 26,
    11: 27, 12: 28, 14: 29, 15: 30, 16: 31, 17: 32,
    18: 33, 19: 34, 20: 35, 22: 36, 24: 36,
}

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var required"); sys.exit(1)

db = psycopg2.connect(DATABASE_URL)
cur = db.cursor()

wb = openpyxl.load_workbook(FILE, data_only=True)
ws = wb[SHEET]

inserted_people = 0
skipped_people = 0
inserted_census = 0
skipped_census = 0
no_address = 0

SKIP_VALS = {'last name','first name(s)','first name','id','largest household',None,''}

for row in ws.iter_rows(min_row=3, values_only=True):
    house_id = row[0]   # Col A: CCN1, CCN2, etc.
    location = row[3]   # Col D: Cavendish Crescent North
    house_no = row[5]   # Col F: house number
    ln       = row[6]   # Col G: last name
    fn       = row[7]   # Col H: first name
    age      = row[20]  # Col U: age
    occ      = row[27]  # Col AB: occupation
    rel_head = row[14]  # Col O: relationship

    if not fn or not ln: continue
    if str(fn).lower().strip() in SKIP_VALS: continue
    if str(ln).lower().strip() in SKIP_VALS: continue

    fn = str(fn).strip()
    ln = str(ln).strip()

    # Strip title prefix from first name if present
    title = None
    for t in ('Sir ','Lady ','Dr ','Rev ','Prof ','Major ','Colonel ','Captain '):
        if fn.startswith(t):
            title = t.strip(); fn = fn[len(t):].strip(); break

    # Calculate born_year
    born_year = (1921 - int(age)) if age and str(age).isdigit() else None
    if age:
        try: born_year = 1921 - int(float(str(age)))
        except: born_year = None

    # Find property_id
    prop_id = None
    if house_no:
        try: prop_id = HOUSE_TO_PROP.get(int(float(str(house_no))))
        except: pass

    # Unresolved address
    if not prop_id:
        unres = 'Cavendish Crescent North'
    else:
        unres = None

    # Occupation cleanup
    occ_val = str(occ).strip() if occ and str(occ).strip() not in ('-','None','') else None

    # Relationship
    rel_val = str(rel_head).strip() if rel_head else None

    # Upsert person
    cur.execute("""
        INSERT INTO people (first_name, last_name, born_year, title)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
    """, (fn, ln, born_year, title))
    row_result = cur.fetchone()
    if row_result:
        person_id = row_result[0]
        inserted_people += 1
    else:
        cur.execute("SELECT id FROM people WHERE LOWER(first_name)=LOWER(%s) AND LOWER(last_name)=LOWER(%s)", (fn, ln))
        r = cur.fetchone()
        if not r:
            print(f"  WARN: could not find person {fn} {ln}"); continue
        person_id = r[0]
        skipped_people += 1

    # Insert census entry
    cur.execute("""
        SELECT id FROM census_entries
        WHERE person_id=%s AND census_year=1921
    """, (person_id,))
    if cur.fetchone():
        skipped_census += 1
        continue

    cur.execute("""
        INSERT INTO census_entries
          (person_id, property_id, census_year, relationship, age_at_census,
           occupation_at_census, source, unresolved_address)
        VALUES (%s, %s, 1921, %s, %s, %s, %s, %s)
    """, (person_id, prop_id, rel_val,
          int(float(str(age))) if age else None,
          occ_val, 'National Archives 1921 Census', unres))
    inserted_census += 1

db.commit()
db.close()

print(f"\nDone:")
print(f"  People inserted: {inserted_people}, skipped (already exist): {skipped_people}")
print(f"  Census entries inserted: {inserted_census}, skipped (already exist): {skipped_census}")
