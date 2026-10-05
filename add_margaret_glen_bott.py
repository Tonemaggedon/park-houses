# -*- coding: utf-8 -*-
"""Margaret Stote Glen Bott, 2 Newcastle Circus from 1916.

A. Hagues sent the Wikipedia article. She was living in The Park at 2 Newcastle
Circus when she came to Nottingham in 1916, and the record had never held her.

She is recorded as a resident rather than a census row: the 1916 date falls
between the 1911 and 1921 rounds, and the record holds no round for 2 Newcastle
Circus before 1939.

**She also bears on an open question.** She came to nurse wounded soldiers at
**Nottingham General Hospital**, which stood on Standard Hill - the hospital
the record has been guessing at for the nine house officers who filled
**Broxtowe House** on census night in 1921, four of them women. She is not one
of the nine; by 1921 she had moved to 9 Wellington Circus. But she puts a woman
doctor of exactly that generation at that hospital, living in The Park, five
years earlier.
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
NEWCASTLE2 = 203
BIO = (
 "Physician and surgeon, and one of the first women to hold a surgical post in Nottingham.\n\n"
 "Born at Bolton in 1891, the daughter of Alexander Glen Bott, a clergyman, and Mina Stote - "
 "her mother's surname is the Stote in her own. She came to Nottingham in 1916 to nurse soldiers "
 "wounded in the First World War at the General Hospital on Standard Hill, and lived at **2 "
 "Newcastle Circus in The Park** while she did it. By 1920 she had moved to 9 Wellington Circus "
 "and was practising as a surgeon, and from 1925 she was at 15 Regent Street, where the 1939 "
 "Register still finds her.\n\n"
 "She specialised in gynaecology, became a Fellow of the Royal College of Obstetricians and "
 "Gynaecologists, and was **the first woman surgeon at the Nottingham Women's Hospital**. She was "
 "made a city magistrate in 1937, sat as a Conservative city councillor for Mapperley from 1939 "
 "to 1958, became an alderman in 1956, and was appointed OBE in 1961. She died in 1969.\n\n"
 "The Margaret Glen-Bott School in Wollaton carries her name."
)


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    cur.execute("""SELECT id FROM people WHERE LOWER(TRIM(first_name))='margaret stote'
                     AND LOWER(TRIM(last_name))='glen bott'""")
    got = cur.fetchone()
    if got:
        print(f"  already in the record as #{got[0]}"); return
    print("  Margaret Stote Glen Bott, 1891-1969 - not in the record")
    print(f"  to be linked as a resident of 2 Newcastle Circus (#{NEWCASTLE2}) from 1916")
    if not APPLY:
        print("\n  preview only - pass --apply"); return
    cur.execute("""INSERT INTO people (first_name, last_name, sex, born_year, died_year, bio,
                                       wikipedia_url, significant, significant_by, significance_note)
                   VALUES ('Margaret Stote','Glen Bott','F',1891,1969,%s,
                           'https://en.wikipedia.org/wiki/Margaret_Glen_Bott', TRUE, 'A. Hagues',
                           'Surgeon and gynaecologist, the first woman surgeon at the Nottingham Women''s Hospital, and an alderman of the city')
                   RETURNING id""", (BIO,))
    pid = cur.fetchone()[0]
    print(f"  added as #{pid}")
    for fn, ln in (('Margaret', 'Glen-Bott'), ('Margaret Stote', 'Glen-Bott'), ('Margaret', 'Glen Bott')):
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT %s,%s,%s,1891,'A. Hagues' FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(%s)
                          AND LOWER(TRIM(a.last_name))=LOWER(%s))""", (pid, fn, ln, fn, ln))
    cur.execute("""INSERT INTO property_residents (property_id, person_id, from_year, notes)
                   VALUES (%s,%s,1916,'Living here when she came to Nottingham in 1916 to nurse '
                           'soldiers wounded in the war, at the General Hospital on Standard Hill. '
                           'She had moved to 9 Wellington Circus by 1920. Recorded as a resident '
                           'rather than a census row: 1916 falls between the 1911 and 1921 rounds, '
                           'and the record holds no round for this house before 1939.')""",
                (NEWCASTLE2, pid))
    cur.execute("""INSERT INTO occupations (person_id, occupation)
                   SELECT %s, x FROM unnest(ARRAY['Surgeon','Gynaecologist','Physician',
                                                  'City magistrate','City councillor','Alderman']) x
                    WHERE NOT EXISTS (SELECT 1 FROM occupations o WHERE o.person_id=%s)""", (pid, pid))
    c.commit()
    print("  resident link, variants and occupations written")


if __name__ == '__main__':
    main()
