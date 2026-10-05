"""Two 1939 households each carry one person twice, the second time unhoused.

They were found by matching the house names in unhoused rows against every name
a property has ever carried, including **prev_house_name** - a field the record
holds and nothing had been reading.

  Brightlands (1), Clumber Road East is **Adam House**, which already holds
  schedule 71. Margery Alice **Marsh** and Margery Alice **Cooper** share a
  birth date, an age, an occupation and that schedule.

  Edgmond, 143a Derby Road is **Edgemont House**, which already holds schedule
  197 - a boarding house of thirty. **Ruth Smith** and **Ruby Rogers** share a
  birth date, an age, an occupation and that schedule.

In each case the housed row is kept and the stray folded into it, with the
other reading held as a variant.

**The direction wants checking against the page.** Four women on these pages
have already been found entered under the married name stamped over the entry
rather than the name they bore on the night, so which of Marsh and Cooper is
which is not settled here. Ruth Smith against Ruby Rogers is a different
difficulty - both forename and surname differ, which is not one name read two
ways but two readings of one line.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
FOLDS = [(8597, 7529, 'Margery Alice', 'Marsh', 'Cooper', 71, 'Adam House'),
         (8615, 7870, 'Ruth', 'Smith', 'Ruby Rogers', 197, 'Edgemont House')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for drop, keep, fn, was, kept, sched, house in FOLDS:
    cur.execute("SELECT id FROM census_entries WHERE person_id=%s", (drop,))
    print(f"  #{drop} {fn} {was} -> #{keep} ({kept}) at {house}, schedule {sched}; rows {[r[0] for r in cur.fetchall()]}")
if apply:
    for drop, keep, fn, was, kept, sched, house in FOLDS:
        kf, kl = (kept.split(' ', 1) + [''])[:2] if ' ' in kept else (fn, kept)
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),'A. Hagues'
                         FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(%s)
                          AND LOWER(TRIM(a.last_name))=LOWER(%s))""", (keep, fn, was, keep, fn, was))
        cur.execute("""UPDATE census_entries
                          SET source = source || ' - the record held this person twice on this '
                                'schedule, the second time unhoused and read as ' || %s ||
                                '. Folded. WHICH READING IS RIGHT IS NOT SETTLED: four women on '
                                'these pages have been found entered under the married name '
                                'stamped over the entry rather than the name borne on the night'
                        WHERE person_id=%s AND census_year=1939
                          AND source NOT ILIKE '%%held this person twice%%'""",
                    (f"{fn} {was}", keep))
        cur.execute("DELETE FROM census_entries WHERE person_id=%s", (drop,))
        for t in ('property_residents', 'occupations', 'person_alias'):
            cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    c.commit()
    print("\n  both folded")
    cur.execute("""SELECT count(DISTINCT census_household_num) FROM census_entries
                    WHERE census_year=1939 AND property_id IS NULL""")
    print(f"  1939 households still with no house: {cur.fetchone()[0]}")
else:
    print("\n  preview only - pass --apply")
