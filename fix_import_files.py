"""Repair the import files the Preview showed would land data on the wrong person.

Each fault is the same shape: a person named in a file with no number against
them, so the importer binds by name and picks whichever of several people it
meets first. Giving each one their number closes it.
"""
import json, sys
apply = '--apply' in sys.argv
D = 'data/'

def load(f): return json.load(open(D+f))
def save(f, d):
    if apply: json.dump(d, open(D+f,'w'), indent=1, ensure_ascii=False)

def find(doc, name, pred=None):
    for q in doc.get('people', []):
        if f"{q.get('first_name','')} {q.get('last_name','')}".strip() == name:
            if pred is None or pred(q): return q
    return None

changes = []

# 1. The Holmes household moved to number 1 this morning; the file still says 19.
f = 'people_1939_cavendish_crescent_south.json'; d = load(f)
for nm in ('Henry J Holmes','Frances M Holmes'):
    q = find(d, nm)
    q['properties'] = [38]
    for ce in q.get('census', []):
        if ce.get('census_year') == 1939:
            ce['property_id'] = 38
            ce['address'] = '1 Cavendish Crescent South'
            ce['census_household_num'] = 229
            ce['source'] = (ce.get('source') or '').replace('19 Cavendish Crescent South','1 Cavendish Crescent South')
    changes.append(f"{nm}: 19 -> 1 Cavendish Crescent South, schedule 229")
save(f, d)

# 2. Florence Bell the stepdaughter was 24 in 1891, so born about 1867 - #6215,
#    not #3142, who was born in 1881 and would have been ten.
f = 'people_1891_lenton_road_rg12_2682.json'; d = load(f)
q = find(d, 'Florence Bell'); q['id'] = 6215; q['born_year'] = 1867
changes.append("Florence Bell -> #6215 (born 1867), not #3142 (born 1881)")
#    The 1891 Lenton Avenue boy is #9224. #7413 is the 1878 man at 4 Park Drive,
#    who carries George Victor only as an alias.
q = find(d, 'George Victor Dunn')
if q: q['id'] = 9224; q['born_year'] = 1888; changes.append("George Victor Dunn -> #9224 (1891), was pointing at #7413")
save(f, d)

f = 'people_1881_1891_lenton_avenue.json'; d = load(f)
q = find(d, 'George Victor Dunn')
if q: q['id'] = 9224; q['born_year'] = 1888; changes.append("George Victor Dunn (Lenton Avenue file) -> #9224")
save(f, d)

# 3. Mary A Wood - the record holds two, and the row is already on #8924.
f = 'people_1881_standard_hill_part9.json'; d = load(f)
q = find(d, 'Mary A Wood'); q['id'] = 8924; q['born_year'] = 1858
changes.append("Mary A Wood -> #8924, not #6808")
save(f, d)

# 4. Alice M. Ellis - the file says 1887, the record 1886, so the year match failed
#    and she would have been made a third time.
f = 'people_1901_clumber_road.json'; d = load(f)
q = find(d, 'Alice M. Ellis'); q['id'] = 4164; q['born_year'] = 1886
changes.append("Alice M. Ellis -> #4164 (born 1886, not 1887)")
save(f, d)

# 5. Elizabeth Lewis at The Chestnuts is Elizabeth G Lewis, #7111, the timber
#    merchant's wife, already on schedule 241.
f = 'people_1881_standard_hill_part2.json'; d = load(f)
q = find(d, 'Elizabeth Lewis'); q['id'] = 7111
changes.append("Elizabeth Lewis -> #7111 Elizabeth G Lewis, The Chestnuts schedule 241")
save(f, d)

# 6. Muriel Langtree is at 7 Hamilton Drive. Her entry says refer to page 18, and
#    she appears there again - the Ribble Lodge row is that second sighting,
#    wrongly made into a household of its own.
f = 'people_1939_rmgc_the_park.json'; d = load(f)
q = find(d, 'Muriel Langtree')
before = len(q.get('census', []))
q['census'] = [ce for ce in q.get('census', [])
               if not (ce.get('census_year') == 1939 and 'Ribble Lodge' in str(ce.get('address') or ce.get('unresolved_address') or ''))]
changes.append(f"Muriel Langtree: Ribble Lodge row dropped ({before} -> {len(q['census'])} census rows)")
save(f, d)

for ch in changes: print("  ", ch)
print("\n  written" if apply else "\n  preview only - pass --apply")
