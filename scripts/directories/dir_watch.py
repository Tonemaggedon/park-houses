"""Architects and lace makers in the whole of Wright's Directory of Nottingham.

The Park index only covers Park streets, so it cannot see somebody living in
Regent Street who later moves in. This searches every Wright's Nottingham volume
Leicester holds (1858 to 1915-16) for each watched person's own alphabetical
entry — a line that begins with their surname and whose forename or initial
agrees — and records the address it gives, flagging any that is in The Park.

usage: python3 dir_watch.py            (writes data/directory_watch.json)
Needs data/people_watch_seed.json? No: the watch list is built from the live
people list (occupations) plus a few named lace makers, below.
"""
import json, os, re, subprocess, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
B = "https://leicester.contentdm.oclc.org/digital/bl/dmwebservices/index.php?q="
SITE = "https://nottinghamparkhouses.com"

# Lace makers worth watching whether or not the record holds them yet.
EXTRA = [
    {'surname': 'Mundella', 'forename': 'Anthony John', 'group': 'lace', 'note': 'A. J. Mundella, of Hine, Mundella & Co.'},
    {'surname': 'Adams', 'forename': 'Thomas', 'group': 'lace', 'note': 'Thomas Adams, lace manufacturer'},
    {'surname': 'Heymann', 'forename': 'Lewis', 'group': 'lace', 'note': 'Lewis Heymann, lace manufacturer'},
    {'surname': 'Birkin', 'forename': 'Richard', 'group': 'lace', 'note': 'Richard Birkin, lace manufacturer'},
    {'surname': 'Birkin', 'forename': 'Thomas Isaac', 'group': 'lace', 'note': 'T. I. Birkin, lace manufacturer'},
]
# Architects the record knows by name but not as a person.
ARCH_NAMES = ['Thomas Chambers Hine', 'George Hine', 'Watson Fothergill', 'Lawrence Bright', 'Arthur Marshall',
              'Frank Littler', 'Samuel Dutton Walker', 'Robert Evans', 'Stockdale Harrison', 'Arthur North',
              # Marriott Ogle Tarbotton is in the record at 6 South Road in 1881, but as borough surveyor
              # and engineer, so the occupation test above never catches him. His son Harold designed
              # Pattishall House for Frank Hawthorn Burn in 1908 and is not in the record at all.
              'Marriott Ogle Tarbotton', 'Harold Ogle Tarbotton',
              # Born Stafford 1850; the directory prints him at 15 Newcastle Drive from
              # 1898-99 to 1915-16, so he lived on the estate as well as building on it.
              # The record already knows his later practice from two property notes —
              # Bromley and Cartwright, and Bromley, Cartwright and Waumsley — but has
              # never held the man.
              'Albert Nelson Bromley']

PARK = ['albury square', 'barrack lane', 'castle grove', 'cavendish crescent', 'cavendish cres', 'cavendish road',
        'cavendish rd', 'clare valley', 'clifton terrace', 'clinton terrace', 'clumber crescent', 'clumber cres',
        'clumber road', 'clumber rd', 'derby terrace', 'duke william', 'fishpond drive', 'fish pond', 'hamilton drive',
        'hardwick road', 'hermitage walk', 'holles crescent', 'hope drive', 'huntingdon drive', 'kenilworth road',
        'lenton avenue', 'lincoln circus', 'maxtoke road', 'newcastle circus', 'newcastle drive', 'newcastle terrace',
        'park drive', 'park ravine', 'park terrace', 'park valley', 'pelham crescent', 'peveril drive', 'tattershall',
        'the ropewalk', 'rope walk', 'tunnel road', 'western terrace', 'the park']
# Streets that run through The Park and beyond: only a "Park" beside them counts.
EDGE = ['lenton road', 'lenton rd', 'derby road', 'derby rd', 'north road', 'south road', 'park row']


def curl(u):
    return subprocess.run(['curl', '-sk', '--max-time', '60', u], capture_output=True, text=True).stdout


def search(word):
    cache = os.path.join(HERE, 'dir_pages', f'search_{word.lower()}.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    out, start = [], 1
    while True:
        try:
            d = json.loads(curl(B + f"dmQuery/p16445coll4/fulla^{urllib.parse.quote(word)}^all^and!title^nottingham^all^and"
                                   f"/title!page/title/200/{start}/0/0/0/0/json") or '{}')
        except json.JSONDecodeError:
            d = {}
        recs = d.get('records', [])
        out += recs
        if len(recs) < 200:
            break
        start += 200
    out = [r for r in out if r['title'].startswith("Wright's")]
    json.dump(out, open(cache, 'w'))
    return out


def page_text(ptr):
    f = os.path.join(HERE, 'dir_pages', f'{ptr}.txt')
    if os.path.exists(f) and os.path.getsize(f) > 0:
        return open(f).read()
    try:
        t = json.loads(curl(B + f'dmGetItemInfo/p16445coll4/{ptr}/json') or '{}').get('fulla') or ''
    except json.JSONDecodeError:
        t = ''
    t = t if isinstance(t, str) else ''
    open(f, 'w').write(t)
    return t


def park_of(addr):
    a = re.sub(r'\s+', ' ', addr.lower())
    # A same-named road elsewhere: Clumber road, West Bridgford; South road, Sherwood.
    if re.search(r'\bw\.\s?b\b|west bridgford|sherwood|basford|carrington|mapperley|beeston|wilford', a):
        return None
    for p in PARK:
        if p in a:
            return p
    for e in EDGE:
        if e in a and re.search(r'\bpark\b', a.split(e, 1)[1][:25]):
            return e + ', park'
    if re.search(r'[;,]\s*(the\s+)?park\b(?!\s*(street|st\b|road|rd\b|hill|lane|place|row|side|gate|view|avenue))', a):
        return 'park'
    return None


def watch_list():
    people = json.loads(curl(SITE + '/api/people?limit=100000') or '[]')
    out = []
    for p in people:
        occ = ' '.join(p.get('occupations') or []).lower()
        group = 'architect' if 'architect' in occ else 'lace' if ('lace' in occ and re.search(r'manufact|merchant|mfr|maker', occ)) else None
        if group and p.get('first_name') and p.get('last_name') and not p['first_name'].startswith('?'):
            out.append({'surname': p['last_name'].strip(), 'forename': p['first_name'].strip(), 'group': group,
                        'person_id': p['id'], 'born_year': p.get('born_year'), 'died_year': p.get('died_year'),
                        'properties': p.get('property_names') or []})
    for w in out:
        w['surname'] = re.sub(r'\s+(jr|sr|junior|senior)$', '', w['surname'], flags=re.I)
        w['forename'] = re.sub(r'\s+(jr|sr|junior|senior)$', '', w['forename'], flags=re.I)
    have = {(w['surname'].lower(), w['forename'].split()[0].lower()) for w in out}
    for n in ARCH_NAMES:
        *fore, sur = n.split()
        if (sur.lower(), fore[0].lower()) not in have:
            out.append({'surname': sur, 'forename': ' '.join(fore), 'group': 'architect'})
    for e in EXTRA:
        if (e['surname'].lower(), e['forename'].split()[0].lower()) not in have:
            out.append(dict(e))
    # "Evans Jr" / "Evans Sr" are one surname in a directory.
    for w in out:
        w['surname'] = re.sub(r'\s+(jr|sr|junior|senior)$', '', w['surname'], flags=re.I)
    return out


def middle_agrees(ours, printed):
    a, b = ours.lower().rstrip('.'), printed.lower().rstrip('.')
    if len(a) == 1 or len(b) == 1:
        return a[0] == b[0]                                # "Thomas C" and "Thomas Chambers" agree
    return a.startswith(b[:3]) or b.startswith(a[:3])


def own_entries(w, pages):
    sur = re.escape(w['surname'])
    fore = [f for f in re.split(r'[\s.]+', w['forename']) if f]
    first = fore[0]
    rows = []
    for rec, text in pages:
        vol = re.sub(r" - Page.*", '', rec['title'])
        m = re.search(r'(\d{4}(?:-\d\d)?)\s*$', vol)
        volume = m.group(1) if m else vol
        pg = re.search(r'Page (\d+)', rec['title'])
        for line in text.split('\n'):
            s = line.strip()
            # An alphabetical entry: the line begins with the surname, then a forename or initial.
            mm = re.match(r'^' + sur + r'\b[\s,.]+(?:(?:Mr|Mrs|Miss|Rev|Dr|Sir|Capt)\.?\s+)?([A-Za-z]+)\.?', s, re.I)
            if not mm:
                continue
            got = mm.group(1)
            if len(got) == 1 and re.match(r'\s?[a-z]{2,}', s[mm.end():]):
                continue                                   # "J oseph": a word split by the OCR, not an initial
            yr = int(re.match(r'\d{4}', volume).group(0)) if re.match(r'\d{4}', volume) else None
            if yr and w.get('born_year') and yr < w['born_year'] + 18:
                continue                                   # too young to head a directory line: a father, most likely
            if yr and w.get('died_year') and yr > w['died_year'] + 1:
                continue
            if not (got.lower().startswith(first.lower()[:3]) or (len(got) == 1 and got[0].lower() == first[0].lower())
                    or first.lower().startswith(got.lower()[:3]) and len(got) >= 3):
                continue
            # A second forename printed before the first comma must agree with the person's own.
            if len(fore) > 1:
                head = s[mm.end():].split(',')[0].split(';')[0].split('(')[0]
                nxt = re.match(r'\s*([A-Z][a-z]*)\.?\b', head)
                if nxt and nxt.group(1).lower() not in ('esq', 'mr', 'jun', 'junr', 'sen', 'j', 'jp') \
                        and not middle_agrees(fore[1], nxt.group(1)):
                    continue
            addr = s[mm.end():]
            # A trade printed straight after the name that is not this person's trade
            # ("Evans Robert, postman") is a namesake.
            chunks = [c.strip() for c in re.split(r'[,;]', addr)]
            trade_txt = next((c for c in chunks[1:3] if re.match(r"^[a-z][a-z' &.]+$", c) and not re.match(r'^(h|house|of|at|esq|jun|sen)\b', c)), None)
            ok_trade = r'architect|archt|surveyor|survyr|civil engineer' if w['group'] == 'architect' \
                else r'lace|hosier|net|curtain|yarn|embroid|manufact|mfr|merchant|agent|dresser|finisher|warehouse|trav'
            if trade_txt and not re.search(ok_trade, trade_txt):
                continue
            rows.append({'volume': volume, 'page': int(pg.group(1)) if pg else None, 'record': int(rec['pointer']),
                         'line': s[:220], 'park': park_of(addr)})
    # A common name ("John Smith") fills a volume with strangers. Where a volume holds
    # more than four lines for the name, keep only those that agree on a middle name or
    # initial, mention the person's trade, or give a Park address.
    per = {}
    for r in rows:
        per[r['volume']] = per.get(r['volume'], 0) + 1
    if rows and max(per.values()) > 4:
        w['common_name'] = True
        middle = fore[1] if len(fore) > 1 else None
        trade = r'lace|architect|surveyor' if w['group'] == 'architect' else r'lace|hosier|net|curtain|yarn|embroid'
        def telling(r):
            after = r['line'][len(w['surname']):]
            if middle and re.match(r'[\s,.]*(?:(?:Mr|Mrs|Miss)\.?\s+)?[A-Za-z]+\.?\s+' + re.escape(middle[0]) + (r'[a-z]*' if len(middle) > 1 else '') + r'\b', after):
                toks = re.findall(r'[A-Za-z]+', after)
                return len(toks) > 1 and (toks[1].lower().startswith(middle.lower()[:3]) or len(toks[1]) == 1)
            return bool(re.search(trade, r['line'], re.I)) or bool(r['park'])
        rows = [r for r in rows if telling(r)]
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (r['volume'], r['page'] or 0)):
        k = (r['volume'], re.sub(r'[^a-z]', '', r['line'].lower())[:60])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def main():
    os.makedirs(os.path.join(HERE, 'dir_pages'), exist_ok=True)
    wl = watch_list()
    print(len(wl), 'people to watch', flush=True)
    surnames = sorted({w['surname'] for w in wl})
    with ThreadPoolExecutor(4) as ex:
        hits = dict(zip(surnames, ex.map(search, surnames)))
    ptrs = sorted({int(r['pointer']) for v in hits.values() for r in v})
    print(len(ptrs), 'pages to read', flush=True)
    with ThreadPoolExecutor(10) as ex:
        texts = dict(zip(ptrs, ex.map(page_text, ptrs)))
    result = []
    for w in wl:
        pages = [(r, texts.get(int(r['pointer']), '')) for r in hits.get(w['surname'], [])]
        w['entries'] = own_entries(w, pages)
        w['first_in_park'] = next((e['volume'] for e in w['entries'] if e['park']), None)
        result.append(w)
    shared = {}
    for w in result:
        for e in w['entries']:
            shared.setdefault((e['record'], e['line']), []).append(w)
    for (rec, line), ws in shared.items():
        if len(ws) > 1:
            for w in ws:
                for e in w['entries']:
                    if e['record'] == rec and e['line'] == line:
                        e['shared_with'] = [f"{o['forename']} {o['surname']}" + (f" (b. {o['born_year']})" if o.get('born_year') else '')
                                            for o in ws if o is not w]
    result.sort(key=lambda w: (w['first_in_park'] is None, w['group'], w['surname'], w['forename']))
    doc = {'note': ("Each watched architect and lace maker's own alphabetical entries in every Wright's Directory of "
                    "Nottingham held by the University of Leicester, read from the page text (not the scans), so a line "
                    "can carry OCR damage and a namesake can slip in: every row links to its page. 'park' names the Park "
                    "street an address mentions."),
           'source': "Wright's Directory of Nottingham, 1858 to 1915-16 — University of Leicester, Special Collections Online",
           'people': result}
    json.dump(doc, open(os.path.join(REPO, 'data', 'directory_watch.json'), 'w'), indent=1, ensure_ascii=False)
    inpark = [w for w in result if w['first_in_park']]
    print(f"{len(result)} watched; {sum(1 for w in result if w['entries'])} found in a directory; {len(inpark)} with a Park address")
    for w in inpark[:40]:
        e = next(e for e in w['entries'] if e['park'])
        print(f"  {w['group']:9} {w['forename']} {w['surname']}: {w['first_in_park']} — {e['line'][:90]}")


if __name__ == '__main__':
    main()
