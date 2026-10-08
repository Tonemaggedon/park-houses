# -*- coding: utf-8 -*-
import json
d = json.load(open('data/research_questions.json'))
Q = {q['slug']: q for q in d['questions']}

Q['lr-peveril-drive']['priority'] = 13
Q['lr-peveril-drive']['title'] = "ANSWERED - Rock Cottage is 3a Peveril Drive and Hamilton View is 10"
Q['lr-peveril-drive']['detail'] = """**Both settled by A. Hagues.**

| | | |
|---|---|---|
| **Rock Cottage** | **3a Peveril Drive** (#453) | formerly **Rock House**, where Sam Roper lived c.1930 |
| **Hamilton View** | **10 Peveril Drive** (#295) | formerly **Harlech House** |

Hamilton View came from a property price record for Hamilton View, Peveril Drive, NG7 1DE, which carries a photograph and a street view beside the sale, so the name, the number and the building are tied together in one place. **Harlech House is the older name** and is held as the former one.

**And the name turns out to describe exactly what it says.** Hamilton View is the house on Peveril Drive that looks across at Hamilton Drive - which was the guess this question started from, now confirmed on a building rather than on reasoning.

Links: [[lr-numbers-not-held]], [[osm-house-names-are-a-source-the-record-has-not-mined]]."""

new = [
{"slug": "fourteen-names-on-the-site-map-that-the-record-has-not-got",
 "area": "House names", "kind": "house-name", "priority": 6,
 "title": "Fourteen house names on the record's own map are not in the record",
 "detail": """**A. Hagues read the names off the site's own map and asked whether the record had them all. It has not got fourteen of them.** The labels come from the OpenStreetMap tiles the site draws over, which is the source [[osm-house-names-are-a-source-the-record-has-not-mined]] was written about - and this is the proof that sweeping it properly is worth the morning.

## Not in the record

| name | number | street |
|---|---|---|
| **Barbican House** | 4a | Castle Grove |
| **The Coach House** | | Castle Grove |
| **Ashley Lodge** | | Park Drive |
| **Gladstone Court** | 1-11 | Park Drive |
| **Holles House** | 5 | Holles Crescent |
| **Birchwood** | | Lenton Road |
| **Fothergill House** | | Lenton Road |
| **Park Estate Office** | | Lenton Road |
| **Terrace House** | | Park Ravine |
| **Iveston House** | 4 | Clifton Terrace |
| **Hamilton Court** | 1-6 | Hamilton Drive |
| **Mews Cottage** | 10c | Hope Drive |
| **Hope House** | | Hope Drive |
| **The Gallery** | 1-24 | Hope Drive |

**Barbican House is the one that stings**, because A. Hagues gave it to this record earlier in the same week - *4a Castle Grove Barbican House* - in a list of house names, and it was not applied. Castle Grove in the record runs 1, 2, 3, 4, 5, 6a, 7, with no 4a at all. **A name handed over and dropped is worse than a name never found**, and this is the second time a supplied list has been half-applied.

**Several of the rest are plainly modern** - Gladstone Court, Hamilton Court and The Gallery are numbered ranges, so blocks of flats; Park Estate Office is not a dwelling. Those want recording as what stands there now rather than as houses. **Barbican House, The Coach House, Holles House, Terrace House, Iveston House, Hope House, Mews Cottage, Birchwood and Fothergill House** are the ones that could be historic, and each wants a census household before it becomes a property.

## Three the map and the record disagree about

- **Barton House.** The map puts it on **Lenton Road**, near Castle Bank. The record holds it as the house name of **1 Huntingdon Drive** (#143). Those are different places.
- **Peveril House.** The map labels it on **Peveril Drive**, which is #300. The record also carries *Peveril House* as a former name of **9 Cavendish Crescent North** (#25). The clash [[peveril-house-or-peveril-tower]] warned about, seen on a map.
- **Castle Rock.** The map writes *1 Castle Rock* at the **Castle Grove** end, by The Coach House. The record holds Castle Rock as the house name of **5 Peveril Drive** (#376).

Links: [[thirty-eight-house-names-the-site-does-not-show]], [[two-castle-lodges-on-castle-grove]], [[dougal-map-unmatched-names]]."""},
{"slug": "barrack-yard-is-the-pelham-cottages-and-two-families-prove-it",
 "area": "Houses to find", "kind": "house", "priority": 4,
 "title": "Barrack Yard, Pelham Cottage and Pelham Cottages are one place, and two families prove it",
 "detail": """**A. Hagues put it that the barrack yard was a barracks and later became 1, 2, 3, Journey's End and Reveille. The record carries the evidence, and it is as strong as this kind of evidence gets: two households, each one person record, each walked straight through the name changes.**

## Arthur William Smith, born 23 January 1869

| round | the address as the page or index writes it | filed at |
|---|---|---|
| 1901 | **Pelham Crescent**, schedule 207 | **unfiled** |
| 1911 | **Barrack Yard, Barrack Lane** | #410 |
| 1921 | **2 Barrack Lane** | #3 |
| 1939 | **2 Pelham Cottage, Barrack Lane**, schedule 206 | #450 |

He is a cabinet maker in 1901, 1911 and 1921 and a joiner at 70 in 1939, and his mother-in-law **Elizabeth Baker** heads the house in 1901 and 1911, aged 71 then 81.

## Edith Annie Hind, born 20 January 1879

| round | the address as the page or index writes it | filed at |
|---|---|---|
| 1881 | **Pelham Cottage**, schedule 92, aged 2, with Fletcher and Sarah | **unfiled** |
| 1911 | **Barrack Yard, Barrack Lane**, aged 32, still with Fletcher and Sarah | #410 |
| 1921 | **3 Barrack Lane**, aged 42, head | #384 |
| 1939 | **3 Pelham Cottage, Barrack Lane**, schedule 207, aged 60 | #451 |

## The numbers are the clincher

**Smith is at 2 in 1921 and at 2 in 1939. Hind is at 3 in 1921 and at 3 in 1939.** One family carrying a number through two addresses could be chance. Two families carrying two different numbers through the same pair of addresses is not. **The 1921 round numbered these cottages on Barrack Lane; the 1939 round numbered them on Pelham Cottage.** They are the same three dwellings.

So the place has been written down six ways in seventy years: **the Barracks** (1871), **Pelham Cottage** (1881), **Pelham Cottages** (1891), **Barrack Yard** (1911), **1, 2 and 3 Barrack Lane** (1921), **1, 2 and 3 Pelham Cottage** (1939) - and **Pelham Cottages** again today, with Journey's End and Reveille beside it.

**And Reveille is the name that says so out loud.** A bugle call to wake soldiers, on a site named for a barracks. It stands a few metres south of number 2.

## What follows, and what has to be put right

1. **The 1881 Hind household belongs at 3 Pelham Cottage** - four people, anchored by Edith Annie at 3 in both later rounds. My caution yesterday, that she had moved about and come back, was reading the record's own misfiling as a fact about her life.
2. **The 1901 Baker/Smith household belongs at 2 Pelham Cottage** - three people, anchored the same way.
3. **The 1921 rows are misfiled.** The Smiths sit at #3, *2 Barrack Lane*, which is a substantial listed house at the top of the lane with a full building description and no other census in it - a cabinet maker and his wife are not in that house. Edith Annie Hind sits at #384, *3 Barrack Lane*, which is a property with no description, no history and no sources at all, created from that one index row. **#384 is a phantom.**
4. **The three 1911 Barrack Yard households split between the three cottages**: Smith to 2, Hind to 3, and the Blythes to 1 by elimination.
5. **Five people sit at #410 for 1911 with no age, no relationship and no source** - H Ernest and Alice Goddard, Mildred Jacklin, Annie Bernuctt and Rose Ella Sharman. Where they came from is not recorded and they are not in the twelve the history describes.
6. **Whether #410 survives as a property is the open decision.** It can stay as the yard the three cottages stand in, which is what it was, or be dissolved into them. The 1921 Allenfield Lodge household filed there is on A. Hagues' word rather than evidence and would have to be thought about either way.

## And the 1871 round may hold the barracks itself

Schedule 162 is headed simply **Barracks** and holds **Henry Rogers, 59, a park keeper**, with his wife, three grown children and a lodger - six people, unfiled. A park keeper living at the Barracks is exactly who would be left in a barracks that had stopped being one.

Links: [[pelham-cottages-where]], [[barrack-yard-where]], [[lr-cavendish-crescent-north]], [[barrack-lane-stops-at-thirty]]."""},
]
for n in new:
    if n['slug'] not in Q: d['questions'].append(n)
json.dump(d, open('data/research_questions.json', 'w'), indent=1, ensure_ascii=False)
print('questions now', len(d['questions']))
