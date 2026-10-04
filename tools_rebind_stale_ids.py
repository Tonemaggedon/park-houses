"""Every import file that names a person by a number which no longer exists.

A number goes stale when two people are found to be one and the copy is folded
away - the file still points at the copy, the importer cannot find it, and
everything that entry carries is lost in silence behind a warning.

Two ways to resolve it, both safe:

  * exactly one person in the record bears that exact name, and any birth year
    the file states agrees - then that is who the entry meant;
  * nobody bears the name, but exactly one person carries it as a former name,
    which is what a fold leaves behind - then that is who they became.

Anything else is left alone and printed. The number is never simply deleted:
an entry with no number and no match is made afresh by the importer, which
would rebuild the duplicate the fold was done to remove.
"""
import os, glob, json, sys, psycopg2
apply = '--apply' in sys.argv
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("SELECT id FROM people"); alive = {r[0] for r in cur.fetchall()}
cur.execute("SELECT id, TRIM(first_name), TRIM(last_name), born_year FROM people")
byname = {}
for pid, fn, ln, by in cur.fetchall(): byname.setdefault((fn.lower(), ln.lower()), []).append((pid, by))
cur.execute("SELECT person_id, TRIM(first_name), TRIM(last_name) FROM person_alias")
byalias = {}
for pid, fn, ln in cur.fetchall(): byalias.setdefault((fn.lower(), ln.lower()), set()).add(pid)

fixed, viaalias, left = [], [], []
for path in sorted(glob.glob('data/people_*.json')):
    doc = json.load(open(path)); touched = False
    for q in doc.get('people', []):
        pid = q.get('id')
        if not isinstance(pid, int) or pid in alive: continue
        fn = str(q.get('first_name') or '').strip(); ln = str(q.get('last_name') or '').strip()
        key = (fn.lower(), ln.lower()); name = f"{fn} {ln}"; f = os.path.basename(path)
        cands = byname.get(key, [])
        want = q.get('born_year')
        if want: cands = [x for x in cands if x[1] == want] or cands
        if len(cands) == 1:
            q['id'] = cands[0][0]; touched = True
            fixed.append(f"{f}: #{pid} {name} -> #{cands[0][0]}")
            continue
        al = byalias.get(key, set())
        if not cands and len(al) == 1:
            new = next(iter(al)); q['id'] = new; touched = True
            viaalias.append(f"{f}: #{pid} {name} -> #{new}, who now carries that as a former name")
            continue
        left.append(f"{f}: #{pid} {name} - {len(cands)} by name, {len(al)} by former name; left alone")
    if touched and apply: json.dump(doc, open(path, 'w'), indent=1, ensure_ascii=False)

print(f"== rebound by name: {len(fixed)} ==")
for x in fixed[:8]: print("  ", x)
if len(fixed) > 8: print(f"   ... and {len(fixed)-8} more")
print(f"\n== rebound through a former name: {len(viaalias)} ==")
for x in viaalias: print("  ", x)
print(f"\n== left alone for a person to decide: {len(left)} ==")
for x in left: print("  ", x)
print("\n  written" if apply else "\n  preview only - pass --apply")
