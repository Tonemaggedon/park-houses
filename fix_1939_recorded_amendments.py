# -*- coding: utf-8 -*-
"""The amendments the record already knew about, and never acted on.

Twenty-six 1939 rows carry a source line that says, in as many words, "entered
as Lewis and amended later to Wormington" - the transcriber read both names off
the page. The rule says the person is named as the page named them on the
night, and the amendment is kept as an alias. The reading was done; the rule
was not applied. So the record still called Elsie Margaret Lewis by the name
somebody wrote over her years afterwards.

This finds them by the shape of the source line rather than by a list, so it
keeps working as more pages are read.

Two are left alone and say why:
  * Meryl Vera Wardle, already put back, with two marriages recorded in order;
  * Meryl Hope M Owen, whose line reads "Taylor and amended to Owen, or the
    other way about; both are written" - the direction is not known, so
    nothing is done.

  railway run python3 fix_1939_recorded_amendments.py --apply
"""
import os, re, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'
PAT = re.compile(r"entered as ([A-Za-z'’-]+) and amended (?:later )?to ([A-Za-z'’-]+)")
# where the page shows more than one amendment, earliest first
EXTRA = {7428: ["Lazareff", "Beaumont"]}
SKIP = {7356: "already put back, with both marriages recorded in order",
        7776: "the page does not say which name came first - both are written"}


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT c.id, p.id, p.first_name, p.last_name, c.source
                     FROM census_entries c JOIN people p ON p.id = c.person_id
                    WHERE c.census_year = 1939 AND c.source ILIKE '%%entered as %% and amended%%'
                    ORDER BY p.id""")
    done = 0
    d = json.load(open(DATA))
    by_id = {}
    for x in d['people']:
        by_id.setdefault((x['first_name'], x['last_name']), x)

    for cid, pid, fn, ln, src in cur.fetchall():
        if pid in SKIP:
            print(f"  #{pid} {fn} {ln}: left alone - {SKIP[pid]}")
            continue
        m = PAT.search(src)
        if not m:
            print(f"  #{pid} {fn} {ln}: the line does not give both names, left alone")
            continue
        was = m.group(1)
        names = EXTRA.get(pid) or [m.group(2)]
        if ln.lower() == was.lower():
            print(f"  #{pid} {fn} {ln}: already as the page has it")
            continue
        kept = ', '.join(names)
        print(f"  #{pid} {fn} {ln}  ->  {fn} {was}, {kept} kept as "
              f"{'an alias' if len(names) < 2 else 'aliases, in that order'}")
        done += 1
        if not APPLY:
            continue
        for i, later in enumerate(names):
            label = ('1939 amendment' if len(names) < 2 else
                     f'1939 amendment ({"latest" if i == len(names)-1 else str(i+1)+"st"} married name)')
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),%s
                           FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE a.person_id=%s
                             AND LOWER(a.last_name)=LOWER(%s))""",
                        (pid, fn, later, pid, label, pid, later))
        cur.execute("UPDATE people SET last_name=%s, maiden_name=NULL WHERE id=%s", (was, pid))
        note = (f"; entered as {fn} {was}, which is her name on the night - the amendment is kept "
                f"as a name she can be found under, and the online indexes show it instead")
        cur.execute("UPDATE census_entries SET source = source || %s WHERE id=%s AND source NOT LIKE %s",
                    (note, cid, '%which is her name on the night%'))
        rec = by_id.get((fn, ln))          # and in the import file, bound by id
        if rec:
            rec['last_name'] = was
            rec['id'] = pid
            for ce in rec['census']:
                if ce.get('census_year') == 1939 and 'which is her name on the night' not in ce.get('source', ''):
                    ce['source'] = ce.get('source', '') + note
        else:
            print(f"        ! {fn} {ln} not found in {DATA}")

    if APPLY:
        json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
        c.commit()
        print(f"\n  {done} put back, committed")
    else:
        print(f"\n  {done} would be put back. Add --apply.")


if __name__ == '__main__':
    main()
