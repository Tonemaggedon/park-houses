# -*- coding: utf-8 -*-
"""2 Newcastle Circus and 9 Park Drive, 1939 - schedules 249 and 251.

**Maria Stepkova, 38, domestic, at 2 Newcastle Circus.** The surname is Czech -
the feminine form - and she is in service in The Park six months after Germany
took Czechoslovakia. She joins a group this book keeps turning up: Anna E
Hirschfield, flagged **refugee** by the register at Felixstowe; the Fischers -
Hans, Horst W and Mariaon Alice - with Marion Rhea Portalski at 39 Newcastle
Drive; and Ernst and Sibylle Zuckermann at 12 The Ropewalk, he a medical
practitioner. The record does not say any of them is a refugee except
Hirschfield, and this entry does not either.

**John G Laing of 9 Park Drive is John "Posvenor" Laing** - almost certainly
**Grosvenor** misread - son of George Dawson Laing, the wine and spirit merchant
of 17 Pelham Crescent. He was 21 in his father's house in 1911 and 31 in 1921,
in the same trade both times. At 50 he is still a wine and spirit merchant,
still single, and keeping his own house with a housekeeper and a parlourmaid.
Bound by number.

  railway run python3 add_rmgb_249_251_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
SRC = ("1939 Register, schedule {sched}, {addr}, ED letter code RMGB, Nottingham registration "
       "district 430-3, sub-district 26, The National Archives RG101/6178A - read from the page "
       "by A. Hagues; sub number {sub}")

HOUSES = [
 (203, 249, "2 Newcastle Circus", [
  (1, None, "John C", "Wright", None, "M", "1884-06-30", 55, "Colliery sales manager", "Married",
   "the record holds nothing for this house in any earlier round"),
  (2, None, "Catherine", "Wright", None, "F", "1890-05-17", 49, "Unpaid domestic duties", "Married",
   "six years younger than John C and sharing his surname, so his wife"),
  (3, None, "Catherine I", "Wright", None, "F", "1921-06-25", 18, "At school", "Single",
   "eighteen and still at school, where most girls of her age in this book are in work or in "
   "service; she carries her mother's forename"),
  (4, None, "Maria", "Stepkova", None, "F", "1900-12-09", 38, "Domestic", "Single",
   "STEPKOVA is a Czech surname in its feminine form, and she is in service here six months "
   "after Germany took Czechoslovakia. The register does not flag her as a refugee, as it does "
   "Anna E Hirschfield at Felixstowe, but she belongs with the continental names this book "
   "keeps turning up"),
 ]),
 (237, 251, "9 Park Drive", [
  (1, None, "Annie", "Rayworth", None, "F", "1884-02-27", 55, "Housekeeper", "Single", None),
  (2, None, "Eileen M", "Baker", "Canor", "F", "1909-02-02", 30, "Parlour maid", "Single",
   "the index gives her as Baker (Canor); single, so Baker is the name the register was written "
   "in. Canor is not a name the record holds - Canner or Cantor is likelier and the page "
   "should settle it"),
  (3, 504, "John Grosvenor", "Laing", None, "M", "1889-09-27", 50, "Wine and spirit merchant", "Single",
   "the index gives him as John G; the record has him as John POSVENOR Laing, which is almost "
   "certainly Grosvenor misread. He is George Dawson Laing's son, 21 in his father's house at 17 "
   "Pelham Crescent in 1911 and 31 there in 1921, a wine and spirit merchant on both rounds as "
   "he is here. His birthday fell two days before the register was taken"),
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
                   "people": out}, open('data/people_1939_rmgb_249_251.json', 'w'),
                  indent=1, ensure_ascii=False)
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
