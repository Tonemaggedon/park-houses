# -*- coding: utf-8 -*-
"""Four questions checked against the record before being handed over. Three were stale."""
import json
d = json.load(open('data/research_questions.json'))
Q = {q['slug']: q for q in d['questions']}

# 1. Rock Cottage is settled; only Hamilton View is open.
q = Q['lr-peveril-drive']
q['title'] = "Hamilton View, Peveril Drive - and Rock Cottage is settled"
q['detail'] = """**Rock Cottage is answered.** A. Hagues has it as **3a Peveril Drive** (#453), formerly **Rock House**, where Sam Roper lived c.1930. The property is in the record and carries the former name.

**Hamilton View is still open.** Land Registry holds it on Peveril Drive with no number. The street in the record runs 1, 1a, 2, 2a, 3, 3a, 4, 5, 6, 7, 8, 10, 11, 12 with Eskdale, Parkdale and Peveril House unnumbered beside it - so a name with no number here could be any of several things.

**Hamilton View is a name that describes a position**, which is the useful part: it should look across at Hamilton Drive. From HM Land Registry's price paid data, which records a house name beside the number for every sale since 1995 - a name in use now, not necessarily the historic one, and a lead rather than a record. Under the rule for this record it becomes a property only when a census household is found at it.

Links: [[lr-numbers-not-held]], [[thirty-eight-house-names-the-site-does-not-show]]."""

# 2. 18 and 18a are both in the record; 16 and 16a are merged, and not as #411.
q = Q['ccn-16-and-18']
q['title'] = "18 Cavendish Crescent North is in the record and has no name - what was it called?"
q['detail'] = """**Corrected 8 October 2026.** This question said 18 was missing from the record. It is not, and has not been for some time:

| | | holds |
|---|---|---|
| **#31** | **Crescent Lodge, 16 and 16a Cavendish Crescent North** | 1891, 1911, 1921, 1939 |
| **#33** | 18 Cavendish Crescent North | 1901, 1921 - **blank 1939** |
| **#428** | 18a Cavendish Crescent North | 1901, 1911 - **blank 1939** |

16 and 16a are held together as one property under the name Crescent Lodge; 18 and 18a are held apart. The listed-building descriptions of the group name **"Nos. 16, 18, 20 and 22/24"**, built c.1885 as four substantial houses, three later subdivided with the former kitchen and butler's quarters made into a flat. So 16a is the flat of 16 and 18a the flat of 18 - and the record has treated one pair as a single house and the other as two.

**What is actually open:**

1. **18 has no name.** 16 is Crescent Lodge. Does 18 carry one?
2. **Should 18 and 18a be one property or two?** They are held both ways on the same street, which cannot both be right. Both were returned separately in 1901, which argues for two.
3. **Do 16 and 16a front the road differently?** That is what would settle where each sits on the map.

Links: [[thirty-eight-house-names-the-site-does-not-show]], [[named-houses-at-numbers]]."""

# 3. The Penrhyn Cottage merge is dead, and the record killed it.
q = Q['is-penrhyn-cottage-23-cavendish-road-east']
q['priority'] = 8
q['title'] = "ANSWERED NO - Penrhyn Cottage is not 23 Cavendish Road East, and the 1921 households prove it"
q['detail'] = """**Settled 8 October 2026 against this question's own proposal, from the record alone. No merge.**

This question argued from the 1939 walk that Penrhyn Cottage must be 23 Cavendish Road East: schedule 59 is Penrhyn Cottage, 60 is 25, and 23 is the only odd number missing from the run. The reasoning was sound and the conclusion is wrong, because **both houses hold a 1921 household and they are not remotely the same kind of household**:

| | 23 Cavendish Road East (#50) | Penrhyn Cottage (#407) |
|---|---|---|
| **1921** | **William C Church**, 50, *managing director, Boots*, with Augusta Stockwell, 48, and a domestic servant | **Jane Houlton**, 53, with **Harry**, 30, *plumber*, Florence, 24, and Tom, 14 |
| **1939** | nothing | **William T Turner**, 45, *gardener*, Alice, 43, and Raymond, 4 |

**One house in one year cannot hold both.** And the character runs the other way too: Penrhyn Cottage holds a plumber's family in 1921 and a gardener's in 1939, while 23 holds Benjamin North in 1891, Richard Henry Swain in 1911 and the managing director of Boots in 1921. A cottage and a villa.

**So Penrhyn Cottage is a cottage** - the Gartree Lodge kind of building, housing the staff of a bigger house, and the gardener in 1939 says whose. It is very likely the northern of the two small buildings by the mouth of the Park Tunnel, which is what [[gees-lodge-which-building]] already supposes, in the grounds of Penrhyn House.

**What is still open is 23's missing 1939**, which this question was right to notice. A house is written in with a household or written in and ticked; 23 is neither. The schedule 59 page may yet give a number alongside the name, and if it does it will not be 23.

Links: [[penrhyn-cottage-or-house]], [[gees-lodge-which-building]], [[lr-coach-houses]], [[a-guessed-position-is-indistinguishable-from-a-surveyed-one]]."""

new = {
 "slug": "the-duplicate-check-matched-on-the-one-field-two-readings-disagree-about",
 "area": "The record itself",
 "kind": "data",
 "priority": 3,
 "title": "Eight households are in the record twice, and my duplicate check reported none",
 "detail": """**I ran a duplicate-household check this week and told A. Hagues there were no duplicated households anywhere in the record. That was wrong. There are eight.**

`tools_duplicate_households.py` matched people on **forename + surname + age**. The record's duplicates are duplicates of the *page*, not of the transcription: the same enumerator's sheet read twice, once with the house number and once without, or once off the image and once off an index. Two readings of one page agree on the forename, the age, the schedule and usually the occupation word for word. **They disagree on the surname**, because the surname is the hardest word on the sheet.

So the key contained the one field the two readings never share, and the check could not see a single one of them.

## The eight

| people | house | year | the two readings |
|---|---|---|---|
| **8** | 19 Lenton Avenue | 1881 | **Heeley** / **Keeley** - a solicitor and dyer employing 82 hands, his wife and five children, plus a housemaid read Girton and Gorton |
| **5** | 8 Lenton Avenue | 1891 | **Bell** / **Hall** - a coachman, his wife and three daughters |
| **4** | 153 Derby Road | 1871 | **de Lascelle** / **Lasalle** - a railway company secretary and three children |
| **3** | 23 Lenton Avenue | 1881 | **Cottee** / **Cobbee** - a coachman, his wife and a model maker |
| **2** | 13 Lenton Avenue | 1891 | **Lowater** / **Corrates** - a hosiery manufacturer and his wife |
| **2** | 7 Park Valley | 1891 | **Gardiner** / **Gardener** - a cook |
| **2** | 3 Park Valley | 1891 | |

Thirty-one people, roughly, standing for about sixteen.

## Why it cannot be fixed without the pages

**Each pair needs a decision about which surname is right**, and that is a decision only the image can make. Heeley or Keeley is not a near-miss to be split - it names a different family. The careful-looking reading is not automatically the right one either: the transcription citing RG11/3367 and the house number looks more careful, and may still have read the initial wrong.

**The non-destructive fix is a fold**: one person, both readings kept as aliases, so a search under either still finds them. That loses nothing and halves the duplicate. It wants A. Hagues' word on which reading leads.

## And there is a second class the new check also sees

Pairs where the two surnames are a **married name and a maiden name** rather than two readings - Nora Lowe and Nora Matthews at Park House in 1939, June E Turpin and June E Blackburn at 33 Newcastle Drive, Vera Sampson and Vera Babrecki at 7 North Road. Those come from the 1939 index against the page, where the stamped surname is the later married name. Whether each is one woman held twice or a deliberate pair has not been checked.

`tools_duplicate_households_v2.py` is the rebuilt check.

Links: [[a-transcription-with-no-address-is-invisible-to-a-street-check]], [[the-lodge-on-tattershall-drive-is-not-gartree-lodge]], [[a-guessed-position-is-indistinguishable-from-a-surveyed-one]]."""}

if new['slug'] not in Q:
    d['questions'].append(new)
json.dump(d, open('data/research_questions.json', 'w'), indent=1, ensure_ascii=False)
print('questions now', len(d['questions']))
