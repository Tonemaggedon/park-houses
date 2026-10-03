# -*- coding: utf-8 -*-
"""Fold away people and rows a full import made that the record already had.

The Import button runs every people_*.json file, so each run re-offers every
household the record already holds. Where a file's person no longer matches the
record - a birth year corrected since, a middle name added, or a born_year the
file works out from an age that is a year off - the importer makes a second
person instead of finding the first, and does it again every time.

This finds them by shape rather than by a list: a person created after a given
id, holding exactly one census row, where some other person of the same surname
and a similar forename already holds a row for the same round, house and age.
It folds the new one away and leaves an alias, which is what stops the importer
making it a third time.

Usage:
  railway run python3 tools_fold_import_duplicates.py 8490          # show
  railway run python3 tools_fold_import_duplicates.py 8490 --apply  # do it
"""
import os, sys, psycopg2

SINCE = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8490
APPLY = '--apply' in sys.argv

FIND = """
SELECT n.id, n.first_name, n.last_name, n.born_year,
       c.id, c.census_year, c.property_id, c.age_at_census,
       o.id, o.first_name, o.last_name, o.born_year, d.id
  FROM people n
  JOIN census_entries c ON c.person_id = n.id
  JOIN census_entries d ON d.census_year = c.census_year
                       AND d.property_id IS NOT DISTINCT FROM c.property_id
                       AND d.age_at_census IS NOT DISTINCT FROM c.age_at_census
                       AND d.id <> c.id
  JOIN people o ON o.id = d.person_id AND o.id <> n.id
 WHERE n.id > %s
   AND LOWER(n.last_name) = LOWER(o.last_name)
   AND LOWER(LEFT(n.first_name,4)) = LOWER(LEFT(o.first_name,4))
   AND (SELECT COUNT(*) FROM census_entries x WHERE x.person_id = n.id) = 1
   AND n.bio IS NULL
   -- A duplicate made by an import differs from its twin by a wobbling birth year,
   -- a year or two at most. Two people fifty years apart are two people: this guard
   -- is what stops the fold undoing a split, which it did to Thomas Shaw - folding
   -- a brush maker born 1877 into a lace manufacturer born 1827.
   AND (n.born_year IS NULL OR o.born_year IS NULL OR ABS(n.born_year - o.born_year) <= 3)
 ORDER BY n.id
"""

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute(FIND, (SINCE,))
    rows = cur.fetchall()
    seen, folded = set(), 0
    for (nid, nfn, nln, nby, cid, yr, prop, age, oid, ofn, oln, oby, did) in rows:
        if nid in seen: continue
        seen.add(nid)
        why = ("birth year" if nby != oby else "name") + f" — file {nby}, record {oby}"
        print(f"  #{nid} {nfn} {nln} (b.{nby})  ->  #{oid} {ofn} {oln} (b.{oby})   {yr}, house {prop}, aged {age}")
        if APPLY:
            # the alias is the point: it is what the importer looks at next time
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,%s,'merge' FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a
                             WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                               AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                        (oid, nfn, nln, nby, nfn, nln))
            # Move the rows the keeper has not got, and only then drop the rest.
            # Deleting outright loses a row whenever the duplicate is holding the
            # only copy of it - which is exactly the case after a split has just
            # handed a new person their own household.
            cur.execute("""UPDATE census_entries n SET person_id=%s
                            WHERE n.person_id=%s AND NOT EXISTS
                              (SELECT 1 FROM census_entries o
                                WHERE o.person_id=%s AND o.census_year=n.census_year
                                  AND o.property_id IS NOT DISTINCT FROM n.property_id)""",
                        (oid, nid, oid))
            cur.execute("DELETE FROM census_entries WHERE person_id=%s", (nid,))
            cur.execute("DELETE FROM property_residents WHERE person_id=%s", (nid,))
            cur.execute("DELETE FROM people WHERE id=%s", (nid,))
        folded += 1
    print(f"\n  {folded} people {'folded away' if APPLY else 'would be folded away'}")
    if APPLY:
        cur.execute("SELECT COUNT(*) FROM (SELECT person_id,census_year FROM census_entries GROUP BY 1,2 HAVING COUNT(*)>1) t")
        print(f"  people in two places in one round: {cur.fetchone()[0]}")
        c.commit(); print("committed")
    else:
        print("  Nothing written. Add --apply.")

if __name__ == '__main__':
    main()
