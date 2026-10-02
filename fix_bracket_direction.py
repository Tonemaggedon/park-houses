# -*- coding: utf-8 -*-
"""The bracket holds the married name, not the name on the night. Four people turned back.

A. Hagues settles the convention: **the name on the line is the name on the
night, and the name written over it - the one the index puts in brackets - is
the married name she took afterwards**. *Lowe (Perry)* is Alice Lowe, who became
Perry. The Acho/Victoria line at 2 South Road, where a forename was rewritten
with the surname, was a one-off and not the rule.

This record read it the other way for a while and put four people back under the
wrong half of their own entry. They are turned round here.

**It makes better sense of the households, not worse.** Ethel M Edward at 8 Park
Drive was taken for a Howitt daughter; she is a woman named Edward living with
the Howitts who married **John Kenneth Howitt**, 28 and single at sub number 3 -
the same shape as Muriel Langtree and Ronald Cotter two doors apart on Hamilton
Drive.

  railway run python3 fix_bracket_direction.py --apply
"""
import os, sys, glob, json, psycopg2

APPLY = '--apply' in sys.argv

# person, forename, name ON THE NIGHT (was the alias), the married name (was the record's)
TURN = [
 (7411, "Ethel M",  "Edward",   "Howitt",
  "she is not a Howitt daughter - she is a woman named Edward in the Howitt household who married "
  "John Kenneth Howitt, 28 and single at sub number 3 of the same schedule"),
 (7412, "Amy M",    "Oakland",  "Jenkins", None),
 (8573, "Alice",    "James",    "Mees",    None),
 (8580, "Victoria", "Wright",   "Richardson",
  "the forename is Victoria either way - A. Hagues settles that the rewritten forename on this "
  "line was a one-off and not the convention"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    files = {f: json.load(open(f)) for f in glob.glob('data/people_19*.json')}
    for pid, fn, night, married, note in TURN:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (pid,))
        got = cur.fetchone()
        if not got:
            print(f"  #{pid}: not in the record"); continue
        if got[1].lower() == night.lower():
            print(f"  #{pid} {got[0]} {got[1]}: already the right way round"); continue
        print(f"  #{pid} {got[0]} {got[1]}  ->  {fn} {night}, afterwards {married}")
        if note:
            print(f"      {note}")
        if not APPLY:
            continue
        cur.execute("UPDATE people SET first_name=%s, last_name=%s WHERE id=%s", (fn, night, pid))
        cur.execute("DELETE FROM person_alias WHERE person_id=%s AND LOWER(last_name)=LOWER(%s)",
                    (pid, night))
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),'1939 amendment'
                       FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                         AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                    (pid, fn, married, pid, fn, married))
        said = (f"; CORRECTED: this record first read the bracketed name as the name on the night "
                f"and had her as {fn} {married}. A. Hagues settles the convention the other way - "
                f"the name on the line is the night name and the one written over it is the "
                f"married name - so she is {fn} {night}, afterwards {married}"
                + (f". {note[0].upper()}{note[1:]}" if note else ""))
        cur.execute("""UPDATE census_entries SET source = COALESCE(source,'') || %s
                        WHERE person_id=%s AND POSITION(%s IN COALESCE(source,'')) = 0""",
                    (said, pid, said))
        for f, d in files.items():
            for x in d.get('people', d if isinstance(d, list) else []):
                if isinstance(x, dict) and x.get('id') == pid:
                    x['first_name'], x['last_name'] = fn, night
                    for ce in x.get('census', []):
                        if ce.get('census_year') == 1939 and 'CORRECTED:' not in ce.get('source', ''):
                            ce['source'] = ce.get('source', '') + said
    if APPLY:
        for f, d in files.items():
            json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
