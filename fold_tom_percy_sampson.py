"""A probate notice in the Nottingham Evening News of 20 October 1950 joins up
four records of one man and resolves a house the record could not read.

Peray Sampson is Tom Percy Sampson. The reading is a misread Percy, and the
chain holds at every link: a lace manufacturer's son at 29 Lenton Avenue in
1901 and 1911; head of his own house on Derby Road by 1921, a Levers lace
manufacturer with a wife called Lilian; and at 4 Clinton Terrace - which is 133
Derby Road - in 1939, with Lilian Lucy. The notice names his firm as W. Sampson
Ltd. of Ruddington, and the W is his father, Walter Sampson of 29 Lenton Avenue.

It also settles the 1921 cover sheet, which the record had down as "129 over
what may be 133". It is 133 - the house he is still in eighteen years later.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
CLINTON4 = 74
FOLDS = [(2449, 7832, 'Peray', 'Sampson'), (8534, 7833, 'Lilian', 'Sampson')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for drop, keep, fn, ln in FOLDS:
    cur.execute("SELECT id, census_year FROM census_entries WHERE person_id=%s ORDER BY census_year", (drop,))
    print(f"  #{drop} {fn} {ln} -> #{keep}: rows {cur.fetchall()}")
cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1921
                AND unresolved_address ILIKE '%129 over%'""")
print(f"  1921 rows to rehouse at 4 Clinton Terrace: {cur.fetchone()[0]}")

BIO = ("Lace manufacturer, of W. Sampson Ltd. of Ruddington - the firm founded by his father Walter, "
       "who brought the family up at 29 Lenton Avenue. Tom Percy Sampson was still living with his "
       "parents and his sisters Flora and Effie at thirty-three, and by 1921 he had a house of his "
       "own at 133 Derby Road, the house that is also 4 Clinton Terrace, where the 1939 Register "
       "still finds him with his wife Lilian Lucy, a cook-housekeeper and a housemaid.\n\n"
       "He died in April 1950, aged seventy-two, by then living at 5 Holles Crescent, and left "
       "£52,983. His will gave the business to his nephew William M. Jones of Westwood, Clumber "
       "Road East, with a thousand pounds each to three long-serving employees and twenty-five to "
       "everyone else who had been ten years with the firm.\n\n"
       "He also left his china, pictures, silver and gold to Nottingham Corporation, to be shown at "
       "Nottingham Castle Museum as the Sampson Bequest, subject to a life interest for Emmeline "
       "D. L. Sampson. Reported in the Nottingham Evening News, 20 October 1950.")

if apply:
    for drop, keep, fn, ln in FOLDS:
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, made_by)
                       VALUES (%s,%s,%s,'A. Hagues') ON CONFLICT DO NOTHING""", (keep, fn, ln))
        cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=%s", (keep, drop))
        for t in ('property_residents', 'occupations'):
            cur.execute(f"UPDATE {t} SET person_id=%s WHERE person_id=%s", (keep, drop))
        cur.execute("DELETE FROM person_alias WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='4 Clinton Terrace (133 Derby Road)', unresolved_address=NULL,
                          source=REPLACE(source,'Derby Road (the cover sheet reads 129 over what may be 133)',
                                 '4 Clinton Terrace (133 Derby Road) - the cover sheet reads 129 over what may be 133, '
                                 'and 133 is right: Tom Percy Sampson is still in the house in 1939')
                    WHERE census_year=1921 AND unresolved_address ILIKE %s""", (CLINTON4, '%129 over%'))
    print(f"  {cur.rowcount} rows of the 1921 household rehoused")
    cur.execute("""UPDATE people SET died_year=1950, died_date='April 1950', bio=%s,
                          significant=TRUE, significant_by='A. Hagues',
                          significance_note='Lace manufacturer who left his collection to Nottingham Castle Museum as the Sampson Bequest'
                    WHERE id=7832""", (BIO,))
    c.commit(); print("\n  folded, rehoused, and Tom Percy Sampson written up")
else:
    print("\n  preview only - pass --apply")
