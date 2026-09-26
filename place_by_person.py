#!/usr/bin/env python3
"""
Unfiled households whose own people are already at a known house in another round.

A head of house who appears at 8 Lenton Road in 1911, 1921 and 1939 was very
probably at 8 Lenton Road in 1901 too, and that places a household the census
page left unnumbered.

But people move, and name-matching alone will cheerfully carry a household
across the estate: William A Patterson matches 4 The Ropewalk from 1881, while
the 1871 walk puts him near 22. So a match is only called DEFINITE when all four
of these hold:

  * the HEAD of the household is the one matched, not a servant
  * the candidate house holds nobody else in that round
  * no other house is competing for the same household
  * the STREET the page itself gives agrees with that house's street

The last one does the work. It cut the first run from twelve confident-looking
placements to five, and three of the seven it removed were plainly wrong.

It reports and changes nothing.

Usage:
  railway run python3 place_by_person.py
"""

import os, re, sys, json, psycopg2
from collections import defaultdict
c=psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL']); cur=c.cursor()
PROPS={p['id']:dict(p) for p in json.load(open('data/all_props.json'))}

def district(src):
    m=re.search(r'schedule [^,]*? in the (.+?) district', str(src or '')); return m.group(1) if m else ''

cur.execute("""SELECT c.id, c.census_year, c.census_household_num, c.property_id,
                      COALESCE(c.unresolved_address,''), c.relationship, c.age_at_census,
                      p.id, p.first_name, p.last_name, c.source, c.occupation_at_census
               FROM census_entries c JOIN people p ON p.id=c.person_id""")
rows=cur.fetchall()

# every person's KNOWN houses, by round
known=defaultdict(list)
for (cid,yr,sched,pid,unres,rel,age,per,fn,ln,src,occ) in rows:
    if pid: known[per].append((yr,pid,age))

# unfiled households
H={}
for (cid,yr,sched,pid,unres,rel,age,per,fn,ln,src,occ) in rows:
    key=(yr,sched,district(src)) if sched is not None else (yr,'A',(unres or '').lower())
    h=H.setdefault(key,dict(yr=yr,sched=sched,people=[],filed=0,head=None,unres=''))
    h['people'].append((per,fn,ln,rel,age,occ))
    if pid: h['filed']+=1
    if (rel or '').lower()=='head': h['head']=(per,fn,ln,age,occ)
    if unres and not h['unres']: h['unres']=unres

out=[]
for key,h in H.items():
    if h['filed'] or not h['people']: continue
    votes=defaultdict(list)
    for (per,fn,ln,rel,age,occ) in h['people']:
        for (kyr,kpid,kage) in known.get(per,[]):
            if kyr==h['yr']: continue
            # an age must advance with the years, within the usual census wobble
            ok = (age is None or kage is None or abs((kage-age)-(kyr-h['yr']))<=3)
            votes[kpid].append((fn+' '+ln, kyr, ok, rel))
    if not votes: continue
    best=max(votes, key=lambda p: (sum(1 for v in votes[p] if v[2]), len(votes[p])))
    good=[v for v in votes[best] if v[2]]
    if not good: continue
    # is that house free in this round?
    cur.execute("SELECT COUNT(*) FROM census_entries WHERE property_id=%s AND census_year=%s",(best,h['yr']))
    taken=cur.fetchone()[0]
    headmatch = any(v[3] and v[3].lower()=='head' for v in good)
    out.append(dict(yr=h['yr'],sched=h['sched'],n=len(h['people']),
                    head=(h['head'][1]+' '+h['head'][2]) if h['head'] else '?',
                    unres=h['unres'],pid=best,addr=PROPS.get(best,{}).get('address',''),
                    nmatch=len(good),rounds=sorted({v[1] for v in good}),taken=taken,
                    headmatch=headmatch,who=[v[0] for v in good][:4],
                    others=len([p for p in votes if p!=best])))

# A man at a house in 1911 was not necessarily there in 1901 - people move, and
# name-matching alone will happily move a household across the estate. The test
# that separates a real placement from a coincidence is whether the STREET the
# page itself gives agrees with the street of the candidate house.
def street_of(t):
    t=re.sub(r'\([^)]*\)',' ',t or '')
    t=re.sub(r'^\s*\d+[a-z]?\s+','',t.strip(),flags=re.I)
    t=re.split(r'\s*[-,]\s*',t)[0]
    return re.sub(r'[^a-z ]','',t.lower()).strip()
for o in out:
    ps=(PROPS.get(o['pid'],{}).get('street') or '').lower().strip()
    us=street_of(o['unres'])
    o['street_ok'] = bool(us and ps and (us==ps or us in ps or ps in us))
    o['street_said'] = us or '(none given)'
strong=[o for o in out if o['headmatch'] and not o['taken'] and o['others']==0 and o['street_ok']]
weak=[o for o in out if o not in strong]
print(f"UNFILED HOUSEHOLDS WHOSE PEOPLE APPEAR AT A KNOWN HOUSE ELSEWHERE: {len(out)}\n")
print(f"── DEFINITE: head at that house in another round, house free, nothing competing, AND the page's own street agrees ({len(strong)}) ──")
for o in sorted(strong,key=lambda x:(x['yr'],x['sched'] or 0)):
    print(f"  {o['yr']} sched {str(o['sched']):>4} {o['head'][:24]:24} n={o['n']:>2} -> #{o['pid']:<4} {o['addr'][:34]:34} via {o['rounds']}")
    print(f"        page says: {o['unres'][:60]}")
print(f"\n── WORTH A LOOK ({len(weak)}) ──")
weak=[o for o in weak if o['headmatch'] and o['nmatch']>=2]
for o in sorted(weak,key=lambda x:(-x['nmatch'],x['yr']))[:20]:
    flag=[]
    if o['taken']: flag.append(f"house already holds {o['taken']} in {o['yr']}")
    if not o['headmatch']: flag.append("not the head")
    if o['others']: flag.append(f"{o['others']} other houses in play")
    if not o['street_ok']: flag.append(f"page says {o['street_said']}, house is on {(PROPS.get(o['pid'],{}).get('street') or '?').lower()}")
    print(f"  {o['yr']} sched {str(o['sched']):>4} {o['head'][:22]:22} n={o['n']:>2} -> #{o['pid']:<4} {o['addr'][:30]:30} {o['nmatch']} match  [{'; '.join(flag)}]")
