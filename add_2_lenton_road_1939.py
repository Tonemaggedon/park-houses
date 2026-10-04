# -*- coding: utf-8 -*-
"""2 Lenton Road, 1939 - schedule 265, Agnes Lymbery widowed in her own house.

The record already holds her. The 1921 census has **Agnes Lymbery, born 1850,
at 2 Lenton Road** with her husband **Richard Henry Lymbery**, born 1846. The
1939 Register has her at the same house, the same birth year, and widowed - so
Richard Henry died between the two rounds, and this is a new row on a person
the record held, not a new person.

The index prints her as **Lymbury**, which is a misreading; the 1921 census and
the rest of the family give **Lymbery**.

**Robert S Lymbery**, born 1885, is at Flixton, 15 Cavendish Crescent North in
this same round. A son born to Richard Henry and Agnes would be about that age,
and the surname is uncommon - but nothing in the record says so yet, and it is
written up as a question rather than a fact.

**The book is RMGB** on the walk: 263 is 3 Park Drive and 264 is 1 Park Drive,
and Park Drive runs into Lenton Road. No other book uses 265.

  railway run python3 add_2_lenton_road_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED, ADDR = 175, 265, "2 Lenton Road"
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")
PEOPLE = [
 (1, 1450, "Agnes", "Lymbery", "F", "1850-04-04", 89, "Retired", "Widowed",
  "the index prints Lymbury, a misreading. The 1921 census has Agnes Lymbery born 1850 in this "
  "same house with her husband Richard Henry, born 1846, so he died between the two rounds"),
 (2, None, "Susan M", "Hurt", "F", "1880-02-09", 59, "Housekeeper", "Single", None),
 (3, None, "Marjorie S", "Allfree", "F", "1920-05-26", 19, "Domestic servant", "Single", None),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print(f"--- schedule {SCHED}, {ADDR} (#{PROP})")
    for row in PEOPLE:
        sub, pid, fn, ln, sex, bd, age, occ, marital = row[:9]
        note = row[9] if len(row) > 9 else None
        if pid:
            cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                            AND census_household_num=%s AND person_id=%s""", (SCHED, pid))
        else:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                        (SCHED, fn, ln))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = SRC.format(sched=SCHED, addr=ADDR, sub=sub) + (('; ' + note) if note else '')
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}" + (f"  [#{pid}, already in the record]" if pid else ""))
        if not APPLY: continue
        if pid:
            cur.execute("UPDATE people SET born_date=COALESCE(born_date,%s) WHERE id=%s", (bd, pid))
        else:
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s)""",
                    (pid, PROP, ADDR, age, occ, SCHED, marital, src))
        out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                    "born_date": bd, "id": pid,
                    "census": [{"census_year": 1939, "age_at_census": age, "address": ADDR,
                                "property_id": PROP, "occupation_at_census": occ,
                                "census_household_num": SCHED, "marital_status": marital,
                                "source": src}]})
    if APPLY:
        json.dump({"note": "**2 Lenton Road, schedule 265 of the 1939 Register, ED letter code "
                           "RMGB.** Agnes Lymbery, 89 and widowed, in the house the 1921 census "
                           "found her in with her husband Richard Henry, with a housekeeper and a "
                           "domestic servant.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_2_lenton_road.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
