# -*- coding: utf-8 -*-
"""4 Barrack Lane, 1939 - schedule 20, a BBC conductor and a singer.

**Eric H Warr is on the music staff of the BBC and conducts an orchestra; his
wife Viola G is a singer.** They are the first people in this record's 1939
round in music or broadcasting of any kind - the trade columns hold no other
conductor, singer, musician or BBC anything.

That matters because of what else this round keeps finding. Government
departments were dispersed out of London at the outbreak of war and The Park
took some of them - twelve civil servants in two boarding houses, a Ministry of
Supply timber officer, a Ministry of Mines clerk. **The BBC dispersed too**, and
a conductor on its music staff lodging in Nottingham three weeks after war was
declared is the same shape of fact.

**Alice Louisa Fitzhugh keeps the house at 68.** She is Richard Fitzhugh's
daughter of 3 Clumber Crescent South, returned there as a daughter in 1891, 1901
and 1911 and never married. Bound by number.

**And a Polish name in the household.** Sylvia J, 17, in domestic service, is
given as *Wooley (Woyciehouski)*. Poland was invaded on 1 September 1939,
twenty-eight days before the register was taken.

  railway run python3 add_4_barrack_lane_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGA, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6177J - read from the page "
       "by A. Hagues; sub number {sub}")

PEOPLE = [
 (1, 377, "Alice Louisa", "Fitzhugh", None, "F", "1870-10-23", 68, "Unpaid domestic duties", "Single",
  "the index gives her as Alice L; she is the Alice Louisa Fitzhugh the record holds at 3 "
  "Clumber Crescent South as Richard Fitzhugh's daughter in 1891, 1901 and 1911, aged 21, 31 "
  "and 40, never married. The register's date of 23 October 1870 agrees with the 1911 age "
  "exactly and the other two within a year"),
 (2, None, "Elizabeth A", "Jones", None, "F", "1883-10-29", 55, "Domestic service", "Single", None),
 (3, None, "Sylvia J", "Woyciehouski", "Wooley", "F", "1922-06-09", 17, "Domestic service", "Single",
  "the index gives her as Wooley (Woyciehouski). WOYCIEHOUSKI is a Polish name - Wojciechowski - "
  "and she is seventeen and single, so a birth name rather than a married one; Wooley reads as "
  "the anglicised form she came to be known by. She is entered under the Polish spelling with "
  "Wooley held beside it, so neither is lost. POLAND WAS INVADED ON 1 SEPTEMBER 1939, "
  "twenty-eight days before this register was taken, and the record cannot say whether that "
  "has anything to do with her being here"),
 (4, None, "Eric H", "Warr", None, "M", "1905-05-04", 34,
  "Orchestral conductor, music staff, BBC", "Married",
  "the first person in this record's 1939 round in music or broadcasting of any kind. The BBC "
  "dispersed staff out of London at the outbreak of war, as the government departments did that "
  "this round keeps finding billeted on the estate"),
 (5, None, "Viola G", "Warr", None, "F", "1906-08-24", 33, "Singer", "Married",
  "sixteen months younger than Eric H and sharing his surname, so his wife - and returned with a "
  "profession of her own, which few married women in this round are"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print("--- schedule 20, 4 Barrack Lane (#4)")
    for sub, exist, fn, ln, later, sex, bd, age, occ, marital, note in PEOPLE:
        if exist:
            cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                            AND census_household_num=20 AND person_id=%s
                            AND source ILIKE %s""", (exist, '%RMGA%'))
        else:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=20
                              AND ce.source ILIKE %s AND LOWER(p.first_name)=LOWER(%s)
                              AND LOWER(p.last_name)=LOWER(%s)""", ('%RMGA%', fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=20, addr="4 Barrack Lane", sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}  [{f'bound to #{exist}' if exist else 'new'}]")
        if not APPLY:
            continue
        if exist:
            pid = exist
            cur.execute("""UPDATE people SET born_date=COALESCE(born_date,%s),
                             born_year=COALESCE(born_year,%s) WHERE id=%s""", (bd, int(bd[:4]), pid))
        else:
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
        if later:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,%s,'1939 Register, the other form of her surname'
                             FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a
                             WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                               AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                        (pid, fn, later, int(bd[:4]), fn, later))
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,4,1939,'4 Barrack Lane',%s,%s,20,%s,%s)""",
                    (pid, age, occ, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                    "born_date": bd, "id": pid,
                    "census": [{"census_year": 1939, "property_id": 4, "address": "4 Barrack Lane",
                                "age_at_census": age, "occupation_at_census": occ,
                                "census_household_num": 20, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        json.dump({"note": "**4 Barrack Lane, schedule 20 of the 1939 Register, ED letter code "
                           "RMGA, RG101/6177J.** Eric H Warr, orchestral conductor on the BBC's "
                           "music staff, and his wife Viola G, a singer - the first people in this "
                           "round in music or broadcasting. Alice Louisa Fitzhugh keeps the house "
                           "at 68 and is bound by number.",
                   "source": "1939 Register, ED letter code RMGA, The National Archives RG101/6177J",
                   "people": out}, open('data/people_1939_rmga_4_barrack_lane.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
