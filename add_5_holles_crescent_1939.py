# -*- coding: utf-8 -*-
"""5 Holles Crescent, 1939 - schedule 259, and the answer to who Emmeline was.

A. Hagues read the page and said Hockmer is the maiden name. The entry prints
her as **Doris (E D L) Sampson (Hockmer)** - so on the night of 29 September
1939 she was **Doris Hockmer**, single, a domestic servant of 40, and Sampson
is the married name written in afterwards.

**E D L are Emmeline D. L. Sampson's initials.** The probate notice of 20
October 1950 gives Emmeline D. L. Sampson a widow's provision in the estate of
**Tom Percy Sampson** - an annuity, the use of his effects for life, and the
life interest standing between his collection and Nottingham Castle Museum.
The record could not place her. She is the woman in service at 5 Holles
Crescent, and 5 Holles Crescent is the house Tom Percy Sampson died in.

So he left 4 Clinton Terrace some time after 1939, married her, and died there
in April 1950. His first wife Lilian Lucy, who is with him in 1921 and 1939,
must have died between.

**The household has no head.** Only two women are entered, both single and both
in work - which on this street means the head's own record is still closed.

  railway run python3 add_5_holles_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
RMGB = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
        "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
        "by A. Hagues; sub number {sub}")
PROP, SCHED, ADDR = 129, 259, "5 Holles Crescent"
PEOPLE = [
 (1, "Doris", "Hockmer", "F", "1898-10-16", 40, "Domestic servant", "Single",
  [("Doris", "Sampson"), ("Emmeline D L", "Sampson")],
  "entered as Doris (E D L) Sampson (Hockmer). HOCKMER IS THE MAIDEN NAME, on A. Hagues' reading "
  "of the page, so Hockmer is the name she bore on the night and Sampson is written in later. "
  "The initials E D L are those of EMMELINE D. L. SAMPSON, who holds a widow's provision in the "
  "will of Tom Percy Sampson, lace manufacturer, reported in the Nottingham Evening News of 20 "
  "October 1950 - and 5 Holles Crescent is the house he died in, in April 1950. She is in service "
  "here in 1939 and is his second wife by 1950"),
 (2, "Marjorie", "Nixon", "F", "1918-01-14", 21, "Hairdresser's receptionist", "Single",
  [("Marjorie", "Swanson")],
  "entered as Marjorie Swanson (Nixon), so Nixon on the night and Swanson written in later"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    print(f"--- schedule {SCHED}, {ADDR} (#{PROP})")
    for sub, fn, ln, sex, bd, age, occ, marital, laters, note in PEOPLE:
        cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                        WHERE ce.census_year=1939 AND ce.census_household_num=%s
                          AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)
                          AND ce.age_at_census=%s""", (SCHED, fn, ln, age))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {ln}: already in the record"); continue
        src = RMGB.format(sched=SCHED, addr=ADDR, sub=sub) + '; ' + note
        print(f"  sub {sub} {fn} {ln}, {age} - {occ}  [later {', '.join(l[1] for l in laters)}]")
        if not APPLY: continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
        pid = cur.fetchone()[0]
        for lfn, lln in laters:
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,%s,'1939 amendment (married name)'
                             FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a
                             WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                               AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                        (pid, lfn, lln, int(bd[:4]), lfn, lln))
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
        json.dump({"note": "**5 Holles Crescent, schedule 259 of the 1939 Register, ED letter code "
                           "RMGB.** Two women in service, no head entered. Doris Hockmer is "
                           "Emmeline D. L. Sampson, second wife of the lace manufacturer Tom Percy "
                           "Sampson, who died in this house in April 1950.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_5_holles_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
