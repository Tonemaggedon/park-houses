# -*- coding: utf-8 -*-
"""Twenty-two people with their own Wikipedia article and no notable mark.

Found by checking who carries a wikipedia_url and significant = false, after
Jesse Boot turned out to be one of them. Applied on A. Hagues' word.

The other twenty-two that check threw up are NOT marked: eleven link to
something that is not a biography - a Wikidata number, a phone directory, a
page about a music venue - and eleven share one article with a relative, which
is not notability. Ethel Fraser lived from 1882 to 1882.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
NOTES = {
 469:  "Flying ace of the Royal Flying Corps, VC, DSO and two bars, MC; killed in action at twenty",
 386:  "One of the great travel photographers of the nineteenth century, best known for his work in India and the Himalaya",
 4717: "Nottingham architect, in practice for close to sixty years",
 752:  "Lace manufacturer, of the Dobson family of Ravine House",
 411:  "Lace dresser employing 108 hands, and a magistrate",
 1872: "Nottingham landscape painter",
 405:  "One of Nottingham's leading Victorian architects, and founder of the Nottingham Architectural Society",
 3:    "Organist, composer and conductor, a central figure in Victorian Nottingham's musical life",
 467:  "Nottingham's most distinctive Victorian architect, whose Gothic buildings still mark the city",
 5193: "Ophthalmic surgeon of the Indian Medical Service, remembered for his work on trachoma, cataract and glaucoma",
 7:    "Cricketer and rugby player, colliery director and cricket club president",
 1315: "Industrialist, lace machine builder and Member of Parliament; first Baronet",
 815:  "City architect of Nottingham",
 186:  "Solicitor, sportsman and Conservative politician in Nottingham; knighted",
 140:  "Solicitor, founder of Maples and McCraith, Justice of the Peace; knighted",
 127:  "Yarn merchant and commission agent; knighted",
 1181: "Nottingham manufacturer and public figure",
 351:  "Draper and company chairman, of James Snook & Co of Nottingham",
 285:  "Barrister and colonial administrator in West Africa; knighted",
 3121: "Politician and Fellow of the Royal Society, first Baron Belper, of the Derbyshire cotton-spinning family",
 5179: "American lawyer, Ohio Secretary of State, and United States consul at Nottingham",
 1885: "Cricketer; captain of Derbyshire",
}
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT id, COALESCE(title||' ','')||first_name||' '||last_name, significant
                 FROM people WHERE id = ANY(%s) ORDER BY last_name""", (list(NOTES),))
for pid, name, sig in cur.fetchall():
    print(f"  #{pid:<5} {name:<42} {'already marked' if sig else NOTES[pid][:60]}")
if apply:
    n = 0
    for pid, note in NOTES.items():
        cur.execute("""UPDATE people SET significant=TRUE, significant_by='A. Hagues',
                              significance_note=COALESCE(NULLIF(significance_note,''),%s)
                        WHERE id=%s AND significant IS NOT TRUE""", (note, pid))
        n += cur.rowcount
    c.commit()
    print(f"\n  {n} marked notable")
    cur.execute("SELECT count(*) FROM people WHERE significant=TRUE")
    print(f"  the record now carries {cur.fetchone()[0]} notable people")
    cur.execute("""SELECT count(*) FROM people WHERE wikipedia_url IS NOT NULL
                     AND wikipedia_url<>'' AND significant IS NOT TRUE""")
    print(f"  still with a page and no mark: {cur.fetchone()[0]}")
else:
    print("\n  preview only - pass --apply")
