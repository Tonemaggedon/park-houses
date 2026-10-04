# -*- coding: utf-8 -*-
"""Cavendish Crescent North, 1939 - schedules 191 to 195 of the RMGB book.

**Two of these households were already half in the record under other spellings,
and entering them as the index writes them would have made duplicates.**

*Weenberg* is **Weinberg**. Caroline R Weinberg kept Hardwicke House in 1911 as
Mehir Weinberg's wife and in 1921 as its head, widowed, with her sons Jacob and
Eli Gustave. The 1939 index gives her as Caroline R Weenberg, 55, of private
means, and her son as Eli G Weenberg - and calls him Female, which he is not.
Both are bound by number.

*H Holliwell* is **Henry Holliwell**, who headed 7 Cavendish Crescent North in
1921 aged 48. That is what identifies the house: there is a number 7 on both the
North and the South, and the index gives neither.

**The brackets hold maiden names in this batch**, on A. Hagues's word - Bould for
Alice, and so Gardener for Muriel and Walter for Anna M. Each is entered under
the name the register was written in, with the married name as the amendment.

Schedule 193 gives no number and no side, and schedule 195 gives the number 5 but
not the side, so both go in unfiled. The walk points to the North for 195 -
schedule 194 beside it is 7 Cavendish Crescent North - but the page has not said
so, and a side is not a thing to guess.

  railway run python3 add_cavendish_crescent_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

# property, schedule, address, [(sub, existing id or None, first, last, later, sex, born, age, occ, marital, note)]
HOUSES = [
 (398, 191, "Hardwicke House, Cavendish Crescent North", [
  (1, 2289, "Caroline R", "Weinberg", None, "F", "1884-08-12", 55, "Private means", None,
   "the index writes the surname Weenberg; she is the Caroline R Weinberg who kept this house in "
   "1911 as Mehir Weinberg's wife and in 1921 as its head, and her recorded ages across the three "
   "rounds do not agree with one another"),
  (2, 705, "Eli Gustave", "Weinberg", None, "M", "1910-10-04", 28, "Company director, merchant", None,
   "the index writes him Eli G Weenberg and gives his sex as Female, which he is not - he is "
   "Caroline's son, ten years old in the 1921 round; the word after Company is unread, so what "
   "kind of director is not known"),
  (3, None, "Alice", "Bould", "Reeve", "F", "1913-05-18", 26, "Domestic", None,
   "the index gives her as Reeve (Bould) and Bould is the maiden name, so she was Bould on the "
   "night; Mary Bould at sub number 6 is thirty-nine years older and most likely her mother"),
  (4, None, "Anna M", "Walter", "Isherwood", "F", "1913-05-10", 26, "State registered nurse", None,
   "the index gives her as Anna M (Hannah) Isherwood (Walter); Walter is the maiden name, so she "
   "was Walter on the night, and Hannah is a second form of her forename"),
  (5, None, "Florence", "Cartwright", None, "F", "1891-07-23", 48, "State registered nurse", None,
   "the record holds several Cartwright families but none that places her"),
  (6, None, "Mary", "Bould", None, "F", "1874-06-10", 65, "Unpaid domestic duties", None, None),
 ]),
 (None, 193, "Cavendish Crescent (no number and no side given)", [
  (1, None, "Miriam", "Raflowitch", None, "F", "1890-09-28", 49, "Lace manufacturer", None,
   "head of the household and a lace manufacturer in her own right, which is unusual on this "
   "estate; her birthday fell the day before the register was taken"),
  (2, None, "Arthur", "Spooner", None, "M", "1885-08-31", 54, "Lace machine fitter", None,
   "the trade is followed by a letter the index could not read"),
  (3, None, "Ethel", "Spooner", None, "F", "1886-07-23", 53, "Housekeeper", None,
   "a year younger than the man at sub number 2 and sharing his surname, so most likely his wife"),
  (4, None, "Muriel A", "Gardener", "Watson", "F", "1916-03-03", 23, "Domestic", None,
   "the index gives her as Watson (Gardener); by the rule for this batch the bracket is the "
   "maiden name, so she was Gardener on the night"),
  (5, None, "Madge", "Smith", None, "F", "1921-12-26", 17, "Domestic", None, None),
 ]),
 (24, 194, "7 Cavendish Crescent North", [
  (1, 2358, "Henry", "Holliwell", None, "M", "1876-05-16", 63, "Lace manufacturer", None,
   "the index gives him only as H Holliwell; he is the Henry Holliwell who headed this house in "
   "1921, and he is what identifies it, since the index names neither the number's side nor a "
   "house and there is a 7 on both the North and the South. His birth year is 1873 on the 1921 "
   "round and 1876 here"),
  (2, None, "Annie C", "Holliwell", None, "F", "1876-07-17", 63, "Unpaid domestic duties", None,
   "two months younger than Henry and sharing his surname, so his wife; the 1921 round names "
   "nobody with him but two women of about thirty"),
  (3, None, "May E", "Corrdy", None, "F", "1912-05-03", 27, "Domestic", None,
   "the surname is written Corrdy and may be Corry, Cordy or Caddy"),
  (4, None, "Jessie E", "Holt", None, "F", "1890-09-21", 49, "Domestic", None, None),
 ]),
 (None, 195, "5 Cavendish Crescent (the side is not given; schedule 194 next to it is the North)", [
  (1, None, "George E", "Yeomans", None, "M", "1880-02-05", 59, "Tobacco manufacturer", None,
   "head of the house; he and Thomas H Clarke at sub number 5 are both tobacco manufacturers, "
   "which in Nottingham means John Player & Sons unless something says otherwise - though "
   "nothing here does"),
  (2, None, "Nora", "Yeomans", None, "F", "1895-04-17", 44, "Unpaid domestic duties", None,
   "fifteen years younger than George E, so most likely his wife and possibly a second one, "
   "given the gap"),
  (3, None, "Ralph B", "Yeomans", None, "M", "1920-10-11", 18, "Unpaid domestic duties", None,
   "the register gives unpaid domestic duties for a man of eighteen, which is unusual enough to "
   "be worth checking against the page; his birthday fell twelve days after it was taken"),
  (4, None, "Helen U H", "Yeomans", "Martlow", "F", "1924-10-24", 14, "At school", None,
   "the index gives her as Martlow (Yeomans); Yeomans is the maiden name, so she was Yeomans on "
   "the night - George E's daughter, fourteen and at school"),
  (5, None, "Thomas H", "Clarke", None, "M", "1913-08-16", 26, "Tobacco manufacturer", None,
   "thirty-three years younger than the head and in the same trade; whether he is family, a "
   "lodger or a colleague is not said"),
  (6, None, "Mary E", "Clarke", None, "F", "1914-06-16", 25, "Unpaid domestic duties", None,
   "ten months younger than Thomas H and sharing his surname, so most likely his wife"),
  (7, None, "Martha", "Jobson", "Fletcher", "F", "1891-06-13", 48, "Cook", None,
   "the index gives her as Martha (Mary) Fletcher (Jobson); Jobson is the maiden name, so she "
   "was Jobson on the night, and Mary is a second form of her forename"),
  (8, None, "Eileen", "Hussey", "Lovegrove", "F", "1914-11-12", 24, "Housemaid", None,
   "the index gives her as Lovegrove (Hussey); Hussey is the maiden name, so she was Hussey on "
   "the night"),
 ]),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    out = []
    for prop, sched, addr, people in HOUSES:
        print(f"--- schedule {sched}, {addr}" + (f" (#{prop})" if prop else " [UNFILED]"))
        for sub, exist, fn, ln, later, sex, bd, age, occ, marital, note in people:
            cur.execute("""SELECT 1 FROM census_entries WHERE census_year=1939
                            AND census_household_num=%s AND person_id = COALESCE(%s, -1)""",
                        (sched, exist))
            if cur.fetchone():
                print(f"  sub {sub} {fn} {ln}: already in the record"); continue
            src = SRC.format(sched=sched, addr=addr, sub=sub) + (('; ' + note) if note else '')
            tag = f"bound to #{exist}" if exist else "new"
            print(f"  sub {sub} {fn} {ln}, {age} - {occ}  [{tag}]")
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
                            (fn, ln, sex, int(bd[:4]) if bd else None, bd))
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
                   "census": [{"census_year": 1939, "address": addr, "age_at_census": age,
                               "occupation_at_census": occ, "census_household_num": sched,
                               "marital_status": marital, "source": src}]}
            if prop:
                rec["census"][0]["property_id"] = prop
            else:
                rec["census"][0]["unresolved_address"] = addr
            out.append(rec)
    if APPLY:
        json.dump({"note": "**Cavendish Crescent North, schedules 191 to 195 of the 1939 "
                           "Register, ED letter code RMGB.** Weenberg in the index is the Weinberg "
                           "family of Hardwicke House, and H Holliwell is the Henry Holliwell who "
                           "headed 7 Cavendish Crescent North in 1921 - which is what identifies "
                           "the house, there being a 7 on both sides. Schedules 193 and 195 are "
                           "unfiled: 193 gives no number and no side, and 195 gives the number "
                           "but not the side. The brackets in this batch hold maiden names.",
                   "source": "1939 Register, ED letter code RMGB, The National Archives RG101/6178A",
                   "people": out}, open('data/people_1939_rmgb_cavendish_crescent.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
