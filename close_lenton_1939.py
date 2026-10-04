"""A. Hagues read these as ticked and left blank on the night of 29 September 1939."""
import os, sys, psycopg2
apply = '--apply' in sys.argv
NOTE = ("{addr}, ticked and left blank in the 1939 Register - nobody was living there on the night "
        "of 29 September 1939. Read from the page by A. Hagues. The schedule number is not yet "
        "recorded against it.")
HOUSES = [(177, '4 Lenton Road'), (179, '6 Lenton Road'), (419, 'Bowling Green, 35 Lenton Road'),
          (365, '33 Lenton Road'), (196, 'Cliff House, Lenton Road'), (364, '24 Lenton Road'),
          (186, '13a Lenton Road'), (368, '6 Lenton Avenue')]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for pid, addr in HOUSES:
    cur.execute("SELECT count(*) FROM census_entries WHERE property_id=%s AND census_year=1939", (pid,))
    n = cur.fetchone()[0]
    print(f"  {pid:<5} {addr:<34} {'ALREADY HAS ' + str(n) + ' 1939 ROWS' if n else 'ok to close'}")
    if apply and not n:
        cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes) VALUES (%s,1939,%s)
                       ON CONFLICT (property_id, census_year) DO UPDATE SET notes=EXCLUDED.notes""",
                    (pid, NOTE.format(addr=addr)))
if apply:
    c.commit(); print(f"\n  {len(HOUSES)} houses closed for 1939")
else:
    print("\n  preview only - pass --apply")
