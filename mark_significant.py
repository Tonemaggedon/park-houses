# -*- coding: utf-8 -*-
"""Mark people whose lives are written up but whose flag was never set.

A biography in the record does not by itself put anyone on the Notable
Residents page - the `significant` flag does, and four people have been
carrying finished lives without it.
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

MARK = [
 (2131, "Editor of Nicholas Breton's prose and a writer on Elizabethan literature"),
 (2130, "Playwright and adapter for the stage, and a Voluntary Aid Detachment nurse in the war"),
 (1909, "Lord Mayor of Nottingham and Conservative Member of Parliament for Nottingham Central"),
 (7564, "Professor of Physics at Nottingham, CBE and Fellow of the Royal Society"),
 # These two arrive with data/people_1921_derby_road.json, so they are named
 # rather than numbered. Re-run after the import and they are picked up.
 (("Virginia", "Compton", 1853),
  "Actress and theatre manager, lessee of the Grand Theatre, Nottingham, from 1920"),
 (("Compton", "Mackenzie", 1883),
  "Novelist, author of Whisky Galore and The Monarch of the Glen. Not a resident of The Park - "
  "he is here as the son of Virginia Compton, who was"),
]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for who, note in MARK:
        if isinstance(who, tuple):
            fn, ln, by = who
            cur.execute("""SELECT id FROM people WHERE LOWER(first_name)=LOWER(%s)
                            AND LOWER(last_name)=LOWER(%s) AND born_year=%s""", (fn, ln, by))
            found = cur.fetchall()
            if len(found) != 1:
                print(f"  {fn} {ln} ({by}): {'not in the record yet' if not found else 'more than one of that name'} - skipped")
                continue
            pid = found[0][0]
        else:
            pid = who
        cur.execute("SELECT first_name||' '||last_name, significant, bio IS NOT NULL FROM people WHERE id=%s", (pid,))
        row = cur.fetchone()
        if not row: print(f"  #{pid}: no such person"); continue
        name, already, has_bio = row
        if already: print(f"  #{pid} {name}: already marked"); continue
        if not has_bio: print(f"  #{pid} {name}: no biography - skipped"); continue
        if APPLY:
            cur.execute("""UPDATE people SET significant=TRUE, significance_note=%s,
                                  significant_by='A. Hagues', significant_at=NOW() WHERE id=%s""", (note, pid))
        print(f"  #{pid} {name} -> {note}")
    if APPLY:
        cur.execute("SELECT COUNT(*) FROM people WHERE significant")
        print(f"\n  people marked significant: {cur.fetchone()[0]}")
        c.commit(); print("committed")
    else:
        print("\nNothing written. Run again with --apply.")

if __name__ == '__main__':
    main()
