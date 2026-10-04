# -*- coding: utf-8 -*-
"""Lincoln Villa and North Lodge, 1939 - schedules 202 and 203.

**Lincoln Villa, 11 Western Terrace**, holds three unmarried Brights and five
domestics. Joseph Bright, solicitor, kept the house from 1901 until his death,
and in 1939 three of his children are still in it: Horace Dickinson, solicitor
like his father, and his sisters Josephine Agnes and Beatrice Evelyn, both of
private means, aged 58, 57 and 55 and none of them married. All three are bound
by number.

**North Lodge** is a boarding house of thirteen, and **seven of them are
government staff**: a tax inspector, a third class officer of the Ministry of
Labour, a senior staff officer of Inland Revenue, two civil servants, a student
at a Home Office laboratory and a private secretary. The register was taken on
29 September 1939, three weeks after war was declared, and this is the second
house on the estate to look like a department billeted together.

The record holds no property called North Lodge, so schedule 203 goes in
unfiled.

  railway run python3 add_lincoln_villa_north_lodge_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (350, 202, "Lincoln Villa, 11 Western Terrace", [
  (1, 575, "Horace Dickinson", "Bright", None, "M", "1881-06-05", 58, "Solicitor", "Single",
   "the index gives him as Horace D; he headed this house in 1921 aged 40 in the same trade, and "
   "was a law articled clerk in it in 1901 under his father Joseph Bright, solicitor"),
  (2, 576, "Josephine Agnes", "Bright", None, "F", "1882-07-22", 57, "Private means", "Single",
   "the index gives her as Josephine A; she was in this house in 1901 and 1911 as Joseph "
   "Bright's daughter"),
  (3, 3849, "Beatrice Evelyn", "Bright", None, "F", "1883-12-25", 55, "Private means", "Single",
   "the index gives her as Beatrice E; she was in this house in 1911 as a daughter and in 1921 "
   "as Horace's sister. Born on Christmas Day"),
  (4, None, "Annie", "Sindall", None, "F", "1886-09-09", 53, "Domestic", "Single", None),
  (5, None, "Charlotte", "Carvell", "Holt", "F", "1894-02-23", 45, "Domestic", "Single",
   "the index gives her as Holt (Carvell), so Carvell is the name the register was written in. "
   "The record holds a Charlotte Carvell who was parlourmaid in THIS HOUSE in 1921 - but aged 37 "
   "there, which makes her born about 1884, ten years before this birth date. The name, the house "
   "and the work all point one way and the age the other, so she is entered as a new person "
   "rather than bound to #1136 on a decade's disagreement"),
  (6, None, "Julia", "Faulconbridge", "Bostock", "F", "1908-12-02", 30, "Domestic", "Single",
   "the index gives her as Bostock (Faulconbridge)"),
  (7, None, "Florence M", "Cook", None, "F", "1919-08-28", 20, "Domestic", "Single", None),
  (8, None, "Ethel A", "Summerjulil", None, "F", "1921-10-31", 17, "Domestic", "Single",
   "the surname is written Summerjulil, which is not a name - the page wants re-reading; "
   "Summerfield is the likeliest thing it stands for"),
 ]),
 (None, 203, "North Lodge", [
  (1, None, "Charlotte E", "Bedford", None, "F", "1877-04-07", 62, "Unpaid domestic duties", "Single", None),
  (2, None, "Ada", "Bedford", None, "F", "1870-05-18", 69, None, "Single",
   "no trade is given for her; seven years older than Charlotte E and sharing her surname, so "
   "most likely her sister"),
  (3, None, "Eric W", "Montgomery", None, "M", "1915-04-09", 24, "Student, Home Office laboratory", "Single", None),
  (4, None, "Walter D P", "Path", None, "M", "1921-04-16", 18, "Student, literature", "Single",
   "the surname is written Path and may be Path, Path or something the page would settle"),
  (5, None, "John B", "Heslin", None, "M", "1908-05-08", 31, "Tax inspector", "Single", None),
  (6, None, "Mary M", "Hall", None, "F", "1911-06-07", 28, "Third class officer, Ministry of Labour", "Single",
   "the page gives 3rd Class Office Minister Labourer, which is a transcription of Ministry of Labour"),
  (7, None, "Scott Nina", "Stewart", None, "M", "1903-11-26", 35, "Private secretary", "Widowed",
   "the forenames are written Scott Nina and the sex Male, which do not sit together; the page "
   "wants checking"),
  (8, None, "Conelian K", "De Farrars", None, "F", "1892-05-12", 47, "Civil servant", "Single",
   "the index gives her as Conelian K (Marjorie Cornelia C) De Farrars, so Conelian is most "
   "likely a reading of Cornelia"),
  (9, None, "David L", "McKenna", None, "M", "1885-07-04", 54, "Civil servant", "Married",
   "his department is written D R N O, which is unexplained"),
  (10, None, "Clara", "Burdett", None, "F", "1874-05-29", 65, "Boarding house proprietor", "Widowed",
   "she keeps the house, which is what makes the other twelve lodgers rather than family"),
  (11, None, "Leonard", "Burdett", None, "M", "1906-05-20", 33, "Chief clerk, insurance", "Single",
   "the index gives him as Leonard (Charles) and his trade as Chief Clerk Surgeon (Insurance), "
   "which wants the page; thirty-two years younger than Clara and sharing her surname, so most "
   "likely her son"),
  (12, None, "Minnie", "Bestwick", "Gilbert", "F", "1909-02-16", 30, "Domestic servant", "Single",
   "the index gives her as Gilbert (Bestwick), so Bestwick is the name the register was written in"),
  (13, None, "Harry R", "Portman", None, "M", "1897-01-22", 42, "Senior staff officer, Inland Revenue", "Married", None),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        for sub, exist, fn, ln, later, sex, bd, age, occ, marital, note in people:
            # by NAME within this book's schedule - a person_id guard misses anyone new,
            # and the other 1939 book numbers its schedules over the same range
            # a bound person is checked by NUMBER, because the index's forename need not
            # match the record's - "Mary E Littlewood" against the record's "Mary" slipped
            # past a name guard and put her row in twice
            if exist:
                cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                                AND census_household_num=%s AND person_id=%s
                                AND source ILIKE %s""", (sched, exist, '%RMGB%'))
            else:
                cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                                WHERE ce.census_year=1939 AND ce.census_household_num=%s
                                  AND ce.source ILIKE %s
                                  AND LOWER(p.first_name)=LOWER(%s)
                                  AND LOWER(p.last_name)=LOWER(%s)""",
                            (sched, '%RMGB%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}  [{f'bound to #{exist}' if exist else 'new'}]")
            if not APPLY:
                continue
            if exist:
                pid = exist
                cur.execute("""UPDATE people SET born_date=COALESCE(born_date,%s),
                                 born_year=COALESCE(born_year,%s) WHERE id=%s""",
                            (bd, int(bd[:4]), pid))
            else:
                cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                            (fn, ln, sex, int(bd[:4]), bd))
                pid = cur.fetchone()[0]
            if later:
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, later, int(bd[:4]), fn, later))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, occupation_at_census, census_household_num,
                            marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, occ, sched, marital, src))
            rec = {"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                   "born_date": bd, "id": pid,
                   "census": [{"census_year": 1939, "age_at_census": age, "address": addr,
                               "occupation_at_census": occ, "census_household_num": sched,
                               "marital_status": marital, "source": src}]}
            if prop:
                rec["census"][0]["property_id"] = prop
            else:
                rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**Lincoln Villa and North Lodge, schedules 202 and 203 of the 1939 "
                           "Register, ED letter code RMGB.** Three unmarried Bright siblings "
                           "still in their father's house at 11 Western Terrace, and a boarding "
                           "house of thirteen on North Lodge of whom seven are government staff. "
                           "North Lodge is not in the property list, so schedule 203 is unfiled.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_lincoln_villa_north_lodge.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
