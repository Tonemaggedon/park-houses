# -*- coding: utf-8 -*-
import json
d = json.load(open('data/research_questions.json'))
Q = {q['slug']: q for q in d['questions']}

Q['lr-cavendish-crescent-north']['priority'] = 15
Q['lr-cavendish-crescent-north']['title'] = (
    "ANSWERED - Journey's End has no number. It is the house past 3 Pelham Cottages")
Q['lr-cavendish-crescent-north']['detail'] = """**Settled 8 October 2026 from the map A. Hagues supplied and the Ordnance Survey data behind it.** The question asked which number on Cavendish Crescent North is Journey's End. **It has not got one**, and that is the answer rather than a gap in the sources.

| | |
|---|---|
| **housename** | Journey's End |
| **street** | Cavendish Crescent North |
| **number** | none - the address is the name |
| **postcode** | **NG7 1AY** |
| **position** | 52.95173, -1.16800 |

**It stands about fourteen metres east of 3 Pelham Cottages**, at the end of that little row, which is what A. Hagues saw on the map and what gives the name its sense - the last house before the road runs out. The three cottages behind it are a street of their own, **Pelham Cottages, NG7 1AQ**, parent street Pelham Crescent; Journey's End is not on it.

**NG7 1AY is a postcode of named and unnumbered houses**, which is why Land Registry had nothing to pair it with: Hamilton Mews 1 and 2, **Hardwick House** (no number), **Jardine House at 7**, **Peveril Towers at 9**. Four of those are in the record. Journey's End is not, and under the rule it stays out until a census household is found at it - it appears in no walk the record holds, and the 1939 round goes 1 Barrack Lane, the three cottages, then straight into Pelham Crescent.

**Two things fall out of the same survey and want their own questions:**

- **Peveril Towers is 9 Cavendish Crescent North**, within two metres of the position the record already holds for #25. See [[peveril-house-or-peveril-tower]].
- **Jardine House is 7 Cavendish Crescent North**, and the record holds 7 with no name at all. **Ernest Jardine** is already in the record at Gwedon, 9 Clumber Crescent South. See [[seven-cavendish-crescent-north-is-jardine-house]].

Links: [[pelham-cottages-where]], [[thirty-eight-house-names-the-site-does-not-show]], [[a-guessed-position-is-indistinguishable-from-a-surveyed-one]]."""

Q['pelham-cottages-where']['priority'] = 10
Q['pelham-cottages-where']['title'] = (
    "Pelham Cottages are found and held - but which of the three did each 1881 household have?")
Q['pelham-cottages-where']['detail'] = """**Found.** Pelham Cottages is a street of its own: three cottages in a row off Pelham Crescent, postcode **NG7 1AQ**, reached by the 1939 enumerator on his Barrack Lane round. The record holds all three (#449, #450, #451), and their positions are now the buildings' own footprints rather than the arithmetic they were created with.

| | 1881 | 1891 | 1939 |
|---|---|---|---|
| **1** | ? | ? | **Florence M Onion**, 40, widowed certified teacher, with two daughters |
| **2** | ? | ? | **Arthur William Smith**, 70, joiner |
| **3** | ? | ? | **Edith Annie Hind**, 60, hosiery shirt machinist |

**The 1881 and 1891 households are still unfiled**, and the obstacle is that neither round gives a number:

| 1881 | schedule 92 | **Fletcher Hind**, 32, *gardener*, Sarah 32, Fred 3, **Edith Annie 2** |
| 1881 | schedule 93 | **Johnson Marriott**, 26, *waiter*, and Matilda E, 27 |
| 1881 | schedule 94 | **Charles Sidney Hill**, 37, *cook*, alone |
| 1891 | schedule 3 | **Ethel Matilda Pitts**, 5, Arthur Clayton 3, Winifred Josephine 1 |
| 1891 | schedule 4 | **Sarah Warriner**, 47, three children, and a dressmaker lodging |

## The Hind temptation, and why the record should resist it

**Edith Annie Hind, aged 2 at Pelham Cottage in 1881, is Edith Annie Hind, aged 60 at 3 Pelham Cottage in 1939.** Born 20 January 1879, so the ages agree exactly, and the 1881 household is her parents. It is tempting to read schedule 92 as number 3 and file four people on the strength of it.

**The intervening rounds say no.** The same woman is at **Barrack Yard** in 1911, aged 32, still with Fletcher and Sarah; and at **3 Barrack Lane** in 1921, aged 42, as head of her own house. She moved about this corner for sixty years and came back. So her being at number 3 in 1939 says nothing about which cottage she was born in, and schedules 93 and 94 cannot be assigned by working outward from a cottage that is not fixed either.

**This is the Tattershall Drive error in a new coat** - a schedule run read as a street order, with a name match to make it feel settled. See [[the-lodge-on-tattershall-drive-is-not-gartree-lodge]].

**What would settle it:** a directory of the 1880s or 1890s listing the cottages by number against a name; or the 1891 and 1901 pages, where an enumerator may have numbered what the 1881 man did not. Failing that, nine people stay unfiled at a group of houses the record now has.

**And there is a fourth name on this little street.** OpenStreetMap holds **Reveille** on Pelham Cottages, NG7 1AQ, with no number, a few metres south of number 2. Whether it is a fourth cottage or a renamed one of the three is not known.

Links: [[lr-cavendish-crescent-north]], [[barrack-yard-where]], [[a-guessed-position-is-indistinguishable-from-a-surveyed-one]]."""

new = [
{"slug": "seven-cavendish-crescent-north-is-jardine-house",
 "area": "House names", "kind": "house-name", "priority": 15,
 "title": "7 Cavendish Crescent North is Jardine House, and the record holds the number with no name",
 "detail": """**OpenStreetMap gives 7 Cavendish Crescent North the housename *Jardine House*, postcode NG7 1AY.** The record holds 7 (#24) with no name at all.

**The name is almost certainly a person in the record.** **Ernest Jardine** is held at **Gwedon, 9 Clumber Crescent South** in 1939, described on the schedule as an **HM Government contractor**, with John Jardine, managing director of an HM gas firm, in the house with him. A Nottingham lace machine builder of that name was knighted and sat as an MP, and a house in The Park named after him would want explaining.

**What is open:** was the house called Jardine House when a Jardine lived in it, or is the name later - a developer's, or a commemoration? And did any Jardine ever live at number 7, which the record could answer from its own rounds if it looked.

**The name is a lead and not a record**, like the Land Registry names: under the rule for this record, a modern name does not become the house's name until a source puts it there in its own time.

Links: [[lr-cavendish-crescent-north]], [[thirty-eight-house-names-the-site-does-not-show]], [[gwedon-9-clumber-crescent-south]]."""},
{"slug": "osm-house-names-are-a-source-the-record-has-not-mined",
 "area": "House names", "kind": "method", "priority": 7,
 "title": "OpenStreetMap carries house names and postcodes for The Park, and one query answered four questions",
 "detail": """**One Overpass query round a single point settled more in a minute than a week of reading pages.** Asking OpenStreetMap for every building within 110 metres of Pelham Cottages returned housenames, housenumbers, street names, parent streets and postcodes - and with them:

| | |
|---|---|
| **Journey's End** | no number, Cavendish Crescent North, NG7 1AY - [[lr-cavendish-crescent-north]] answered |
| **Peveril Towers** | **9** Cavendish Crescent North, within 2 m of the position the record already held |
| **Jardine House** | **7** Cavendish Crescent North, a name the record has not got |
| **Pelham Cottages** | a street of its own, NG7 1AQ, parent street Pelham Crescent - with 1, 2 and 3 as separate buildings, and **Reveille** as a fourth name |
| **Khera House** | **20** Pelham Crescent |
| **Hardwick House** | no number, NG7 1AY - and the record spells it **Hardwicke** |
| **Graylands** | **31** Lenton Avenue - and A. Hagues gave this one as **Greylands** |

**The record has never asked this source anything.** It has mined Dougal de Havilland's map, the Land Registry price paid data, the listed-building descriptions and the directories. OpenStreetMap carries the same class of fact - the name in use now, against a number and a postcode - and it carries building footprints too, which is what positions should be read from rather than calculated.

## What it is good for, and what it is not

**It is a modern name, exactly like a Land Registry name**, so the rule stands: it does not become the house's name in the record until a source puts it there in its own time. What it is unbeatably good for is the **reverse lookup** - a name off a census page that the property list has not got, run against a street to find which number carries it now.

**And the postcode groups are a finding of their own.** NG7 1AY holds Hamilton Mews 1 and 2, Hardwick House, Journey's End, Jardine House at 7 and Peveril Towers at 9 - the named and half-numbered houses at the Pelham Crescent end of Cavendish Crescent North, which is precisely the stretch the record keeps losing houses on.

**The job:** a sweep of every street in The Park, held in a data file as a lead list the way `data/map_dougal_unmatched.json` holds the map's names, with the matches against the property list worked out and the rest left as questions.

Links: [[dougal-map-unmatched-names]], [[lr-numbers-not-held]], [[thirty-eight-house-names-the-site-does-not-show]], [[a-guessed-position-is-indistinguishable-from-a-surveyed-one]]."""},
]
for n in new:
    if n['slug'] not in Q:
        d['questions'].append(n)

# Peveril House/Tower advanced
q = Q['peveril-house-or-peveril-tower']
q['detail'] = """**The name in use now is *Peveril Towers*, plural, at 9 Cavendish Crescent North.** OpenStreetMap holds it as the housename against number 9, postcode NG7 1AY, within two metres of the position the record already carries for #25 - so the house is certainly the right one.

**The record has 9 Cavendish Crescent North under *Peveril House/Peveril Tower***, both singular, as former names. Neither is quite what the house is called today.

**What is open is the period.** Which name did it carry, and when? *Towers* may be the modern form of *Tower*, or a later renaming altogether. And the clash is live: there is a second **Peveril House** on **Peveril Drive** (#300, which holds only 1891), so a census address reading simply *Peveril House* could be filed against either, on either street.

Links: [[lr-cavendish-crescent-north]], [[osm-house-names-are-a-source-the-record-has-not-mined]], [[thirty-eight-house-names-the-site-does-not-show]]."""

json.dump(d, open('data/research_questions.json', 'w'), indent=1, ensure_ascii=False)
print('questions now', len(d['questions']))
