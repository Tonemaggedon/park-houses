# -*- coding: utf-8 -*-
"""The 1939 rows that came in with no source, and what is wrong with them.

Eighty 1939 rows across fifteen houses were imported early with no source line,
no schedule number and no ED. The RMGB pages show what that import did: it took
the **indexed** surname, which for a woman amended after 1939 is the married
name written over the original.

17 Lenton Road, schedule 143, proves it in one household - the record holds
Sleigh, Mason and Gannon, and the page has Hodkin, Padgett and Barefoot on the
line with those three names written above them in a later hand.

Until each is read from the page, the rows say so on their face.

  railway run python3 tools_flag_thin_1939_rows.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
NOTE = ("1939 Register - entered from an index rather than from the page, so this row carries no "
        "schedule number, no sub number and no enumeration district. **The surname may be a later "
        "amendment**: where this batch can be checked against the page, the index gives the "
        "married name written over the original and not the name the register had on the night. "
        "See the research question on the unsourced 1939 batch")

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT c.id, p.first_name, p.last_name, c.property_id
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                WHERE c.census_year = 1939 AND c.source IS NULL
                ORDER BY c.property_id, c.id""")
rows = cur.fetchall()
print(f"  {len(rows)} rows with no source at all")
if APPLY and rows:
    cur.execute("UPDATE census_entries SET source = %s WHERE id = ANY(%s)",
                (NOTE, [r[0] for r in rows]))
    c.commit()
    print("  flagged, committed")
else:
    print("  Add --apply to flag them.")
