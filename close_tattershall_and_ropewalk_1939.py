"""A. Hagues read these as ticked and left blank on the night of 29 September 1939.

He also gave 29 The Ropewalk. The property list holds no odd number on that
street at all - every house in it is even, bar 2a, 32a and 36a - so there is
nothing to close, and it is written up as a question instead.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
NOTE = ("{addr}, ticked and left blank in the 1939 Register - nobody was living there on the night "
        "of 29 September 1939. Read from the page by A. Hagues. The schedule number is not yet "
        "recorded against it.")
HOUSES = [(307, '2 Tattershall Drive'), (309, '4 Tattershall Drive'),
          (404, 'Gartree Lodge, 17a Tattershall Drive'),
          (317, '10 The Ropewalk'), (322, '20 The Ropewalk'), (326, '28 The Ropewalk'),
          (327, '30 The Ropewalk'), (329, '32a The Ropewalk'), (418, '36a The Ropewalk'),
          (332, '38 The Ropewalk'), (417, '46 The Ropewalk')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for pid, addr in HOUSES:
    cur.execute("SELECT count(*) FROM census_entries WHERE property_id=%s AND census_year=1939", (pid,))
    n = cur.fetchone()[0]
    print(f"  {pid:<5} {addr:<40} {'ALREADY HAS A HOUSEHOLD' if n else 'closed'}")
    if apply and not n:
        cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes) VALUES (%s,1939,%s)
                       ON CONFLICT (property_id, census_year) DO UPDATE SET notes=EXCLUDED.notes""",
                    (pid, NOTE.format(addr=addr)))
if apply:
    c.commit(); print(f"\n  {len(HOUSES)} houses closed for 1939")
else:
    print("\n  preview only - pass --apply")
