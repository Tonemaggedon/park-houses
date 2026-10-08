# -*- coding: utf-8 -*-
import json
d = json.load(open('data/research_questions.json'))
Q = {q['slug']: q for q in d['questions']}

q = Q['fourteen-names-on-the-site-map-that-the-record-has-not-got']
q['priority'] = 5
q['title'] = "Eighty-five house names on the record's own map have no property in the record"
q['detail'] = """**A. Hagues read the names off the site's own map, across six views, and asked whether the record had them all. It has eighty-five it has not got.** They are kept in `data/map_osm_unmatched.json`, the way Dougal de Havilland's unmatched names are kept in `data/map_dougal_unmatched.json`.

The labels come from the OpenStreetMap tiles the site draws over - the source [[osm-house-names-are-a-source-the-record-has-not-mined]] was written about, and this is what sweeping it properly turns up. **Fifty-three of the names checked were already held**, which is the reassuring half.

## The ones most likely to be historic

| | |
|---|---|
| **Castle Grove** | **Barbican House 4a**, The Coach House |
| **Lenton Road** | Birchwood, Fothergill House, West Park Lodge, The Point 40 |
| **Clare Valley** | Whitehouse, Evergreen, Idle Rocks, Maredo, Tree Tops, The Corner House, Sun Drive 12 |
| **Huntingdon Drive** | **Burnham House 11, The Magpies 13**, The Hunting House |
| **Park Terrace** | Abbot House, Richmond House 14D, The Garden House 14A, The Town House, The Studio Terrace 14 |
| **Cavendish Crescent South** | Park Hall 5, Sutherland House 25, Courtyard House, Cavendish Place |
| **South Road** | Kirkstall Lodge, Orchard House 3a, South Lodge 2a, The Old Coach House |
| **Tunnel Road** | Tunnel Lodge, Park Yard |
| **elsewhere** | Clumber Lodge, Holles House 5, Terrace House, Iveston House 4, Hope House, Mews Cottage 10c, Greenmantle, The Blue House, Khera House 20, Edale Lodge, Yorke Mews 23, Hamilton Mews 1 and 2, Peveril Towers 9, Westwood House 3, Glendower, Fantasque House |

**Burnham House and The Magpies are the find.** [[huntingdon-drive-past-ten]] asked whether the second run on Huntingdon Drive - 11 Burnham House, 13 The Magpies, 15 The Coach House and the rest - are separate houses or flats of houses already held. **The modern map numbers them**, which is a good deal more than Dougal's drawing did.

## Plainly modern, and wanting recording as what stands there now

Gladstone Court 1-11, Hamilton Court 1-6, The Gallery 1-24, Westcliffe Court 1-8, Park Rock 1A-6H, The Park Octagon, Saco House 1-27, Ropewalk Court, Broadgate, City Point, Royal Standard House, Agora House, Charles House, Regency House West, Park Edge, One Degree West (built 2003), Park Estate Office (not a dwelling).

## Three the map and the record disagree about, and one that is settled

- **Barton House.** **Settled by A. Hagues: it is on the corner of Lenton Road and Huntingdon Drive, and both the map and the record are right.** And the rule he gave with it is the general one: **two houses can carry the same name in different eras** - so a clash is not automatically an error to resolve. See [[two-houses-can-share-a-name-in-different-eras]].
- **Peveril House.** The map labels it on **Peveril Drive** (#300); the record also carries it as a former name of **9 Cavendish Crescent North** (#25), where the map writes *Peveril Towers*. Now read as the same rule rather than a fault.
- **Castle Rock.** The map writes *1 Castle Rock* at the **Castle Grove** end; the record holds Castle Rock as the house name of **5 Peveril Drive** (#376).

**Barbican House is the one that stings**, because A. Hagues gave it to this record earlier in the same week - *4a Castle Grove Barbican House* - and it was not applied. Castle Grove in the record runs 1, 2, 3, 4, 5, 6a, 7, with no 4a at all. A name handed over and dropped is worse than a name never found.

**The sweep is partial.** Six views do not cover the estate, and the job is to ask OpenStreetMap for every street in The Park at once rather than reading labels off pictures.

Links: [[thirty-eight-house-names-the-site-does-not-show]], [[two-castle-lodges-on-castle-grove]], [[dougal-map-unmatched-names]], [[huntingdon-drive-past-ten]], [[lr-numbers-not-held]]."""

q = Q['barrack-yard-is-the-pelham-cottages-and-two-families-prove-it']
q['priority'] = 4
q['title'] = "ANSWERED - Barrack Yard is the Pelham Cottages, it survives, and twenty-two people are filed"
q['detail'] = q['detail'].replace(
 "## What follows, and what has to be put right",
 "## Settled and done, 8 October 2026\n\n**A. Hagues confirms Barrack Yard survives**, so the record "
 "keeps it as the yard and the three cottages stand in it. **Twenty-two people were filed or "
 "refiled:**\n\n"
 "| | | |\n|---|---|---|\n"
 "| 1881 | schedule 92, the Hinds | **unfiled -> 3 Pelham Cottage**, 4 people |\n"
 "| 1901 | schedule 207, Baker and the Smiths | **unfiled -> 2 Pelham Cottage**, 3 people |\n"
 "| 1911 | the Blythes | Barrack Yard -> **1 Pelham Cottage**, 6 people |\n"
 "| 1911 | Baker and the Smiths | Barrack Yard -> **2**, 3 people |\n"
 "| 1911 | the Hinds | Barrack Yard -> **3**, 3 people |\n"
 "| 1921 | the Smiths | *2 Barrack Lane* -> **2**, 2 people |\n"
 "| 1921 | Edith Annie Hind | *3 Barrack Lane* -> **3**, 1 person |\n\n"
 "**#3, 2 Barrack Lane, is now empty of census** - it is a substantial listed house at the top of "
 "the lane and a cabinet maker and his wife were never in it. **#384, 3 Barrack Lane, is empty "
 "too, and is a phantom**: no description, no history, no sources, made from the single index row "
 "that has now been moved out of it. It wants deleting, which is A. Hagues' call.\n\n"
 "**Barrack Yard's position has moved 76 m south** onto the block it is, derived from the four "
 "building footprints around it and flagged as derived.\n\n"
 "## Still open")
q['detail'] = q['detail'].replace(
 "1. **The 1881 Hind household belongs at 3 Pelham Cottage** - four people, anchored by Edith Annie "
 "at 3 in both later rounds. My caution yesterday, that she had moved about and come back, was "
 "reading the record's own misfiling as a fact about her life.\n", "")
json.dump(d, open('data/research_questions.json','w'), indent=1, ensure_ascii=False)
print('ok')
