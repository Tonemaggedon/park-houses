# -*- coding: utf-8 -*-
"""Barrack Yard survives as the yard, and the three cottages take their households back.

A. Hagues settled it: Barrack Yard is a place in its own right, and 1, 2 and 3
Pelham Cottage are the cottages standing in it. So the record keeps #410 and
files into the cottages everything two person records can place.

  1881  schedule 92   Hind          -> #451  3 Pelham Cottage   (4 people, unfiled)
  1901  schedule 207  Baker/Smith   -> #450  2 Pelham Cottage   (3 people, unfiled)
  1911  Barrack Yard  Smith         -> #450                     (3 people, from #410)
  1911  Barrack Yard  Hind          -> #451                     (3 people, from #410)
  1911  Barrack Yard  Blythe        -> #449  1 Pelham Cottage   (6 people, from #410)
  1921  "2 Barrack Lane" Smith      -> #450                     (2 people, from #3)
  1921  "3 Barrack Lane" Hind       -> #451                     (1 person, from #384)

**The anchors are two people, not one.** Arthur William Smith, born 23 January
1869, carries the number 2 from 1921 into 1939. Edith Annie Hind, born 20
January 1879, carries the number 3. Two families holding two different numbers
across the same pair of addresses is not a coincidence, and the Blythes follow
by elimination of three households into three cottages.

**#3 is a substantial listed house at the top of the lane** with a full building
description and no census but this one. A cabinet maker and his wife were never
in it. **#384 has no description, no history and no sources at all** - it was
made from the single index row being moved out of it, and will be left empty.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
NOTE = (" - Barrack Yard, Pelham Cottage and Pelham Cottages are one place; filed to the cottage "
        "by the household's own people, who carry their number across the rounds")

MOVES = [
  # (label, where to, SQL predicate selecting the rows)
  ("1881 s92 Hind -> 3 Pelham Cottage", 451,
   "census_year=1881 AND census_household_num=92 AND property_id IS NULL"
   " AND COALESCE(address,unresolved_address) ILIKE '%%pelham cottage%%'"),
  ("1901 s207 Baker/Smith -> 2 Pelham Cottage", 450,
   "census_year=1901 AND census_household_num=207 AND property_id IS NULL"),
  ("1911 Smith/Baker -> 2 Pelham Cottage", 450,
   "census_year=1911 AND property_id=410 AND person_id IN (485,486,487)"),
  ("1911 Hind -> 3 Pelham Cottage", 451,
   "census_year=1911 AND property_id=410 AND person_id IN (494,495,496)"),
  ("1911 Blythe -> 1 Pelham Cottage", 449,
   "census_year=1911 AND property_id=410 AND person_id IN (488,489,490,491,492,493)"),
  ("1921 Smith -> 2 Pelham Cottage", 450, "census_year=1921 AND property_id=3"),
  ("1921 Hind -> 3 Pelham Cottage", 451, "census_year=1921 AND property_id=384"),
]
ADDR = {449: '1 Pelham Cottage, Barrack Lane', 450: '2 Pelham Cottage, Barrack Lane',
        451: '3 Pelham Cottage, Barrack Lane'}
for label, to, pred in MOVES:
    cur.execute(f"""SELECT p.first_name, p.last_name, ce.age_at_census
                      FROM census_entries ce JOIN people p ON p.id=ce.person_id
                     WHERE {pred} ORDER BY ce.id""")
    rows = cur.fetchall()
    print(f"  {label:<44} {len(rows)}  " + ', '.join(f"{a} {b} {d}" for a,b,d in rows))
    if apply and rows:
        cur.execute(f"""UPDATE census_entries SET property_id=%s, address=%s,
                               source = COALESCE(source,'') || %s
                         WHERE {pred}""", (to, ADDR[to], NOTE))
if apply:
    c.commit()
    print("\n  applied")
    for pid in (3, 384, 410, 449, 450, 451):
        cur.execute("SELECT census_year, count(*) FROM census_entries WHERE property_id=%s"
                    " GROUP BY 1 ORDER BY 1", (pid,))
        print(f"   #{pid:<4} " + (' '.join(f"{y}:{n}" for y, n in cur.fetchall()) or "EMPTY"))
else:
    print("\n  preview only - pass --apply")
