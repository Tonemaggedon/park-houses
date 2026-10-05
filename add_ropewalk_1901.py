# -*- coding: utf-8 -*-
"""The Ropewalk, 1901 - schedules 1 to 6, read from the enumerator's page.

**The Ropewalk had no 1901 round at all.** The record held 2 to 14 for 1861,
1871, 1881 and 1939 and nothing between. This fills the gap for six houses.

**Four people are already in the record and are bound by number, not made again:**

  Hannah Brooke, at 10 The Ropewalk in 1881 as Benjamin Brooke's wife, aged 56
  and born at Sandiacre - a widow in the same house twenty years later. Her age
  on the page is hard to read; 1881 settles it at 76.

  Emilie Feilman, Gertrude Feilman and Max Loewenstein, all three at 29
  Newcastle Drive in 1911 - Emilie as head and widow at 56, Gertrude as
  Principal of a school at 35, Max as her brother at 58. In 1901 Emilie is 46
  and a wife, Gertrude 25 and a schoolmistress, Max 48 and her brother-in-law.
  The 1911 round spells the family Feilmann with two n's; this page gives one.

**6 The Ropewalk holds two servants and nobody else** - a cook of 24 and a
housemaid of 25, with no employer. The same shape as the seven houses of 1921.

  railway run python3 add_ropewalk_1901.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1901 census, {addr}, schedule {sched} - read from the enumerator's page by A. Hagues; "
       "person {no} on the page")
# (prop, schedule, address, [(person no, bound id, forename, surname, sex, age, relationship,
#                             condition, occupation, employment, birthplace, note)])
HOUSES = [
 (313, 1, "2 The Ropewalk", [
  (1, None, "Walter H", "des Forges", "M", 52, "Head", "Married", "Colour manufacturer's agent", "Worker", "South Cave, East Yorkshire", None),
  (2, None, "Louise A", "des Forges", "F", 49, "Wife", "Married", None, None, "Kingston upon Hull", "the age is written over another figure"),
  (3, None, "Charles L", "des Forges", "M", 21, "Son", "Single", "Solicitor's articled clerk", "Worker", "Kingston upon Hull", None),
  (4, None, "Clara", "Howe", "F", 26, "Servant", "Single", "Cook, domestic", "Worker", "Livermere, Suffolk", None),
  (5, None, "Mary", "Parkin", "F", 18, "Servant", "Single", "Housemaid, domestic", "Worker", "Waingroves, Derbyshire", None),
  (6, None, "Eliza A", "Lee", "F", 36, "Sister-in-law", "Single", None, "Worker", "Kingston upon Hull", None),
  (7, None, "Mary E", "Lee", "F", 40, "Sister-in-law", "Single", None, "Worker", "Kingston upon Hull",
   "the age is written over another figure, and the infirmity column carries a mark that cannot be read with confidence"),
 ]),
 (314, 2, "4 The Ropewalk", [
  (8, None, "William", "Tibbles", "M", 41, "Head", "Married", "Physician and surgeon", "Own account, at home", "Leicester", None),
  (9, None, "Lavinia", "Tibbles", "F", 14, "Daughter", "Single", "Scholar", None, "Nottingham", None),
  (10, None, "Maria", "Tibbles", "F", 37, "Sister", "Single", "Teacher of music", "Own account, at home", "Leicester",
   "the occupation is written over something struck through"),
  (11, None, "Emily", "Lowe", "F", 20, "Servant", "Single", "Cook, domestic", "Worker", "Burton Joyce, Nottinghamshire", None),
  (12, None, "Ada", "Moore", "F", 15, "Servant", "Single", "Housemaid, domestic", "Worker", "Bleasby, Nottinghamshire", None),
 ]),
 (315, 3, "6 The Ropewalk", [
  (13, None, "Elizabeth", "Wallace", "F", 24, "Servant", "Single", "Cook, domestic", "Worker", "Woolsthorpe, Lincolnshire",
   "THE HOUSE HOLDS TWO SERVANTS AND NOBODY ELSE on this page - no employer is entered. The household was away"),
  (14, None, "Emily A", "Carlin", "F", 25, "Servant", "Single", "Housemaid, domestic", "Worker", "Kimberley, Nottinghamshire", None),
 ]),
 (316, 4, "8 The Ropewalk", [
  (15, None, "William", "Hutton", "M", 42, "Head", "Married", "Solicitor", "Own account", "Northampton", None),
  (16, None, "Lucy", "Hutton", "F", 39, "Wife", "Married", None, None, "Finsbury Square, London", None),
  (17, None, "Elsie", "Hutton", "F", 12, "Daughter", "Single", None, None, "Nottingham", None),
  (18, None, "Thomas", "Hutton", "M", 11, "Son", "Single", None, None, "Nottingham", None),
  (19, None, "George", "Hutton", "M", 9, "Son", "Single", None, None, "Nottingham", None),
  (20, None, "Alice", "Ratcliffe", "F", 25, "Servant", "Single", "Housemaid, domestic", "Worker", "India", None),
  (21, None, "Emma", "Glazier", "F", 24, "Servant", "Single", "Cook, domestic", "Worker", "Camden Town, London", None),
  (22, None, "Kate", "Palethorpe", "F", 18, "Servant", "Single", "Parlourmaid, domestic", "Worker", "Lincolnshire",
   "the place of birth is a Lincolnshire name that cannot be read with confidence - Frodingham or Froxfield or similar"),
 ]),
 (317, 5, "10 The Ropewalk", [
  (23, 6061, "Hannah", "Brooke", "F", 76, "Head", "Widowed", "Living on own means", None, "Sandiacre, Derbyshire",
   "the 1881 census has her in this same house as Benjamin Brooke's wife, aged 56 and born at Sandiacre. "
   "The age on the page is hard to read; 1881 settles it at 76"),
  (24, None, "Maggie", "Taylor", "F", 22, "Servant", "Single", "Cook, domestic", "Worker", "Golden Valley, Gloucestershire", None),
  (25, None, "Catherine", "Gilman", "F", 20, "Servant", "Single", "Housemaid, domestic", "Worker", "Church Gresley, Derbyshire", None),
  (26, None, "Lizzie", "Rawlinson", "F", 42, "Visitor", "Married", None, None, "Market Rasen, Lincolnshire", None),
 ]),
 (319, 6, "14 The Ropewalk", [
  (27, None, "John", "Feilman", "M", 69, "Head", "Married", "Lace merchant", "Employer", "Germany",
   "returned as a naturalised British subject. The 1911 round spells the family Feilmann"),
  (28, 5128, "Emilie", "Feilman", "F", 46, "Wife", "Married", None, None, "Russia",
   "returned as naturalised. She is at 29 Newcastle Drive in 1911, head and widowed at 56, spelt Feilmann"),
  (29, 5129, "Gertrude", "Feilman", "F", 25, "Daughter", "Single", "Schoolmistress", "Employer, at home", "Nottingham",
   "the page gives her as Gert. She is Principal of a school at 29 Newcastle Drive in 1911, aged 35"),
  (30, None, "Otto", "Feilman", "M", 19, "Son", "Single", "Assistant in lace trade", "Worker", "Nottingham", None),
  (31, 5132, "Max", "Loewenstein", "M", 48, "Brother-in-law", "Single", "Manager in lace trade", "Worker", "Russia",
   "returned as a naturalised British subject. He is with his sister Emilie at 29 Newcastle Drive in 1911, "
   "aged 58 and a lace manufacturer employing others"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr} (#{prop})")
        for no, pid, fn, ln, sex, age, rel, cond, occ, emp, bp, note in people:
            if pid:
                cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1901
                                AND census_household_num=%s AND person_id=%s""", (sched, pid))
            else:
                cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                                WHERE ce.census_year=1901 AND ce.census_household_num=%s
                                  AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)""",
                            (sched, fn, ln))
            if cur.fetchone():
                print(f"   {no:>2} {fn} {ln}: already in the record"); continue
            src = SRC.format(addr=addr, sched=sched, no=no) + (('; ' + note) if note else '')
            if emp: src += f"; the employment column reads {emp}"
            print(f"   {no:>2} {fn} {ln}, {age}, {rel}" + (f" — {occ}" if occ else "")
                  + (f"   [#{pid}]" if pid else ""))
            if not APPLY: continue
            if not pid:
                cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_place)
                               VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, 1901 - age, bp))
                pid = cur.fetchone()[0]
            else:
                cur.execute("UPDATE people SET born_place=COALESCE(born_place,%s) WHERE id=%s", (bp, pid))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, age_at_census, relationship,
                            occupation_at_census, census_household_num, marital_status, birth_place, source)
                           VALUES (%s,%s,1901,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr, age, rel, occ, sched, cond, bp, src))
            out.append({"first_name": fn, "last_name": ln, "sex": sex, "born_year": 1901 - age,
                        "id": pid, "born_place": bp,
                        "census": [{"census_year": 1901, "age_at_census": age, "address": addr,
                                    "property_id": prop, "relationship": rel,
                                    "occupation_at_census": occ, "census_household_num": sched,
                                    "marital_status": cond, "birth_place": bp, "source": src}]})
    if APPLY:
        json.dump({"note": "**The Ropewalk, 1901, schedules 1 to 6** - 2, 4, 6, 8, 10 and 14. The "
                           "street had no 1901 round in the record at all. Four people are bound to "
                           "records the record already held: Hannah Brooke from 1881 in the same "
                           "house, and Emilie and Gertrude Feilman and Max Loewenstein from 1911 at "
                           "29 Newcastle Drive.",
                   "source": "1901 census, The Ropewalk, Nottingham - read from the enumerator's page",
                   "people": out}, open('data/people_1901_ropewalk.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print(f"\n  committed - {len(out)} rows")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
