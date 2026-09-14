"""Turn the page readers' transcriptions (dir_read_<volume>.json) into
data/directory_park_entries.json, the index the site reads.

Only volumes that have a transcription are replaced; any volume without one keeps
the entries the OCR reader produced, so a half-finished run never loses data.
"""
import datetime, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
OFF = {'1894-95': 164506, '1898-99': 165176, '1910-11': 165676, '1913-14': 166356, '1915-16': 347641}
YEAR = {'1894-95': 1894, '1898-99': 1898, '1910-11': 1910, '1913-14': 1913, '1915-16': 1915}
LONG = {'Derby Road', 'Lenton Road', 'Park Row'}
SITE_NOS = {}
for _p in json.load(open(os.path.join(REPO, 'data/all_props.json'))):
    _m = re.match(r'^(\d+)', str(_p.get('no') or ''))
    if _m:
        SITE_NOS.setdefault((_p.get('street') or '').strip(), set()).add(int(_m.group(1)))
norm = lambda v: re.sub(r'[^a-z]', '', str(v or '').lower().replace('house', ''))
SITE_NAMES = {}
for _p in json.load(open(os.path.join(REPO, 'data/all_props.json'))):
    for _n in [_p.get('name'), *str(_p.get('prev_house_name') or '').split('\n')]:
        if norm(_n):
            SITE_NAMES.setdefault((_p.get('street') or '').strip(), set()).add(norm(_n))
STREETS = {(p.get('street') or '').strip() for p in json.load(open(os.path.join(REPO, 'data/all_props.json')))} - {''}

TITLES = r"(mr|mrs|miss|misses|messrs|dr|rev|revd|sir|lady|capt|captain|col|colonel|major|ald|alderman|prof|the hon|hon)\.?"
FORENAMES = {'jno': 'John', 'wm': 'William', 'thos': 'Thomas', 'ths': 'Thomas', 'jas': 'James', 'geo': 'George',
             'chas': 'Charles', 'hy': 'Henry', 'edw': 'Edward', 'edwd': 'Edward', 'rd': 'Richard', 'richd': 'Richard',
             'robt': 'Robert', 'rbt': 'Robert', 'saml': 'Samuel', 'sml': 'Samuel', 'jos': 'Joseph', 'jph': 'Joseph',
             'benj': 'Benjamin', 'fredk': 'Frederick', 'fdk': 'Frederick', 'fred': 'Frederick', 'alfd': 'Alfred',
             'albt': 'Albert', 'arth': 'Arthur', 'danl': 'Daniel', 'dnl': 'Daniel', 'eliz': 'Elizabeth',
             'elzh': 'Elizabeth', 'hn': 'Hannah', 'wltr': 'Walter', 'fras': 'Francis', 'frs': 'Francis'}


def split_name(name, surname_first):
    """(surname, forename) from a directory name; None for a firm or an unreadable line."""
    s = re.sub(r'\(.*?\)', ' ', name or '')
    if not surname_first:
        # "John Manning, Esq, J.P, of S. Manning & Co" — the name ends at the first comma.
        s = s.split(',')[0]
    s = re.sub(r'\b(esq|j\.?p|m\.?d|m\.?a|b\.?a|f\.?r\.?c\.?s|m\.?r\.?c\.?s|l\.?r\.?c\.?p)\b\.?', ' ', s, flags=re.I)
    s = re.sub(r'\b(jun|junr|sen|senr)\b\.?', ' ', s, flags=re.I)
    s = re.sub(r'^\s*(' + TITLES + r')\s+', ' ', s, flags=re.I).strip(' ,;.')
    if not s or re.search(r'&|\b(co|ltd|limited|bros|sons?|company|school|church|club|hospital)\b', s, re.I):
        return None, None
    words = [w for w in re.split(r'\s+', s) if w]
    if surname_first:
        sur, rest = words[0], words[1:]
        rest = [w for w in rest if not re.fullmatch(TITLES, w, re.I)]
    else:
        sur, rest = words[-1], words[:-1]
    fore = rest[0] if rest else ''
    fore = FORENAMES.get(fore.lower().strip('.'), fore.strip('.'))
    return sur.strip(".,;'"), fore


def main():
    old = json.load(open(os.path.join(REPO, 'data/directory_park_entries.json')))
    records, done = [], []
    finished = set(sys.argv[1:])            # only volumes whose reader has finished
    for f in sorted(glob.glob(os.path.join(HERE, 'dir_read_*.json'))):
        if 'plan' in f:
            continue
        d = json.load(open(f))
        vol = d['volume']
        if vol not in finished:
            continue
        done.append(vol)
        for st in d.get('streets', []):
            street = st['street'] if st['street'] in STREETS else None
            if not street:
                print(f'  {vol}: "{st["street"]}" is not a site street name — skipped')
                continue
            for e in st.get('entries', []):
                if e.get('kind') in ('cross_street', 'note'):
                    continue
                # Terraces printed as a sub-list inside another street's listing.
                # Readers marked these with `group`, or with `side` when the sub-heading names a street.
                sub = (e.get('group') or '').strip() or (e.get('side') or '').strip()
                grp = next((g for g in STREETS if g != street and sub.lower().startswith(g.lower())), None)
                e_street = grp or street
                if e.get('group') and not grp:
                    continue                      # a side block off the Park (Beeston lane, Butt houses …)
                if e.get('side') and not grp and street in LONG and re.search(
                        r'\b(street|lane|terrace|place|row|road|yard|walk|buildings|houses|villas)\b', sub, re.I):
                    continue
                no_txt = (e.get('no') or '').strip()
                m = re.match(r'^(\d+)', no_txt)
                # Derby Road, Lenton Road and Park Row run on well past The Park: keep
                # only the numbers the site has on them, or a house name it knows.
                if e_street in LONG and not (m and int(m.group(1)) in SITE_NOS[e_street]) \
                        and norm(e.get('house_name')) not in SITE_NAMES.get(e_street, set()):
                    continue
                sur, fore = split_name(e.get('name'), YEAR[vol] >= 1905)
                page = e.get('page') or (st.get('pages') or [None])[0]
                text = ', '.join(x for x in [e.get('house_name'), e.get('name'), e.get('occupation')] if x)
                records.append({'volume': vol, 'year': YEAR[vol], 'street': e_street, 'page': page,
                                'record': OFF[vol] + page if page else None,
                                'no': int(m.group(1)) if m else None, 'no_printed': no_txt or None,
                                'inferred': False, 'house_name': e.get('house_name'),
                                'surname': sur if e.get('kind') != 'business' else None,
                                'forename': fore if e.get('kind') != 'business' else None,
                                'name': e.get('name'), 'occupation': e.get('occupation'),
                                'kind': e.get('kind') or 'resident', 'side': e.get('side'),
                                'unsure': bool(e.get('unsure')), 'text': text[:160]})
    # A line a reader filed both under its terrace and inside Derby Road (or Lenton
    # Road) is one householder: keep the copy on the terrace's own street.
    seen, deduped = {}, []
    for r in sorted(records, key=lambda r: r['street'] in LONG):
        k = (r['volume'], re.sub(r'[^a-z]', '', str(r['name'] or '').lower()), r['no_printed'], r['house_name'])
        if k[1] and k in seen and seen[k] != r['street']:
            continue
        seen.setdefault(k, r['street'])
        deduped.append(r)
    print(f'  {len(records) - len(deduped)} lines filed twice by a reader, kept once')
    records = deduped
    kept = [r for r in old['entries'] if r['volume'] not in done]
    doc = {
        'note': ("Occupants of The Park's streets as printed in Wright's Directory of Nottingham. Volumes "
                 f"{', '.join(done) or 'none'} were read from the page scans held by the University of Leicester's "
                 "Special Collections; any other volume is still the older machine reading of the page text. "
                 "A directory records a householder a year or so after its survey: evidence to weigh against a "
                 f"census household, never a filing on its own. Built {datetime.date.today().isoformat()}."),
        'source': "Wright's Directory of Nottingham, 1894-95, 1898-99, 1910-11, 1913-14 and 1915-16 — University of Leicester, Special Collections Online",
        'volumes': old.get('volumes'),
        'read_from_scans': done,
        'entries': records + kept,
    }
    json.dump(doc, open(os.path.join(REPO, 'data/directory_park_entries.json'), 'w'), indent=1, ensure_ascii=False)
    print(f'{len(records)} entries from scans ({", ".join(done)}), {len(kept)} kept from the older reading')


if __name__ == '__main__':
    main()
