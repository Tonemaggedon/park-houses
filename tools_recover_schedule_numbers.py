# -*- coding: utf-8 -*-
"""Schedule numbers written into the source sentence but never into the column.

A run of 1939 rows carries its schedule in prose - *1939 Register, schedule 231
sub 5 - single* - while `census_household_num` sits empty. The number is there
to read and the record cannot use it: the walk comes back with holes in it, the
site cannot gather a household, and the duplicate checks that key on
(year, schedule) cannot see those rows at all.

That is how **Florence Northern** came to be in the record twice. Her filed row
carried schedule 228; a second copy of her, under her married name Verner, had
no schedule number, so nothing matched them and nothing complained.

This reads the number out of the sentence and writes it into the column. It
only ever fills a column that is **empty**, and only where the sentence names
exactly one schedule.

  railway run python3 tools_recover_schedule_numbers.py            # preview
  railway run python3 tools_recover_schedule_numbers.py --apply
"""
import os, re, sys, psycopg2

APPLY = '--apply' in sys.argv
PAT = re.compile(r'\bschedule\s+(\d{1,4})\b', re.I)


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT ce.id, ce.census_year, p.first_name, p.last_name,
                          COALESCE(NULLIF(ce.address,''), ce.unresolved_address), ce.source
                     FROM census_entries ce JOIN people p ON p.id=ce.person_id
                    WHERE ce.census_household_num IS NULL AND ce.source ~* 'schedule [0-9]+'
                    ORDER BY ce.id""")
    done = skipped = 0
    for rid, year, fn, ln, addr, src in cur.fetchall():
        found = {int(m) for m in PAT.findall(src or '')}
        if len(found) != 1:
            print(f"  row {rid} {fn} {ln}: sentence names {sorted(found) or 'none'} - left alone")
            skipped += 1
            continue
        sched = found.pop()
        print(f"  row {rid} | {year} | {fn} {ln:<22} {addr or 'unfiled'} -> schedule {sched}")
        done += 1
        if APPLY:
            cur.execute("""UPDATE census_entries SET census_household_num=%s
                            WHERE id=%s AND census_household_num IS NULL""", (sched, rid))
    print(f"\n  {done} recovered, {skipped} left alone")
    if APPLY:
        c.commit(); print("  committed")
    else:
        print("  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
