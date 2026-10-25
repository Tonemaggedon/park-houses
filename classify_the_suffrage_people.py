#!/usr/bin/env python3
"""Give everybody already marked for suffrage the classification, in one word.

It was being carried five different ways at once — as an occupation spelt
Suffragist, suffragist, Suffrage, suffrage supporter and Secretary Suffrage;
as a line in a biography; as a link to the Nottingham Women's History Group
article; and as a note on a house. None of those group, none of them count,
and none of them can be searched for as one thing.

The occupations are left exactly where they are. An occupation is what the
census said somebody did and is not ours to tidy away — 'Secretary of the
Nottingham branch of the Friends League for Women's Suffrage' is a real post
and belongs on the record as written. The classification sits beside it.
"""
import os, sys, psycopg2

FIND = """
  SELECT p.id, p.first_name, p.last_name, p.sex,
     (SELECT STRING_AGG(o.occupation, '; ') FROM occupations o
       WHERE o.person_id = p.id AND o.occupation ILIKE '%%suffrag%%') AS occ,
     p.bio ILIKE '%%Park News%%' AS park_news,
     EXISTS (SELECT 1 FROM person_links l WHERE l.person_id = p.id
              AND l.url ILIKE '%%Park-Suffragists%%') AS linked,
     p.significance_note ILIKE '%%suffrag%%' AS notable
    FROM people p
   WHERE p.bio ILIKE '%%suffrag%%' OR p.bio ILIKE '%%Park News%%'
      OR p.significance_note ILIKE '%%suffrag%%'
      OR EXISTS (SELECT 1 FROM occupations o WHERE o.person_id = p.id AND o.occupation ILIKE '%%suffrag%%')
      OR EXISTS (SELECT 1 FROM person_links l WHERE l.person_id = p.id AND l.url ILIKE '%%Park-Suffragists%%')
      OR EXISTS (SELECT 1 FROM property_residents r WHERE r.person_id = p.id AND r.notes ILIKE '%%Park News%%')
   ORDER BY p.sex, p.last_name, p.first_name"""


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    # The server makes this on boot; make it here too so the classifying can be
    # done before the deploy rather than after it.
    cur.execute("""CREATE TABLE IF NOT EXISTS person_tags (
      id SERIAL PRIMARY KEY,
      person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
      tag TEXT NOT NULL,
      note TEXT,
      added_by TEXT,
      added_at TIMESTAMPTZ DEFAULT NOW(),
      UNIQUE (person_id, tag))""")
    cur.execute('CREATE INDEX IF NOT EXISTS person_tags_tag_idx ON person_tags(tag)')
    c.commit()

    cur.execute(FIND)
    rows = cur.fetchall()

    added = 0
    for pid, first, last, sex, occ, park_news, linked, notable in rows:
        why = []
        if occ:        why.append('entered as an occupation: ' + occ)
        if notable:    why.append('named in the significance note')
        if park_news:  why.append("named in David S Stewart, 'A Century of Women's Suffrage', Park News, pp. 9-11")
        if linked:     why.append('linked to the Nottingham Women’s History Group article')
        note = 'Classified from what the record already held — ' + '; '.join(why) + '.'
        cur.execute("""INSERT INTO person_tags (person_id, tag, note, added_by)
                       VALUES (%s, 'Suffrage', %s, 'A. Hagues and Claude')
                       ON CONFLICT (person_id, tag) DO NOTHING RETURNING id""", (pid, note))
        if cur.fetchone():
            added += 1
            print(f"  {sex}  {(first + ' ' + last):<30} {('#' + str(pid)):<7} {(occ or '')[:46]}")

    c.commit()
    cur.execute("""SELECT p.sex, COUNT(*)::int FROM person_tags t JOIN people p ON p.id = t.person_id
                    WHERE t.tag = 'Suffrage' GROUP BY p.sex ORDER BY p.sex""")
    tally = dict(cur.fetchall())
    print(f"\n{added} newly classified. Suffrage now holds "
          f"{tally.get('F', 0)} women and {tally.get('M', 0)} men.")
    cur.close(); c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
