"""Three named houses fold into the numbered ones they always were.

  #433 Lynwood   -> #307 2 Tattershall Drive
  #434 St Ives   -> #309 4 Tattershall Drive
  #435 Elmsdale  -> #63  5 Clare Valley

**The record confirms the first of them on its own.** Richard Warwick Bond and
Amy Constance Bond are at 2 Tattershall Drive in the 1921 census and at Lynwood
in the 1939 Register - the same couple, the same house, eighteen years apart,
held as two properties.

**And this is where three wrong empty marks came from.** All three numbered
houses were marked ticked and blank for 1939 yesterday, on A. Hagues' word -
but the word was given off a gaps list I built, and that list treated the named
house and the numbered house as two. The houses were never empty; their 1939
households were filed under the other property. The marks go.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
M = [(433, 307, "2 Tattershall Drive", "Lynwood"),
     (434, 309, "4 Tattershall Drive", "St Ives"),
     (435, 63,  "5 Clare Valley",      "Elmsdale")]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for drop, keep, addr, name in M:
    cur.execute("SELECT count(*) FROM census_entries WHERE property_id=%s", (drop,))
    n = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM census_unoccupied WHERE property_id=%s AND census_year=1939", (keep,))
    e = cur.fetchone()[0]
    print(f"  #{drop} {name:<9} -> #{keep} {addr:<22} {n} rows to move, {e} wrong empty mark")
if apply:
    for drop, keep, addr, name in M:
        cur.execute("""UPDATE census_entries
                          SET property_id=%s, address=%s,
                              source = source || ' - ' || %s || ' and ' || %s || ' are one house; '
                                'the record held them as two properties until A. Hagues said so'
                        WHERE property_id=%s""", (keep, f"{name}, {addr}", name, addr, drop))
        cur.execute("""UPDATE property_residents SET property_id=%s WHERE property_id=%s
                        AND NOT EXISTS (SELECT 1 FROM property_residents b
                          WHERE b.property_id=%s AND b.person_id=property_residents.person_id)""",
                    (keep, drop, keep))
        for t in ('property_residents','property_names','property_research','property_watches',
                  'census_unoccupied'):
            cur.execute(f"DELETE FROM {t} WHERE property_id=%s", (drop,))
        cur.execute("""DELETE FROM census_unoccupied WHERE property_id=%s AND census_year=1939""", (keep,))
    c.commit()
    d = json.load(open('data/all_props.json'))
    byid = {p['id']: p for p in d}
    for drop, keep, addr, name in M:
        k = byid[keep]
        k['name'] = name; k['house_name'] = name
        if not str(k.get('address') or '').lower().startswith(name.lower()):
            k['address'] = f"{name}, {addr}"
        k['history'] = (k.get('history') or '') + (
            f"\n\n**The house is {name}.** The record held the name and the number as two separate "
            f"properties until A. Hagues joined them." +
            (" Richard Warwick Bond and his wife Amy Constance are at 2 Tattershall Drive on the "
             "1921 census and at Lynwood in the 1939 Register - the same couple in the same house, "
             "eighteen years apart." if name == 'Lynwood' else ""))
        print(f"  #{keep} is now {k['address']}")
    d = [p for p in d if p['id'] not in (433, 434, 435)]
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"  property list now {len(d)}")
else:
    print("\n  preview only - pass --apply")
