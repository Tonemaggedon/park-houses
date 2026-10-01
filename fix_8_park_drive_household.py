# -*- coding: utf-8 -*-
"""Schedule 23, 8 Park Drive: the whole household, and the surname put right.

A. Hagues supplies the full schedule from the Register's own index. It mends
four things at once:

  * the surname is **Howitt**, not Hewitt - every one of them;
  * **four people were missing**. Two of them are in this file's own list of
    forenames lost under repair strips - the master printer born 13 February
    1911 and the servant born 26 December 1905 - and the index names them;
  * **three amended surnames are readable after all.** The page shows only the
    name written on top; the index carries what is under it, so Ethel, Amy and
    Alice get their names on the night back and keep the later one as an alias;
  * one forename and one birth date were read wrong.

  railway run python3 fix_8_park_drive_household.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
PROP, SCHED = 432, 23
SRC = ("1939 Register, schedule 23, 8 Park Drive, ED letter code RMGC, Nottingham "
       "registration sub-district 3 - read from the page by A. Hagues; sub number {sub}")

# Corrections to people the record already holds: id, forename, surname on the
# night, the surname written over it, born_date, and what to say.
MEND = [
    (7410, "John Arthur", "Howitt", None, None,
     "the surname is Howitt; the line is under a repair strip, so the trade is lost and "
     "the birth month with it - the day is 12 and the year 1885"),
    (7411, "Ethel M", "Howitt", "Edward", "1912-08-07",
     "entered as Ethel M Howitt, which is her name on the night; Edward is written over it "
     "in a later hand, and the birth date is 7 August, not 7 February"),
    (7412, "Amy M", "Jenkins", "Oakland", "1916-02-24",
     "entered as Amy M Jenkins, which is her name on the night; Oakland is written over it "
     "in a later hand, and the forename is Amy, not Emily"),
]

# People the record did not hold at all: sub, forename, surname on the night,
# amended surname, sex, born_date, born_year, age, occupation, marital, note
ADD = [
    (2, "Sybil", "Howitt", None, "F", "1884-08-30", 1884, 55,
     "Unpaid domestic duties", None, "the schedule leaves her marital status blank"),
    (3, "John Kenneth", "Howitt", None, "M", "1911-02-13", 1911, 28,
     "Master printer", "Single",
     "the forename is from the Register's index; the page has it under a repair strip, "
     "which is why this record carried a Howitt with no forename"),
    (6, "Alice", "Mees", "James", "F", "1905-12-26", 1905, 33,
     "Domestic servant", "Single",
     "entered as Alice Mees, which is her name on the night; James is written over it in a "
     "later hand. The forename is from the index; the page has it under a repair strip"),
    (7, "Francis O", "Wardle", None, "F", None, 1898, None,
     "Domestic servant", "Single",
     "the birth date cannot be read beyond the year; the forename is written Francis for a "
     "woman and may be Frances"),
]


def alias(cur, pid, first, later, label='1939 amendment'):
    cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                   SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),%s
                   FROM (SELECT 1) t WHERE NOT EXISTS
                   (SELECT 1 FROM person_alias a WHERE a.person_id=%s AND LOWER(a.last_name)=LOWER(%s))""",
                (pid, first, later, pid, label, pid, later))


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    for pid, fn, was, later, bd, note in MEND:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (pid,))
        cfn, cln = cur.fetchone()
        print(f"  #{pid} {cfn} {cln}  ->  {fn} {was}" + (f", {later} kept as an alias" if later else ""))
        if not APPLY:
            continue
        if later:
            alias(cur, pid, fn, later)
        cur.execute("UPDATE people SET first_name=%s, last_name=%s, maiden_name=NULL WHERE id=%s",
                    (fn, was, pid))
        if bd:
            cur.execute("UPDATE people SET born_date=%s WHERE id=%s", (bd, pid))
        if pid == 7410:
            cur.execute("UPDATE people SET born_year=1885 WHERE id=7410")
        cur.execute("""UPDATE census_entries
                          SET source = regexp_replace(source, '; the house is not identified.*$', '')
                                       || %s
                        WHERE person_id=%s AND census_year=1939""", ('; ' + note, pid))

    for sub, fn, was, later, sex, bd, by, age, occ, marital, note in ADD:
        cur.execute("""SELECT p.id FROM people p JOIN census_entries c ON c.person_id=p.id
                        WHERE c.census_year=1939 AND c.census_household_num=%s
                          AND LOWER(p.first_name)=LOWER(%s)""", (SCHED, fn))
        if cur.fetchone():
            print(f"  sub {sub} {fn} {was}: already in the record")
            continue
        print(f"  sub {sub} {fn} {was}: new" + (f", {later} kept as an alias" if later else ""))
        if not APPLY:
            continue
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, born_date)
                       VALUES (%s,%s,%s,%s,%s) RETURNING id""", (fn, was, sex, by, bd))
        pid = cur.fetchone()[0]
        if later:
            alias(cur, pid, fn, later)
        cur.execute("""INSERT INTO census_entries
                       (person_id, property_id, census_year, address, age_at_census,
                        occupation_at_census, census_household_num, marital_status, source)
                       VALUES (%s,%s,1939,'8 Park Drive',%s,%s,%s,%s,%s)""",
                    (pid, PROP, age, occ, SCHED, marital, SRC.format(sub=sub) + '; ' + note))

    if APPLY:
        c.commit(); print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
