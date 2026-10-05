# -*- coding: utf-8 -*-
"""Standard Hill and the houses beyond it, 1901 - schedules 28 to 35.

The enumerator leaves The Ropewalk at schedule 28 and goes onto Standard Hill.
**None of these addresses is in the property list**, so every household is
filed unresolved against the address the page gives.
"""
import os, sys, json, psycopg2
APPLY = '--apply' in sys.argv
SRC = "1901 census, {addr}, schedule {sched} - read from the enumerator's page by A. Hagues"
H = [
 (28, "1 Standard Hill", [
  ("Elijah","Lyneham","M",56,"Head","Married","Retired actor and theatre manager","Nottinghamshire","the surname may be Lyncham or Lynehan"),
  ("Emma","Lyneham","F",57,"Wife","Married",None,"Nottinghamshire",None),
  ("Maud","Wright","F",26,"Boarder","Single","Practical milliner","Bromsgrove, Worcestershire",None),
 ]),
 (29, "3 Standard Hill", [
  ("Hannah","Stapleton","F",67,"Head","Single","Living on own means","Nottingham",None),
  ("Ellen","King","F",53,"Boarder","Single","Nurse, hospital","Lincoln",None),
  ("Sarah","Jarrow","F",51,"Boarder","Single","Charing","Nottingham",None),
 ]),
 (30, "St Peter's Rectory, Standard Hill", [
  ("George","Edgcome","M",70,"Head","Widowed","Minister, Church of England","St Thomas Mount, Madras","the surname may be Edgcombe or Edgecumbe"),
  ("Margaret","Edgcome","F",25,"Daughter","Single",None,"Nottingham",None),
  ("Fannie J","Edgcome","F",57,"Sister","Single",None,"Madras Presidency, India",None),
  ("Mary","Lambert","F",18,"Servant","Single","Domestic","Leicestershire",None),
  ("Nora","Towers","F",19,"Servant","Single","Domestic","Annesley, Nottinghamshire",None),
 ]),
 (31, "Standard Hill (no number given)", [
  ("William","Staunton","M",50,"Head","Married","Tailor","Gateshead, Durham",None),
  ("Gertrude","Staunton","F",33,"Wife","Married",None,"Nottingham",None),
 ]),
 (32, "Standard Hill (no number given)", [
  ("Hephzibah","Baxter","F",70,"Head","Widowed","Dressmaker, at home","Nottingham",None),
 ]),
 (33, "Standard Hill (no number given)", [
  ("Charles","King","M",35,"Head","Married","Music hall artiste","Leicester",None),
  ("Susan","King","F",28,"Wife","Married",None,"Basford, Nottinghamshire",None),
  ("Mirian","King","F",2,"Daughter",None,None,"Nottinghamshire","the forename may be Miriam or Marian"),
 ]),
 (34, "Standard Hill (no number given)", [
  ("William","King","M",66,"Head","Married","Provision merchant, employer","Cromford, Derbyshire",None),
  ("Rachel","King","F",62,"Wife","Married",None,"Derby",None),
  ("Louis H","King","M",28,"Son","Single","Restaurant caterer","Nottingham",None),
  ("Charles E","King","M",25,"Son","Single","Restaurant caterer","Nottingham",None),
  ("Helen M","King","F",18,"Daughter","Single",None,"Nottingham",None),
  ("Mary","Allen","F",24,"Servant","Single","Cook, domestic","Sheffield",None),
  ("Gertrude","Heath","F",17,"Servant","Single","Housemaid, domestic","Edwinstowe, Nottinghamshire",None),
 ]),
 (35, "Park View, Standard Hill", [
  ("William","Dalton","M",65,"Head","Married","Pork butcher, own account","Northamptonshire",None),
  ("Henrietta","Dalton","F",61,"Wife","Married",None,"Island of Jersey",None),
  ("Jane","Dalton","F",59,"Aunt","Single",None,"Northamptonshire",None),
  ("Flora","Dalton","F",29,"Daughter","Single","Governess, school","Nottingham",None),
 ]),
]
def main():
    c=psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL']); cur=c.cursor()
    out,n=[],0
    for sched, addr, people in H:
        print(f"--- schedule {sched}, {addr}  ({len(people)})")
        for fn,ln,sex,age,rel,cond,occ,bp,note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1901 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)
                              AND ce.age_at_census=%s""",(sched,fn,ln,age))
            if cur.fetchone(): continue
            src=SRC.format(addr=addr,sched=sched)+(('; '+note) if note else '')
            n+=1
            if not APPLY: continue
            cur.execute("""INSERT INTO people (first_name,last_name,sex,born_year,born_place)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",(fn,ln,sex,1901-age,bp))
            pid=cur.fetchone()[0]
            cur.execute("""INSERT INTO census_entries
                           (person_id,census_year,unresolved_address,age_at_census,relationship,
                            occupation_at_census,census_household_num,marital_status,birth_place,source)
                           VALUES (%s,1901,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid,addr,age,rel,occ,sched,cond,bp,src))
            out.append({"first_name":fn,"last_name":ln,"sex":sex,"born_year":1901-age,"id":pid,
                        "born_place":bp,
                        "census":[{"census_year":1901,"age_at_census":age,"unresolved_address":addr,
                                   "relationship":rel,"occupation_at_census":occ,
                                   "census_household_num":sched,"marital_status":cond,
                                   "birth_place":bp,"source":src}]})
    print(f"\n  {n} rows")
    if APPLY:
        json.dump({"note":"**Standard Hill, 1901, schedules 28 to 35** - the enumerator leaves The "
                          "Ropewalk here. None of these addresses is in the property list, so every "
                          "household is filed unresolved.",
                   "source":"1901 census, Standard Hill, Nottingham - read from the enumerator's page",
                   "people":out}, open('data/people_1901_standard_hill_ropewalk_round.json','w'),
                  indent=1,ensure_ascii=False)
        c.commit(); print("  committed")
if __name__=='__main__': main()
