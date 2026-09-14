import json, subprocess, re, os
from concurrent.futures import ThreadPoolExecutor
OFF={'1894-95':164506,'1898-99':165176,'1910-11':165676,'1913-14':166356,'1915-16':347641}
SPAN={'1894-95':(18,172),'1898-99':(18,182),'1910-11':(39,262),'1913-14':(39,272),'1915-16':(40,272)}
os.makedirs('dir_pages',exist_ok=True)
def text(ptr):
    f=f'dir_pages/{ptr}.txt'
    if os.path.exists(f) and os.path.getsize(f)>0: return open(f).read()
    u=f'https://leicester.contentdm.oclc.org/digital/bl/dmwebservices/index.php?q=dmGetItemInfo/p16445coll4/{ptr}/json'
    for _ in range(3):
        r=subprocess.run(['curl','-sk','--max-time','40',u],capture_output=True,text=True).stdout
        try:
            t=json.loads(r).get('fulla') or ''; t=t if isinstance(t,str) else ''
            open(f,'w').write(t); return t
        except Exception: pass
    return None
jobs=[(v,p) for v,(a,b) in SPAN.items() for p in range(a,b+1)]
with ThreadPoolExecutor(12) as ex: res=list(ex.map(lambda j:(j,text(OFF[j[0]]+j[1])),jobs))
out={}
for (v,p),t in res:
    if t is None: out.setdefault(v,{})[p]={'error':True}; continue
    lines=[l.strip() for l in t.split('\n') if l.strip()][:6]
    upper=[m for m in re.findall(r"\b([A-Z][A-Z' .]{3,}(?:STREET|ROAD|DRIVE|TERRACE|CRESCENT|VALLEY|RAVINE|GROVE|CIRCUS|MOUNT|WALK|AVENUE|LANE|ROW|PLACE|SQUARE|HILL|GATE|YARD|COURT|PASSAGE))\b", t)]
    out.setdefault(v,{})[p]={'top':' / '.join(lines)[:160],'headings':list(dict.fromkeys(u.strip() for u in upper))}
json.dump(out,open('dir_headers.json','w'),indent=1)
print({v:sum(1 for x in d.values() if x.get('error')) for v,d in out.items()}, 'errors per volume')
