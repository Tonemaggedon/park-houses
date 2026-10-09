# -*- coding: utf-8 -*-
"""The people page took 7.4 seconds because three foreign keys had no index.

/api/people runs four correlated subqueries per person over census_entries,
occupations and property_residents. With no index on their person_id columns
that is roughly 33,000 sequential scans for one page load - 7.5 million buffer
hits to return 8,352 rows.
"""
import os, sys, time, psycopg2
IDX = [
 ("census_entries_person_idx",      "census_entries(person_id)"),
 ("census_entries_property_idx",    "census_entries(property_id)"),
 ("census_entries_year_idx",        "census_entries(census_year)"),
 ("occupations_person_idx",         "occupations(person_id)"),
 ("property_residents_person_idx",  "property_residents(person_id)"),
 ("property_residents_property_idx","property_residents(property_id)"),
 ("person_alias_person_idx",        "person_alias(person_id)"),
 ("people_name_idx",                "people(last_name, first_name)"),
]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
c.autocommit = True
cur = c.cursor()
for name, spec in IDX:
    t = time.time()
    cur.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {spec}")
    print(f"  {name:<34} {time.time()-t:.2f}s")
cur.execute("ANALYZE census_entries"); cur.execute("ANALYZE occupations")
cur.execute("ANALYZE property_residents"); cur.execute("ANALYZE people")
print("  analyzed")
