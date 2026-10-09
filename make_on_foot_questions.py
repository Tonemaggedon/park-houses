# -*- coding: utf-8 -*-
"""Forty questions were on the walk. About six of them could be answered standing there.

A. Hagues asked to see the walk's questions and check they made sense. They did
not. The walk took every open question tied to a property, and most of those are
documentary - *the Ashworths had four children and lost one, was it Leslie?* is a
death register, not a gatepost. Offering it to somebody on a pavement wastes
their evening and makes the whole idea look silly.

So a question now carries **on_foot**, and the walk shows only those. The ones
that qualify are the ones where the record has run out of documents and a pair of
eyes settles it in a minute.

The record already had the right list - seventeen numbered items inside
`questions-for-a-walk-round-the-park` - but as prose in one question rather than
as questions tied to houses, so the walk could not see them. They become
questions of their own here, each phrased as the thing you would actually look at.
"""
import json, re, sys

apply = '--apply' in sys.argv
P = json.load(open('data/all_props.json'))
def find(addr):
    a = addr.lower()
    for p in P:
        if (p.get('address') or '').lower() == a: return p['id']
    for p in P:
        if a in (p.get('address') or '').lower(): return p['id']
    return None

# Existing questions that genuinely are on-foot work.
MARK = [
 'barrack-yard-where', 'hermitage-position', 'is-there-a-house-at-14-huntingdon-drive',
 'gees-lodge-which-building', 'yorke-mews-address', 'clumber-court-stub',
 'ccn-8-old-door', 'penrhyn-cottage-or-house', 'the-stables-lenton-road',
 'two-castle-lodges-on-castle-grove', 'ccn-16-and-18', 'pelham-cottages-where',
 'huntingdon-drive-past-ten', 'park-terrace-has-a-number-38',
 'park-drive-missing-numbers-5-8-and-10', 'lr-numbers-not-held',
 'fourteen-names-on-the-site-map-that-the-record-has-not-got',
 'not-one-post-box-in-the-park-has-been-recorded',
 'seventy-four-houses-have-never-been-photographed',
]

# The seventeen out of questions-for-a-walk-round-the-park, as questions of their own.
NEW = [
 ("the-small-building-between-4-and-2-ropewalk", "The Ropewalk (unnumbered, between 4 and 2)",
  "Does the small building between 4 and 2 The Ropewalk have a number or a name now?",
  "It held **William Hurst, solicitor**, and three others in 1861. The page gives it no number and "
  "the record has none. **It still stands.** Is there a number or a name on it today — and is it a "
  "coach house, which is what it looks like?"),
 ("is-2-the-ropewalk-visibly-two-houses", "2 The Ropewalk",
  "Is 2 The Ropewalk visibly two houses?",
  "The listing calls it *formerly 2no. townhouses c1835-40*, and the 1861 enumerator walks it as "
  "**2 and 2a with ten people in each**. From the street: one front door or two?"),
 ("thirty-and-thirty-two-ropewalk-doors", "30 The Ropewalk",
  "Do 30, 32 and 32a The Ropewalk have separate front doors?",
  "They hold a household in 1861 and nothing in any other round, which is odd for three houses. "
  "**Count the doors.**"),
 ("four-clinton-terrace-one-dwelling-or-two", "4 Clinton Terrace",
  "Is 4 Clinton Terrace one dwelling or two?",
  "The Sampsons' 1921 schedule is written over — 129 on top of what looks like 133 — and the "
  "Essexes are already at 133. **If the house is two dwellings the difficulty disappears.** "
  "Is there one front door or two?"),
 ("clinton-terrace-door-numbers", "1 Clinton Terrace",
  "Do the Clinton Terrace doors run one-to-one with the odd Derby Road numbers?",
  "The record says 1 to 7 Clinton Terrace are 127 to 139 Derby Road, and a servant in 1921 "
  "confirms 5 = 135 by writing both. **Walk the row and read the doors.**"),
 ("what-stands-on-sunnysides-ground", "Sunnyside, Park Terrace",
  "What stands on Sunnyside's ground now?",
  "Sunnyside was still there and still named on the 1953 Ordnance Survey, so it came down after "
  "1955. **What is on the plot today?**"),
 ("is-there-anything-on-sun-drive-but-sunnyside", "Sunnyside, Park Terrace",
  "Is there anything on Sun Drive but Sunnyside?",
  "A. Hagues gives Sun Drive as a real road with **only one property on it**, which is why the "
  "record does not hold it as a street. **Worth confirming there is nothing else along it.**"),
 ("how-many-doors-has-cliff-house", "Cliff House, Lenton Road (32, 33, 33a, 33b)",
  "How many front doors has Cliff House?",
  "The record carries it as 32, 33, 33a and 33b in one property, with **52 people across four "
  "rounds**. Are there four doors, or fewer?"),
 ("twenty-two-and-twenty-four-ccn-doors", "22 and 24 Cavendish Crescent North",
  "Are 22 and 24 Cavendish Crescent North one house or two?",
  "Two numbers in one record, two rounds of people, and no evidence either way. **Count the doors.**"),
 ("does-the-split-show-at-16-ccn", "Crescent Lodge, 16 and 16a Cavendish Crescent North",
  "Does the split show from the street at 16 and 16a Cavendish Crescent North?",
  "A. Hagues confirms it is **one house of about 1885 now split into two households**. Does that "
  "show from the pavement — two doors, two bells, two numbers?"),
]

d = json.load(open('data/research_questions.json'))
have = {q['slug']: q for q in d['questions']}
marked = 0
for slug in MARK:
    if slug in have:
        if apply: have[slug]['on_foot'] = True
        marked += 1
    else:
        print(f"  (no such question: {slug})")

added = []
for slug, addr, title, detail in NEW:
    pid = find(addr)
    if slug in have:
        if apply: have[slug]['on_foot'] = True
        continue
    if pid is None:
        print(f"  NO PROPERTY for {addr} — skipped"); continue
    added.append((slug, addr, pid, title))
    if apply:
        d['questions'].append({
            "slug": slug, "area": "On foot", "kind": "address", "priority": 20,
            "status": "open", "on_foot": True, "property_id": pid,
            "title": title,
            "detail": detail + "\n\nOne of the things the record cannot settle from paper. "
                      "From [[questions-for-a-walk-round-the-park]]."})

print(f"\n  {marked} existing questions marked on_foot")
print(f"  {len(added)} new on-foot questions:")
for slug, addr, pid, title in added:
    print(f"    #{pid:<4} {addr[:36]:<38} {title[:54]}")
if apply:
    json.dump(d, open('data/research_questions.json', 'w'), indent=1, ensure_ascii=False)
    print(f"\n  written — {len(d['questions'])} questions in all")
else:
    print("\n  preview only — pass --apply")
