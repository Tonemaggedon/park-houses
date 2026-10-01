# -*- coding: utf-8 -*-
"""Two people of one name, each holding both their rows.

This is not a weld and it does not want a split. An import that matches on a
name alone gives **each** of two same-named people a copy of the **other's**
census row, so both end up in two houses in one round and the record has four
rows where it should have two.

The extra rows are the ones the import just made, and they are told apart by
arithmetic: a row belongs to the person whose birth year agrees with the age on
it. Where another person of the same name already holds that exact row and the
ages agree with *them* and not with this one, the copy comes out.

  railway run python3 tools_drop_crisscrossed_rows.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
YEAR_SLACK = 2

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT c.person_id, c.census_year FROM census_entries c
                WHERE c.property_id IS NOT NULL GROUP BY 1,2
               HAVING COUNT(DISTINCT c.property_id) > 1""")
suspects = cur.fetchall()
drop = []
for pid, yr in suspects:
    cur.execute("""SELECT c.id, c.property_id, c.age_at_census, p.born_year, p.first_name, p.last_name
                     FROM census_entries c JOIN people p ON p.id = c.person_id
                    WHERE c.person_id = %s AND c.census_year = %s ORDER BY c.id""", (pid, yr))
    rows = cur.fetchall()
    for cid, prop, age, born, fn, ln in rows:
        if age is None or born is None:
            continue
        mine = abs((yr - age) - born) <= YEAR_SLACK
        if mine:
            continue
        # somebody else of the same name holds this house this round, and it fits them
        cur.execute("""SELECT c2.id, p2.id, p2.born_year FROM census_entries c2
                         JOIN people p2 ON p2.id = c2.person_id
                        WHERE c2.census_year = %s AND c2.property_id = %s AND c2.person_id <> %s
                          AND LOWER(p2.first_name) = LOWER(%s) AND LOWER(p2.last_name) = LOWER(%s)""",
                    (yr, prop, pid, fn, ln))
        for cid2, pid2, born2 in cur.fetchall():
            if born2 is not None and abs((yr - age) - born2) <= YEAR_SLACK:
                drop.append((cid, pid, fn, ln, yr, prop, age, born, pid2))
                break

for cid, pid, fn, ln, yr, prop, age, born, keeper in drop:
    print(f"  row {cid}: {fn} {ln} #{pid} (born {born}) holds a {yr} row aged {age} at house {prop}"
          f" - that row is #{keeper}'s, who already has it")
if APPLY and drop:
    cur.execute("DELETE FROM census_entries WHERE id = ANY(%s)", ([d[0] for d in drop],))
    c.commit()
    print(f"\n  {len(drop)} copies removed, committed")
else:
    print(f"\n  {len(drop)} would be removed." + ("" if APPLY else " Add --apply."))
