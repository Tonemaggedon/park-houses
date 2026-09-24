import json, glob, re, sys, os, psycopg2
ROOT='/Users/antonyhagues/Claude Projects/park-houses'
WRITE='--write' in sys.argv
c=psycopg2.connect(os.environ['DATABASE_PUBLIC_URL']); cur=c.cursor()
cur.execute("select lower(trim(first_name)), lower(trim(last_name)) from people")
HELD=set(cur.fetchall())
ABBR={'elizth':'Elizabeth','eliz':'Elizabeth','wm':'William','chas':'Charles','thos':'Thomas',
 'jno':'John','geo':'George','robt':'Robert','fredk':'Frederick','edwd':'Edward','margt':'Margaret',
 'saml':'Samuel','jas':'James','gert':'Gertrude','adelade':'Adelaide',
 'caarine':'Catharine','benj':'Benjamin','danl':'Daniel','alexr':'Alexander','richd':'Richard',
 'matw':'Matthew','hy':'Henry'}
def fix(fn):
    parts=re.split(r'(\s+)', fn.strip()); out=[]; ch=False
    for p in parts:
        if not p.strip(): out.append(p); continue
        bare=p.rstrip('.').lower()
        if bare in ABBR: out.append(ABBR[bare]); ch=True
        else: out.append(p)
    return ''.join(out), ch
safe=0; held_back=0; files=0
for fp in sorted(glob.glob(f'{ROOT}/data/people_*.json')):
    doc=json.load(open(fp)); ppl=doc.get('people') if isinstance(doc,dict) else doc
    if not isinstance(ppl,list): continue
    did=[]
    for p in ppl:
        if not isinstance(p,dict): continue
        fn,ln=p.get('first_name'),p.get('last_name')
        if not fn or not ln: continue
        new,ch=fix(fn)
        if not ch: continue
        k_new=(new.lower().strip(), ln.lower().strip())
        k_old=(fn.lower().strip(), ln.lower().strip())
        # Safe when the record already holds the expanded name (the rename makes the
        # file meet the person it should have met), or holds neither form.
        if k_new in HELD or k_old not in HELD:
            p['first_name']=new; did.append((fn,new,'record holds the full name' if k_new in HELD else 'record holds neither')); safe+=1
        else:
            held_back+=1
            print(f'  HELD BACK  {os.path.basename(fp)}: {fn} {ln} -> {new} (record has only the short form)')
    if did:
        files+=1
        if WRITE:
            if isinstance(doc,dict): doc['people']=ppl
            json.dump(doc, open(fp,'w'), indent=1, ensure_ascii=False); open(fp,'a').write('\n')
print(f'\nsafe to expand: {safe} in {files} files   held back: {held_back}')
