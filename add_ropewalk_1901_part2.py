# -*- coding: utf-8 -*-
"""The Ropewalk, 1901 - schedules 7 to 27, continuing from the first page.

Read from the enumerator's pages sent by A. Hagues. Three houses in the run -
50, 58 and 60 - are not in the property list, so those households are filed
unresolved against their address.

**12 The Ropewalk is returned UNINHABITED**, with "Lace Manufacturer, Employer"
written in and struck through - so the house had a tenant the enumerator began
to record and then found empty.
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1901 census, {addr}, schedule {sched} - read from the enumerator's page by A. Hagues")
# prop (None = unresolved), schedule, address, [(fn, ln, sex, age, rel, cond, occ, birthplace, note)]
H = [
 (320, 7, "16 The Ropewalk", [
  ("Charles J","Cabron","M",44,"Head","Married","Lace manufacturer, employer","Nottingham","the surname may be Cadron; the hand is not clear"),
  ("Alice","Cabron","F",39,"Wife","Married",None,"Nottingham",None),
  ("Marjorie","Cabron","F",8,"Daughter","Single",None,"Radcliffe on Trent, Nottinghamshire",None),
  ("Dora","Cabron","F",5,"Daughter","Single",None,"Radcliffe on Trent, Nottinghamshire",None),
  ("Ethel","Borebank","F",16,"Servant","Single","Housemaid, domestic","Sheffield","the surname may be Borebanks or Forebank"),
 ]),
 (321, 8, "18 The Ropewalk", [
  ("Ada","Eames","F",52,"Head of house","Single","Living on own means","Nottingham",None),
  ("Ida","Cave","F",24,"Servant","Single","Lady's help, domestic","Baston, Market Deeping, Lincolnshire",None),
 ]),
 (322, 9, "20 The Ropewalk", [
  ("Lucy","Carey","F",54,"Sister","Single","Living on own means","Nottingham","NO HEAD IS ENTERED for this house; all three Careys are returned as Sister"),
  ("Henry","Carey","M",49,"Brother","Single","Living on own means","Nottingham",None),
  ("Henrietta","Carey","F",47,"Sister","Single","Living on own means","Nottingham",None),
  ("Mary","Hallewell","F",21,"Servant","Single","Cook, domestic","Benbrook near Market Rasen, Lincolnshire","the surname may be Hettewell"),
  ("Emma","Longmate","F",17,"Servant","Single","Housemaid, domestic","Bulwell, Nottinghamshire",None),
 ]),
 (323, 10, "22 The Ropewalk", [
  ("George","Kenrick","M",68,"Head","Single","Living on own means","West Bromwich","the birthplace is written over and may read Sheffield"),
  ("Eva","Kennedy","F",29,"Servant","Single","Nursing, domestic","Kirkdale, Liverpool",None),
  ("Harriet","Bush","F",35,"Servant","Single","Cook, domestic","Askham, Nottinghamshire",None),
  ("Eliza A","Coy","F",18,"Servant","Single","Housemaid, domestic","Bingham, Nottinghamshire","the birthplace is not clear; it may be Byford or Bingham"),
 ]),
 (324, 11, "24 The Ropewalk", [
  ("George","Coke","M",48,"Head","Married","Civil and mining engineer, employer","Chesterfield, Derbyshire",None),
  ("Annie","Coke","F",46,"Wife","Married",None,"Chesterfield, Derbyshire",None),
  ("R A J","Coke","M",9,"Son","Single",None,"Nottingham","the page gives initials only"),
  ("Fanny E","Humble","F",45,"Sister-in-law","Single","Living on own means","Derbyshire",None),
  ("Anneta","Taylor","F",20,"Servant","Single","Parlourmaid, domestic","Leadenham, Lincolnshire",None),
  ("Minnie","Dent","F",22,"Servant","Single","Housemaid, domestic","Caistor, Lincolnshire",None),
  ("Ellen","Hunt","F",25,"Servant","Single","Cook, domestic","Caistor, Lincolnshire",None),
 ]),
 (325, 12, "26 The Ropewalk", [
  ("Edward","Schilling","M",57,"Head","Married","No occupation; returned as Consul","Germany","the employment column reads CONSUL against no occupation"),
  ("Mary","Schilling","F",49,"Wife","Married",None,"England",None),
  ("Julie","Schilling","F",28,"Daughter","Single",None,"England",None),
  ("Emily","Richards","F",23,"Servant","Single","Housemaid, domestic","England",None),
  ("Marie","Rohe","F",30,"Servant","Single","Cook, domestic","Germany",None),
 ]),
 (326, 13, "28 The Ropewalk", [
  ("James","Ward","M",54,"Head","Single","Solicitor, employer","Tollerton, Nottinghamshire",None),
  ("William","Ward","M",51,"Brother","Single","Bank clerk, cashier","Tollerton, Nottinghamshire",None),
  ("Ellen","Harrison","F",32,"Servant","Single","Cook, domestic","Brighton, Sussex",None),
  ("Jane","Sharp","F",18,"Servant","Single","Housemaid, domestic","East Stoke, Nottinghamshire",None),
  ("Harry","Sharp","M",15,"Servant","Single","Page, domestic","East Stoke, Nottinghamshire",None),
 ]),
 (327, 14, "30 The Ropewalk", [
  ("Jessie","Batten","F",39,"Partner","Single","Principal of a private school","Ely, Cambridgeshire",
   "THE HOUSE IS A GIRLS' BOARDING SCHOOL run by three partners. The page gives it two schedule "
   "numbers, 14 and 15, bracketed together"),
  ("Annie","Green","F",40,"Partner","Single","Principal of a private school","Beverley, Yorkshire",None),
  ("Florence","Green","F",38,"Partner","Single","Principal of a private school","Beverley, Yorkshire",None),
  ("Annie","Green","F",72,"Mother","Widowed","Living on own means","Bridlington, Yorkshire",
   "mother to the Green partners; the record now holds two Annie Greens in this house"),
  ("Ellen","Wilson","F",24,"Teacher","Single","Teacher, school","Peterborough, Northamptonshire",None),
  ("Ethel","Wilson","F",19,"Teacher","Single","Teacher, school","Peterborough, Northamptonshire",None),
  ("Muriel","Shaw","F",21,"Teacher","Single","Teacher, school","India",None),
  ("Elise","Saegesser","F",24,"Teacher","Single","Teacher, school","Switzerland","returned as a Swiss subject"),
  ("Constance","Wilmott","F",17,"Boarder","Single","Scholar, boarder","Essex",None),
  ("May","Chambers","F",16,"Boarder","Single","Scholar, boarder","Leicestershire",None),
  ("Janie","Denton","F",16,"Boarder","Single","Scholar, boarder","Manchester",None),
  ("Florence","Berridge","F",16,"Boarder","Single","Scholar, boarder","Lincolnshire",None),
  ("Norah","Maxwell","F",16,"Boarder","Single","Scholar, boarder","Yorkshire",None),
  ("Julia","Hallett","F",15,"Boarder","Single","Scholar, boarder","Finchley, London",None),
  ("Zilla","Marshall","F",15,"Boarder","Single","Scholar, boarder","Long Eaton, Derbyshire",None),
  ("Gladys","Hooton","F",15,"Boarder","Single","Scholar, boarder","Long Eaton, Derbyshire",None),
  ("Maud","Hallett","F",14,"Boarder","Single","Scholar, boarder","Finchley, London",None),
  ("Alice","Haggas","F",14,"Boarder","Single","Scholar, boarder","Keighley, Yorkshire",None),
  ("Muriel","Willmott","F",12,"Boarder","Single","Scholar, boarder","Ilford, Essex",None),
  ("Clare","Morgan","F",12,"Boarder","Single","Scholar, boarder","Long Eaton, Derbyshire",None),
  ("Edith","Haggas","F",12,"Boarder","Single","Scholar, boarder","Keighley, Yorkshire",None),
  ("Mary","Forman","F",28,"Servant","Single","Cook, domestic","Leicestershire",None),
  ("Eliza","Webster","F",24,"Servant","Single","Housemaid, domestic","Nottinghamshire",None),
  ("Alice","Clark","F",22,"Servant","Single","Housemaid, domestic","Staffordshire",None),
  ("Annie","Smith","F",16,"Servant","Single","Kitchen maid, domestic","Leicestershire",None),
 ]),
 (328, 16, "32 The Ropewalk", [
  ("John W","Jacoby","M",52,"Head","Single","Lace manufacturer, employer","Nottingham",None),
  ("Mary","Hart","F",66,"Servant","Single","Housekeeper, domestic","Bingham, Nottinghamshire",None),
  ("Annie M","Pawn","F",38,"Servant","Single","Cook, domestic","Wisbech St Mary's, Cambridgeshire","the forename is not clear and may be Minnie or Nina"),
  ("Rebecca","Cole","F",33,"Servant","Single","Parlourmaid, domestic","Paston near Peterborough, Northamptonshire",None),
  ("Ethel","Savage","F",19,"Servant","Single","Kitchen maid, domestic","East Leake near Loughborough, Nottinghamshire",None),
 ]),
 (330, 17, "34 The Ropewalk", [
  ("Herbert G","Ashwell","M",43,"Head","Married","Surgeon, own account, at home","Nottingham","NO WIFE IS ENTERED although he is returned as married"),
  ("Elizabeth","Vasey","F",25,"Servant","Single","Parlourmaid, domestic","Melton Mowbray, Leicestershire","the surname may be Kasey"),
  ("Charlotte","Hardy","F",40,"Servant","Single","Cook, domestic","Mumby Chapel, Lincolnshire",None),
  ("Emma","Smith","F",17,"Servant","Single","Housemaid, domestic","Weston, Lincolnshire",None),
 ]),
 (331, 18, "36 The Ropewalk", [
  ("Arthur H","Dobson","M",42,"Head","Married","Lace dyer and dresser, employer","Nottingham",
   "the record already holds William Ebenezer Dobson and Charles Frederick Dobson, lace dressers of "
   "Nottingham; whether he is of that family has not been established"),
  ("Jannette","Dobson","F",33,"Wife","Married",None,"Nottingham",None),
  ("Catherine","Millband","F",20,"Servant","Single","Cook, domestic","Melton, Leicestershire",None),
  ("Lily","Graney","F",18,"Servant","Single","Housemaid, domestic","Codnor Park, Derbyshire",None),
  ("Nora M","Dobson","F",11,"Daughter","Single",None,"Nottingham",None),
 ]),
 (332, 19, "38 The Ropewalk", [
  ("Frederick Dore","Nordle","M",44,"Head","Married","Starch manufacturer, employer","Norton Fitzwarren, Somerset",
   "the surname is hard to read and may be Mordle or Nordle; Dore is written in above the line and "
   "may be part of a double-barrelled name"),
  ("M Dore","Nordle","F",43,"Wife","Married",None,"Nottingham",None),
  ("Freda Dore","Nordle","F",12,"Daughter","Single",None,"Bulwell, Nottinghamshire",None),
  ("Lionel Dore","Nordle","M",9,"Son","Single",None,"Bulwell, Nottinghamshire",None),
  ("Mabel","Bradbury","F",19,"Servant","Single","Cook, domestic","East Kirkby, Nottinghamshire",None),
  ("Annie","Randall","F",21,"Servant","Single","Housemaid, domestic","Charlton Horethorne, Somerset",None),
 ]),
 (333, 20, "40 The Ropewalk", [
  ("Margaret","Shaw","F",28,"Head","Single","Apartment keeper, employer, at home","Nottingham",None),
  ("Alice","Shaw","F",27,"Sister","Single","Professor of music, own account","Nottingham",None),
  ("Stanley J","Pickard","M",30,"Boarder","Single","Lace maker's agent","Gloucester",None),
  ("Rudolph","Borup","M",26,"Boarder","Single","Warehouseman","Hamburg","returned as a German subject"),
  ("William","Moss","M",25,"Boarder","Single","Solicitor, employer","Leeds",None),
  ("Harriett","Shepherd","F",18,"Servant","Single","Cook, domestic","Breadsall, Derbyshire",None),
  ("Sarah","Beeby","F",18,"Servant","Single","Housemaid, domestic","Castle Donington, Leicestershire",None),
 ]),
 (336, 21, "48 The Ropewalk", [
  ("Lewis W","Marshall","M",52,"Head","Married","Doctor of medicine, own account, at home","Reading, Berkshire",None),
  ("Frances","Marshall","F",45,"Wife","Married",None,"Sutton Bonington, Nottinghamshire",None),
  ("Frances","Marshall","F",18,"Daughter","Single",None,"Nottingham","mother and daughter share a forename"),
  ("Pamelia","Upton","F",25,"Servant","Single","Parlourmaid, domestic","Pointon, Lincolnshire","the forename may be Damelia"),
  ("Rachel","Grice","F",21,"Servant","Single","Housemaid, domestic","Hemmingham, Norfolk",None),
  ("Gertrude","Reavill","F",15,"Servant","Single","Kitchen maid, domestic","Ollerton, Nottinghamshire",None),
  ("Harry","Braine","M",19,"Servant","Single","Groom, domestic","Wymeswold, Leicestershire",None),
  ("Stella","Daws","F",26,"Servant","Single","Cook, domestic","Corby, Lincolnshire",None),
 ]),
 (None, 22, "50 The Ropewalk", [
  ("Martin","Preston","M",45,"Head","Married","Solicitor, licensed; employer, at home","Nottingham",
   "50 THE ROPEWALK IS NOT IN THE PROPERTY LIST"),
  ("Arundel","Preston","F",39,"Wife","Married",None,"Nottingham",None),
  ("Richard","Preston","M",12,"Son",None,None,"Nottingham",None),
  ("Overton","Preston","M",6,"Son",None,None,"Nottingham",None),
  ("Catherine","Betts","F",25,"Servant","Single","Cook, domestic","Balderton, Nottinghamshire","the surname may be Boots or Beets"),
  ("Betsey","Read","F",25,"Servant","Single","Housemaid, domestic","Woolsthorpe, Lincolnshire",None),
 ]),
 (337, 23, "52 The Ropewalk", [
  ("Jane","Chatwin","F",70,"Head","Widowed","Living on own means","Breaston Lodge, Leicestershire",
   "THE RECORD ALREADY HOLDS HER: the 1881 census has Jane Chatwin, 50, an annuitant, at Standard "
   "Hill with her son Herbert F Chatwin. Fifty in 1881 is seventy in 1901. Her son is at 52 The "
   "Ropewalk in the 1939 Register, a solicitor of 68 - the same house, thirty-eight years later"),
  ("Catherine","Hanson","F",37,"Servant","Single","Cook, domestic","Pye Bridge, Derbyshire",None),
  ("Agnes","Lloyd","F",20,"Servant","Single","Housemaid, domestic","Riddings, Derbyshire",None),
 ]),
 (338, 24, "54 The Ropewalk", [
  ("James P","Bailey","M",84,"Head","Widowed","Barrister at law","Nottingham",None),
  ("Mary","Pyatt","F",60,"Niece","Married",None,"Harrow, Middlesex",None),
  ("Mary","Pyatt","F",29,"Great-niece","Single",None,"Arlecdon, Cumberland","aunt and great-niece share a forename"),
  ("Mary","Shimmin","F",24,"Servant","Single","Cook, domestic","Nottingham",None),
 ]),
 (339, 25, "56 The Ropewalk", [
  ("Thomas","Hardstaff","M",61,"Head","Married","Basket manufacturer, employer, at home","Linby, Nottinghamshire","the surname may be Wardstaff"),
  ("Louisa","Hardstaff","F",58,"Wife","Married",None,"East Bridgford, Nottinghamshire",None),
  ("Arthur","Hardstaff","M",44,"Brother","Single","Assistant, basket manufacture","Linby, Nottinghamshire",None),
  ("Mary","Newberry","F",22,"Servant","Single","Cook, domestic","Hucknall Torkard, Nottinghamshire",None),
  ("Sarah A","Swanwick","F",21,"Servant","Single","Housemaid, domestic","Shelford, Nottinghamshire",None),
 ]),
 (None, 26, "58 The Ropewalk", [
  ("Henry C","Thornton","M",58,"Head","Married","Banker, employer","Wendover, Buckinghamshire",
   "58 THE ROPEWALK IS NOT IN THE PROPERTY LIST"),
  ("Katherine C","Thornton","F",58,"Wife","Married",None,"Paddington, London",None),
  ("Claude C","Thornton","M",22,"Son","Single",None,"Nottingham",None),
  ("Sarah A","Sturges","F",45,"Servant","Single","Maid, domestic","Northampton",None),
  ("Edith","Smallwood","F",31,"Servant","Single","Parlourmaid, domestic","Killamarsh, Derbyshire",None),
  ("Mary","Chapman","F",22,"Servant","Single","Housemaid, domestic","Kirkby in Ashfield, Nottinghamshire",None),
  ("Emily","Selby","F",16,"Servant","Single","Kitchen maid, domestic","Beeston, Nottinghamshire",None),
 ]),
 (None, 27, "60 The Ropewalk", [
  ("Robert","Hogarth","M",32,"Head","Married","Surgeon, own account, at home","Scotland",
   "60 THE ROPEWALK IS NOT IN THE PROPERTY LIST. The record holds a Robert S Hogarth, surgeon, at "
   "48 The Ropewalk in the 1939 Register; whether that is this man at 70 has not been established"),
  ("Mabel","Hogarth","F",28,"Wife","Married",None,"Nottingham",None),
  ("George","Lattemore","M",15,"Servant","Single","Page boy","St Albans, Hertfordshire",None),
  ("Emily","Norman","F",20,"Servant","Single","Cook, domestic","Fishtoft, Lincolnshire",None),
  ("Elizabeth","Sims","F",39,"Servant","Single","Nurse, domestic","Derby",None),
  ("John","Hogarth","M",1,"Son","Single",None,"Nottingham",None),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out, n = [], 0
    for prop, sched, addr, people in H:
        print(f"--- schedule {sched}, {addr}" + ("" if prop else "   [NO PROPERTY - filed unresolved]"))
        for fn, ln, sex, age, rel, cond, occ, bp, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1901 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)
                              AND ce.age_at_census=%s""", (sched, fn, ln, age))
            if cur.fetchone():
                continue
            src = SRC.format(addr=addr, sched=sched) + (('; ' + note) if note else '')
            n += 1
            if not APPLY: continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_place)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, 1901-age, bp))
            pid = cur.fetchone()[0]
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, relationship, occupation_at_census, census_household_num,
                            marital_status, birth_place, source)
                           VALUES (%s,%s,1901,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, rel, occ, sched, cond, bp, src))
            rec = {"first_name": fn, "last_name": ln, "sex": sex, "born_year": 1901-age, "id": pid,
                   "born_place": bp,
                   "census": [{"census_year": 1901, "age_at_census": age, "relationship": rel,
                               "occupation_at_census": occ, "census_household_num": sched,
                               "marital_status": cond, "birth_place": bp, "source": src}]}
            rec["census"][0]["address" if prop else "unresolved_address"] = addr
            if prop: rec["census"][0]["property_id"] = prop
            out.append(rec)
        print(f"      {len(people)} people")
    print(f"\n  {n} rows to write")
    if APPLY:
        # 12 The Ropewalk is returned uninhabited
        cur.execute("""INSERT INTO census_unoccupied (property_id, census_year, notes)
                       VALUES (318,1901,'12 The Ropewalk, returned UNINHABITED on the 1901 census - '
                         'the column for houses not in occupation is marked, and a line reading '
                         '"Lace Manufacturer, Employer" is written in and struck through, so the '
                         'enumerator began to record a household here and then found the house empty. '
                         'Read from the page by A. Hagues.')
                       ON CONFLICT (property_id, census_year) DO UPDATE SET notes=EXCLUDED.notes""")
        json.dump({"note": "**The Ropewalk, 1901, schedules 7 to 27.** 50, 58 and 60 The Ropewalk "
                           "are not in the property list and are filed unresolved. 12 is returned "
                           "uninhabited. 30 is a girls' boarding school run by three partners.",
                   "source": "1901 census, The Ropewalk, Nottingham - read from the enumerator's pages",
                   "people": out}, open('data/people_1901_ropewalk_part2.json','w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("  committed")
    else:
        print("  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
