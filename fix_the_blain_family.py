# -*- coding: utf-8 -*-
"""The Blanns of 17 Cavendish Crescent South are the Blains.

A. Hagues: "william a blann and his family are in fact Sir William Arbuthnot
Blain, President of the Nottingham Savings Bank". The surname is a misreading -
nn for in - and the head of the household is a knight the record did not know
it held.

**Which of the two.** The 1881 household has two William A Blanns, father and
son. *Who Was Who* and the genealogical record give Sir William Arbuthnot Blain
as born about May 1830 at Grimsby and dying on 11 February 1911, which is the
**father** - 50 years old in the 1881 census and returned there as a wholesale
grocer and magistrate. The son, 18 in 1881, is a different man and keeps his
initial.

**What he was.** Knighted in 1897. President of the Nottingham Savings Bank,
president of the Conservative Association, acting chairman of the High School,
and on the directorate of the Nottingham and District Bank by 1898. *Who Was
Who* gives his address simply as The Park, Nottingham.

Sources: Who Was Who, by way of wikitree.com/wiki/Blain-129; and Nottingham &
Notts Illustrated, "Up-to-Date" Commercial Sketches, 1898, at
nottshistory.org.uk.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
FAMILY = [(6980, 'William Arbuthnot', 'William A'), (6981, 'Harriett A', None),
          (6982, 'Annie M', None), (6983, 'William A', None)]
BIO = (
 "Wholesale grocer, magistrate, and president of the Nottingham Savings Bank.\n\n"
 "Born at Grimsby in Lincolnshire about May 1830. The 1881 census finds him at **17 Cavendish "
 "Crescent South**, 50 years old and returned as a wholesale grocer and magistrate, with his wife "
 "Harriett A, their daughter Annie M of 21 and their son William A of 18.\n\n"
 "He was **knighted in 1897**. Besides the Savings Bank he was president of the Conservative "
 "Association and acting chairman of the High School, and by 1898 he sat on the directorate of "
 "the Nottingham and District Bank. *Who Was Who* gives his address as simply The Park, "
 "Nottingham. He died on 11 February 1911.\n\n"
 "The record held him as **William A Blann** until A. Hagues corrected the reading: the surname "
 "is Blain, and the A is Arbuthnot."
)

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for pid, fn, oldfn in FAMILY:
    cur.execute("SELECT first_name,last_name,born_year FROM people WHERE id=%s", (pid,))
    print(f"  #{pid} {cur.fetchone()} -> {fn} Blain")
if apply:
    for pid, fn, oldfn in FAMILY:
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT %s, (SELECT first_name FROM people WHERE id=%s), 'Blann',
                              (SELECT born_year FROM people WHERE id=%s), 'A. Hagues'
                         FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a
                         WHERE LOWER(TRIM(a.first_name))=LOWER((SELECT first_name FROM people WHERE id=%s))
                           AND LOWER(TRIM(a.last_name))='blann')""", (pid, pid, pid, pid))
        cur.execute("UPDATE people SET first_name=%s, last_name='Blain' WHERE id=%s", (fn, pid))
        cur.execute("""UPDATE census_entries
                          SET source = source || ' - the surname is read Blann in the index and in '
                                'the record until now; A. Hagues gives it as BLAIN, and the head of '
                                'this household as Sir William Arbuthnot Blain, president of the '
                                'Nottingham Savings Bank'
                        WHERE person_id=%s AND source NOT ILIKE '%%BLAIN%%'""", (pid,))
    cur.execute("""UPDATE people
                      SET title='Sir', born_year=1830, died_date='11 February 1911', died_year=1911,
                          born_place='Grimsby, Lincolnshire', bio=%s,
                          significant=TRUE, significant_by='A. Hagues',
                          significance_note='Knighted 1897; president of the Nottingham Savings Bank'
                    WHERE id=6980""", (BIO,))
    for fn, ln in (('William Arbuthnot', 'Blane'), ('W A', 'Blain'), ('Sir William', 'Blain')):
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT 6980,%s,%s,1830,'A. Hagues' FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(%s)
                          AND LOWER(TRIM(a.last_name))=LOWER(%s))""", (fn, ln, fn, ln))
    cur.execute("""INSERT INTO occupations (person_id, occupation)
                   SELECT 6980, x FROM unnest(ARRAY['Wholesale grocer','Magistrate',
                          'President of the Nottingham Savings Bank','Bank director']) x
                    WHERE NOT EXISTS (SELECT 1 FROM occupations o WHERE o.person_id=6980
                                        AND o.occupation='Magistrate')""")
    c.commit()
    print("\n  renamed, and Sir William Arbuthnot Blain written up")
    cur.execute("""SELECT p.id,p.title,p.first_name,p.last_name,p.born_year,p.died_year,p.significant,
                          STRING_AGG(a.first_name||' '||a.last_name,' / ')
                     FROM people p LEFT JOIN person_alias a ON a.person_id=p.id
                    WHERE p.id IN (6980,6981,6982,6983) GROUP BY 1,2,3,4,5,6,7 ORDER BY 1""")
    for r in cur.fetchall(): print("   ", r)
else:
    print("\n  preview only - pass --apply")
