# -*- coding: utf-8 -*-
"""The RMGB pages: schedules, sub numbers and a source for the unsourced rows.

Forty-six 1939 rows came into the record from an index - no schedule, no sub
number, no district, no source line at all. A. Hagues has supplied the pages of
the **RMGB** enumeration district, which is where they came from, and they give
the structure back.

**Only the structure is taken here, not the names.** The hand is difficult and
my reading of it is worse than A. Hagues's - where I read Barefoot he reads
Brailsford - so nothing in this script changes a name. What it does is tie each
row to its schedule and sub number, which are printed clearly, and give every
row a source that says who read what.

The households line up person for person and in order, which is the check:
17 Lenton Road runs Brown, Willmot, Kirk, Meakin, Padget, Brailsford at sub
numbers 6 to 11 on the page and in the same order in the record.

  railway run python3 transcribe_rmgb_structure.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
ED = ("ED letter code RMGB, Nottingham registration district 430-3, sub-district 26 - the "
      "schedule and sub number read from the page image by Claude; the names are A. Hagues's "
      "reading")

# property, schedule, first sub number, address as the page writes it, note
HOUSES = [
 (188, 143, 6,  "17 Lenton Rd", None),
 (189, 144, 1,  "19 Lenton Rd", None),
 (303, 236, 1,  "4 South Rd", None),
 (302, 237, 1,  "3 South Rd", None),
 (383, 244, 1,  "Gwelen, Clumber Crescent",
  "the page heads this household with a house name the record has not got, read as Gwelen"),
]
# houses where the page gives sub numbers out of a run
EXPLICIT = {
 (301, 234): [1, 2, 3, 4, 5, 7, 8],   # sub 6 is behind the closed band
}
# two households in one house
SPLIT = [
 (305, 238, 1, "6 South Rd", 3,
  "6 South Rd carries four schedules - 238, 239, 240 and 241 - and 239 and 240 are marked empty, "
  "so the house is in flats and two of them stood unoccupied"),
 (305, 241, 1, "6 South Rd", 2,
  "the second of the two occupied flats at 6 South Rd; schedules 239 and 240 are marked empty"),
]


def rows_for(cur, prop):
    cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                     JOIN people p ON p.id = c.person_id
                    WHERE c.census_year = 1939 AND c.property_id = %s
                      AND c.census_household_num IS NULL
                    ORDER BY c.id""", (prop,))
    return cur.fetchall()


def tag(cur, cid, fn, ln, sched, sub, addr, note):
    src = (f"1939 Register, schedule {sched}, {addr}, {ED}; sub number {sub}"
           + (f"; {note}" if note else ""))
    print(f"    sub {sub:<3} row {cid} {fn} {ln}")
    if APPLY:
        cur.execute("""UPDATE census_entries
                          SET census_household_num = %s, source = %s WHERE id = %s""",
                    (sched, src, cid))


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    P = {p['id']: p.get('address') for p in json.load(open('data/all_props.json'))}

    for prop, sched, first, addr, note in HOUSES:
        rows = rows_for(cur, prop)
        subs = EXPLICIT.get((prop, sched)) or list(range(first, first + len(rows)))
        print(f"  schedule {sched}, {P.get(prop)} - {len(rows)} rows")
        for (cid, fn, ln), sub in zip(rows, subs):
            tag(cur, cid, fn, ln, sched, sub, addr, note)

    for prop, sched, first, addr, n, note in SPLIT:
        rows = rows_for(cur, prop)
        take = rows[:n] if sched == 238 else rows[-n:]
        print(f"  schedule {sched}, {P.get(prop)} - {len(take)} rows")
        for i, (cid, fn, ln) in enumerate(take):
            tag(cur, cid, fn, ln, sched, first + i, addr, note)

    # 1 South Road, with sub 6 behind the closed band
    rows = rows_for(cur, 301)
    print(f"  schedule 234, {P.get(301)} - {len(rows)} rows")
    for (cid, fn, ln), sub in zip(rows, EXPLICIT[(301, 234)]):
        tag(cur, cid, fn, ln, 234, sub, "1 South Rd",
            "sub number 6 of this schedule is behind the closed band")

    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
