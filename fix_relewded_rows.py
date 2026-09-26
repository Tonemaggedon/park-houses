# -*- coding: utf-8 -*-
"""Rows a later import put back on a person they had been split off.

tools_split_welded_people.py moves a row to the person it belongs to. But the
importer matches on a name, so re-running the source file afterwards creates the
row again on the name-match - and the split quietly comes undone. A merge is
protected from this by person_alias; a split has no such guard.

Two rows of Elizabeth G Lewis's were back where they had been taken from.
"""
import os, psycopg2

# (row to delete, the row it duplicates, why)
DELETE = [
  (9071, 8095, "Henry Lewis's wife at The Chestnuts, 38 in 1881 - split off to #7111 and "
               "then recreated on #4124 by a later import"),
  (9089, 5401, "the wife of 49 at #398 in 1881, who is #4124's - recreated on #7111 the same way"),
]
BORN = [(7163, 1831, 1890, "Henry Wing the solicitor of 12 Park Terrace, head of the house at 30, "
                           "40 and 50 in 1861, 1871 and 1881. The 1890 came off his grandson's rows.")]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for bad, keep, why in DELETE:
        cur.execute("""SELECT a.census_year,a.property_id,a.age_at_census,b.census_year,b.property_id,b.age_at_census
                       FROM census_entries a, census_entries b WHERE a.id=%s AND b.id=%s""", (bad, keep))
        r = cur.fetchone()
        assert r and r[:3] == r[3:], f"rows {bad} and {keep} are not the same round, house and age: {r}"
        cur.execute("DELETE FROM census_entries WHERE id=%s", (bad,))
        print(f"  row {bad} removed ({cur.rowcount}) - {why}")
    for pid, new, old, why in BORN:
        cur.execute("UPDATE people SET born_year=%s WHERE id=%s AND born_year=%s", (new, pid, old))
        print(f"  #{pid} born_year {old} -> {new} ({cur.rowcount} row) - {why}")
    for pid in (4124, 7111, 7163):
        cur.execute("""SELECT census_year,property_id,age_at_census FROM census_entries
                       WHERE person_id=%s ORDER BY census_year""", (pid,))
        cur2 = cur.fetchall()
        cur.execute("SELECT first_name||' '||last_name, born_year FROM people WHERE id=%s", (pid,))
        print(f"\n  #{pid} {cur.fetchone()} now holds {cur2}")
    c.commit(); print("\ncommitted")

if __name__ == '__main__':
    main()
