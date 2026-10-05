"""The Newcastle Circus page settles four things.

**Schedule 248 is Castlethorpe**, on A. Hagues' reading - the household of
Louisa M Riley, 66 and widowed, which had been the last on that street with no
house. Three attempts to place it from the walk, from the ground and from the
earlier rounds had all failed.

**The family with her is GREIG, not Grey.** The page writes it plainly four
times over.

**Eileen M at 9 Park Drive is in under the stamp.** The page strikes her
surname through and stamps BAKER above it in green, so Baker is the married
name written in later and the struck one is what she bore on the night - the
same fault as the three on the Peveril Drive pages.

**5 South Road is schedule 250**, ticked and struck through on the same page.
The record already had it down as empty, but on a note that said only "1939
census" and gave no evidence - one of the nine stubs.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
CASTLETHORPE, SOUTHROAD5 = 206, 304
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1939
                AND census_household_num=248 AND property_id IS NULL""")
print(f"  schedule 248 -> Castlethorpe: {cur.fetchone()[0]} rows")
cur.execute("SELECT id, first_name FROM people WHERE last_name='Grey' AND id BETWEEN 9090 AND 9093")
print(f"  Grey -> Greig: {[r[1] for r in cur.fetchall()]}")
print("  Eileen M Baker -> Eileen M Canor, Baker kept as the later name")
print("  5 South Road: stub note replaced with schedule 250")

if apply:
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='Castlethorpe, Newcastle Circus', unresolved_address=NULL,
                          source = REPLACE(source, 'Newcastle Circus (no house given)',
                                   'Castlethorpe, Newcastle Circus - the page gives the street and no '
                                   'house; A. Hagues placed it at Castlethorpe, which with Burton House '
                                   'was the last pair left open on the circus')
                    WHERE census_year=1939 AND census_household_num=248 AND property_id IS NULL""",
                (CASTLETHORPE,))
    print(f"\n  {cur.rowcount} rows housed at Castlethorpe")

    cur.execute("UPDATE people SET last_name='Greig' WHERE last_name='Grey' AND id BETWEEN 9090 AND 9093")
    print(f"  {cur.rowcount} Greys renamed Greig")
    cur.execute("""UPDATE census_entries SET source = source || ' - entered as Grey until A. Hagues '
                        'sent the page, which writes Greig four times over'
                    WHERE person_id BETWEEN 9090 AND 9093 AND census_year=1939""")

    cur.execute("DELETE FROM person_alias WHERE person_id=9100")
    cur.execute("UPDATE people SET last_name='Canor' WHERE id=9100")
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   VALUES (9100,'Eileen M','Baker',1909,'1939 amendment (married name)')
                   ON CONFLICT DO NOTHING""")
    cur.execute("""UPDATE census_entries SET source = source || ' - entered as Eileen M Baker until '
                        'A. Hagues sent the page, which strikes her surname through and stamps BAKER '
                        'above it in green. The stamp is the married name written in afterwards'
                    WHERE person_id=9100 AND census_year=1939""")
    print("  Eileen M put the right way round")

    cur.execute("""UPDATE census_unoccupied
                      SET notes = '5 South Road, schedule 250 of the 1939 Register, ED letter code '
                                  'RMGB - written into the street between 2 Newcastle Circus at 249 '
                                  'and 9 Park Drive at 251, ticked and every column after it struck '
                                  'through. Read from the page by A. Hagues, which replaces a note '
                                  'that said only "1939 census" and gave no evidence.'
                    WHERE property_id=%s AND census_year=1939""", (SOUTHROAD5,))
    print(f"  5 South Road note replaced: {cur.rowcount}")
    c.commit()
else:
    print("\n  preview only - pass --apply")
