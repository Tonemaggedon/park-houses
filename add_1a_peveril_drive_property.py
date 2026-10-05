"""1a Peveril Drive - a census-only property, and the house for schedule 61.

A. Hagues sent the Ordnance Survey of the Castle end of Peveril Drive. The map
carries **1** and **1A** side by side at the eastern end, south of the road by
the car park, which is where the record already puts 1 Peveril Drive. So 1a
exists on the ground; it has simply never been a property in the record, which
is why schedule 61 has sat unhoused as "1a Peveril Drive".

**The position is read off that map to about twenty metres and wants dragging
into place**, the same as the Pelham Cottages. It is set just east of 1 Peveril
Drive, which is where the map shows 1A against 1.

  railway run python3 add_1a_peveril_drive_property.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NEW = {
 "id": 452,
 "address": "1a Peveril Drive",
 "name": "",
 "house_name": "",
 "street": "Peveril Drive",
 "no": "1a",
 "lat": 52.949030,
 "lng": -1.156450,
 "census_only": True,
 "desc": ("A small house at the Castle end of Peveril Drive, standing beside number 1 on the "
          "south side of the road. The Ordnance Survey carries 1 and 1A together here. "
          "**The position is read off the map to about twenty metres and wants dragging into "
          "place.**"),
 "history": ("**Named by the 1939 Register and by nothing else in the record.** Schedule 61 of ED "
             "letter code RMGC writes the address out as *1a Peveril Drive* and holds **Thomas F "
             "Cooper** and **Mary E Cooper**, with a second **Thomas F Cooper** and **Minnie** - "
             "two generations under one roof.\n\n"
             "The household had no house until A. Hagues went to the map and found 1A standing "
             "next to 1 at the eastern end of the street. The record had never held it as a "
             "property, so the schedule sat unfiled."),
 "sources": [],
}
SRC_OLD = "1a Peveril Drive"


def main():
    P = json.load(open('data/all_props.json'))
    if any(p['id'] == NEW['id'] for p in P):
        print(f"  property {NEW['id']} already exists"); return
    if any(str(p.get('address') or '').lower() == '1a peveril drive' for p in P):
        print("  1a Peveril Drive is already in the property list"); return
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT ce.id, p.first_name, p.last_name, ce.age_at_census, ce.occupation_at_census
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.census_year=1939 AND ce.census_household_num=61
                      AND ce.property_id IS NULL ORDER BY ce.id""")
    rows = cur.fetchall()
    print(f"  new property {NEW['id']}: {NEW['address']}  ({NEW['lat']}, {NEW['lng']})")
    for r in rows:
        print(f"    row{r[0]} {r[1]} {r[2]}, {r[3]} - {r[4]}")
    if not APPLY:
        print("\n  preview only - pass --apply"); return
    P.append(NEW)
    json.dump(P, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address=%s, unresolved_address=NULL,
                          source = source || ' - the house had no property in the record until '
                                   'A. Hagues found 1A beside 1 on the Ordnance Survey at the '
                                   'Castle end of the street'
                    WHERE census_year=1939 AND census_household_num=61 AND property_id IS NULL
                      AND COALESCE(NULLIF(address,''), unresolved_address) ILIKE %s""",
                (NEW['id'], NEW['address'], '%peveril%'))
    print(f"\n  {cur.rowcount} rows housed at {NEW['address']}")
    c.commit()
    print(f"  property list now {len(P)} houses")


if __name__ == '__main__':
    main()
