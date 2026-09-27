# -*- coding: utf-8 -*-
"""What a full import does to people the record has since corrected.

The Import button runs every people_*.json file, not just the new one. Two
things then go wrong, and both had happened by the time this was written.

1. A person whose birth year was corrected in the record no longer matches the
   file. The 1939 file works born_year out as 1939 minus the age on the page,
   which is a year early whenever the birthday falls after the census date. With
   match_born_year set, the importer finds nobody and makes a second person -
   and does it again on every run. The same happens when somebody is given their
   full middle name afterwards: Leslie F Bates stops matching Leslie Fleetwood
   Bates.

2. A split is undone. tools_split_welded_people.py moves a row to the person it
   belongs to, but the name in the file still points at the person it was taken
   from, so the row comes straight back. A merge is safe from this because
   person_alias records the name that went away; a split has no such guard.

This removes the copies and binds the files by person number, which survives
both a rename and a corrected year.
"""
import json, io, os, psycopg2

# people this import minted that already existed  (new, keeps, why the match failed)
DUPES = [
  (8389, 268,  "born_year 1882 against 1883 - the file works it out as 1939 minus the age"),
  (8390, 2263, "born_year 1857 against 1858"),
  (8394, 1865, "born_year 1866 against 1864"),
  (8396, 7564, "Leslie F Bates against Leslie Fleetwood Bates - the record has since given him his middle name"),
  (8397, 7565, "Winifred Frances Bates against Winifred Frances Furze Bates"),
  (8399, 2084, "born_year 1868 against 1869"),
  (8400, 1876, "born_year 1862 against 1863"),
  (8401, 143,  "born_year 1876 against 1877"),
]
# rows the import put back on a person they had been split off
SPLIT_UNDONE = [10524, 10525, 10526, 10527, 10568, 10569, 10570]
# Henry Wing was already held twice; the import gave the fuller record copies of the other's rows
WING = (7163, 3648, [10521, 10522, 10523])

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    for new, keep, why in DUPES:
        cur.execute("SELECT COUNT(*) FROM census_entries WHERE person_id=%s", (new,))
        n = cur.fetchone()[0]
        assert n == 1, f"#{new} holds {n} rows, not the single copy that was checked"
        cur.execute("""SELECT a.id FROM census_entries a, census_entries b
                       WHERE a.person_id=%s AND b.person_id=%s AND a.census_year=b.census_year
                         AND a.property_id IS NOT DISTINCT FROM b.property_id""", (new, keep))
        assert cur.fetchone(), f"#{new}'s row is not a copy of one #{keep} already has"
        cur.execute("SELECT first_name,last_name,born_year FROM people WHERE id=%s", (new,))
        fn, ln, by = cur.fetchone()
        cur.execute("DELETE FROM census_entries WHERE person_id=%s", (new,))
        cur.execute("DELETE FROM property_residents WHERE person_id=%s", (new,))
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT %s,%s,%s,%s,'merge' FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE a.person_id=%s AND a.first_name=%s AND a.last_name=%s)""",
                    (keep, fn, ln, by, keep, fn, ln))
        cur.execute("DELETE FROM people WHERE id=%s", (new,))
        print(f"  #{new} {fn} {ln} folded into #{keep} - {why}")

    for rid in SPLIT_UNDONE:
        cur.execute("""SELECT a.census_year,a.property_id,a.age_at_census FROM census_entries a WHERE a.id=%s""", (rid,))
        r = cur.fetchone()
        assert r, f"row {rid} is gone"
        cur.execute("""SELECT COUNT(*) FROM census_entries b WHERE b.id<>%s AND b.census_year=%s
                        AND b.property_id IS NOT DISTINCT FROM %s AND b.age_at_census IS NOT DISTINCT FROM %s""",
                    (rid, r[0], r[1], r[2]))
        assert cur.fetchone()[0] >= 1, f"row {rid} has no twin - not a re-weld"
        cur.execute("DELETE FROM census_entries WHERE id=%s", (rid,))
    print(f"  {len(SPLIT_UNDONE)} rows removed that a split had already taken off their person")

    drop, keep, copies = WING
    cur.execute("DELETE FROM census_entries WHERE id = ANY(%s)", (copies,))
    print(f"  {cur.rowcount} copied Henry Wing rows removed from #{keep}")
    cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=%s", (keep, drop))
    moved = cur.rowcount
    cur.execute("UPDATE property_residents SET person_id=%s WHERE person_id=%s AND NOT EXISTS "
                "(SELECT 1 FROM property_residents r2 WHERE r2.person_id=%s AND r2.property_id=property_residents.property_id)",
                (keep, drop, keep))
    cur.execute("DELETE FROM property_residents WHERE person_id=%s", (drop,))
    cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    print(f"  Henry Wing #{drop} folded into #{keep} ({moved} rows) - the record held the solicitor twice")

    cur.execute("SELECT COUNT(*) FROM census_entries")
    print(f"\n  census rows now: {cur.fetchone()[0]}")
    c.commit(); print("committed")

if __name__ == '__main__':
    main()
