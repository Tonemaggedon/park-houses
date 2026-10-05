"""How many unfiled records sit under a suggestion the record is confident of.

Mirrors the rule the Unfiled page uses: the top suggestion must score 10 or
more - which only a house name or former name earns - must beat the second
outright, and the group must hold exactly one household.
"""
import os, re, json, psycopg2
from collections import defaultdict
P = json.load(open('data/all_props.json'))
c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
cur = c.cursor()
cur.execute("""SELECT c.id,c.census_year,c.unresolved_address,c.relationship
                 FROM census_entries c WHERE c.property_id IS NULL ORDER BY c.id""")
rows = cur.fetchall()
def norm(s): return re.sub(r'[^a-z0-9 ]',' ', str(s or '').lower()).replace('  ',' ').strip()
def suggest(addr):
    a = norm(addr)
    if not a: return []
    out = []
    for pr in P:
        st = norm(pr.get('street')); no = str(pr.get('no') or '').strip()
        names = [norm(x) for x in ([pr.get('name'), pr.get('house_name')] +
                 str(pr.get('prev_house_name') or '').split('\n')) if norm(x) and len(norm(x)) > 3]
        score = 0; why = []
        hit = next((n for n in names if n in a), None)
        if hit: score += 10; why.append('house name' if norm(pr.get('name'))==hit or norm(pr.get('house_name'))==hit else 'former name')
        if st and st in a: score += 4; why.append('street')
        m = re.match(r'^[a-z]{0,4}(\d+)\b', a)
        if m and no and m.group(1)==no: score += 5; why.append('number')
        if score >= 4: out.append((score, pr['id'], pr.get('address') or pr.get('name'), ' + '.join(why)))
    out.sort(key=lambda x: (-x[0], x[1]))
    return out[:6]
by = defaultdict(list)
for r in rows: by[(r[2] or '').strip() or '\0none'].append(r)
conf, confrows, groups, rejected = [], 0, 0, []
for addr, es in by.items():
    groups += 1
    s = [] if addr == '\0none' else suggest(addr)
    per = defaultdict(lambda: [0,0])
    for e in es:
        rel = (e[3] or '').strip()
        if re.match(r'^head$', rel, re.I) or re.match(r'^\d+$', rel): per[e[1]][0] += 1
        if re.match(r'^wife$', rel, re.I): per[e[1]][1] += 1
    hh = max([1] + [max(v) for v in per.values()])
    streets = {norm(p.get('street')) for p in P if norm(p.get('street'))}
    astreet = next((st for st in streets if st in norm(addr)), None)
    agrees = (not astreet) or (s and norm(next((p.get('street') for p in P if p['id']==s[0][1]), '')) == astreet)
    if s and s[0][0] >= 10 and (len(s) == 1 or s[0][0] > s[1][0]) and hh == 1 and agrees:
        conf.append((len(es), addr, s[0])); confrows += len(es)
    elif s and s[0][0] >= 10 and (len(s) == 1 or s[0][0] > s[1][0]) and hh == 1:
        rejected.append((len(es), addr, s[0]))
conf.sort(reverse=True)
print(f"  {len(rows)} unfiled records in {groups} address groups")
print(f"  {len(conf)} groups are CONFIDENT, covering {confrows} records\n")
for n, addr, s in conf[:25]:
    print(f"   {n:>3}  {addr[:46]:<48} -> #{s[1]} {str(s[2])[:34]}  ({s[3]})")
if len(conf) > 25: print(f"   ... and {len(conf)-25} more")
rejected.sort(reverse=True)
print(f"\n  {len(rejected)} groups were green before and are not now - the street contradicts the name:")
for n,addr,s2 in rejected:
    print(f"   {n:>3}  {addr[:44]:<46} -> #{s2[1]} {str(s2[2])[:36]}")
