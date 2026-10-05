"""The Walkers of 4 Castle Grove and 2 Huntingdon Drive.

A. Hagues brought this from Dougal de Havilland's map of the Park. John B
Walker, a Justice of the Peace, lived at 4 Castle Grove; his son Dudley married
Nellie Crawford in 1908 and the couple moved into a newly built house at 2
Huntingdon Drive, where their son John was born in 1910.

**The record already held that household and could not number it.** The 1911
census has Robert Dudley Walker, 28, a lace thread manufacturer and employer,
with his wife Helen Main, 26, their son John Alexander, aged one, and two
servants - all of them filed at *Huntingdon Drive (the cover gives no number)*,
with a note reading "probably 2 Huntingdon Drive".

**Four things agree.** Dudley is his second forename. The house was **built in
1908**, the year of the marriage, which is what makes it the new house. The son
John was born in 1910 and is one year old in the 1911 census. And 2 Huntingdon
Drive's own history already records a single-storey side extension built **for
Robert Walker**.

**Nellie is Helen.** Nellie has been an everyday short form of Helen for
centuries, and Crawford would be her maiden name, so Helen Main Walker is
entered with Nellie Crawford and Nellie Walker held as variants.

**And a second household resolves itself on the way.** The 1911 Ball household
sits at *Whitegates, Huntingdon Drive (not in the property list)* - but White
Gates is in the list, at number 8. The note was written before it was added.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
HUNT2, WHITEGATES, CASTLE4 = 144, 150, 18
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1911 AND property_id IS NULL
                AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE '%probably 2 Huntingdon%'""")
print(f"  Walker household -> 2 Huntingdon Drive: {cur.fetchone()[0]} rows")
cur.execute("""SELECT count(*) FROM census_entries WHERE census_year=1911 AND property_id IS NULL
                AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE '%Whitegates, Huntingdon%'""")
print(f"  Ball household -> White Gates, 8 Huntingdon Drive: {cur.fetchone()[0]} rows")

CASTLE_NOTE = (
 "\n\n**The Walkers were here before the Vogels.** Dougal de Havilland's map of the Park gives the "
 "house as the home of **John B Walker, a Justice of the Peace**. His son **Dudley** married "
 "**Nellie Crawford** in 1908 and the couple did not stay - they moved into a house built that same "
 "year at **2 Huntingdon Drive**, where their son John was born in 1910.\n\n"
 "The record holds the younger household from the other end. The 1911 census has **Robert Dudley "
 "Walker**, 28, a lace thread manufacturer employing others, with his wife **Helen Main** and their "
 "son **John Alexander**, aged one - a household the record could place only as *Huntingdon Drive, "
 "the cover gives no number* until this. **John B Walker himself is not yet in the record**, and "
 "the census rounds the record holds for this house begin only in 1921, with Rudolf Vogel.")

if apply:
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='2 Huntingdon Drive', unresolved_address=NULL,
                          source = source || ' - placed at 2 Huntingdon Drive from Dougal de '
                            'Havilland''s map of the Park, which has John B Walker JP at 4 Castle '
                            'Grove and his son Dudley moving to a newly built house at 2 Huntingdon '
                            'Drive after marrying Nellie Crawford in 1908. The house was built in '
                            '1908, the son John was born in 1910, and this house''s own history '
                            'records a side extension built for Robert Walker'
                    WHERE census_year=1911 AND property_id IS NULL
                      AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE %s""",
                (HUNT2, '%probably 2 Huntingdon%'))
    print(f"\n  {cur.rowcount} Walker rows housed at 2 Huntingdon Drive")
    cur.execute("""UPDATE census_entries
                      SET property_id=%s, address='White Gates, 8 Huntingdon Drive', unresolved_address=NULL,
                          source = source || ' - the note saying White Gates is not in the property '
                            'list was written before it was added; it is number 8'
                    WHERE census_year=1911 AND property_id IS NULL
                      AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE %s""",
                (WHITEGATES, '%Whitegates, Huntingdon%'))
    print(f"  {cur.rowcount} Ball rows housed at White Gates")
    for fn, ln in (('Nellie', 'Crawford'), ('Nellie', 'Walker'), ('Helen Main', 'Crawford')):
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT 2115,%s,%s,1885,'A. Hagues' FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(%s)
                          AND LOWER(TRIM(a.last_name))=LOWER(%s))""", (fn, ln, fn, ln))
    cur.execute("UPDATE people SET maiden_name=COALESCE(maiden_name,'Crawford') WHERE id=2115")
    c.commit()
    d = json.load(open('data/all_props.json'))
    for p in d:
        if p['id'] == CASTLE4 and 'Dougal de Havilland' not in (p.get('history') or ''):
            p['history'] = (p.get('history') or '') + CASTLE_NOTE
            print("  4 Castle Grove history extended")
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
else:
    print("\n  preview only - pass --apply")
