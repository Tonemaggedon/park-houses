"""The six stale numbers the automatic rebinding would not touch.

George S M Johnson is in the record three times over - #3552, #5863 and #7099,
all of them the solicitor's son aged twelve at schedule 140 of the 1871 census,
born at Faversham in Kent. #3552 is the one who goes on to 17 Pelham Crescent
in 1881 and 1891 under his full name, George Milton Sydney Johnson, so the two
bare copies fold into him.

The rest are bindings a file could not make on its own:

  Henry Wing      - two men of the name; the file is the Pelham Crescent round,
                    so it means #8402 at Kentmere, not #3648 at 12 Park Terrace
  Constance Lindley - #1820 Constance Agnes Lindley, Tinsley's wife
  John Shaw Perry - #8037 John Thorpe Perry, folded this morning. Shaw was a
                    misreading of the Register, and it is kept as a variant so
                    a search under it still finds him.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
KEEP, DROPS = 3552, (5863, 7099)
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

for d in DROPS:
    cur.execute("SELECT id FROM census_entries WHERE person_id=%s", (d,))
    print(f"  #{d} carries census rows {[r[0] for r in cur.fetchall()]}")

BINDS = [('data/people_1901_pelham_crescent.json', 'Henry Wing', 670, 8402),
         ('data/people_1901_park_terrace_gap_round.json', 'Constance Lindley', 7890, 1820),
         ('data/people_1939_rmgc_the_park.json', 'John Shaw Perry', 8392, 8037)]
for path, name, old, new in BINDS:
    doc = json.load(open(path)); hit = False
    for q in doc.get('people', []):
        if f"{q.get('first_name','')} {q.get('last_name','')}".strip() == name and q.get('id') == old:
            q['id'] = new; hit = True
    print(f"  {os.path.basename(path)}: {name} #{old} -> #{new} {'' if hit else '(NOT FOUND)'}")
    if apply and hit: json.dump(doc, open(path, 'w'), indent=1, ensure_ascii=False)

if apply:
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, made_by)
                   VALUES (8037,'John Shaw','Perry','A. Hagues') ON CONFLICT DO NOTHING""")
    for d in DROPS:
        cur.execute("DELETE FROM census_entries WHERE person_id=%s", (d,))
        for t in ('property_residents', 'occupations', 'person_alias'):
            cur.execute(f"DELETE FROM {t} WHERE person_id=%s", (d,))
        cur.execute("DELETE FROM people WHERE id=%s", (d,))
    c.commit()
    print(f"\n  folded {DROPS} into #{KEEP}, and the three bindings written")
else:
    print("\n  preview only - pass --apply")
