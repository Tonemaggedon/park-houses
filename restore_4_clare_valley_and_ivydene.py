# -*- coding: utf-8 -*-
"""4 Clare Valley restored, and two surnames corrected on A. Hagues' reading.

**4 Clare Valley, schedule 51, was genuinely absent from the record** and my
blanket removal of schedules 49 to 72 took it out along with the duplicates.
It goes back, with the head's surname as A. Hagues reads it: **Page**, not
Wilkins.

**Schedule 53 is George PEARSON, not Ranson**, and the house is **Ivydene** -
the existing transcription has it as "Ivy Dene [?]" with the reading queried.

George Hill at the Lodge, schedule 52, is confirmed as the record already has
him.
"""
import os, sys, json, psycopg2
APPLY = '--apply' in sys.argv
SRC = ("1901 census, 4 Clare Valley, schedule 51 - read from the enumerator's page by A. Hagues, "
       "who gives the head's surname as Page")
PEOPLE = [
 ("Lawrence","Page","M",39,"Head","Married","Clergyman, Church of England","Richmond, Yorkshire"),
 ("E J","Page","F",30,"Wife","Married",None,"Nottingham"),
 ("L A","Page","M",6,"Son","Single",None,"Nottingham"),
 ("Eleanor","Page","F",5,"Daughter","Single",None,"Nottingham"),
 ("Jessie","Page","F",4,"Daughter","Single",None,"Nottingham"),
 ("Minnie","Lee","F",25,"Servant","Single","Nurse, domestic","Sudbury, Staffordshire"),
 ("Ida","Scott","F",20,"Servant","Single","Cook, domestic","Mansfield, Nottinghamshire"),
 ("Ruth","Wallam","F",14,"Servant","Single","Housemaid, domestic","Hoveringham, Nottinghamshire"),
]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT count(*) FROM census_entries WHERE census_year=1901 AND census_household_num=51")
print(f"  schedule 51 currently holds {cur.fetchone()[0]} rows")
cur.execute("""SELECT p.id,p.first_name,p.last_name FROM census_entries ce JOIN people p ON p.id=ce.person_id
                WHERE ce.census_year=1901 AND ce.census_household_num=53 AND p.last_name='Ranson'""")
print("  Ranson -> Pearson:", cur.fetchall())
if APPLY:
    out = []
    for fn, ln, sex, age, rel, cond, occ, bp in PEOPLE:
        cur.execute("""INSERT INTO people (first_name,last_name,sex,born_year,born_place)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, 1901-age, bp))
        pid = cur.fetchone()[0]
        note = (SRC + ("; the page gives initials only" if fn in ('E J','L A') else ""))
        cur.execute("""INSERT INTO census_entries
                       (person_id,property_id,census_year,address,age_at_census,relationship,
                        occupation_at_census,census_household_num,marital_status,birth_place,source)
                       VALUES (%s,62,1901,'4 Clare Valley',%s,%s,%s,51,%s,%s,%s)""",
                    (pid, age, rel, occ, cond, bp, note))
        out.append({"first_name":fn,"last_name":ln,"sex":sex,"born_year":1901-age,"id":pid,
                    "born_place":bp,
                    "census":[{"census_year":1901,"age_at_census":age,"address":"4 Clare Valley",
                               "property_id":62,"relationship":rel,"occupation_at_census":occ,
                               "census_household_num":51,"marital_status":cond,"birth_place":bp,
                               "source":note}]})
    cur.execute("UPDATE people SET last_name='Pearson' WHERE last_name='Ranson' AND id IN (4618,4619,4620)")
    print(f"  Pearsons renamed: {cur.rowcount}")
    cur.execute("""UPDATE census_entries
                      SET unresolved_address='Ivydene, Clare Valley',
                          source = source || ' - the surname is PEARSON and the house is IVYDENE, on '
                                   'A. Hagues'' reading; the transcription had Ranson and queried the '
                                   'house name'
                    WHERE census_year=1901 AND census_household_num=53
                      AND source NOT ILIKE '%IVYDENE%'""")
    print(f"  Ivydene rows corrected: {cur.rowcount}")
    c.commit()
    json.dump({"note":"**4 Clare Valley, schedule 51 of the 1901 census.** The Reverend Lawrence "
                      "Page, a Church of England clergyman, with his wife, three young children and "
                      "three servants.",
               "source":"1901 census, Clare Valley, Nottingham - read from the enumerator's page",
               "people":out}, open('data/people_1901_4_clare_valley.json','w'),indent=1,ensure_ascii=False)
    print(f"  4 Clare Valley restored - {len(out)} people")
else:
    print("\n  preview only - pass --apply")
