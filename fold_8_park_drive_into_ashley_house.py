"""8 Park Drive is Ashley House.

A. Hagues has been to the road: nothing stands between 6 Park Drive and Ashley
House, so the number 8 belongs to the house that already has a name. The record
had made a property of it on the strength of one 1939 household, which is the
same way 15 Clare Valley came to exist.

Everything else fits. **8 Park Drive holds nothing but that one round.** Ashley
House holds 1881, 1891, 1901, 1911 and 1921 and then stops dead - a house with
a century of record behind it does not simply vanish from the Register.

So the Howitts move into Ashley House, and the number goes.

Also: John Arthur Howitt is in the record, but the index reads his middle name
as **Anther**, and a search under that found nobody. The spelling is kept as a
variant so it does.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
GONE, ASHLEY = 432, 238
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT ce.id, p.first_name, p.last_name, ce.census_year, ce.census_household_num
                 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.property_id=%s ORDER BY ce.id""", (GONE,))
for r in cur.fetchall(): print(f"  row{r[0]} {r[1]} {r[2]} ({r[3]}, schedule {r[4]}) -> Ashley House")
cur.execute("SELECT count(*) FROM census_entries WHERE property_id=%s", (ASHLEY,))
print(f"  Ashley House already holds {cur.fetchone()[0]} rows")

if apply:
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='Ashley House, Park Drive', unresolved_address=NULL,
                          source = REPLACE(source, '8 Park Drive', 'Ashley House, Park Drive')
                                   || ' - the page writes the house as 8 Park Drive. A. Hagues has '
                                      'established that nothing stands between 6 Park Drive and '
                                      'Ashley House, so the number is Ashley House''s own; the '
                                      'record had made a separate property of it holding this one '
                                      'round and nothing else'
                    WHERE property_id=%s""", (ASHLEY, GONE))
    print(f"\n  {cur.rowcount} rows moved into Ashley House")
    for t in ('property_residents', 'property_names', 'property_research',
              'property_watches', 'census_unoccupied', 'property_data', 'coords'):
        col = 'id' if t in ('property_data', 'coords') else 'property_id'
        try:
            cur.execute(f"DELETE FROM {t} WHERE {col}=%s", (GONE,))
        except Exception:
            c.rollback(); continue
        if cur.rowcount: print(f"  {t}: {cur.rowcount} row removed")
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   SELECT 7410,'John Anther','Howitt',1885,'A. Hagues' FROM (SELECT 1) t
                    WHERE NOT EXISTS (SELECT 1 FROM person_alias a
                      WHERE LOWER(TRIM(a.first_name))='john anther' AND LOWER(TRIM(a.last_name))='howitt')""")
    print(f"  John Anther Howitt kept as a variant: {cur.rowcount}")
    c.commit()
    d = json.load(open('data/all_props.json'))
    before = len(d)
    d = [p for p in d if p['id'] != GONE]
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
    print(f"  property list: {before} -> {len(d)}")
else:
    print("\n  preview only - pass --apply")
