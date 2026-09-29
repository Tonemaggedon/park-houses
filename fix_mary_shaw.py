# -*- coding: utf-8 -*-
"""Three Mary Shaws, welded into one and then copied back by later imports.

The record has three women of that name in 1881 and they are not hard to tell
apart - a cook of 22 born Kimberley, a cook of 36 born Rowsley, and Charles
Shaw's wife of 65 born Nottingham. Person #7109 was holding all three, with two
of the rows duplicating rows the right people already had.
"""
import os, psycopg2

DELETE = [
 (9064, 7900, "the cook of 36 at 4 Park Drive, born Rowsley - #7110 already holds her"),
 (9092, 8811, "Charles Shaw's wife of 65 at Rock House, born Nottingham - #6170 already holds her"),
]
MOVE = [(9146, 7109, 6170, "the 1891 row at Rock House, aged 75 - Charles Shaw's wife ten years on, "
                           "not the cook of 22 from Cavendish Crescent South")]
BORN = [(7109, 1859, "the cook of 22 at 15 Cavendish Crescent South in 1881, born Kimberley"),
        (7110, 1845, "the cook of 36 at 4 Park Drive in 1881, born Rowsley"),
        (6170, 1816, "Charles Shaw's wife, 65 in 1881 and 75 in 1891 at Rock House")]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for bad, twin, why in DELETE:
        cur.execute("""SELECT a.census_year,a.property_id,a.age_at_census,b.census_year,b.property_id,b.age_at_census
                       FROM census_entries a, census_entries b WHERE a.id=%s AND b.id=%s""", (bad, twin))
        r = cur.fetchone()
        assert r and r[:3] == r[3:], f"rows {bad} and {twin} do not match: {r}"
        cur.execute("DELETE FROM census_entries WHERE id=%s", (bad,))
        print(f"  row {bad} removed - {why}")
    for rid, frm, to, why in MOVE:
        cur.execute("SELECT person_id, census_year, property_id FROM census_entries WHERE id=%s", (rid,))
        pid, yr, prop = cur.fetchone()
        assert pid == frm, f"row {rid} is on #{pid}, not #{frm}"
        cur.execute("SELECT COUNT(*) FROM census_entries WHERE person_id=%s AND census_year=%s", (to, yr))
        assert cur.fetchone()[0] == 0, f"#{to} already has a {yr} row"
        cur.execute("UPDATE census_entries SET person_id=%s WHERE id=%s", (to, rid))
        print(f"  row {rid} moved #{frm} -> #{to} - {why}")
    for pid, yr, why in BORN:
        cur.execute("UPDATE people SET born_year=%s WHERE id=%s AND born_year IS DISTINCT FROM %s", (yr, pid, yr))
        if cur.rowcount: print(f"  #{pid} born_year set to {yr} - {why}")
    for pid in (7109, 7110, 6170):
        cur.execute("""SELECT p.born_year, array_agg(c.census_year ORDER BY c.census_year),
                              array_agg(c.age_at_census ORDER BY c.census_year)
                       FROM people p LEFT JOIN census_entries c ON c.person_id=p.id
                       WHERE p.id=%s GROUP BY p.born_year""", (pid,))
        print(f"\n  #{pid} born {cur.fetchone()}")
    c.commit(); print("\ncommitted")

if __name__ == '__main__':
    main()
