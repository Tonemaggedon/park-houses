# -*- coding: utf-8 -*-
"""Barrack Lane's missing 1939 houses are not missing - they are not in the Register.

A. Hagues searched the 1939 Register for Barrack Lane, Nottingham, and it
returns **thirteen addresses in two pieces** - nine in RG101/6177, one in 6178,
and the three Pelham Cottages in 6178. Those are the ones already sent, and
there are no others.

So the twelve Barrack Lane properties the record holds with no 1939 round are
**not waiting on a transcription**. The Register does not list them. A house
missing from it in 1939 was not a separate dwelling that year: demolished,
amalgamated with its neighbour, renumbered, or standing empty and unlisted.

They are recorded as having no 1939 household, **with a note that says why** -
because *the Register does not list the address* is a different fact from
*nobody was in it*, and the record should not pretend otherwise.

  railway run python3 close_barrack_lane_1939.py            # preview
  railway run python3 close_barrack_lane_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NOTE = ("{addr} - **the 1939 Register does not list this address at all.** A. Hagues searched it "
        "for Barrack Lane, Nottingham, on 4 October 2026: it returns thirteen addresses across "
        "RG101/6177 and RG101/6178, every one of which is in this record, and no others. So this "
        "is not a household waiting to be read - the house was not a separate dwelling in 1939, "
        "whether through demolition, amalgamation or renumbering. The record last saw it in "
        "{yr}{head}.")


def main():
    props = {p['id']: p.get('address') for p in json.load(open('data/all_props.json'))}
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT DISTINCT ce.property_id FROM census_entries ce
                    WHERE ce.property_id IS NOT NULL""")
    held = {r[0] for r in cur.fetchall()}
    done = 0
    for pid, addr in sorted(props.items(), key=lambda kv: str(kv[1])):
        if not addr or 'barrack' not in addr.lower() or pid not in held:
            continue
        cur.execute("""SELECT 1 FROM census_entries WHERE property_id=%s AND census_year=1939""", (pid,))
        if cur.fetchone():
            continue
        cur.execute("""SELECT 1 FROM census_unoccupied WHERE property_id=%s AND census_year=1939""", (pid,))
        if cur.fetchone():
            print(f"  {addr}: already closed"); continue
        cur.execute("""SELECT MAX(census_year) FROM census_entries WHERE property_id=%s""", (pid,))
        yr = cur.fetchone()[0]
        cur.execute("""SELECT p.first_name||' '||p.last_name, ce.occupation_at_census
                         FROM census_entries ce JOIN people p ON p.id=ce.person_id
                        WHERE ce.property_id=%s AND ce.census_year=%s
                          AND lower(COALESCE(ce.relationship,'')) LIKE 'head%%' LIMIT 1""", (pid, yr))
        h = cur.fetchone()
        head = (f", when {h[0]} had it" + (f", {h[1].lower()}" if h[1] else "")) if h else ""
        print(f"  {addr:<34} closed - last held {yr}{head}")
        done += 1
        if APPLY:
            cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes)
                           VALUES (%s, 1939, %s)""", (pid, NOTE.format(addr=addr, yr=yr, head=head)))
    print(f"\n  {done} Barrack Lane properties closed for 1939")
    if APPLY:
        c.commit(); print("  committed")
    else:
        print("  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
