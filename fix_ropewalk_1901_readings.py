"""A. Hagues has settled the readings I flagged, and ruled out Standard Hill.

Confirmed as transcribed: Louise des Forges 49, Mary E Lee 40, Cabron, Annie M,
Hardstaff. Corrected: Kettlebell for Hallewell, Veasey for Vasey, Barns for
Betts, Damelia for Pamelia, and Kate Palethorpe's birthplace is Frith Bank in
Lincolnshire. Dore is Frederick's middle name, not part of the surname.

**Standard Hill is removed.** Those eight schedules are outside the record's
ground and should not have been entered.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
RENAME = [("Mary","Hallewell","Mary","Kettlebell"),
          ("Elizabeth","Vasey","Elizabeth","Veasey"),
          ("Catherine","Betts","Catherine","Barns"),
          ("Pamelia","Upton","Damelia","Upton")]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for ofn, oln, nfn, nln in RENAME:
    cur.execute("""SELECT p.id FROM people p JOIN census_entries ce ON ce.person_id=p.id
                    WHERE ce.census_year=1901 AND p.first_name=%s AND p.last_name=%s""", (ofn, oln))
    got = cur.fetchall()
    print(f"  {ofn} {oln} -> {nfn} {nln}  {got}")
cur.execute("""SELECT count(*) FROM census_entries
                WHERE census_year=1901 AND census_household_num BETWEEN 28 AND 35
                  AND unresolved_address ILIKE '%Standard Hill%'""")
print(f"  Standard Hill rows to remove: {cur.fetchone()[0]}")
if apply:
    for ofn, oln, nfn, nln in RENAME:
        cur.execute("""UPDATE people SET first_name=%s, last_name=%s
                        WHERE id IN (SELECT p.id FROM people p JOIN census_entries ce ON ce.person_id=p.id
                                      WHERE ce.census_year=1901 AND p.first_name=%s AND p.last_name=%s)""",
                    (nfn, nln, ofn, oln))
    cur.execute("""UPDATE census_entries SET birth_place='Frith Bank, Lincolnshire',
                      source = REPLACE(source,'the place of birth is a Lincolnshire name that cannot be '
                                 'read with confidence - Frodingham or Froxfield or similar',
                                 'the place of birth is Frith Bank, Lincolnshire, on A. Hagues'' reading')
                    WHERE census_year=1901 AND person_id IN
                      (SELECT id FROM people WHERE first_name='Kate' AND last_name='Palethorpe')""")
    cur.execute("""UPDATE people SET born_place='Frith Bank, Lincolnshire'
                    WHERE first_name='Kate' AND last_name='Palethorpe'""")
    cur.execute("""UPDATE census_entries
                      SET source = REPLACE(source, 'the surname is hard to read and may be Mordle or '
                            'Nordle; Dore is written in above the line and may be part of a '
                            'double-barrelled name',
                            'Dore is his middle name, on A. Hagues'' reading, not part of the surname')
                    WHERE census_year=1901 AND census_household_num=19""")
    for fn in ('M Dore','Freda Dore','Lionel Dore'):
        cur.execute("""UPDATE people SET first_name=REPLACE(first_name,' Dore','')
                        WHERE first_name=%s AND last_name='Nordle'""", (fn,))
    # Standard Hill is outside the record's ground
    cur.execute("""SELECT person_id FROM census_entries
                    WHERE census_year=1901 AND census_household_num BETWEEN 28 AND 35
                      AND unresolved_address ILIKE '%Standard Hill%'""")
    ids = [r[0] for r in cur.fetchall()]
    cur.execute("""DELETE FROM census_entries WHERE census_year=1901
                    AND census_household_num BETWEEN 28 AND 35
                    AND unresolved_address ILIKE '%Standard Hill%'""")
    n = cur.rowcount
    for pid in ids:
        cur.execute("SELECT count(*) FROM census_entries WHERE person_id=%s", (pid,))
        if cur.fetchone()[0] == 0:
            for t in ('property_residents','occupations','person_alias'):
                cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (pid,))
            cur.execute("DELETE FROM people WHERE id=%s", (pid,))
    c.commit()
    print(f"\n  readings corrected; {n} Standard Hill rows and their people removed")
    import os as _os
    f = 'data/people_1901_standard_hill_ropewalk_round.json'
    if _os.path.exists(f): _os.remove(f); print("  import file removed too")
else:
    print("\n  preview only - pass --apply")
