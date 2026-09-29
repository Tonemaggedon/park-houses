# -*- coding: utf-8 -*-
"""The 1939 Register's amended surnames, put back the way the page had them.

The Register was not a census. It was an identity register, kept up to date for
decades, so a woman who married after 1939 has her married name written across
the original and the online indexes show the LATER name. Ivy Burton, cook at
Penrhyn House on 29 September 1939, is indexed as Ivy Luke because somebody
wrote LUKE over Burton years afterwards.

The rule this record follows: **a person is named as the page named them on the
night**. The amendment is a real and valuable fact - it dates a marriage - but
it is a fact about what happened later, not the name of the woman in the house.

So the name goes back to the one she had, the married name is kept as an alias
so a search for it still finds her and a re-import cannot make a second person,
and the census row says what the page does.

Usage:
  railway run python3 fix_1939_amended_names.py          # show
  railway run python3 fix_1939_amended_names.py --apply  # do it
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

# person, name on the night, the name written over it, and where
AMENDED = [
 (7519, "Ivy", "Burton", "Luke", "Penrhyn House, Clumber Road East",
  "the Register is amended to LUKE in a later hand, struck through Burton"),
]

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    for pid, fn, was, later, where, note in AMENDED:
        cur.execute("SELECT first_name, last_name, maiden_name FROM people WHERE id=%s", (pid,))
        row = cur.fetchone()
        if not row: print(f"  #{pid}: no such person"); continue
        cfn, cln, cmaiden = row
        if cln == was:
            print(f"  #{pid} {cfn} {cln}: already as the page has it"); continue
        print(f"  #{pid} {cfn} {cln} (née {cmaiden})  ->  {fn} {was}, with {later} kept as an alias")
        print(f"      {where} - {note}")
        if APPLY:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),'1939 amendment'
                           FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE a.person_id=%s AND a.last_name=%s)""",
                        (pid, fn, later, pid, pid, later))
            cur.execute("UPDATE people SET last_name=%s, maiden_name=NULL WHERE id=%s", (was, pid))
            cur.execute("""UPDATE census_entries SET source = source || %s
                            WHERE person_id=%s AND census_year=1939 AND source NOT LIKE %s""",
                        (f"; entered as {fn} {was}, which is her name on the night; {note}, and the online "
                         f"indexes show the later name", pid, '%amended to ' + later.upper() + '%'))
    print("\n  Nothing written. Add --apply." if not APPLY else "\n  done")
    if APPLY: c.commit(); print("committed")

if __name__ == '__main__':
    main()
