# -*- coding: utf-8 -*-
"""Albert Ball VC is holding his father's census records.

**#469 carries the flying ace's dates and Wikipedia article - born 14 August
1896, died 7 May 1917 - and two census rows that cannot be his:**

    1911  aged 47  Head  43 Lenton Road  Real Estate and landagent
    1921  aged 58  Head  43 Lenton Road  Land Agent

A boy born in 1896 is fourteen in 1911, not forty-seven, and was two years dead
by 1921. Those rows are his **father's** - Albert Ball the elder, land agent,
born about 1863 by both ages.

The household settles it. In 1911 the head of 43 Lenton Road has a wife of 46
and a daughter of 19; in 1921 a wife of 57. The wife is the same woman twice
over under two readings - **Harvell Mary Ball** in 1911 and **Mary Harriett**
in 1921, the latter with her forenames run into the name columns so that
*Harriett* became her surname. *Harvell* is not a name; the 1921 row supplies
what it should be.

So: the elder Albert Ball becomes his own person and takes the census rows.
#469 keeps the ace's dates and his article, and ends with no census row - which
is right, because he is not in either return. The wife is joined into one and
given the name the 1921 page spells.

  railway run python3 fix_albert_ball.py            # preview
  railway run python3 fix_albert_ball.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT id, census_year, age_at_census, occupation_at_census
                     FROM census_entries WHERE person_id=469 ORDER BY census_year""")
    rows = cur.fetchall()
    if not rows:
        print("  #469 already holds no census row - the split has been done")
    else:
        for r in rows:
            print(f"  #469 holds {r[1]}, aged {r[2]}, {r[3]} - which makes him born about "
                  f"{r[1] - r[2]}, not 1896")
    cur.execute("SELECT first_name, last_name, born_year FROM people WHERE id=1503")
    dup = cur.fetchone()
    if dup:
        print(f"\n  #1503 {dup[0]} {dup[1]!r} (b.{dup[2]}) is the 1921 wife, with her forenames "
              f"in the wrong columns")
    if not APPLY:
        print("\n  Nothing written. Add --apply."); return

    if rows:
        cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, bio)
                       VALUES ('Albert','Ball','M',1863,%s) RETURNING id""", (
         "Albert Ball the elder, land agent, of **43 Lenton Road**, where he was returned as head "
         "in 1911 aged 47 and in 1921 aged 58 - which puts his birth about 1863. With him in 1911 "
         "were his wife Harriett Mary, 46, and their daughter Lois Beatrice, 19.\n\n"
         "He was separated from his son on 4 October 2026. The record had been holding both men as "
         "one person: these census rows sat on the record carrying the dates and Wikipedia article "
         "of **Albert Ball VC**, the flying ace, who was born in 1896 and died in 1917 and so can "
         "be neither a man of 47 in 1911 nor a man of 58 in 1921.\n\n"
         "The record does not yet hold his own dates, the offices he held, or a source for them.",))
        new = cur.fetchone()[0]
        cur.execute("UPDATE census_entries SET person_id=%s WHERE person_id=469", (new,))
        cur.execute("UPDATE property_residents SET person_id=%s WHERE person_id=469", (new,))
        cur.execute("UPDATE occupations SET person_id=%s WHERE person_id=469", (new,))
        print(f"\n  the elder Albert Ball is now #{new}, and holds both census rows")
        cur.execute("""UPDATE people SET bio=%s WHERE id=469 AND (bio IS NULL OR bio='')""", (
         "Albert Ball VC, the flying ace, born 14 August 1896 and killed 7 May 1917. He grew up at "
         "**43 Lenton Road**, his father's house.\n\n"
         "He is not in either of the returns the record holds for that house: in 1911 he was "
         "fourteen and away, and by 1921 he was dead. Until 4 October 2026 this record was also "
         "carrying his father's two census rows, which made him a land agent of 47 and then 58.",))

    if dup:
        cur.execute("""SELECT census_year FROM census_entries WHERE person_id=1503
                        INTERSECT SELECT census_year FROM census_entries WHERE person_id=889""")
        if cur.fetchall():
            print("  #1503 and #889 hold the same round - left alone")
        else:
            cur.execute("UPDATE census_entries SET person_id=889 WHERE person_id=1503")
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year)
                           VALUES (889,'Mary','Harriett',1864) ON CONFLICT DO NOTHING""")
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year)
                           VALUES (889,'Harvell Mary','Ball',1865) ON CONFLICT DO NOTHING""")
            cur.execute("DELETE FROM property_residents WHERE person_id=1503")
            cur.execute("DELETE FROM occupations WHERE person_id=1503")
            cur.execute("DELETE FROM people WHERE id=1503")
            cur.execute("""UPDATE people SET first_name='Harriett Mary' WHERE id=889""")
            print("  #1503 folded into #889, who is now Harriett Mary Ball")
    c.commit(); print("\n  committed")


if __name__ == '__main__':
    main()
