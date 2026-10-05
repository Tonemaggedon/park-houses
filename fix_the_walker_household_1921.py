# -*- coding: utf-8 -*-
"""Two faults in the 1921 household at 2 Huntingdon Drive.

**Florence Maripalker is Florence Walker.** The index has run her surname
together with her middle name. Walker is certain - her mother heads the house,
her brother is Robert C Walker and her sister Elizabeth Walker - and *Mari* is
what is left when Walker is taken off the end. Entered as Florence Mari Walker
with the index reading kept as a variant.

**Elizabeth Olivers and Elizabeth Oliver are one woman.** Born 1886 at
Ruddington, a domestic nurse, in this same household in 1911 at 25 and in 1921
at 35. The 1911 reading has a stray s. Folded, keeping Oliver, with Olivers as
a variant - she is the only servant in the house across both rounds, which is
ten years with the same family.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
FLORENCE, KEEP_OLIVER, DROP_OLIVERS = 2117, 2119, 5151
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT id,first_name,last_name,born_year FROM people WHERE id IN (%s,%s,%s)",
            (FLORENCE, KEEP_OLIVER, DROP_OLIVERS))
for r in cur.fetchall(): print("  ", r)
if apply:
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   VALUES (%s,'Florence','Maripalker',1916,'A. Hagues') ON CONFLICT DO NOTHING""", (FLORENCE,))
    cur.execute("UPDATE people SET first_name='Florence Mari', last_name='Walker' WHERE id=%s", (FLORENCE,))
    cur.execute("""UPDATE census_entries SET source = source || ' - the index runs her surname '
                        'together with her middle name and gives Florence Maripalker. Walker is '
                        'certain: her mother heads the house and her brother and sister are both '
                        'Walkers. Mari is what is left when Walker is taken off the end'
                    WHERE person_id=%s AND source NOT ILIKE '%%runs her surname%%'""", (FLORENCE,))
    print("  Florence renamed")
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   VALUES (%s,'Elizabeth','Olivers',1886,'A. Hagues') ON CONFLICT DO NOTHING""", (KEEP_OLIVER,))
    cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=%s", (KEEP_OLIVER, DROP_OLIVERS))
    for t in ('property_residents','occupations','person_alias'):
        cur.execute(f"UPDATE {t} SET person_id=%s WHERE person_id=%s", (KEEP_OLIVER, DROP_OLIVERS)) \
            if t != 'person_alias' else cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (DROP_OLIVERS,))
    cur.execute("""UPDATE people SET born_place=COALESCE(born_place,'Ruddington, Nottinghamshire')
                    WHERE id=%s""", (KEEP_OLIVER,))
    cur.execute("DELETE FROM people WHERE id=%s", (DROP_OLIVERS,))
    cur.execute("""UPDATE census_entries SET source = source || ' - the 1911 reading gives her '
                        'surname as Olivers; she is the same woman, born 1886 at Ruddington, nurse '
                        'to this family in 1911 and still with them in 1921'
                    WHERE person_id=%s AND source NOT ILIKE '%%Olivers%%'""", (KEEP_OLIVER,))
    c.commit()
    print("  Elizabeth Oliver folded")
    cur.execute("""SELECT ce.census_year,p.id,p.first_name,p.last_name,ce.age_at_census,ce.relationship
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.property_id=144 AND ce.census_year IN (1911,1921)
                    ORDER BY ce.census_year, ce.id""")
    print("\n  2 Huntingdon Drive now:")
    for r in cur.fetchall(): print(f"     {r[0]} #{r[1]:<5} {r[2]} {r[3]:<14} age{r[4]:<4} {r[5]}")
else:
    print("\n  preview only - pass --apply")
