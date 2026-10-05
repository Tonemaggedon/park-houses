"""Four households in the 1901 Brewhouse Yard and Standard Hill transcription
have an address the record can match to a house, and were never joined to one.

  s61  13 Park Valley                  -> #396
  s96  18 Park Terrace                 -> #416
  s112 Tattershall Corner              -> #227, 39 Newcastle Drive, which carries
                                          Tattershall Corner as a former name
  s116 131 Derby Road                  -> #73, 3 Clinton Terrace, whose address
                                          in the record is "3 Clinton Terrace
                                          (131 Derby Road)" - the match is in the
                                          bracket, which is why a plain comparison
                                          missed it

The other fifty-one unhoused rows cannot be placed: the page gives no number
for Huntingdon Drive, Park Row, Clinton Terrace, Clare Valley or Newcastle
Terrace, and Brewhouse Yard and the lodging over the Peveril Drive stables are
not houses the record holds.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
M = [(61, 396, "13 Park Valley"),
     (96, 416, "18 Park Terrace"),
     (112, 227, "39 Newcastle Drive"),
     (116, 73, "3 Clinton Terrace (131 Derby Road)")]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for sched, prop, addr in M:
    cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1901
                    AND census_household_num=%s AND property_id IS NULL
                    AND source ILIKE '%%Brewhouse Yard and Standard Hill%%'""", (sched,))
    print(f"  s{sched} -> #{prop} {addr}: {cur.fetchone()[0]} rows")
if apply:
    tot = 0
    for sched, prop, addr in M:
        cur.execute("""UPDATE census_entries
                          SET property_id=%s, address=%s,
                              source = source || ' - housed at ' || %s ||
                                ' from the address the page gives, which the record had never joined'
                        WHERE census_year=1901 AND census_household_num=%s AND property_id IS NULL
                          AND source ILIKE %s""",
                    (prop, addr, addr, sched, '%Brewhouse Yard and Standard Hill%'))
        tot += cur.rowcount
    c.commit()
    print(f"\n  {tot} rows housed")
    cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1901
                    AND source ILIKE '%Brewhouse Yard and Standard Hill%' AND property_id IS NULL""")
    print(f"  still unhoused in that transcription: {cur.fetchone()[0]}")
else:
    print("\n  preview only - pass --apply")
