# -*- coding: utf-8 -*-
"""Source sentences that cite the wrong schedule and the wrong house.

A source line is the record's evidence. It should say which schedule and which
house a row was read from, so anybody can go back to the page and check. When a
batch of households is written with **one source string copied across all of
them**, every row but one cites a house it did not come from - and that is worse
than no citation at all, because it looks like evidence.

**Sixty-nine 1939 rows carry the identical sentence** *"schedule 83, 7 Hamilton
Drive"* while their own schedule column and their own property say otherwise,
each one coherently: schedule 80 is 10 Hamilton Drive, 81 is 9, 82 is 8, 84 is
6, and so on down the street. The column and the property are right; the
sentence was copied.

This rewrites the opening citation of each such row to match the row itself,
and leaves the rest of the sentence alone. It only touches a row where the
schedule named in the sentence differs from the schedule in the column, where
the row has a property to name, and where **the text the sentence names after
the schedule is itself a house the property list holds** - so an address is only
ever swapped for an address, and a sentence of another shape is left alone.

  railway run python3 fix_source_citations.py            # preview
  railway run python3 fix_source_citations.py --apply
"""
import os, re, sys, json, psycopg2

APPLY = '--apply' in sys.argv


def main():
    props = {p['id']: p.get('address') for p in json.load(open('data/all_props.json'))}
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    known = {str(p.get('address', '')).lower() for p in json.load(open('data/all_props.json'))}
    cur.execute("""SELECT id, census_year, census_household_num, property_id, source
                     FROM census_entries
                    WHERE census_household_num IS NOT NULL AND source ~* 'schedule [0-9]+'
                    ORDER BY census_year, census_household_num, id""")
    done = skipped = 0
    shown = set()
    for rid, yr, sched, prop, src in cur.fetchall():
        m = re.search(r'schedule\s+(\d+)\s*,\s*([^,]+),', src, re.I)
        if not m or int(m.group(1)) == sched:
            continue
        addr = props.get(prop)
        cited = m.group(2).strip()
        # only ever swap an address for an address: the text the sentence names after the
        # schedule must itself be a house the property list holds, or this is a different
        # kind of sentence and must be left alone
        if not addr or cited.lower() not in known:
            print(f"  row {rid} ({yr} s{sched}): the sentence says schedule {m.group(1)} and then "
                  f"{cited!r}, which is not a house in the list - left alone")
            skipped += 1
            continue
        old = m.group(0)
        new = f"schedule {sched}, {addr},"
        if (yr, sched) not in shown:
            shown.add((yr, sched))
            print(f"  {yr} s{sched:<4} {addr:<30} was cited as: {old}")
        done += 1
        if APPLY:
            cur.execute("UPDATE census_entries SET source = replace(source, %s, %s) WHERE id=%s",
                        (old, new, rid))
    print(f"\n  {done} rows re-cited, {skipped} left alone")
    if APPLY:
        c.commit(); print("  committed")
    else:
        print("  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
