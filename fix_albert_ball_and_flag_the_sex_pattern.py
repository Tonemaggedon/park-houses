#!/usr/bin/env python3
"""Albert Ball VC is marked female, and he is not the only one.

Found while building the women's walk, which selects on people.sex and would
otherwise have opened with the most famous airman of the First World War.

The one certain correction is made here. The pattern behind it is measured and
written up as a question for the Forename sex page rather than bulk-changed,
because deciding a person's sex from their forename is exactly the judgement
that page exists to make one name at a time.
"""
import os, sys, psycopg2

c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()

cur.execute("UPDATE people SET sex='M' WHERE id=469 AND sex='F' RETURNING first_name, last_name")
r = cur.fetchone()
print('corrected:', ' '.join(r) if r else 'already M')

# How far does this go? Names the record reads as male far more often than female.
cur.execute("""
  WITH f AS (SELECT LOWER(SPLIT_PART(first_name,' ',1)) nm,
               COUNT(*) FILTER (WHERE sex='M')::int m,
               COUNT(*) FILTER (WHERE sex='F')::int f
               FROM people WHERE sex IN ('M','F') GROUP BY 1)
  SELECT nm, m, f FROM f WHERE m >= 10 AND f > 0 AND f::float / (m + f) < 0.34
   ORDER BY f DESC, m DESC LIMIT 25""")
rows = cur.fetchall()
total = sum(x[2] for x in rows)
print(f'\n{len(rows)} forenames the record reads as male 2:1 or better, with {total} people on the female side:')
for nm, m, fem in rows[:15]:
    print(f'  {nm:<14} {m:>4} male  {fem:>3} female')

DETAIL = ("Building the women's walk turned up **Albert Ball VC marked female** — the most famous "
  "airman of the First World War, who would have opened the walk. That one is corrected.\n\n"
  "**It is not an isolated slip.** Taking only forenames the record itself reads as male at least "
  "twice as often as female, and only where there are ten or more men to judge by:\n\n"
  "| forename | read as male | read as female |\n|---|---|---|\n"
  + '\n'.join(f'| {nm} | {m} | **{fem}** |' for nm, m, fem in rows[:12])
  + f"\n\nThat is **{total} people** across {len(rows)} names, and most of them are probably wrong. "
  "Most will have come in from a census transcription where the sex column was blank or misread.\n\n"
  "**Not bulk-changed, deliberately.** Some of these are real — Sidney, Leslie and Evelyn were all "
  "given to girls in this period, and the record holds at least one woman christened William May. "
  "Deciding from a forename is exactly the judgement the **Forename sex** page exists to make one "
  "name at a time, and it already orders them by how much work each click does.\n\n"
  "**What this costs if left.** Sex drives the women's walk, the Origins page and any count of who "
  "worked at what. A man filed as a woman is invisible until something like this walks into him.\n\n"
  "**Where to start:** the names above, highest female count first, on the Forename sex page — then "
  "the individuals, since a name can be right in general and wrong on one person, which is what "
  "happened to Albert Ball.")

cur.execute("""INSERT INTO research_questions (slug, title, detail, kind, priority, status, on_foot, created_by)
  VALUES ('forenames-read-as-the-wrong-sex',
          'Albert Ball VC is marked female, and about a hundred others may be too',
          %s, 'person', 5, 'open', false, 'Claude')
  ON CONFLICT (slug) DO UPDATE SET detail=EXCLUDED.detail, edited_at=NOW() RETURNING id""", (DETAIL,))
print('\nquestion written:', cur.fetchone()[0])
c.commit(); cur.close(); c.close()
