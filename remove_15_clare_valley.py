"""There is no 15 Clare Valley. A. Hagues has been to the street.

The record held it as a property on the strength of one household - John
Holland Walker's, in 1921 - and that household is at **15 Park Valley**, where
the record already has the same man in 1911 and again in 1939. A single
mis-filed round had invented a house.

So the four 1921 rows move to 15 Park Valley and the property goes.

A. Hagues also read **5 Clare Valley** as ticked and left blank, which closes
the street: 1, 2, 4, Grove House, Ribble Lodge, Springdale and The Spinney all
have households, and 3 and 5 are blank.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
GONE, PARKVALLEY15, CLARE5 = 386, 268, 63
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.id, p.first_name, p.last_name, ce.census_year
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id=%s ORDER BY ce.id""", (GONE,))
rows = cur.fetchall()
for r in rows: print(f"  row{r[0]} {r[1]} {r[2]} ({r[3]}) -> 15 Park Valley")
cur.execute("SELECT count(*) FROM census_entries WHERE property_id=%s", (PARKVALLEY15,))
print(f"  15 Park Valley already holds {cur.fetchone()[0]} rows")

if apply:
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='15 Park Valley', unresolved_address=NULL,
                          source = source || ' - filed at 15 Clare Valley until A. Hagues '
                                   'established that no such house exists; John Holland Walker is '
                                   'at 15 Park Valley in 1911 and again in 1939'
                    WHERE property_id=%s""", (PARKVALLEY15, GONE))
    print(f"\n  {cur.rowcount} rows moved")
    for t in ('coords', 'property_data', 'property_names', 'property_research',
              'property_residents', 'property_watches', 'census_unoccupied'):
        try:
            cur.execute(f"DELETE FROM {t} WHERE property_id=%s", (GONE,))
        except Exception:
            c.rollback(); continue
        if cur.rowcount: print(f"  {t}: {cur.rowcount} row removed")
    NOTE = ("5 Clare Valley, ticked and left blank in the 1939 Register - nobody was living there "
            "on the night of 29 September 1939. Read from the page by A. Hagues. The schedule "
            "number is not yet recorded against it.")
    cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes) VALUES (%s,1939,%s)
                   ON CONFLICT (property_id, census_year) DO UPDATE SET notes=EXCLUDED.notes""",
                (CLARE5, NOTE))
    c.commit()
    d = json.load(open('data/all_props.json'))
    before = len(d)
    d = [p for p in d if p['id'] != GONE]
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"  property list: {before} -> {len(d)}")
    print("  5 Clare Valley closed as blank")
else:
    print("\n  preview only - pass --apply")
