# -*- coding: utf-8 -*-
"""Mark the 1939 rows whose surname is an amendment, not the name on the night.

The Register was an identity register kept up to date until 1991, so a woman who
married later has her married name written across the original. Where the
original is still legible the row can be put right (fix_1939_amended_names.py).
Where it is not - and the transcriber said so, sixty times - the surname in the
record IS the later name and the 1939 one is gone.

Nothing can recover those from the page. What can be done is to stop the record
claiming they are 1939 names. This writes that onto the row, so anybody reading
it knows the surname is later than the household it sits in.

Usage:
  railway run python3 mark_1939_amended_surnames.py          # show
  railway run python3 mark_1939_amended_surnames.py --apply  # do it
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
NOTE = (" - NOTE: the surname here is the amendment, not the name on the night. The 1939 Register was "
        "kept up to date as an identity register until 1991, and a married name has been written across "
        "the original, which cannot be read. Sixty of the sixty-one rows flagged this way are women")

def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT COUNT(*) FROM census_entries
                    WHERE census_year=1939 AND source ILIKE %s AND source NOT LIKE %s""",
                ('%written under the amendment cannot be read%', '%NOTE: the surname here is the amendment%'))
    n = cur.fetchone()[0]
    print(f"  {n} rows to mark")
    if APPLY:
        cur.execute("""UPDATE census_entries SET source = source || %s
                        WHERE census_year=1939 AND source ILIKE %s AND source NOT LIKE %s""",
                    (NOTE, '%written under the amendment cannot be read%',
                     '%NOTE: the surname here is the amendment%'))
        print(f"  {cur.rowcount} rows marked")
        c.commit(); print("committed")
    else:
        print("  Nothing written. Add --apply.")

if __name__ == '__main__':
    main()
