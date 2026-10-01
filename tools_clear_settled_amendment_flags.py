# -*- coding: utf-8 -*-
"""Take the "cannot be read" note off rows where the name HAS been read.

Sixty-one 1939 rows carry a note saying the name under the amendment cannot be
made out. The Register's own index often carries it anyway, so as each one is
settled the note stops being true and starts contradicting the line beside it.

This clears the note from any row whose person now holds a '1939 amendment'
alias - that alias is the proof the name was recovered.

  railway run python3 tools_clear_settled_amendment_flags.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
STALE = ("; the name written under the amendment cannot be read - NOTE: the surname here is the "
         "amendment, not the name on the night. The 1939 Register was kept up to date as an "
         "identity register until 1991, and a married name has been written across the original, "
         "which cannot be read. Sixty of the sixty-one rows flagged this way are women")

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT c.id, p.first_name, p.last_name
                 FROM census_entries c JOIN people p ON p.id = c.person_id
                WHERE c.census_year = 1939
                  AND c.source LIKE %s
                  AND EXISTS (SELECT 1 FROM person_alias a
                               WHERE a.person_id = p.id AND a.made_by LIKE '1939 amendment%%')
                ORDER BY c.id""", ('%' + STALE + '%',))
rows = cur.fetchall()
for cid, fn, ln in rows:
    print(f"  row {cid} {fn} {ln}: the name under the amendment is read, so the note comes off")
if APPLY and rows:
    cur.execute("UPDATE census_entries SET source = replace(source, %s, '') WHERE id = ANY(%s)",
                (STALE, [r[0] for r in rows]))
    c.commit()
    print(f"\n  {len(rows)} cleared, committed")
else:
    print(f"\n  {len(rows)} would be cleared." + ("" if APPLY else " Add --apply."))
