# -*- coding: utf-8 -*-
"""5 Hope Drive, 1939 - schedule 65, and five working daughters.

**Harry Leavesley, garage foreman, and his wife Grace Dorothy, with five
daughters, every one of them earning except the youngest.** Nothing else in this
round looks like it.

    Irene,     24  tobacco stripper
    Constance, 20  embroidery machinist
    Ivy,       17  cigarette packer
    Violet,    15  printing machinist
    Dorothy,   13  at school

Three of the five are in Nottingham's own trades - tobacco twice over and
embroidery once - and Violet is fifteen and already at a printing machine. A
nurse, Gertrude Norton, 62, lodges with them, and **two further lines the
register will not open**, so the house held at least ten.

The index prints sub number 4 twice, the second time as *Constance D Wright
(Jeavesley)* - a J for an L - which is what supplies her middle initial. All
four bracketed daughters were **Leavesley** on the night: they are in their
parents' house and single.

  railway run python3 add_5_hope_drive_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code {book}, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

# property, schedule, address, book, people
HOUSES = [
 (353, 65, "5 Hope Drive", [
  (1, None, "Harry", "Leavesley", None, "M", "1889-01-21", 50, "Garage foreman", "Married",
   "the page gives Garage Forman. The garage attendant at number 4, Sidney Edson, is two doors "
   "away, though the record cannot say they worked at the same one"),
  (2, None, "Grace Dorothy", "Leavesley", None, "F", "1891-01-15", 48,
   "Unpaid domestic duties", "Married",
   "the index gives her as G D (Grace Dorothy); her daughter at sub number 7 carries her name"),
  (3, None, "Irene", "Leavesley", "Pass", "F", "1915-03-29", 24, "Tobacco stripper", "Single",
   "stripping tobacco leaf, a Nottingham trade; she is single in her parents' house, so "
   "Leavesley on the night and Pass the name she came to later"),
  (4, None, "Constance D", "Leavesley", "Wright", "F", "1919-06-15", 20,
   "Embroidery machinist", "Single",
   "the index prints her twice, the second time as Constance D Wright (JEAVESLEY) - a J read "
   "for an L - which is what supplies her middle initial"),
  (5, None, "Ivy", "Leavesley", None, "F", "1922-03-04", 17, "Cigarette packer", "Single",
   "the second of the daughters in tobacco"),
  (6, None, "Violet", "Leavesley", "Davis", "F", "1924-03-07", 15, "Printing machinist", "Single",
   "FIFTEEN and already at a printing machine"),
  (7, None, "Dorothy", "Leavesley", "Rumph", "F", "1926-05-28", 13, "At school", "Single",
   "the index gives her as Dorothy (Mary); the only one of the five daughters not earning"),
  (9, None, "Gertrude", "Norton", None, "F", "1877-07-17", 62, "Nurse", "Single",
   "a lodger rather than family. Sub numbers 8 and 10 are lines the register keeps closed, so "
   "the house held at least ten people"),
 ]),
]
BOOK = {65: 'RMGC'}


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
                                AND source ILIKE %s""", (sched, exist, f'%{BOOK[sched]}%'))
            else:
                cur.execute("""SELECT 1 FROM census_entries ce JOIN people p ON p.id=ce.person_id
                                WHERE ce.census_year=1939 AND ce.census_household_num=%s
                                  AND ce.source ILIKE %s
                                  AND LOWER(p.first_name)=LOWER(%s)
                                  AND LOWER(p.last_name)=LOWER(%s)""",
                            (sched, f'%{BOOK[sched]}%', fn, ln))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub, book=BOOK[sched]) + (('; ' + note) if note else '')
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
            # a woman may have more than one later name, written here latest last
            for i, one in enumerate([x.strip() for x in (later or '').split(',') if x.strip()]):
                nlater = len([x for x in (later or '').split(',') if x.strip()])
                label = ('1939 amendment (married name)' if nlater < 2 else
                         f"1939 amendment ({'latest' if i == nlater-1 else 'first'} married name)")
                cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                               SELECT %s,%s,%s,%s,%s
                                 FROM (SELECT 1) t WHERE NOT EXISTS
                               (SELECT 1 FROM person_alias a
                                 WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                                   AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""",
                            (pid, fn, one, int(bd[:4]), label, fn, one))
            cur.execute("""INSERT INTO census_entries
                           (person_id, property_id, census_year, address, unresolved_address,
                            age_at_census, occupation_at_census, census_household_num,
                            marital_status, source)
                           VALUES (%s,%s,1939,%s,%s,%s,%s,%s,%s,%s)""",
                        (pid, prop, addr if prop else None, None if prop else addr,
                         age, occ, sched, marital, src))
            rec = {"first_name": fn, "last_name": ln, "sex": sex, "born_year": int(bd[:4]),
                   "born_date": bd if len(bd) > 4 else None, "id": pid,
                   "census": [{"census_year": 1939, "age_at_census": age, "address": addr,
                               "occupation_at_census": occ, "census_household_num": sched,
                               "marital_status": marital, "source": src}]}
            if prop:
                rec["census"][0]["property_id"] = prop
            else:
                rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**5 Clumber Crescent South, schedule 242 of the 1939 Register, ED "
                           "letter code RMGB.** William Crane, builder and contractor, his wife "
                           "and his daughter Joyce M, a British Red Cross volunteer, with two "
                           "domestics who are most likely sisters. None of the five was in the "
                           "record.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgc_5_hope_drive.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
