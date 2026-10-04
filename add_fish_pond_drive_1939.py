# -*- coding: utf-8 -*-
"""Fish Pond Drive, 1939 - and a book the record cannot yet name.

Three households. **11a Fishpond Drive carries its ED code in full: RMGB,
RG101/6178A, schedule 269** - which pushes that book's known range from 257 to
269. The other two give no code, and the record cannot supply one:

**Schedules 77 and 78 are already used by RMGC**, for *4 Clare Valley* and for
*3 Clare Valley*, which that book marks empty between numbers 4 and 2. Those are
different houses and different people, so these two Fish Pond Drive households
belong to some other book. It cannot be RMGC, and RMGB's low schedules have
never been read, so it may be RMGB - or a fourth book the record has not met.

They are entered with **the book left unstated** rather than guessed at, because
a schedule number means nothing without the book it belongs to, and this record
has already been bitten once by Bancroft going in under RMGC when it was RMGA.

**Arthur Shaw at 11a is another government post.** The page gives *Civil Servant
Investigating Clerk Un Board* - the **Unemployment Assistance Board**, which ran
means-tested relief. 11a is not in the property list, so he is unfiled.

  railway run python3 add_fish_pond_drive_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
NOBOOK = ("1939 Register, schedule {sched}, {addr} - read from the page by A. Hagues; sub number "
          "{sub}. THE ED LETTER CODE IS NOT KNOWN for this household: schedule {sched} is already "
          "used by the RMGC book for Clare Valley, so this is another book, and the record will "
          "not guess which")
RMGB = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
        "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
        "by A. Hagues; sub number {sub}")

HOUSES = [
 (109, 77, "4 Fish Pond Drive", NOBOOK, [
  (1, "John J H", "Eggleston", "M", "1886-01-02", 53, "Railway clerk", "Married", None),
  (2, "Edith J", "Eggleston", "F", "1887-02-12", 52, "Unpaid domestic duties", "Married",
   "thirteen months younger than John J H and sharing his surname, so his wife"),
  (3, "Phyllis", "Dinwoodie", "F", "1917-12-02", 21, "Unpaid domestic duties", "Married", None),
  (4, "D", "Dinwoodie", "M", "1902-04-10", 37, "Engineer examiner", "Married",
   "the index gives his forename as the single letter D and his trade as Engineer Examiner Ci, "
   "the last word cut off. Fifteen years older than Phyllis and sharing her surname, so her husband"),
  (5, "Effie", "Keller", "F", "1905-09-18", 34, "Unpaid domestic duties", "Married", None),
  (6, "Frank", "Keller", "M", "1906-06-11", 33, "Clothing manufacturer", "Married",
   "nine months younger than Effie and sharing her surname, so her husband. Three married "
   "couples under one roof, none of them sharing a surname with another"),
 ]),
 (110, 78, "6 Fish Pond Drive", NOBOOK, [
  (1, "Alfred E", "Read", "M", "1905-04-15", 34, "Transport manager", "Married", None),
  (2, "Phillis", "Read", "F", "1902-02-06", 37, "Unpaid domestic duties", "Married",
   "three years older than Alfred E and sharing his surname, so his wife"),
 ]),
 (None, 269, "11a Fish Pond Drive", RMGB, [
  (1, "Arthur", "Shaw", "M", "1902-05-28", 37,
   "Civil servant, investigating clerk, Unemployment Assistance Board", "Single",
   "the page gives Civil Servant Investigating Clerk Un Board - the Unemployment Assistance "
   "Board, which ran means-tested relief. His line is RG101/6178A, item 25, line 14, and his "
   "schedule of 269 pushes the RMGB book's known range from 257. The record holds 11 Fish Pond "
   "Drive but no 11a, so he is unfiled"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, tmpl, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        for sub, fn, ln, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                            WHERE ce.census_year=1939 AND ce.census_household_num=%s
                              AND LOWER(p.first_name)=LOWER(%s) AND LOWER(p.last_name)=LOWER(%s)
                              AND ce.age_at_census=%s""", (sched, fn, ln, age))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = tmpl.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}")
            if not APPLY:
                continue
            cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, ln, sex, int(bd[:4]), bd))
            pid = cur.fetchone()[0]
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
            if prop: rec["census"][0]["property_id"] = prop
            else: rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**Fish Pond Drive, 1939.** 11a is schedule 269 of the RMGB book, which "
                           "pushes its known range from 257. Numbers 4 and 6 are schedules 77 and "
                           "78 of a book the record cannot name: RMGC already uses both numbers "
                           "for Clare Valley.",
                   "source": "1939 Register, The National Archives RG101/6178A for 11a; the book "
                             "is not known for numbers 4 and 6",
                   "people": out}, open('data/people_1939_fish_pond_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
