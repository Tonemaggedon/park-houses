# -*- coding: utf-8 -*-
"""Thomas Shaw is three men, and the record was carrying all of them as one.

A. Hagues reads the page: a lace manufacturer, a general agent and a brush
maker. The ages and the birthplaces say the same thing, and the record had the
youngest man's birth year on the record as a whole.

  the lace manufacturer   born Nottingham about 1827 - 34 at 14 The Ropewalk in
                          1861 and 43 in the same house in 1871
  the general agent       born Derby about 1834 - 37 at 147 Derby Road in 1871,
                          the same night the lace manufacturer is on the Ropewalk
  the brush maker         born Derby about 1877 - a boarder of 24 on Pelham
                          Crescent in 1901, forty years younger than the first

The 1871 round settles it on its own: one man cannot head two houses on one
night, and these two did.

The record keeps the lace manufacturer, because the house is his and he is in
twice; the other two are made fresh, bound by round and house rather than by a
row number, so a re-import cannot put them back together.

  railway run python3 fix_thomas_shaw.py          # show
  railway run python3 fix_thomas_shaw.py --apply  # do it
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
KEEP = 7144

# (round, property_id or None, forename, surname, born_year, born_place, who)
MOVE = [
 (1871, 104, "Thomas", "Shaw", 1834, "Derby",
  "the general agent of 37 at 147 Derby Road - not the lace manufacturer of 43 who heads "
  "14 The Ropewalk the same night, and born Derby where that man is born Nottingham"),
 (1901, None, "Thomas", "Shaw", 1877, "Derby",
  "the brush maker of 24, boarding on Pelham Crescent - born Derby and forty years younger "
  "than the lace manufacturer whose record carried him"),
]


def main():
    made = []
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("SELECT first_name, last_name, born_year, born_place FROM people WHERE id=%s", (KEEP,))
    got = cur.fetchone()
    if not got:
        print(f"  #{KEEP} is not in the record"); return
    print(f"  #{KEEP} {got[0]} {got[1]}, born {got[2]} {got[3]}  ->  the lace manufacturer, "
          f"born Nottingham about 1827")

    for yr, prop, fn, ln, by, bp, why in MOVE:
        if prop is None:
            cur.execute("""SELECT id FROM census_entries
                            WHERE person_id=%s AND census_year=%s AND property_id IS NULL""",
                        (KEEP, yr))
        else:
            cur.execute("""SELECT id FROM census_entries
                            WHERE person_id=%s AND census_year=%s AND property_id=%s""",
                        (KEEP, yr, prop))
        rows = [r[0] for r in cur.fetchall()]
        if not rows:
            print(f"  {yr}: nothing left to move - already split"); continue
        print(f"  {yr}: {len(rows)} row(s) -> a new {fn} {ln}, born about {by} at {bp}")
        print(f"      {why}")
        if not APPLY:
            continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_place)
                       VALUES (%s,%s,'M',%s,%s) RETURNING id""", (fn, ln, by, bp))
        nid = cur.fetchone()[0]
        cur.execute("UPDATE census_entries SET person_id=%s WHERE id=ANY(%s)", (nid, rows))
        cur.execute("""UPDATE census_entries SET source = COALESCE(source,'') || %s
                        WHERE id=ANY(%s) AND COALESCE(source,'') NOT LIKE %s""",
                    (f"; this is {why}. The record held three Thomas Shaws as one man until "
                     f"A. Hagues read them apart", rows, '%three Thomas Shaws%'))
        made.append(nid)
        print(f"      entered as #{nid}")

    # The occupations list and the resident links hang off the person, not off
    # the census row, so they stay with the wrong man unless they are moved too.
    # Restricted to the men this split made. A join on year and trade alone
    # reaches every lace manufacturer in the record, and hands this man's
    # occupation to a stranger - which is exactly what it did the first time.
    cur.execute("""SELECT o.id, o.occupation, o.from_year, c.person_id
                     FROM occupations o
                     JOIN census_entries c ON c.census_year = o.from_year
                                         AND c.occupation_at_census = o.occupation
                                         AND c.person_id = ANY(%s)
                    WHERE o.person_id = %s""", (made, KEEP))
    for oid, occ, yr, owner in cur.fetchall():
        print(f"  the {yr} occupation '{occ}' belongs to #{owner}")
        if APPLY:
            cur.execute("UPDATE occupations SET person_id=%s WHERE id=%s", (owner, oid))

    cur.execute("""SELECT r.id, r.property_id, c.person_id
                     FROM property_residents r
                     JOIN census_entries c ON c.property_id = r.property_id
                                          AND c.person_id = ANY(%s)
                    WHERE r.person_id = %s
                      AND NOT EXISTS (SELECT 1 FROM census_entries k
                                       WHERE k.person_id = %s
                                         AND k.property_id = r.property_id)""",
                (made, KEEP, KEEP))
    for rid, prop, owner in cur.fetchall():
        print(f"  the link to house {prop} belongs to #{owner}")
        if APPLY:
            cur.execute("UPDATE property_residents SET person_id=%s WHERE id=%s", (owner, rid))

    if APPLY:
        cur.execute("""UPDATE people SET born_year=1827, born_place='Nottingham, Nottinghamshire'
                        WHERE id=%s""", (KEEP,))
        cur.execute("""UPDATE census_entries SET source = COALESCE(source,'') || %s
                        WHERE person_id=%s AND COALESCE(source,'') NOT LIKE %s""",
                    ("; the lace manufacturer of 14 The Ropewalk, born Nottingham - the record "
                     "held him, a general agent and a brush maker as one man until A. Hagues "
                     "read them apart", KEEP, '%three Thomas Shaws%'))
        c.commit()
        print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
