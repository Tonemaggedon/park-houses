"""Kentmere is 8 North Road, on the corner of Pelham Crescent.

A. Hagues has it from the ground and from the walk. The record agrees at every
point it can be tested.

**The house has exactly the right hole in it.** 8 North Road is held for 1939
and for nothing else - no 1901, no 1911 - which is what a house occupied by one
family across both rounds looks like when the record has never placed them.

**The walk reaches it where it should.** Schedule 195 of 1901 is 1 Cavendish
Crescent North, 196 is Kentmere, and the numbered Pelham Crescent houses do not
begin until 199 at number 5. A corner house is where the enumerator turns.

**And the two returns name the two streets the corner joins.** 1901 gives
Pelham Crescent, 1911 gives Cavendish Crescent North. A house on that corner
takes whichever street the enumerator is walking - the same thing that settled
Flixton, Pendower and Castle Mount this week.

Twelve records, one family across ten years: William Wing, solicitor, his wife
Sarah Whitehead, their sons Henry and Richard, and two servants in each round.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
NORTH8 = 231
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
W = """property_id IS NULL AND COALESCE(NULLIF(address,''),unresolved_address) ILIKE %s"""
PAT = '%Kentmere%' 
cur.execute(f"""SELECT ce.census_year,ce.census_household_num,p.first_name,p.last_name,ce.age_at_census
                  FROM census_entries ce JOIN people p ON p.id=ce.person_id
                 WHERE {W} ORDER BY ce.census_year, ce.id""", (PAT,))
for r in cur.fetchall(): print(f"   {r[0]} s{r[1]} {r[2]} {r[3]}, {r[4]}")
if apply:
    cur.execute(f"""UPDATE census_entries
                      SET property_id=%s, address='8 North Road', unresolved_address=NULL,
                          source = source || ' - housed at 8 NORTH ROAD, on the corner of Pelham '
                            'Crescent, by A. Hagues from the ground and the walk. The house is held '
                            'for 1939 and for nothing else, which is the gap a family across both '
                            'these rounds would leave; schedule 195 of 1901 is 1 Cavendish Crescent '
                            'North and the numbered Pelham Crescent houses do not begin until 199 at '
                            'number 5, so 196 falls where the enumerator turns the corner; and the '
                            'two returns name the two streets that corner joins'
                    WHERE {W}""", (NORTH8, PAT))
    print(f"\n  {cur.rowcount} rows housed at 8 North Road")
    c.commit()
    d = json.load(open('data/all_props.json'))
    for p in d:
        if p['id'] == NORTH8:
            prev = [x.strip() for x in str(p.get('prev_house_name') or '').split('\n') if x.strip()]
            if 'Kentmere' not in prev: prev.append('Kentmere')
            p['prev_house_name'] = '\n'.join(prev)
            p['house_name'] = p.get('house_name') or 'Kentmere'
            p['history'] = (p.get('history') or '') + (
              "\n\n**The house was called Kentmere.** William Wing, solicitor, is here in 1901 and "
              "again in 1911 with his wife Sarah Whitehead and their sons Henry and Richard - the "
              "1901 enumerator writes *Pelham Crescent, Kentmere* and the 1911 one *Cavendish "
              "Crescent North*, which is a corner house taking whichever street the walk is on. "
              "A. Hagues placed it from the ground; the record had both rounds unfiled under the "
              "name alone.\n\n**Not to be confused with Kenmare**, also written Kenmore, which is a "
              "former name of Avalon, 10 Huntingdon Drive.")
            print(f"  Kentmere recorded as a former name of {p['address']}")
    json.dump(d, open('data/all_props.json','w'), indent=1, ensure_ascii=False)
else:
    print("\n  preview only - pass --apply")
