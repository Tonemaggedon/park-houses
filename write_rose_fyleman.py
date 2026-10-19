#!/usr/bin/env python3
"""Write up Rose Fyleman, her sister's school, and the house they kept it in.

A. Hagues pointed at the Thoroton Society's article on her by Sian Trafford of
Nottingham Women's History Group. The record already held the bones of it
without knowing: the 1911 schedule for 29 Newcastle Drive has Gertrude entered
as principal of a school and Rose as a vocalist on her own account.

The prose here is written from the sources, not copied from them.

One thing the two disagree about is left disagreeing, and goes into the
research questions instead of being quietly reconciled: the article says the
family moved to the house in 1912, and the 1911 census has them already in it.
"""
import os, sys
import psycopg2

ROSE, GERTRUDE, EMILIE, JOHN = 5130, 5129, 5128, 9277
HOUSE = 222

ROSE_BIO = """Rose Amy Feilmann, who wrote as Rose Fyleman, was born in Nottingham on 6 March 1877, the third of five children of John Joseph Moritz Feilmann and his wife Emilie, née Loewenstein. Both parents came from German Jewish families; Emilie's were of Russian descent. Her father was a partner in Flersheim, Feilmann & Co of St Mary's Gate in the Lace Market, a firm wound up by agreement at the end of 1884.

A singer first
She was taught at Western House Ladies' School at 30 The Ropewalk, kept by Miss Louisa Clark, and was marked out for her German in the Cambridge local examinations — unsurprising in that household. She went to University College Nottingham and left without finishing, and trained as a singer instead: Paris, Berlin and London, and a diploma from the Royal College of Music. The opera career did not come. Concert work did, and she sang as a contralto, first at a Promenade Concert at the Queen's Hall in August 1903, billed as Fräulein Rose Feilmann of Berlin.

The house, and the school in it
The 1911 census finds the family at this house, her mother at the head of it and her father dead. Her sister Gertrude is entered as principal of a school and Rose as a vocalist on her own account. The school was kept in the house; Rose taught music in it and went on performing. The address was then 10 Pelham Terrace.

When war came, a German surname was an awkward thing for a British family to carry, and the Feilmanns became the Fylemans.

Fairies at the bottom of the garden
Looking for verse fit for her pupils and not finding it, she began writing her own. 'Fairies at the Bottom of Our Garden' went to Punch in 1917 and was printed unsigned. It made her name and never afterwards let go of it. Her first book, The Sunny Book, followed in 1918, and Fairies and Chimneys the same year — reprinted twenty times inside a decade. Then The Fairy Green (1919), The Fairy Flute (1921) and Fairies and Friends (1925).

She wrote for children's stages as well: Eight Little Plays for Children (1924), Nine New Plays for Children (1934), and the libretto for Thomas Frederick Dunhill's opera Happy Families, first given in 1933. A Princess Comes to Our Town (1927) is a fairy story for grown-ups set in a Nottingham of the 1920s that can still be recognised, illustrated by Gertrude Lindsay; Five Leaves reissued it in 2023.

More than sixty volumes of verse, fiction and plays in all. She never married, and died at St Albans on 1 August 1957, aged eighty. She is buried at Golders Green.

A year that does not agree
The Thoroton Society's account has the family moving here in 1912, after her father's death. The 1911 census has them in the house already, on the night of 2 April 1911. The schedule is the earlier and the nearer witness, so the record follows it, and the difference is kept as an open question rather than smoothed over.

Sources: Sian Trafford, 'Rose Fyleman — 1877-1957, author, poet, teacher, singer, translator', Thoroton Society of Nottinghamshire newsletter article, thorotonsociety.org.uk, drawing on the research of Rowena Edlin-White; the 1901 and 1911 censuses as transcribed here; Wikipedia. Nottingham Women's History Group has been raising money for a blue plaque to her."""

GERTRUDE_BIO = """Gertrude Feilmann kept a private school in this house. The 1911 census enters her as principal of a school, employer, at home — the school was run from the family's own rooms rather than from premises of its own, which is why it leaves so little trace. Her younger sister Rose, later known as the children's poet Rose Fyleman, taught music in it while still singing professionally.

She was born in Nottingham in 1876, the eldest of the surviving daughters of John Joseph Moritz Feilmann, a Lace Market merchant, and his wife Emilie. The 1901 census has her at 14 The Ropewalk, already principal of a school at twenty-five, with her father still alive and at the head of the house. By 1911 her mother was head, the family had moved here, and the school had come with them.

Nothing is yet known of how long the school lasted, how many it taught, or what it was called.

Sources: the 1901 and 1911 censuses as transcribed here; Sian Trafford, 'Rose Fyleman', Thoroton Society of Nottinghamshire."""

HOUSE_NOTE = """Rose Fyleman lived here. The house was 10 Pelham Terrace before Newcastle Drive was renumbered, and the 1911 census finds the Feilmann family in it: Emilie Feilmann at the head, her daughter Gertrude entered as principal of a school, and her daughter Rose Amy — who as Rose Fyleman wrote 'Fairies at the Bottom of Our Garden' for Punch in 1917 — as a vocalist on her own account. Gertrude's school was kept in the house and Rose taught music in it. Her brother Max Loewenstein, a machine-made lace manufacturer, was living with them, along with a boarder and three servants."""

QUESTIONS = [
    dict(slug='feilmann-moved-in-1911-or-1912',
         title='Did the Feilmanns move to 29 Newcastle Drive in 1911 or 1912?',
         kind='house', property_id=HOUSE, priority=3,
         detail="The Thoroton Society's article on Rose Fyleman says the family moved to "
              "10 Pelham Terrace, now 29 Newcastle Drive, in 1912, after her father's death. "
              "The 1911 census has the household in the house already on 2 April 1911, with "
              "Emilie Feilmann at its head. Both cannot be right. A directory for 1911 or 1912, "
              "or a rate book, would settle it. The record follows the census for now. "
              "The address itself is not in doubt: the record's own working rule for this "
              "street - Newcastle Drive number = 39 minus the Pelham Terrace number - puts "
              "10 Pelham Terrace at 29 Newcastle Drive, which is where the article puts it too."),
    dict(slug='feilmann-at-7-cavendish-crescent-1888',
         title='Were the Feilmanns at 7 Cavendish Crescent in the 1880s?',
         kind='address', property_id=None, priority=4,
         detail="The Thoroton Society's article says the family was living at 7 Cavendish Crescent "
              "in The Park by 1888. Neither 7 Cavendish Crescent North nor South holds a Feilmann "
              "in any census transcribed here — the 1891 return for the South house has the Gibson "
              "family. A directory for the late 1880s would say which house they had and when."),
    dict(slug='when-did-john-feilmann-die',
         title='When did John Joseph Moritz Feilmann die?',
         kind='person', property_id=None, priority=4,
         detail="He is head of the house at 14 The Ropewalk in 1901 and his widow is head at "
              "29 Newcastle Drive in 1911, so he died between those two censuses. The date would "
              "fix when the family moved and settle the question above. Probate or a death notice "
              "in the Nottingham papers would give it."),
    dict(slug='gertrude-feilmann-school-name',
         title="What was Gertrude Feilmann's school called, and how long did it run?",
         kind='house', property_id=HOUSE, priority=4,
         detail="She is principal of a school in both 1901 and 1911, running it from the family's "
              "own house. A school kept at home leaves little behind. Wright's Directory lists "
              "private schools by name and street and would be the first place to look."),
]


def main():
    url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    if not url:
        print('No database URL in the environment.', file=sys.stderr)
        return 1
    c = psycopg2.connect(url)
    cur = c.cursor()

    cur.execute("""UPDATE people SET bio=%s, died_date=%s, died_year=%s, died_place=%s,
                   known_as=%s WHERE id=%s""",
                (ROSE_BIO, '1 August 1957', 1957, 'St Albans, Hertfordshire', 'Fyleman', ROSE))
    print('Rose Amy Feilmann  — biography, death 1 August 1957 at St Albans')

    cur.execute("UPDATE people SET bio=%s WHERE id=%s", (GERTRUDE_BIO, GERTRUDE))
    print('Gertrude Feilmann  — biography')

    # Her mother's forename is spelt Emilee in the article and Emilie on the
    # census. The census is what the record holds, so it stays as it is and the
    # other spelling is simply noted here rather than overwriting anything.

    made = 0
    for q in QUESTIONS:
        cur.execute("""INSERT INTO research_questions (slug, title, detail, kind, property_id,
                       priority, status, on_foot, created_by)
                       VALUES (%s,%s,%s,%s,%s,%s,'open',false,'A. Hagues and Claude')
                       ON CONFLICT (slug) DO NOTHING RETURNING id""",
                    (q['slug'], q['title'], q['detail'], q['kind'], q['property_id'], q['priority']))
        if cur.fetchone():
            made += 1
            print('question:', q['title'])
    print(f'{made} questions written')

    c.commit()
    cur.close()
    c.close()
    print('\nNow the house itself — that is a repo file, not the database.')
    return 0


if __name__ == '__main__':
    sys.exit(main())


# ── The question this answers ────────────────────────────────────────────────
# 'the-feilmann-household' was opened off the 1911 round, asking who these
# people were, which school Gertrude ran, and what a professional singer was
# doing in The Park. Most of it is now answered, so it is closed rather than
# left open beside a biography that settles it.
ANSWER = """**Answered, by the Thoroton Society's account of Rose Fyleman.**

The vocalist is **Rose Amy Feilmann (1877-1957)**, who wrote as **Rose Fyleman** and is one of the best known children's poets of the century. 'Fairies at the Bottom of Our Garden' went to Punch in 1917 and was printed unsigned; more than sixty volumes of verse, stories and plays followed, along with a libretto for Thomas Frederick Dunhill's opera Happy Families. She trained as a singer in Paris, Berlin and London, took a diploma at the Royal College of Music, and first sang at the Queen's Hall in August 1903 billed as Fräulein Rose Feilmann of Berlin. She died at St Albans on 1 August 1957 and is buried at Golders Green. Her account is on her person page.

**Gertrude's school was kept in this house** rather than in premises of its own, which is why the directories are so quiet about it. Rose taught music in it while still performing. What it was called, and how long it ran, is still open - see the question of that name.

**The name changed because of the war.** A German surname was an awkward thing for a British family to carry after 1914, and the Feilmanns became the Fylemans. That is why Rose is indexed under both.

**And the Flersheim caution resolves itself.** The father, John Joseph Moritz Feilmann, was a partner in **Flersheim, Feilmann & Co** of St Mary's Gate in the Lace Market, dissolved by agreement at the end of 1884. The two names sit together in the record because they sat together on a letterhead. They are still different families, and still should not be merged.

**Max Loewenstein's naturalisation file has not been looked for**, and the struck-out occupation on Emilie's form is still unexplained. Both are worth keeping.

Source: Sian Trafford, 'Rose Fyleman - 1877-1957, author, poet, teacher, singer, translator', Thoroton Society of Nottinghamshire, drawing on research by Rowena Edlin-White. Brought to the record by A. Hagues."""


def answer_the_household_question():
    url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    c = psycopg2.connect(url)
    cur = c.cursor()
    cur.execute("""UPDATE research_questions
                      SET answer=%s, status='answered', answered_by=%s, answered_at=NOW()
                    WHERE slug='the-feilmann-household' AND status <> 'answered'
                RETURNING id""", (ANSWER, 'A. Hagues and Claude'))
    row = cur.fetchone()
    print('answered the-feilmann-household' if row else 'already answered')
    c.commit(); cur.close(); c.close()


if __name__ == '__main__' and os.environ.get('ANSWER_ONLY'):
    answer_the_household_question()
