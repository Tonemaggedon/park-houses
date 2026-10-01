# -*- coding: utf-8 -*-
"""8 Park Drive, which the 1939 page names and the record did not hold.

Schedule 23 of the 1939 Register is headed 8 Park Drive, and the record had no
such house - so John Arthur Hewitt and the two women with him sat unfiled.
A. Hagues confirms the address, so the house is made and they go into it.

The position is provisional: it is set on the carriageway between 7 and 9, and
nothing in the record fixes it yet. See the research question on Park Drive's
missing numbers.

  railway run python3 place_8_park_drive.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP = 432
ROWS = (9419, 9420, 9421)


def add_property():
    path = 'data/all_props.json'
    props = json.load(open(path))
    if any(p['id'] == PROP for p in props):
        print(f"  #{PROP} is already in all_props.json")
        return
    props.append({
        "id": PROP, "name": "", "street": "Park Drive", "no": "8",
        "address": "8 Park Drive", "desc": "",
        "history": "**Named by the 1939 Register and by nothing else in the record.** "
                   "Schedule 23 is headed 8 Park Drive and holds **John Arthur Hewitt**, "
                   "with **Ethel M Edwards**, 27, keeping house, and **Emily M Oakland**, "
                   "23, domestic servant. Hewitt's own line runs under a repair strip, so "
                   "his age and his trade are lost; sub numbers 2 and 3 are absent from the "
                   "page, which is what a record still closed looks like.\n\n"
                   "**The number is a gap in the record, not only here.** Park Drive runs "
                   "1, 2, 3, 4, 6, 7 and 9 with Ashley House and Clumber House unnumbered, "
                   "so 5, 8 and 10 are all missing - and the 1881 round heads a household "
                   "of fifteen at 10 Park Drive. Whether 8 Park Drive is a house the record "
                   "holds under a name is open; the position below is provisional, set "
                   "between 7 and 9 and not fixed by anything.",
        "date_built": "", "listed": "No", "census_only": True,
        "lat": 52.95026, "lng": -1.16102,
    })
    props.sort(key=lambda p: p['id'])
    if APPLY:
        json.dump(props, open(path, 'w'), indent=1, ensure_ascii=False)
    print(f"  #{PROP} 8 Park Drive added to all_props.json "
          f"({'written' if APPLY else 'not written'})")


def file_them(cur):
    cur.execute("""SELECT c.id, p.first_name, p.last_name, c.property_id
                     FROM census_entries c JOIN people p ON p.id = c.person_id
                    WHERE c.id = ANY(%s) ORDER BY c.id""", (list(ROWS),))
    for cid, fn, ln, pid in cur.fetchall():
        if pid == PROP:
            print(f"  row {cid} {fn} {ln}: already at 8 Park Drive")
            continue
        print(f"  row {cid} {fn} {ln}: unfiled -> 8 Park Drive")
        if not APPLY:
            continue
        cur.execute("""UPDATE census_entries
                          SET property_id = %s, unresolved_address = NULL,
                              address = '8 Park Drive',
                              source = replace(source,
                                'the house is not identified in the record, so this row is left unfiled',
                                'the house is 8 Park Drive, which the page names and the record now holds')
                        WHERE id = %s""", (PROP, cid))


def main():
    add_property()
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    file_them(cur)
    if APPLY:
        c.commit()
        print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
