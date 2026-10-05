# -*- coding: utf-8 -*-
"""Clare Valley and Park Valley, 1901 - schedules 49 to 72.

Read from the enumerator's pages A. Hagues sent. Brewhouse Yard, which the
pages run through first, is left out on his word - it is outside the record's
ground, as Standard Hill was.

The enumerator comes up from the Brewhouse Yard, takes a lodging over the
stables on Peveril Drive, works through Clare Valley, then goes down Park
Valley - the odd numbers from 25 to 1, then the even numbers from 10 to 2.
"""
import os, sys, json, psycopg2
APPLY = '--apply' in sys.argv
SRC = "1901 census, {addr}, schedule {sched} - read from the enumerator's page by A. Hagues"
H = [
 (None, 49, "Peveril Drive, over the stables", [
  ("John","Langsdale","M",44,"Head","Widowed","Coachman","Nottingham","THE ADDRESS IS NOT IN THE PROPERTY LIST: the page reads Peveril Drive, over stables"),
  ("Harry","Langsdale","M",21,"Son","Single","Machine minder","Nottingham",None),
  ("William","Langsdale","M",15,"Son","Single","Page boy","Nottingham",None),
 ]),
 (67, 50, "Clare Valley (no number given)", [
  ("Arthur","Lewis","M",44,"Head","Married","Iron merchant, employer","Nottingham","the page gives no number; filed at the unnumbered Clare Valley property"),
  ("Margaret","Lewis","F",37,"Wife","Married",None,"Staffordshire",None),
  ("Gwendolen","Lewis","F",14,"Daughter","Single",None,"Nottingham",None),
  ("Kathleen","Lewis","F",12,"Daughter","Single",None,"Nottingham",None),
  ("Stafford","Lewis","M",7,"Son","Single",None,"Nottingham",None),
  ("R","Butterworth","F",31,"Servant","Single","Cook, domestic","Grantham, Lincolnshire","the page gives an initial only"),
  ("Annie","Thacker","F",17,"Servant","Single","Housemaid, domestic","Ashby de la Zouch, Leicestershire",None),
 ]),
 (62, 51, "4 Clare Valley", [
  ("Lawrence","Wilkins","M",39,"Head","Married","Clergyman, Church of England","Richmond, Yorkshire",None),
  ("E J","Wilkins","F",30,"Wife","Married",None,"Nottingham","the page gives initials only"),
  ("L A","Wilkins","M",6,"Son","Single",None,"Nottingham","the page gives initials only"),
  ("Eleanor","Wilkins","F",5,"Daughter","Single",None,"Nottingham",None),
  ("Jessie","Wilkins","F",4,"Daughter","Single",None,"Nottingham",None),
  ("Minnie","Lee","F",25,"Servant","Single","Nurse, domestic","Sudbury, Staffordshire",None),
  ("Ida","Scott","F",20,"Servant","Single","Cook, domestic","Mansfield, Nottinghamshire",None),
  ("Ruth","Wallam","F",14,"Servant","Single","Housemaid, domestic","Hoveringham, Nottinghamshire",None),
 ]),
 (None, 52, "The Lodge, Clare Valley", [
  ("George","Hill","M",53,"Head","Married","Baptist minister","Worcestershire","THE LODGE, CLARE VALLEY IS NOT IN THE PROPERTY LIST"),
  ("Mary J","Hill","F",55,"Wife","Married",None,"Leicestershire",None),
  ("Ethel","Hill","F",27,"Daughter","Single",None,"Oxford",None),
  ("Eveline","Hill","F",25,"Daughter","Single",None,"Derby",None),
  ("Helen","Hill","F",23,"Daughter","Single",None,"Leeds, Yorkshire",None),
  ("Clara","Hill","F",22,"Daughter","Single",None,"Leeds, Yorkshire",None),
  ("Sydney","Hill","M",20,"Son","Single","Articled clerk","Leeds, Yorkshire",None),
  ("Charlotte","Johnson","F",24,"Servant","Single","Servant, domestic","Claypole, Lincolnshire",None),
 ]),
 (None, 53, "The Pines, Clare Valley", [
  ("George","Ranson","M",39,"Head","Married","Grocer, employer","Nottingham","THE PINES, CLARE VALLEY IS NOT IN THE PROPERTY LIST; the house name is not clear and may be The Firs"),
  ("Emily","Ranson","F",42,"Wife","Married",None,"Nottingham",None),
  ("George E","Ranson","M",12,"Son","Single",None,"Nottingham",None),
  ("Elizabeth","Lichfield","F",23,"Servant","Single","General servant, domestic","Derbyshire",None),
 ]),
 (None, 54, "Clare Valley (no number given)", [
  ("Bernard","Wright","M",24,"Head","Married","Solicitor","Nottingham",
   "the record already holds several Bernard Wrights; A. Hagues has warned that three separate men "
   "of the name appear in 1939 alone, so no connection is made here"),
  ("Florence","Wright","F",25,"Wife","Married",None,"Nottingham",None),
  ("Edith","Saunders","F",37,"Not stated","Single","Private nurse, own account","Stanley, Liverpool",None),
  ("Lettie","Pearson","F",21,"Servant","Single","Cook, domestic","Derbyshire",None),
 ]),
 (273, 55, "25 Park Valley", [
  ("John","Langham","M",60,"Head","Married","Iron merchant, employer","Leicestershire",None),
  ("Martha","Langham","F",58,"Wife","Married",None,"Nottingham",None),
  ("Thomas","Langham","M",21,"Son","Single","Farmer, employer","Nottingham",None),
  ("Ruth","Snell","F",21,"Visitor","Single",None,"Staffordshire",None),
  ("Clara","Dick","F",29,"Servant","Single","Cook, domestic","Lincolnshire",None),
  ("Elizabeth","Fletcher","F",16,"Servant","Single","Maid, domestic","Gotham, Nottinghamshire",None),
 ]),
 (272, 56, "23 Park Valley", [
  ("Harriett","Hackett","F",70,"Head","Single","Living on own means","Nottingham",None),
  ("Elizabeth","Bennett","F",42,"Servant","Single","Cook, domestic","Nuttall, Nottinghamshire",None),
  ("Mag","Millwood","F",18,"Servant","Single","Housemaid, domestic","Riddings, Derbyshire","the forename is given as Mag and is probably Margaret"),
 ]),
 (271, 57, "21 Park Valley", [
  ("Elizabeth","Verner","F",42,"Servant","Single","Housemaid, domestic","Oakham, Rutland",
   "THE HOUSE HOLDS TWO SERVANTS AND NOBODY ELSE - no employer is entered"),
  ("Alice","Downes","F",20,"Servant","Single","Cook, domestic","Chesterfield, Derbyshire",None),
 ]),
 (270, 58, "19 Park Valley", [
  ("Edwin","Bagshaw","M",37,"Head","Married","Living on own means","Nottingham",None),
  ("Elizabeth","Bagshaw","F",41,"Wife","Married",None,"Nottingham",None),
  ("Edwin","Bagshaw","M",5,"Son","Single",None,"Nottingham","father and son share a forename"),
  ("Irene","Bagshaw","F",5,"Daughter","Single",None,"Nottingham","twin to Edwin, by the ages"),
  ("Edna","Bagshaw","F",0,"Daughter","Single",None,"Nottingham","the page gives her age as five months"),
  ("Maryian","Bagshaw","F",63,"Mother","Widowed",None,"Nottingham","the forename may be Marian or Mary Ann"),
  ("Sarah","Smith","F",38,"Servant","Single","Cook, domestic","Lincolnshire",None),
  ("Rose","Aster","F",19,"Servant","Single","Housemaid, domestic","Ollerton, Nottinghamshire",None),
 ]),
 (269, 59, "17 Park Valley", [
  ("Grace","Stedman","F",19,"Servant","Single","Nurse, domestic","Ollerton, Nottinghamshire",None),
  ("William","Ransom","M",77,"Head","Widowed","Physician, at home","Cromer, Norfolk",None),
  ("Mary","Bramwell","F",53,"Niece","Single",None,"North Shields",None),
  ("Mary","Cross","F",32,"Servant","Single","Cook, domestic","Everdon, Northamptonshire",None),
  ("Emma","Parsons","F",30,"Servant","Single","Housemaid, domestic","Somerset",None),
  ("William","Bramwell","M",30,"Visitor","Single",None,"North Shields",None),
 ]),
 (268, 60, "15 Park Valley", [
  ("J T","McCraith","M",52,"Head","Single","Yarn agent, employer","Leicester",
   "THE RECORD ALREADY HOLDS HIM as Sir John Tom McCraith, born Leicester 1847, died 1919 - marked "
   "notable this week. The ages differ by two years; no binding is made here without A. Hagues' word"),
  ("Emma","Marriott","F",40,"Servant","Single","Housekeeper, domestic","Lincolnshire",None),
  ("Nelly","Hands","F",24,"Servant","Single","Cook, domestic","Lincolnshire",None),
 ]),
 (396, 61, "13 Park Valley", [
  ("Scot","Hartshorn","M",33,"Head","Married","Lace manufacturer, employer","Nottingham","the forename may be Scott"),
  ("Ida","Hartshorn","F",27,"Wife","Married",None,"Leicester",None),
  ("Sarah","Champney","F",26,"Servant","Single","Cook, domestic","Flintham, Nottinghamshire",None),
  ("Mary A","Green","F",20,"Servant","Single","Housemaid, domestic","Rotherham, Yorkshire",None),
 ]),
 (267, 62, "11 Park Valley", [
  ("Sarah","Dawson","F",81,"Head","Widowed","Retired from work","Nottingham",None),
  ("Arthur","Dawson","M",24,"Grandson","Single","Auctioneer's pupil","Nottingham",None),
  ("Percy","Dawson","M",20,"Grandson","Single","Chemist's apprentice","Nottingham",None),
  ("Caroline","Wheeler","F",48,"Servant","Single","Companion, domestic","Birmingham",None),
  ("Elizabeth","Allwood","F",33,"Servant","Single","Housemaid, domestic","Newton, Nottinghamshire",None),
 ]),
 (265, 63, "9 Park Valley", [
  ("Charles","Cullen","M",89,"Head","Single","Retired chemist","Nottingham",None),
  ("Annie","Ball","F",37,"Servant","Single","Housekeeper, domestic","Nottingham",None),
  ("Edith","Maynard","F",23,"Servant","Single","Housemaid, domestic","Derby",None),
  ("Christina","Sawyer","F",30,"Servant","Single","Servant, domestic","Ferry Bogg, Yorkshire",None),
 ]),
 (263, 64, "7 Park Valley", [
  ("Alfred","Wilson","M",81,"Head","Widowed","Living on means","Nottingham",None),
  ("Alice","Lynam","F",39,"Daughter","Widowed",None,"Nottinghamshire",None),
  ("Mary","Watson","F",30,"Servant","Single","Cook, domestic","South Witham, Lincolnshire",None),
  ("Annie","Clarke","F",22,"Servant","Single","Housemaid, domestic","Hemingby, Lincolnshire",None),
 ]),
 (261, 65, "5 Park Valley", [
  ("Frederick","Pearson","M",71,"Head","Widowed","Gentleman","Rutland",None),
  ("Mary","Pearson","F",36,"Daughter","Single",None,"Nottingham",None),
  ("Rose","Morris","F",28,"Servant","Single","Cook, domestic","Surrey",None),
  ("Annie","Allen","F",25,"Servant","Single","Housemaid, domestic","Nottinghamshire",None),
 ]),
 (259, 66, "3 Park Valley", [
  ("Walter","Wadsworth","M",60,"Head","Married","Lace merchant, employer","Nottingham",None),
  ("Elizabeth","Wadsworth","F",53,"Wife","Married",None,"Basford, Nottinghamshire",None),
  ("John","Wadsworth","M",25,"Son","Single","Mechanical engineer, employer","Nottingham",None),
  ("Hope","Wadsworth","F",23,"Daughter","Single",None,"Nottingham",None),
  ("Sarah","Barks","F",23,"Servant","Single","Cook, domestic","Lincolnshire",None),
  ("Jane","Gregory","F",30,"Servant","Single","Housemaid, domestic","Nottingham",None),
 ]),
 (258, 67, "1 Park Valley", [
  ("Arundel","Preston","M",63,"Head","Widowed","Gentleman","Wiltshire",
   "the 50 The Ropewalk household at schedule 22 has a wife returned as Arundel Preston; the two "
   "readings cannot both be right and the pages want checking together"),
  ("Bracher","Preston","M",31,"Son","Single","Lace manufacturer, employer","Nottingham","the forename is not clear"),
  ("Ada","Whatnall","F",22,"Servant","Single","Cook, domestic","Loughborough, Leicestershire",None),
  ("S A","Willington","F",21,"Servant","Single","Parlourmaid, domestic","East Bridgford, Nottinghamshire","the page gives initials only"),
  ("Charlie","Tilley","F",19,"Servant","Single","Housemaid, domestic","Nottingham",None),
 ]),
 (266, 68, "10 Park Valley", [
  ("Edmund","Dalton","M",48,"Head","Married","Bank clerk","Lincoln",None),
  ("Mary","Dalton","F",49,"Wife","Married",None,"Lincoln",None),
  ("Julia","Eckington","F",47,"Visitor","Single",None,"Lincoln",None),
  ("Gertrude","Withers","F",22,"Servant","Single","Cook, domestic","Lincoln",None),
 ]),
 (264, 69, "8 Park Valley", [
  ("Edward","Francis","M",55,"Head","Married","School teacher","Flintshire",None),
  ("Annie","Francis","F",40,"Wife","Married",None,"Derbyshire",None),
  ("Arthur","Francis","M",21,"Son","Single","Student","Derbyshire",None),
  ("Constance","Francis","F",19,"Daughter","Single","Student","Nottingham",None),
  ("Minnie","Slaney","F",24,"Servant","Single","General domestic","Sutton in Ashfield, Nottinghamshire",None),
 ]),
 (262, 70, "6 Park Valley", [
  ("Mary","Enfield","F",69,"Head","Single","Living on means","Hampstead, London",
   "the record holds Henry Enfield, the Nottingham landscape painter, born 1849 - whether she is of "
   "that family has not been established"),
  ("Jane","Chaffer","F",58,"Visitor","Single",None,"Burnley, Lancashire",None),
  ("Jane","Jones","F",32,"Servant","Single","Cook, domestic","Ashford, Derbyshire",None),
  ("Annie","Butler","F",24,"Servant","Single","Housemaid, domestic","Nottingham",None),
 ]),
 (260, 71, "4 Park Valley", [
  ("Harry","Myles","M",51,"Head","Married","Solicitor","Faversham, Kent",None),
  ("Frances","Myles","F",37,"Wife","Married",None,"Devon",None),
  ("Kate","Toohey","F",31,"Servant","Single","Cook, domestic","Yorkshire",None),
  ("Susan","Nichols","F",37,"Servant","Single","Housemaid, domestic","Warwickshire",None),
  ("Samuel","Fuller","M",17,"Servant","Single","Parlour servant, domestic","Suffolk",None),
 ]),
 (387, 72, "2 Park Valley", [
  ("Wilson","Armitage","M",45,"Head","Married","Grocer, employer","Nottingham",None),
  ("Mary E","Armitage","F",40,"Wife","Married",None,"Middlesex, London",None),
  ("Stanley W","Armitage","M",7,"Son","Single",None,"Nottingham",None),
  ("Kathleen M","Armitage","F",6,"Daughter","Single",None,"Nottingham",None),
  ("Emma","Twigg","F",25,"Servant","Single","Cook, domestic","Spondon, Derbyshire",None),
  ("Annie","Allwood","F",18,"Servant","Single","Housemaid, domestic","Waddington, Lincolnshire",None),
  ("Edith","Miller","F",17,"Servant","Single","Nurse, domestic","Nottingham",None),
 ]),
]
def main():
    c=psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL']); cur=c.cursor()
    out,n=[],0
    for prop,sched,addr,people in H:
        print(f"--- s{sched} {addr}" + ("" if prop else "   [unresolved]") + f"  ({len(people)})")
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
                           (person_id,property_id,census_year,address,unresolved_address,age_at_census,
                            relationship,occupation_at_census,census_household_num,marital_status,
                            birth_place,source)
                           VALUES (%s,%s,1901,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid,prop,addr if prop else None,None if prop else addr,age,rel,occ,sched,cond,bp,src))
            rec={"first_name":fn,"last_name":ln,"sex":sex,"born_year":1901-age,"id":pid,"born_place":bp,
                 "census":[{"census_year":1901,"age_at_census":age,"relationship":rel,
                            "occupation_at_census":occ,"census_household_num":sched,
                            "marital_status":cond,"birth_place":bp,"source":src}]}
            rec["census"][0]["address" if prop else "unresolved_address"]=addr
            if prop: rec["census"][0]["property_id"]=prop
            out.append(rec)
    print(f"\n  {n} rows")
    if APPLY:
        json.dump({"note":"**Clare Valley and Park Valley, 1901, schedules 49 to 72.** Brewhouse Yard "
                          "is left out on A. Hagues' word. The enumerator works through Clare Valley "
                          "then goes down Park Valley - odd numbers 25 to 1, then even 10 to 2.",
                   "source":"1901 census, Clare Valley and Park Valley, Nottingham - read from the enumerator's pages",
                   "people":out}, open('data/people_1901_clare_and_park_valley.json','w'),indent=1,ensure_ascii=False)
        c.commit(); print("  committed")
if __name__=='__main__': main()
