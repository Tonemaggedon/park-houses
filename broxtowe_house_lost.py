"""Broxtowe House - a lost house, and Arthur Carr assigned to it.

A. Hagues gives both from Dougal de Havilland's map of the Park: the house
stood where **Hart's Hotel** was built in **2002**, and **Arthur Carr**, the
England cricket captain, lived there.

**The link is made as a resident, not as a census row, and deliberately so.**
The record already holds Broxtowe House on the night of the 1921 census, and it
was full: nine house officers of a Nottingham hospital, John Kneebone at their
head, and nobody else. Arthur Carr is in the 1921 census the same night with a
household of seven of his own - his wife Ivy, his son Angus of three, a visitor
and three servants - at an address the record can place no closer than *Park
Terrace*.

So he cannot have been at Broxtowe House **on that night**, and nothing here
says he was. The resident link records that he lived there, which is what the
map says, and leaves the year open. See the question written on it.

**He is also marked notable**, which he was not. He captained Nottinghamshire
and England, and the record already held his life but not the mark.

**The position is read off the map to about twenty metres** and wants dragging
into place - Hart's Hotel stands below Tower House at the top of Park Steps,
and the record had Broxtowe House some way north-west of there.
"""
import os, sys, json, psycopg2
apply = '--apply' in sys.argv
BROXTOWE, CARR = 406, 1850
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT first_name,last_name,significant FROM people WHERE id=%s", (CARR,))
print("  Arthur Carr:", cur.fetchone())
cur.execute("SELECT count(*) FROM property_residents WHERE property_id=%s AND person_id=%s", (BROXTOWE, CARR))
print("  resident link already there:", cur.fetchone()[0])

NOTE = ("House demolished. **Hart's Hotel was built on the site in 2002**, on Dougal de Havilland's "
        "map of the Park. The position is read off the map to about twenty metres and wants "
        "dragging into place: Hart's Hotel stands below Tower House at the top of Park Steps.")
HIST = ("\n\n**Arthur Carr lived here**, on Dougal de Havilland's map - **Arthur William Carr "
        "(1893-1963), captain of Nottinghamshire and of England at cricket**.\n\n"
        "**He was not here on census night in 1921**, and the record should not be read as saying "
        "so. That night Broxtowe House held nine house officers of a Nottingham hospital and "
        "nobody else, while Carr was returned with a household of seven of his own - his wife Ivy, "
        "his son Angus aged three, a visitor and three servants - at an address the record can "
        "place no closer than Park Terrace. So he is recorded here as a resident with the years "
        "left open, which is what the map supports and no more.\n\n"
        "**The house was replaced by Hart's Hotel in 2002.**")

if apply:
    cur.execute("""UPDATE people SET significant=TRUE, significant_by='A. Hagues',
                          significance_note='Captain of Nottinghamshire and of England at cricket'
                    WHERE id=%s AND significant IS NOT TRUE""", (CARR,))
    print(f"\n  Arthur Carr marked notable: {cur.rowcount}")
    cur.execute("""INSERT INTO property_residents (property_id, person_id, notes)
                   SELECT %s,%s,'Placed here by Dougal de Havilland''s map of the Park. The years '
                                'are left open: on census night in 1921 Broxtowe House held nine '
                                'hospital house officers and Carr was elsewhere on Park Terrace '
                                'with a household of his own.'
                     FROM (SELECT 1) t
                    WHERE NOT EXISTS (SELECT 1 FROM property_residents
                                       WHERE property_id=%s AND person_id=%s)""",
                (BROXTOWE, CARR, BROXTOWE, CARR))
    print(f"  resident link written: {cur.rowcount}")
    c.commit()
    d = json.load(open('data/all_props.json'))
    for p in d:
        if p['id'] == BROXTOWE:
            p['demolished'] = True
            p['demolished_notes'] = NOTE
            p['lat'], p['lng'] = 52.95125, -1.15655
            if "Hart's Hotel" not in (p.get('history') or ''):
                p['history'] = (p.get('history') or '') + HIST
            print(f"  Broxtowe House: demolished, repositioned to {p['lat']}, {p['lng']}")
    json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
else:
    print("\n  preview only - pass --apply")
