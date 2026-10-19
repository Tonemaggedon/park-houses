#!/usr/bin/env python3
"""Put the school in the right house, and the right year.

A. Hagues asked whether the school was at 29 Newcastle Terrace, and whether 14
The Ropewalk was a school too. Wright's Directory answers both, and the record
has held the pages since September without anybody reading them for this.

  29 Newcastle Drive, 1913-14 and 1915-16
      Loewenstein Max
      Feilmann Mrs. John
      Feilmann Miss Rose, vocalist
      Feilmann Miss Gertrude, private school      <- entered as a business

  14 The Ropewalk, 1894-95 and 1898-99
      Jno. Feilmann, of J. Flmn & Co.             <- a residence, no school

  30 The Ropewalk, 1894-95 to 1915-16
      Mrs. Louisa Clark, Western house school (boarding & day)
      then Misses Batten & Green, same school

So the school was Gertrude's own and it was kept at 29 Newcastle Drive. There
is no 29 Newcastle Terrace: Wright's only ever numbers 1 and 1a on that name,
and the record established separately that Newcastle Terrace is 1 to 13 of
Newcastle Drive. And 14 The Ropewalk was the family's house, not a school —
the school on that street was Western House at number 30, sixteen doors up,
which is where Rose herself was taught.

A. Hagues also supplies, from Find My Past: the family at 7 Regent Street in
1891, indexed there under the mangled surname Falinan; and Rose away from home
on census night 1901, boarding at 20 Montague Place, St Giles in the Fields.
"""
import os, sys
import psycopg2

ROSE, GERTRUDE = 5130, 5129

ROSE_BIO = """Rose Amy Feilmann, who wrote as Rose Fyleman, was born in Nottingham on 6 March 1877, the third of five children of John Joseph Moritz Feilmann and his wife Emilie, née Loewenstein. Both parents came from German Jewish families; Emilie's were of Russian descent. Her father was a partner in Flersheim, Feilmann & Co of St Mary's Gate in the Lace Market, a firm wound up by agreement at the end of 1884.

Where the family lived
They were at 7 Cavendish Crescent in The Park by 1888 and had left it by 1891, when they were at 7 Regent Street, just outside the estate. By 1894 Wright's Directory has her father at 14 The Ropewalk — 'Jno. Feilmann, of J. Flmn & Co.' — and the 1901 census finds the household there. They were back inside The Park by 1911, at 29 Newcastle Drive, which was 10 Pelham Terrace before the street was renumbered.

A singer first
She was taught at Western House School at 30 The Ropewalk, a boarding and day school sixteen doors from the family's own house, kept by Mrs Louisa Clark and afterwards by the Misses Batten and Green. She was marked out for her German in the Cambridge local examinations — unsurprising in that household. She went to University College Nottingham and left without finishing, and trained as a singer instead: Paris, Berlin and London, and a diploma from the Royal College of Music. The opera career did not come. Concert work did, and she sang as a contralto, first at a Promenade Concert at the Queen's Hall in August 1903, billed as Fräulein Rose Feilmann of Berlin.

She was not at home on census night in 1901. While her parents, her sister and her brother were counted at 14 The Ropewalk, she was boarding in London at 20 Montague Place, St Giles in the Fields.

The house, and the school in it
The 1911 census finds her at 29 Newcastle Drive with her mother at the head of the house and her father dead. Her sister Gertrude is entered as principal of a school and Rose as a vocalist on her own account. Wright's Directory prints the same arrangement twice over, in 1913-14 and again in 1915-16: Mrs John Feilmann, Max Loewenstein, 'Feilmann Miss Rose, vocalist' and 'Feilmann Miss Gertrude, private school'. Gertrude's school was kept in the house and Rose taught music in it while going on performing.

When war came, a German surname was an awkward thing for a British family to carry, and the Feilmanns became the Fylemans.

Fairies at the bottom of the garden
Looking for verse fit for her pupils and not finding it, she began writing her own. 'Fairies at the Bottom of Our Garden' went to Punch in 1917 and was printed unsigned. It made her name and never afterwards let go of it. Her first book, The Sunny Book, followed in 1918, and Fairies and Chimneys the same year — reprinted twenty times inside a decade. Then The Fairy Green (1919), The Fairy Flute (1921) and Fairies and Friends (1925).

She wrote for children's stages as well: Eight Little Plays for Children (1924), Nine New Plays for Children (1934), and the libretto for Thomas Frederick Dunhill's opera Happy Families, first given in 1933. A Princess Comes to Our Town (1927) is a fairy story for grown-ups set in a Nottingham of the 1920s that can still be recognised, illustrated by Gertrude Lindsay; Five Leaves reissued it in 2023.

More than sixty volumes of verse, fiction and plays in all. She never married, and died at St Albans on 1 August 1957, aged eighty. She is buried at Golders Green.

A year that does not agree
The Thoroton Society's account has the family moving to Newcastle Drive in 1912, after her father's death. The 1911 census has them in the house already, on the night of 2 April 1911. The schedule is the earlier and the nearer witness, so the record follows it, and the difference is kept as an open question rather than smoothed over.

Searching for her
The surname is indexed in several shapes. Find My Past carries the 1891 household under Falinan. The censuses here spell it Feilmann for the women and Feilman for the men, and she published as Fyleman.

Sources: Sian Trafford, 'Rose Fyleman — 1877-1957, author, poet, teacher, singer, translator', Thoroton Society of Nottinghamshire, drawing on the research of Rowena Edlin-White; Wright's Directory of Nottingham, 1894-95, 1898-99, 1913-14 and 1915-16, read from the University of Leicester scans; the 1901 and 1911 censuses as transcribed here; Find My Past, and Wikipedia. The London address and the Regent Street household were supplied by A. Hagues. Nottingham Women's History Group has been raising money for a blue plaque to her."""

GERTRUDE_BIO = """Gertrude Feilmann kept a private school at 29 Newcastle Drive, in the house her family lived in. Wright's Directory prints her there in 1913-14 and again in 1915-16 as 'Feilmann Miss Gertrude, private school', entered among the businesses rather than the residents, and the 1911 census has her as principal of a school, employer, at home. The school was run from the family's own rooms rather than from premises of its own, which is why it leaves so little behind. Her younger sister Rose, later known as the children's poet Rose Fyleman, taught music in it while still singing professionally.

She was born in Nottingham in 1876, the eldest of the surviving daughters of John Joseph Moritz Feilmann, a Lace Market merchant, and his wife Emilie. The 1901 census has her at 14 The Ropewalk, aged twenty-five, entered as a schoolmistress — not, at that date, as the principal of anything. The directory shows no school at number 14; the school on that street was Western House at number 30, a boarding and day school sixteen doors up where her sister Rose had been a pupil. Whether she taught there, or somewhere else, is not yet known.

Her own school appears once the family has moved to Newcastle Drive, and the directories never give it a name beyond 'private school'. How long it ran, and how many it taught, is still open.

Sources: Wright's Directory of Nottingham, 1894-95, 1898-99, 1910-11, 1913-14 and 1915-16; the 1901 and 1911 censuses as transcribed here; Sian Trafford, 'Rose Fyleman', Thoroton Society of Nottinghamshire."""

SCHOOL_ANSWER = """**Answered for the where, still open for the name.**

The school was at **29 Newcastle Drive**, in the family's own house, and it never seems to have had a printed name. Wright's Directory lists it twice under the plainest possible description:

| volume | entry |
|---|---|
| 1913-14 | Feilmann Miss Gertrude, **private school** — entered as a *business* |
| 1915-16 | Feilmann Miss Gertrude, **private school** |

Both volumes print the whole household at number 29 around it: Mrs John Feilmann, Max Loewenstein, and 'Feilmann Miss Rose, vocalist'. The 1911 census agrees — principal of a school, employer, **at home**.

**It was not at Newcastle Terrace.** Wright's only ever numbers **1 and 1a** on that name, and the record established separately that Newcastle Terrace is the low end of Newcastle Drive, numbers 1 to 13. There is no 29 Newcastle Terrace to put a school in.

**And 14 The Ropewalk was not a school.** The directory has the family's own house there — 'Jno. Feilmann, of J. Flmn & Co.' in 1894-95 and 1898-99 — with no school attached. The school on that street was **Western House School at number 30**, boarding and day, kept by Mrs Louisa Clark and afterwards by the Misses Batten and Green, and running under that name from at least 1894 to 1916. **Rose Fyleman was taught there**, sixteen doors from her own front door. Gertrude is a *schoolmistress* at 14 The Ropewalk in 1901, which may well mean she taught at Western House, but nothing yet says so.

**Still wanted:** a name for Gertrude's school, how long it ran, and how many it took. The volumes after 1915-16 would show when it stops."""

CAVENDISH_EXTRA = """

**Since added, from Find My Past (A. Hagues):** the family had left Cavendish Crescent by 1891 and were at **7 Regent Street**, just outside the estate. Find My Past indexes that household under the mangled surname **Falinan**, which is why an ordinary search for Feilmann does not turn it up. So the Cavendish Crescent stay was a short one, somewhere between 1888 and 1891, and a directory of those three years is the thing to look at."""


def main():
    url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    c = psycopg2.connect(url)
    cur = c.cursor()

    cur.execute("UPDATE people SET bio=%s WHERE id=%s", (ROSE_BIO, ROSE))
    print('Rose    — biography rewritten with the directory, Regent Street and Montague Place')
    cur.execute("UPDATE people SET bio=%s WHERE id=%s", (GERTRUDE_BIO, GERTRUDE))
    print('Gertrude— biography corrected: a schoolmistress in 1901, her own school later')

    cur.execute("""UPDATE research_questions
                      SET answer=%s, status='answered', answered_by=%s, answered_at=NOW()
                    WHERE slug='gertrude-feilmann-school-name' RETURNING id""",
                (SCHOOL_ANSWER, 'A. Hagues and Claude'))
    print('question answered:', 'yes' if cur.fetchone() else 'not found')

    cur.execute("""UPDATE research_questions SET detail = detail || %s, edited_at = NOW()
                    WHERE slug='feilmann-at-7-cavendish-crescent-1888'
                      AND detail NOT LIKE '%%Falinan%%' RETURNING id""", (CAVENDISH_EXTRA,))
    print('Cavendish question extended:', 'yes' if cur.fetchone() else 'already had it')

    c.commit(); cur.close(); c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
