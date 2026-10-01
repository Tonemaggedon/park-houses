# -*- coding: utf-8 -*-
"""Standard Hill is not in The Park, so its eighteen people come out.

The record is the estate. Brewhouse Yard was kept out on the same ground - the
1891 enumerator's own boundary says "Lenton Boulevard (omitting Brewhouse
Yard)" - and its households were written into the note rather than entered, so
the names are not lost. Standard Hill gets the same treatment, except that
these eighteen were entered by mistake and have to be taken out again.

**One of them is not going anywhere.** Henry Bell, verger of 1 Standard Hill,
born 22 March 1885, had been welded to a Henry Bell the record holds properly:
a son at 19 Park Valley in 1881, aged 4, and at 15 Cavendish Crescent South in
1891, aged 14 - born about 1877, eight years earlier. Two men, one name. The
1939 row comes off; the Park boy stays, with his birth year put back to what
the two census pages support.

  railway run python3 remove_standard_hill_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'
WELD = 7669          # Henry Bell: the person stays, only the 1939 row goes
IDS = [7666, 7667, 7668, 7669, 7670, 7671, 7672, 7673, 7674, 7675, 7676, 7677,
       7678, 7679, 7680, 7681, 7682, 7683]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT p.id, p.first_name, p.last_name, c.id, c.census_year,
                          c.unresolved_address, c.age_at_census, c.occupation_at_census
                     FROM people p JOIN census_entries c ON c.person_id = p.id
                    WHERE p.id = ANY(%s) ORDER BY p.id, c.id""", (IDS,))
    rows = cur.fetchall()
    keep = [r for r in rows if r[4] != 1939]
    drop = [r for r in rows if r[4] == 1939]
    for pid, fn, ln, cid, yr, addr, age, occ in drop:
        print(f"  row {cid}  #{pid} {fn} {ln}, {age} - {occ}  [{addr}]")
    print(f"\n  {len(drop)} census rows out of the record")
    for pid, fn, ln, cid, yr, addr, age, occ in keep:
        print(f"  kept: row {cid} #{pid} {fn} {ln}, {yr}, aged {age} - a Park row, not Standard Hill")
    going = [i for i in IDS if i != WELD]
    print(f"  {len(going)} people deleted; #{WELD} stays, holding only his Park rows")

    if not APPLY:
        print("\n  Nothing written. Add --apply.")
        return

    cur.execute("DELETE FROM census_entries WHERE id = ANY(%s)", ([r[3] for r in drop],))
    cur.execute("DELETE FROM person_alias WHERE person_id = ANY(%s)", (going,))
    cur.execute("DELETE FROM people WHERE id = ANY(%s)", (going,))
    cur.execute("""UPDATE people SET born_year = 1877, born_date = NULL WHERE id = %s""", (WELD,))
    cur.execute("""UPDATE census_entries SET source = source ||
                     '; a Henry Bell of the same name, verger of 1 Standard Hill, born 22 March '
                     '1885, had been joined to this one by the importer - he is eight years '
                     'younger and outside the estate, and his row has been taken out'
                    WHERE person_id = %s AND source NOT LIKE %s""",
                (WELD, '%verger of 1 Standard Hill%'))

    d = json.load(open(DATA))
    names = {(r[1], r[2]) for r in drop}
    before = len(d['people'])
    d['people'] = [x for x in d['people']
                   if not ((x['first_name'], x['last_name']) in names
                           or x.get('id') in going)]
    print(f"\n  {before - len(d['people'])} removed from {DATA}")
    json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
    c.commit()
    print("  committed")


if __name__ == '__main__':
    main()
