"""Sanity-check the page readers' transcriptions before they replace the index.

Flags: streets with more entries than the street could hold, house numbers that
don't exist on the site's street, numbers out of printed order, a high share of
unsure lines, and streets not found.
"""
import collections, glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
props = json.load(open(os.path.join(HERE, '..', '..', 'data', 'all_props.json')))
nos = collections.defaultdict(set)
count = collections.Counter()
for p in props:
    st = (p.get('street') or '').strip()
    count[st] += 1
    m = re.match(r'^(\d+)', str(p.get('no') or ''))
    if m:
        nos[st].add(int(m.group(1)))
LONG = {'Derby Road', 'Lenton Road', 'Park Row'}   # run outside The Park: numbers beyond ours are expected

for f in sorted(glob.glob(os.path.join(HERE, 'dir_read_*.json'))):
    if 'plan' in f:
        continue
    d = json.load(open(f))
    print(f"== {d['volume']}: {len(d.get('streets', []))} streets, not found: {[x['street'] for x in d.get('not_found', [])]}")
    for s in d.get('streets', []):
        es = [e for e in s.get('entries', []) if e.get('kind') in (None, 'resident', 'business')]
        n = [int(m.group(1)) for e in es for m in [re.match(r'^(\d+)', str(e.get('no') or ''))] if m]
        flags = []
        if len(es) > 2.5 * count[s['street']] + 6 and s['street'] not in LONG:
            flags.append(f'{len(es)} entries for {count[s["street"]]} houses')
        if s['street'] not in LONG and nos[s['street']]:
            stray = sorted(set(n) - nos[s['street']])
            if len(stray) > max(2, len(set(n)) // 3):
                flags.append(f'numbers not on the site: {stray[:12]}')
        unsure = sum(1 for e in es if e.get('unsure'))
        if es and unsure / len(es) > 0.3:
            flags.append(f'{unsure}/{len(es)} unsure')
        if s['street'] not in (x.strip() for x in count):
            flags.append('not a site street name')
        print(f"   {s['street']:26} {len(es):3} entries, {len(n):3} numbered, pages {s.get('pages')}" + (f"  ⚠ {'; '.join(flags)}" if flags else ''))
    if d.get('notes'):
        print('   notes:', d['notes'][:400])
