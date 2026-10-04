# -*- coding: utf-8 -*-
"""The surnames that are really ditto marks, traced back through the page.

An enumerator writes the family name against the head of the household and
rules it down the column. A transcription that reads the mark as a value puts
people into the record with their **middle initial** standing where the family
name should be - *Ellen T.*, *Frank B.*, *Annie E.* - and they are invisible
everywhere on the site except Names to Check. Nineteen came in with the 1901
gap round.

**The address cannot find them**: six sit under a bare "Lenton Road" that holds
five households, and seven have no schedule number at all. What finds them is
the order of the rows, which is the order of the enumerator's page, read
together with the household the record already holds for that house.

And most of them are not missing a surname at all - they are **duplicates**.
Fifteen of the nineteen are people the record already holds under their proper
names, created a second time because the initial made the name unmatchable.
The initials prove it: Elizabeth **B.** is Elizabeth **Beatrice** Lewis, Edith
**C.** is Edith **Constance** Lewis, Mary **D.** is Mary **Daykene** Townroe,
each of an age that works out exactly ten years on from 1891.

The remaining four are genuinely new people who need their family name.

Every pair below was read off the page order and checked against the household
the record holds for that house in another round. Nothing here is a guess from
a name alone.

  railway run python3 tools_ditto_surnames.py            # preview
  railway run python3 tools_ditto_surnames.py --apply
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv

# ditto person, the person the record already holds, why
FOLD = [
 (4290, 2914, "Lisle N., 10, son - the Robinsons of 21 Lenton Avenue, where the record has him filed"),
 (4301, 2473, "Alice M., 1, daughter - Alice May Rawson, with Ernest H. and Edith H. in schedule 148"),
 (4302, 2818, "Henry C., 22, son - Henry C Thompson of 8 Lenton Avenue"),
 (4303, 2819, "Arthur J., 20, son - Arthur J Thompson of 8 Lenton Avenue"),
 (4304,  489, "Annie E., 38, wife - Annie Blythe of 6 Lenton Avenue"),
 (4305,  492, "Arthur E., 7, son - Arthur Blythe of 6 Lenton Avenue"),
 (4306,  490, "Marjorie P., 5, daughter - Marjorie Blythe of 6 Lenton Avenue"),
 (4307,  491, "Kathleen W., 2, daughter - Kathleen Blythe of 6 Lenton Avenue"),
 (4311,  837, "Amy M., 26, wife - Amy Marguerite Forman of 13 Lenton Road"),
 (8336, 2955, "Margaret A., 23, sister - Margaret A. Parkin of 14 Lenton Avenue"),
 (8337, 2956, "Katharine J., 19, sister - Katharine J. Parkin of 14 Lenton Avenue"),
 (4362,  814, "Ellen T., 43, daughter - Ellen Frances Lewis, 33 in 1891 at 6 Lenton Road"),
 (4364,  816, "Elizabeth B., 35, daughter - Elizabeth BEATRICE Lewis, 25 in 1891"),
 (4365, 3399, "Edith C., 29, daughter - Edith CONSTANCE Lewis, 19 in 1891"),
 (4375, 3424, "Mary D., 50, wife - Mary DAYKENE Townroe, 41 in 1891 at 2 Lenton Road"),
 (4374, 3423, "Charles E. Tomnroe, 43, head - Charles Edward Townroe, 34 in 1891; "
              "the variant-spelling check found this one"),
]

# ditto person, the forename to keep, the family name the page gives, why
NAME = [
 (4204, "Jane A. B.",  "Martin",  "wife of William Martin, 34, head of schedule 77 on Hamilton Drive"),
 (4279, "Margaret E.", "Bowers",  "daughter in the household of William Bowers, 58, of 3 Lenton Avenue"),
 (4363, "Frank B.",    "Lewis",   "son in William W Lewis's household - but see the note below"),
 (4376, "Geoffrey C.", "Townroe", "son of Charles Edward Townroe, born about 1895, not in the 1891 return"),
]


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    print("-- held twice: the ditto copy folds into the person the record already has --")
    folded = 0
    for drop, keep, why in FOLD:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (drop,))
        d = cur.fetchone()
        if not d:
            continue
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (keep,))
        k = cur.fetchone()
        if not k:
            print(f"  !! #{keep} is not in the record - #{drop} left alone"); continue
        print(f"  #{drop} {d[0]} {d[1]!r}  ->  #{keep} {k[0]} {k[1]}")
        print(f"      {why}")
        folded += 1
        if not APPLY:
            continue
        # the row only moves where the keeper has nothing for that round
        cur.execute("""UPDATE census_entries n SET person_id=%s
                        WHERE n.person_id=%s AND NOT EXISTS
                          (SELECT 1 FROM census_entries o WHERE o.person_id=%s
                             AND o.census_year=n.census_year)""", (keep, drop, keep))
        # anything the copy knows and the keeper does not is worth keeping - Annie
        # Blythe's birthplace of Yorkshire is only on the ditto row
        cur.execute("""UPDATE census_entries k SET
                          birth_place     = COALESCE(k.birth_place, d.birth_place),
                          marital_status  = COALESCE(k.marital_status, d.marital_status),
                          occupation_at_census = COALESCE(k.occupation_at_census, d.occupation_at_census)
                         FROM census_entries d
                        WHERE k.person_id=%s AND d.person_id=%s
                          AND d.census_year=k.census_year""", (keep, drop))
        # the name the round used, so a re-import finds the keeper instead of making him again
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name)
                       VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""", (keep, d[0], d[1]))
        cur.execute("DELETE FROM census_entries WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM property_residents WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM occupations WHERE person_id=%s", (drop,))
        cur.execute("DELETE FROM people WHERE id=%s", (drop,))

    print("\n-- new people: the initial moves into the forename, the family name comes off the page --")
    named = 0
    for pid, first, last, why in NAME:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (pid,))
        p = cur.fetchone()
        if not p or len(p[1].strip().rstrip('.')) > 2:
            print(f"  #{pid}: already named"); continue
        print(f"  #{pid} {p[0]} {p[1]!r}  ->  {first} {last}")
        print(f"      {why}")
        named += 1
        if APPLY:
            cur.execute("UPDATE people SET first_name=%s, last_name=%s WHERE id=%s", (first, last, pid))

    print(f"\n  {folded} folded, {named} named")
    if APPLY:
        c.commit(); print("  committed")
    else:
        print("  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
