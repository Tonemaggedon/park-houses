# -*- coding: utf-8 -*-
"""Two houses the record was holding twice - once described, once with the people.

A. Hagues confirms both pairs are one house. In each the described property had
the architecture and no census at all, while a census-only shell beside it held
every household. The people move onto the described house and the shell goes.

  #382 6 Castle Grove            -> #174 1 Lenton Road (6 and 6a Castle Grove)
  #411 16 Cavendish Crescent N.  -> #31  16 and 16a Cavendish Crescent North

NOT merged: #93 159-161 Derby Road and #98 159 Derby Road (2 Derby Terrace).
A. Hagues confirms these are two buildings - #98 is a house in the Regency
terrace of about 1829, probably by P. F. Robinson; #93 is the four-storey
towered corner block at Barrack Lane, originally Rock Terrace of about 1860.
"""
import os, psycopg2

MERGE = [(382, 174, "6 Castle Grove", "1 Lenton Road (6 and 6a Castle Grove)"),
         (411, 31,  "16 Cavendish Crescent North", "16 and 16a Cavendish Crescent North")]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for drop, keep, dropname, keepname in MERGE:
        cur.execute("SELECT COUNT(*) FROM census_entries WHERE property_id=%s", (keep,))
        assert cur.fetchone()[0] == 0, f"#{keep} already holds census rows - stopping"
        cur.execute("UPDATE census_entries SET property_id=%s, address=%s WHERE property_id=%s",
                    (keep, keepname, drop))
        rows = cur.rowcount
        cur.execute("""UPDATE property_residents SET property_id=%s WHERE property_id=%s AND NOT EXISTS
                       (SELECT 1 FROM property_residents r2 WHERE r2.property_id=%s
                          AND r2.person_id=property_residents.person_id)""", (keep, drop, keep))
        res = cur.rowcount
        cur.execute("DELETE FROM property_residents WHERE property_id=%s", (drop,))
        cur.execute("UPDATE census_unoccupied SET property_id=%s WHERE property_id=%s", (keep, drop))
        unocc = cur.rowcount
        cur.execute("DELETE FROM coords WHERE id=%s", (drop,))
        cur.execute("DELETE FROM property_data WHERE id=%s", (drop,))
        print(f"  #{drop} {dropname} -> #{keep} {keepname}")
        print(f"      {rows} census rows, {res} residencies, {unocc} unoccupied notes")
    cur.execute("""SELECT COUNT(*) FROM property_data pd WHERE NOT EXISTS
                   (SELECT 1 FROM census_entries c WHERE c.property_id=pd.id)""")
    print(f"\n  properties still holding no census at all: {cur.fetchone()[0]}")
    c.commit(); print("committed")

if __name__ == '__main__':
    main()
