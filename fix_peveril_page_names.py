"""Three women on the Peveril Drive pages are in the record under the married
name stamped over their entry, not the name they bore on the night.

A. Hagues sent the pages. In each case the original surname is written and then
struck through, with the later one stamped above it in capitals - and in each
case the record has taken the stamp as the name and the original as the variant,
which is the wrong way round.

The households say the same thing on their own. A daughter sitting in her
family's household carries her family's surname on the night:

  Gwen Hote is the fourth of six CARVERS at schedule 113, entered as Schofield;
  Nellie M is the fifth of five KELLS at schedule 115, entered as Goodman;
  Millicent at schedule 117 is written Powell and struck through for Taylor.

Swapping each pair puts the name borne on the night in the record and keeps the
married name as a variant - which the People search now reads, so nobody is
lost either way.
"""
import os, sys, psycopg2
apply = '--apply' in sys.argv
SWAPS = [(8759, 'Gwen Hote', 'Schofield', 'Carver', 113),
         (8769, 'Nellie M', 'Goodman', 'Kell', 115),
         (8780, 'Millicent', 'Taylor', 'Powell', 117)]
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
for pid, fn, was, now, sched in SWAPS:
    print(f"  #{pid} {fn} {was}  ->  {fn} {now}   (schedule {sched}; {was} kept as the later name)")
if apply:
    for pid, fn, was, now, sched in SWAPS:
        cur.execute("DELETE FROM person_alias WHERE person_id=%s AND LOWER(TRIM(last_name))=LOWER(%s)",
                    (pid, now))
        cur.execute("UPDATE people SET last_name=%s WHERE id=%s", (now, pid))
        cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                       SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),
                              '1939 amendment (married name)'
                         FROM (SELECT 1) t WHERE NOT EXISTS
                       (SELECT 1 FROM person_alias a WHERE LOWER(TRIM(a.first_name))=LOWER(TRIM(%s))
                          AND LOWER(TRIM(a.last_name))=LOWER(TRIM(%s)))""", (pid, fn, was, pid, fn, was))
        cur.execute("""UPDATE census_entries
                          SET source = source || ' - entered as ' || %s || ' until A. Hagues sent '
                                       'the page, which writes ' || %s || ' and strikes it through '
                                       'with ' || %s || ' stamped above. The stamp is the married '
                                       'name written in afterwards, so ' || %s || ' is the name '
                                       'borne on the night'
                        WHERE person_id=%s AND census_year=1939
                          AND source NOT ILIKE '%%which writes%%'""",
                    (f"{fn} {was}", now, was.upper(), now, pid))
    c.commit()
    print("\n  three names put the right way round")
    for pid, fn, was, now, sched in SWAPS:
        cur.execute("""SELECT p.first_name,p.last_name,STRING_AGG(a.first_name||' '||a.last_name,' / ')
                         FROM people p LEFT JOIN person_alias a ON a.person_id=p.id
                        WHERE p.id=%s GROUP BY 1,2""", (pid,))
        print("   ", cur.fetchone())
else:
    print("\n  preview only - pass --apply")
