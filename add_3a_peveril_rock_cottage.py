"""3a Peveril Drive, Rock Cottage - a census-only property.

A. Hagues gives it from Dougal de Havilland's map of the Park and from the
Ordnance Survey he sent earlier, which carries **Rock Cottage** on the north
side of Peveril Drive towards the Castle end. **Sam Roper** lived there about
1930. The record has never held the house under either name.

**It matters to the whole street.** Peveril Drive has stood all day at **nine
1939 households with no house against eight houses with no household** - an
arithmetic that cannot close. A ninth house makes it nine against nine.

**The position wants dragging into place.** It is set from the map label, north
of the road near the eastern end, to about twenty metres. Note that the number
sits oddly against it: the record's other Peveril Drive houses run with 1 at
the eastern end and 3 some sixty metres west, so a 3a beside 3 would be west of
here. Either the numbering does not run as the record's positions suggest, or
one of the two is out. See the question written on this.
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NEW = {
 "id": 453,
 "address": "Rock Cottage, 3a Peveril Drive",
 "name": "Rock Cottage",
 "house_name": "Rock Cottage",
 "street": "Peveril Drive",
 "no": "3a",
 "lat": 52.949300,
 "lng": -1.156600,
 "census_only": True,
 "desc": ("A cottage on the north side of Peveril Drive towards the Castle end, carried on the "
          "Ordnance Survey as Rock Cottage. **The position is read off the map to about twenty "
          "metres and wants dragging into place.**"),
 "history": ("**Named by Dougal de Havilland's map of the Park**, which has **Sam Roper** living "
             "here about 1930. The record had never held the house under either its name or its "
             "number.\n\nIts absence had been doing damage. Peveril Drive stood at **nine 1939 "
             "households with no house against eight houses with no household**, which cannot "
             "close - and a ninth house makes the two sides equal. Which household belongs here is "
             "not yet known; the candidates are schedules 118, 120, 121, 122, 124, 125, 126, 127 "
             "and 129, all of which the Register writes as Peveril Drive with no number."),
 "sources": [],
}


def main():
    P = json.load(open('data/all_props.json'))
    if any(p['id'] == NEW['id'] for p in P):
        print(f"  property {NEW['id']} already exists"); return
    if any('rock cottage' in str(p.get('name') or '').lower()
           and 'peveril' in str(p.get('street') or '').lower() for p in P):
        print("  Rock Cottage, Peveril Drive is already in the property list"); return
    print(f"  new property {NEW['id']}: {NEW['address']}  ({NEW['lat']}, {NEW['lng']})")
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT count(DISTINCT census_household_num) FROM census_entries
                    WHERE census_year=1939 AND property_id IS NULL
                      AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE '%peveril%'""")
    print(f"  Peveril households still with no house: {cur.fetchone()[0]}")
    if not APPLY:
        print("\n  preview only - pass --apply"); return
    P.append(NEW)
    json.dump(P, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"  property list now {len(P)} houses")


if __name__ == '__main__':
    main()
