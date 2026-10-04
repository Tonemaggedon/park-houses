# -*- coding: utf-8 -*-
"""15 and 21 Hope Drive, 1939 - schedules 71, 72 and 75, and the war in lodgings.

**15 Hope Drive holds two households and three Royal Ordnance Factory men.**
Schedule 71 is Ida Limb's lodging house: a progressman and two electrical and
mechanical engineers' representatives, all three returned **ROF**. Schedule 72
is William H Sherwin, company director - and the Sherwins had this house in 1911
and 1921, when William Sherwin was a cricket bat maker and then a sports
manufacturer, so he is of that family though not that man.

**21 Hope Drive is a boarding house of thirteen**, and four of its lodgers are
**piling winchmen** - Birch, Hutchins, Lisney and Martin - men who drive piles.
Four of one trade under one roof in September 1939 is a gang, and a gang of pile
drivers in that month was putting in foundations for something. A ministry clerk
lodges with them.

**Two children settle the brackets, and they settle them opposite ways.** Ruby
Limb is **fourteen**, so at schedule 71 the surname in front is the name borne on
the night. Barbara Rona Tippett (Sherwin) is **eight**, so at schedule 72 it is
the bracket. Audrey M Austin (Simpson) at 21 goes with Barbara: she is 21 and
single in the Simpsons' own house.

  railway run python3 add_hope_drive_71_72_75_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGC, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (358, 71, "15 Hope Drive", [
  (2, "Ida", "Limb", "Kitch, Austin", "F", "1884-05-25", 55, "Housekeeper", "Married",
   "the index gives her as Limb (Kitch) (Austin). Ruby at sub number 3 is fourteen and cannot "
   "carry a married name, which settles this page: the surname in front is the one borne on the "
   "night. Sub number 1 is a line the register keeps closed"),
  (3, "Ruby", "Limb", "Cooper", "F", "1924-10-08", 14, "Office clerk", "Single",
   "FOURTEEN and already a clerk. Being fourteen and single she cannot be a Cooper yet, which "
   "is what fixes the direction of the bracket for this whole schedule"),
  (4, "Leslie A", "Howe", None, "M", "1893-02-04", 46, "Progressman, Royal Ordnance Factory", "Single",
   "the page gives Progressman Rof. A progressman chased work through a factory to keep it to "
   "time, and ROF is the Royal Ordnance Factory - the record already holds eight others on "
   "ordnance work in this round, on Hamilton Drive, Hope Drive, Lenton Avenue and Peveril Drive"),
  (5, "James", "Mahon", None, "M", "1901-03-31", 38,
   "Electrical and mechanical engineer, representative, Royal Ordnance Factory", "Single",
   "the page gives Electrical Meconisedd Engineer C Representative Oac Ia Rof, badly read; the "
   "man at sub number 6 is given in almost the same words"),
  (6, "James", "Booth", None, "M", None, None,
   "Electrical and mechanical engineer, representative, Royal Ordnance Factory", "Married",
   "the index gives him NO BIRTH DATE at all, so the record cannot say his age. His trade is "
   "written in almost the same words as James Mahon's at sub number 5, so the two were sent "
   "here together"),
  (7, "Mona", "Limb", "Shelton, Hayter", "F", "1901-09-23", 38, "Office clerk, cellular", "Single",
   "the index prints her at sub number 3, which Ruby already holds, so her true sub number is "
   "not known and 7 is used here to keep her in the household. Seventeen years older than Ruby "
   "and sharing a surname with her and with Ida"),
 ]),
 (358, 72, "15 Hope Drive", [
  (1, "William H", "Sherwin", None, "M", "1893-05-04", 46, "Company director", "Married",
   "the Sherwins had this house in 1911 and 1921 - William Sherwin, cricket bat maker and then "
   "sports manufacturer, born 1872, with his wife Rose and sons Harold, Stuart and Jack. This "
   "William H is born 1893 and is none of them, but he is plainly of that family and in their "
   "house"),
  (2, "Elizabeth E", "Sherwin", None, "F", "1895-04-11", 44, "Unpaid domestic duties", "Married", None),
  (3, "Barbara Rona", "Sherwin", "Tippett", "F", "1931-07-04", 8, "At school", "Single",
   "the index gives her as Tippett (Sherwin); she is EIGHT, so Sherwin is what she bore on the "
   "night - which turns the bracket the opposite way round from schedule 71 next door, on the "
   "same page of the same book"),
  (4, "Constance L", "Bland", None, "F", "1904-02-24", 35, "Clerk, retail mantle trade", "Single",
   "a mantle is a woman's cloak; the mantle trade was Nottingham's own"),
 ]),
 (361, 75, "21 Hope Drive", [
  (1, "Florence M", "Simpson", None, "F", "1897-08-01", 42, "Boarding house keeper", "Married",
   "she keeps a house of thirteen - the third boarding house this round has turned up, after "
   "19 Pelham Crescent and North Lodge, and like both of those its lodgers are in war work"),
  (2, "William", "Simpson", None, "M", "1891-08-03", 48, "Domestic worker", "Married",
   "six years older than Florence M and sharing her surname, so her husband, working in the "
   "house she keeps"),
  (3, "Audrey M", "Simpson", "Austin", "F", "1918-07-13", 21, "Domestic helper", "Single",
   "the index gives her as Austin (Simpson); 21 and single in the Simpsons' own house, so "
   "Simpson on the night"),
  (4, "George", "Viggers", None, "M", "1875-01-18", 64, "Caretaker, dance hall", "Widowed", None),
  (5, "Stanley", "Martin", None, "M", "1887-12-16", 51, "Clerk, Ministry of Mines", "Married",
   "the page gives Clerk Ministry Of Min; the record already holds a Ministry of Mines man at "
   "1a Hamilton Drive in this round"),
  (6, "Edward", "Birch", None, "M", "1906-09-26", 33, "Piling winchman", "Single",
   "the first of FOUR piling winchmen in this house - men who drove piles, working a winch. "
   "Four of one trade under one roof in September 1939 is a gang, and his birthday fell three "
   "days before the register was taken"),
  (7, "Arthur J", "Hutchins", None, "M", "1909-11-25", 29, "Piling winchman", "Married", None),
  (8, "George T", "Lisney", None, "M", "1889-08-10", 50, "Piling winchman", "Married", None),
  (9, "Charles", "Martin", None, "M", "1901-03-09", 38, "Piling winchman", "Widowed",
   "he shares a surname with Stanley Martin at sub number 5, the ministry clerk, though nothing "
   "says they were kin"),
  (10, "Sydney", "Snipper", None, "M", "1892", 47, "Salesman, photographic", "Married",
   "the page gives his birth as 17 ? 1892, the month unread, so he was 46 or 47 and 47 is used "
   "here. His trade is written Salesman Photgraphic En, the last word cut off"),
  (11, "Edward", "Barrow", None, "M", "1919-06-14", 20, "Electrician", "Single", None),
  (12, "William", "Gray", None, "M", "1908-08-03", 31, "Joiner", "Married", None),
  (13, "Alfred", "Rowe", None, "M", "1914-02-13", 25, "Sign writer", "Married", None),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr} (#{prop})")
        for sub, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                              AND LOWER(p.last_name)=LOWER(%s)""", (sched, '%RMGC%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age if age is not None else '?'} - {occ}")
            if not APPLY:
                continue
            yr = int(bd[:4]) if bd else None
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, yr, bd if bd and len(bd) > 4 else None))
            pid = cur.fetchone()[0]
            names = [x.strip() for x in (later or '').split(',') if x.strip()]
            for i, one in enumerate(names):
                label = ('1939 amendment (married name)' if len(names) < 2 else
                         f"1939 amendment ({'latest' if i == len(names)-1 else 'first'} married name)")
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,%s FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, one, yr, label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census,
                            occupation_at_census, census_household_num, marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, occ, sched, marital, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": yr,
                        "born_date": bd if bd and len(bd) > 4 else None, "id": pid,
                        "census": [{"census_year": 1939, "property_id": prop, "address": addr,
                                    "age_at_census": age, "occupation_at_census": occ,
                                    "census_household_num": sched, "marital_status": marital,
                                    "source": src}]})
    if APPLY:
        json.dump({"note": "**15 and 21 Hope Drive, schedules 71, 72 and 75 of the 1939 Register, "
                           "ED letter code RMGC.** Three Royal Ordnance Factory men lodge at 15 and "
                           "four piling winchmen at 21, which is a boarding house of thirteen.",
                   "source": "1939 Register, ED letter code RMGC, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgc_hope_drive_71_72_75.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
