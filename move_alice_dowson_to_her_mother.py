#!/usr/bin/env python3
"""Linzi Kemp's research on Alice Dowson went onto her daughter's record.

#2806 Alice M Dowson is entered on the census as *Daughter*, aged 10 in 1881
and 30 in 1901, occupation Scholar. #2805 Alice Dowson is the *Wife* in 1871,
1881, 1891 and 1901, aged 26 to 56, married to Benjamin.

The biography itself settles which is which: it opens "Alice Dowson was born
in 1844 and, in her 83 years (died 1927)" and goes on to describe a woman
married to Benjamin with ten children. That is the mother. It had been written
onto the daughter, and with it the photograph, the everybodywiki link, the
death in 1927 and the suffrage classification.

All of it moves to #2805, which held none of those fields, so nothing of hers
is overwritten. The daughter keeps what is actually hers: her birth in 1871,
her birthplace, her census rows, her occupation and her link to the house.
"""
import os, sys, psycopg2

MOTHER, DAUGHTER = 2805, 2806


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()

    cur.execute("""SELECT bio, photo_url, wikipedia_url, died_date, died_year
                     FROM people WHERE id=%s""", (DAUGHTER,))
    bio, photo, wiki, died_date, died_year = cur.fetchone()

    cur.execute("""SELECT COALESCE(bio,''), photo_url, wikipedia_url, died_date, died_year
                     FROM people WHERE id=%s""", (MOTHER,))
    m_bio, m_photo, m_wiki, m_dd, m_dy = cur.fetchone()
    if m_bio or m_photo or m_wiki or m_dd or m_dy:
        print('STOP: the mother already holds something in one of these fields.')
        print('  bio:', len(m_bio), '| photo:', bool(m_photo), '| wiki:', bool(m_wiki),
              '| died:', m_dd, m_dy)
        return 1

    cur.execute("""UPDATE people SET bio=%s, photo_url=%s, wikipedia_url=%s,
                     died_date=%s, died_year=%s WHERE id=%s""",
                (bio, photo, wiki, died_date, died_year, MOTHER))
    print(f'moved to #{MOTHER}: biography ({len(bio or "")} characters), photograph, '
          f'everybodywiki link, died {died_date}')

    cur.execute("""UPDATE people SET bio=NULL, photo_url=NULL, wikipedia_url=NULL,
                     died_date=NULL, died_year=NULL WHERE id=%s""", (DAUGHTER,))
    print(f'cleared from #{DAUGHTER}: the same five fields')

    # The classification goes with it, note and all.
    cur.execute("""INSERT INTO person_tags (person_id, tag, note, added_by)
                   SELECT %s, tag, note, added_by FROM person_tags
                    WHERE person_id=%s AND tag='Suffrage'
                   ON CONFLICT (person_id, tag) DO NOTHING""", (MOTHER, DAUGHTER))
    cur.execute("DELETE FROM person_tags WHERE person_id=%s AND tag='Suffrage'", (DAUGHTER,))
    print('moved the Suffrage classification')

    # The census says daughter of the house and the record never joined them.
    cur.execute("""INSERT INTO people_relationships (person_a_id, relationship, person_b_id)
                   SELECT %s, 'parent_of', %s WHERE NOT EXISTS (
                     SELECT 1 FROM people_relationships
                      WHERE person_a_id=%s AND person_b_id=%s AND relationship='parent_of')""",
                (MOTHER, DAUGHTER, MOTHER, DAUGHTER))
    cur.execute("""INSERT INTO people_relationships (person_a_id, relationship, person_b_id)
                   SELECT %s, 'child_of', %s WHERE NOT EXISTS (
                     SELECT 1 FROM people_relationships
                      WHERE person_a_id=%s AND person_b_id=%s AND relationship='child_of')""",
                (DAUGHTER, MOTHER, DAUGHTER, MOTHER))
    print('joined them as mother and daughter, which the census said and the record had not')

    for who, pid in (('mother', MOTHER), ('daughter', DAUGHTER)):
        cur.execute("""SELECT first_name, last_name, born_year, died_year,
                         LENGTH(COALESCE(bio,'')), photo_url IS NOT NULL,
                         (SELECT STRING_AGG(tag, ', ') FROM person_tags WHERE person_id=p.id)
                         FROM people p WHERE id=%s""", (pid,))
        f, l, by, dy, bl, ph, tg = cur.fetchone()
        print(f'  {who:<9} #{pid}  {f} {l}  {by or "?"}-{dy or "?"}  '
              f'bio {bl} chars, photo {"yes" if ph else "no"}, tags: {tg or "none"}')

    c.commit(); cur.close(); c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
