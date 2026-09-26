# -*- coding: utf-8 -*-
"""Corrections to 1921 rows that were filed against the wrong house.

Tone read the householders' own schedules for the run and gave the addresses.
Four households were sitting in a neighbour's house; three of the four are
confirmed by the schedule itself, because a servant's place of work in 1921 is
the house she lives in, and by the same family standing at the same address in
the rounds either side.

Also folds away a second Sybil Speed. The record held her twice - as Cybil for
1901 and 1911 and as Sybil for 1881 and 1921 - and the 1921 move below puts both
halves in the same house, which is what made the pair visible.
"""
import os, psycopg2

MOVES = [
    # people,                  year, from, to, address written on the row
    ([1948, 1949, 1950], 1921, 61, 62, "4 Clare Valley",
     "Wilkins: the servant gives her place of work as 4 Clare Valley, and the "
     "family stands at 4 in 1901, 1911 and 1939. It was filed at 3, which left "
     "3 Clare Valley holding two heads of household in one year."),
    ([2024, 2025], 1921, 56, 52, "27 Cavendish Road East",
     "Speed: the family had been at 27 Cavendish Road East since 1891, and the "
     "house had no 1921 household at all."),
    ([2284, 1064, 1065, 1066, 1067], 1921, 27, 38, "1 Cavendish Crescent South",
     "The five servants keeping a sixteen-room house with the family away. The "
     "schedule is signed by the head from off the page; the hand reads Crewdson, "
     "and a Henry Crewdson, solicitor, was at 25 Lenton Avenue in 1901 and 1911."),
]

# surnames the schedule corrects in its own margin
RENAMES = [(1064, "Harison", "Hanson"), (1066, "Stranther", "Strauther")]

# the occupation as the householder wrote it
OCCS = [(1949, 1921, "Instructress of physical training")]

# both 1921 returns from Sunnyside give Park Valley as the postal address, not
# the Park Terrace the record carries. Recorded on the rows; the house itself is
# left alone, because Sunnyside stands in the record twice and only Tone can say
# whether #390 and #415 are one house.
SUNNYSIDE = ([1863, 1864], 390, "Sunnyside, Park Valley")

MERGE = (286, 2024, "Cybil", "Speed", 1874)   # (fold away, keep, alias to leave behind)

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for people, year, frm, to, addr, why in MOVES:
        cur.execute("""UPDATE census_entries SET property_id=%s, address=%s
                        WHERE person_id = ANY(%s) AND census_year=%s AND property_id=%s""",
                    (to, addr, people, year, frm))
        print(f"  moved {cur.rowcount} rows  #{frm} -> #{to}  {addr}")
        print(f"      {why}")
    for pid, old, new in RENAMES:
        cur.execute("UPDATE people SET last_name=%s WHERE id=%s AND last_name=%s", (new, pid, old))
        if cur.rowcount:
            cur.execute("INSERT INTO person_alias (person_id, first_name, last_name, made_by) "
                        "SELECT p.id, p.first_name, %s, 'schedule margin' FROM people p "
                        "WHERE p.id=%s AND NOT EXISTS "
                        "(SELECT 1 FROM person_alias a WHERE a.person_id=p.id AND a.last_name=%s)",
                        (old, pid, old))
        print(f"  renamed {cur.rowcount and 1 or 0}: #{pid} {old} -> {new}")
    for pid, year, occ in OCCS:
        cur.execute("UPDATE census_entries SET occupation_at_census=%s WHERE person_id=%s AND census_year=%s",
                    (occ, pid, year))
        print(f"  occupation #{pid}: {occ}  ({cur.rowcount} row)")
    people, prop, addr = SUNNYSIDE
    cur.execute("UPDATE census_entries SET address=%s WHERE person_id=ANY(%s) AND census_year=1921 AND property_id=%s",
                (addr, people, prop))
    print(f"  Sunnyside: {cur.rowcount} rows now carry the postal address the cover sheet gives")

    drop, keep, afn, aln, ayr = MERGE
    cur.execute("SELECT COUNT(*) FROM property_residents WHERE person_id=%s", (drop,))
    assert cur.fetchone()[0] == 0, "merge: the folded person still has residency rows"
    cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=%s", (keep, drop))
    moved = cur.rowcount
    cur.execute("INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by) "
                "SELECT %s,%s,%s,%s,'merge' FROM (SELECT 1) t WHERE NOT EXISTS "
                "(SELECT 1 FROM person_alias a WHERE a.person_id=%s AND a.first_name=%s AND a.last_name=%s)",
                (keep, afn, aln, ayr, keep, afn, aln))
    cur.execute("DELETE FROM people WHERE id=%s", (drop,))
    print(f"  merged #{drop} {afn} {aln} into #{keep} ({moved} census rows), alias kept")
    c.commit()
    print("\ncommitted")

if __name__ == '__main__':
    main()
