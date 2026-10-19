#!/usr/bin/env python3
"""Two returns from outside The Park that say a great deal about one of its own.

A. Hagues supplied the 1891 enumerator's page for 7 Regent Street and the 1921
entry for Newlands Corner, Albury, Surrey. Neither address is on the estate, so
nothing is filed against a property and no person is created: this is
background to Rose Fyleman, who is in the record at 29 Newcastle Drive.

What the 1891 page shows, read from the image:

    schedule 58, No 7
    John Feilmann      Head   M   59?  lace/cotton manufacturer  Germany (British subject)
    Amelia  do         Wife   Mar 36                             Russia
    Martin E do        Son    S   16   scholar                   Nottingham
    Agnes G do         Dau    S   15?                            Nottingham
    Amy R   do         Dau    S   14                             Nottingham
    Frederick C do     Son                                       Nottingham
    Max Loewenstein    Bro-in-law S 38 manager                   Russia (British subject)
    Thirza Spencer     Serv   S   28?  cook, domestic
    Margaret Burrows   do     S   18   housemaid

Three of those readings check out against things the record already holds or
has since been told: Max Loewenstein at 38 gives 1853, which is his birth year
here; Amy R at 14 gives 1877, which is Rose's; and Frederick C is confirmed as
a brother born 1881 by the 1921 return below. So the page is almost certainly
the right family, indexed by Find My Past under the mangled surname Falinan.

The 1921 return, Newlands Corner, Albury, Surrey, in the Spanner household:

    Rose Amy  Fyleman  Boarder  F  1877  44  Nottingham
        Teacher of voice production and authoress, own account
    Frederick Fyleman  Boarder  M  1881  40  Nottingham
        Salesman, International Multigraph Co Ltd
"""
import os, sys
import psycopg2

ROSE = 5130

INSERT_AFTER = """She was not at home on census night in 1901. While her parents, her sister and her brother were counted at 14 The Ropewalk, she was boarding in London at 20 Montague Place, St Giles in the Fields."""

NEW_PASSAGE = INSERT_AFTER + """

Her own account of herself, 1921
By the 1921 census she had left Nottingham. She was boarding at Newlands Corner, Albury in Surrey, in the household of Charles Spanner, a council roadman, and his wife Clara — and the form has her, in her own words, as **teacher of voice production and authoress**, working on her own account. Four years after Punch printed the fairies, the singer had become a writer and was still teaching the voice. Her brother Frederick, forty, was boarding in the same house, a salesman for the International Multigraph Company. Both of them were entered as Fyleman."""

QUESTION = dict(
    slug='feilmann-children-in-1891',
    title='Who were the four Feilmann children on the 1891 return, and are two of them Gertrude and Rose?',
    kind='person',
    detail="""A. Hagues supplied the 1891 enumerator's page for the family at **7 Regent Street**, outside the estate — the household Find My Past indexes under the mangled surname **Falinan**. Read from the image, schedule 58 gives John Feilmann, head, born Germany and a British subject; his wife, whose forename reads more like **Amelia** than the Emilie the later censuses give her; **Max Loewenstein**, brother-in-law, 38, born Russia and naturalised; two servants; and four children, all born Nottingham:

| as written | age | probably |
|---|---|---|
| Martin E | 16 | not in the record |
| Agnes G | 15? | **Gertrude?** — the record's Gertrude was born 1876 |
| Amy R | 14 | **Rose Amy** — the age gives 1877, which is hers |
| Frederick C | — | **Frederick**, confirmed born 1881 by the 1921 return |

**Three of the readings check out.** Max Loewenstein at 38 gives 1853, which is the birth year the record already holds for him. Amy R at 14 gives 1877, Rose's year. And Frederick is independently confirmed as a brother born 1881 in Nottingham by the 1921 census, where he and Rose are boarding in the same Surrey house.

**Which raises a naming pattern worth testing.** If Agnes G is Gertrude and Amy R is Rose Amy, then both sisters were entered by a first name they later dropped in favour of their second. That would explain a good deal of why this family is hard to find, and it is the kind of thing a birth registration settles in one line.

**Two things it does not settle.** Martin E does not appear anywhere else in the record. And the record holds an **Otto Feilman born 1882** in the 1901 household at 14 The Ropewalk, which sits awkwardly beside a Frederick born 1881 — two brothers a year apart is possible, the same brother under two names is also possible, and nothing here chooses between them.

**What would settle it:** the birth registrations for the Nottingham children, or the 1881 return for wherever the family then was. None of this is filed against a property, because none of these addresses is in The Park.""",
    property_id=None, person_id=ROSE, priority=5)


def main():
    url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    c = psycopg2.connect(url)
    cur = c.cursor()

    cur.execute("SELECT bio FROM people WHERE id=%s", (ROSE,))
    bio = cur.fetchone()[0]
    if 'voice production' in bio:
        print('Rose    — already has the 1921 passage')
    else:
        assert INSERT_AFTER in bio, 'the paragraph to hang it on has moved'
        cur.execute("UPDATE people SET bio=%s WHERE id=%s",
                    (bio.replace(INSERT_AFTER, NEW_PASSAGE), ROSE))
        print('Rose    — the 1921 return added, in her own words')

    cur.execute("""INSERT INTO research_questions (slug, title, detail, kind, property_id,
                   person_id, priority, status, on_foot, created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,'open',false,'A. Hagues and Claude')
                   ON CONFLICT (slug) DO UPDATE SET detail=EXCLUDED.detail, edited_at=NOW()
                   RETURNING id""",
                (QUESTION['slug'], QUESTION['title'], QUESTION['detail'], QUESTION['kind'],
                 QUESTION['property_id'], QUESTION['person_id'], QUESTION['priority']))
    print('question:', QUESTION['title'][:60] + '…')

    c.commit(); cur.close(); c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
