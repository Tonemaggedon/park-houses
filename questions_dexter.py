# -*- coding: utf-8 -*-
import json
d = json.load(open('data/research_questions.json'))
Q = {q['slug']: q for q in d['questions']}

new = {"slug":"richard-j-dexter-and-the-number-ten-that-never-existed",
 "area":"Houses to find","kind":"house","priority":7,
 "title":"Richard J Dexter's fifteen are at 10 Park Drive, and A. Hagues says there was no number 10",
 "detail":"""**The 1881 page heads schedule 185 *10 Park Drive*. A. Hagues has walked the run and says it works, and that there does not look to have been a number 10.** So the record holds a household of fifteen with an address the street has never had, and the fifteen are unfiled.

## The household

**Richard J Dexter**, 43, **cigar manufacturer employing 200 girls**, born Nottingham, with **Harriett**, 44, and **nine sons**:

| | | |
|---|---|---|
| Frank E, 19 | Arthur H, 18, **cigar maker** | Frederick J, 16 |
| Walter J, 13 | Albert B, 9 | Richard J, 8 |
| Clement G, 6 | Horace M, 5 | **William E G, 4** |

With **Sarah Fidler**, 50, widowed, and **Elizabeth Mullington**, 47, unmarried - both entered as his sisters - and two servants, **Jane Harris**, housemaid, and **Esther Cox**, cook. Fifteen in the house, every one of the family born in Nottingham.

**William E G is William Ernest Gladstone Dexter**, born about 1877, which dates the household's politics as precisely as anything in the record.

## They stay in The Park for forty years, and four sons take the trade

| round | where | who |
|---|---|---|
| **1911** | **22 and 24 Cavendish Crescent North** | Frank Earnest, Frederick Suyer, Clement George and William Ernest G Dexter |
| **1921** | **Overdale, Cavendish Road East** | the same four, aged 51, 52, 47 and 43 - **all four returned *Cigar Manufacturer*** |

**Four brothers under one roof, all in their father's trade, none of them married.** That is worth saying on its own, whatever happens to the address.

## What the 1881 walk shows

| s176 | 1 Park Drive |
| s177 | 3 Park Drive |
| s178-180 | 1, 3, 5 Tattershall Drive |
| s181 | 6 Park Drive |
| s182 | 4 Park Drive |
| s183 | 2 Park Drive |
| **s184** | **Ashley House** |
| **s185** | **"10 Park Drive"** |
| s186 | away to Tunnel Road |

**And Clumber House is not in this run** - the enumerator took it earlier, at schedule 160, coming off South Road, along with another unnumbered Park Drive household at 159. So it cannot be the house at 185.

**7 and 9 Park Drive are in no part of the 1881 book at all.** The round covers 1, 2, 3, 4, 6, Ashley House and this one. If 7 and 9 were standing in 1881 the enumerator would have taken them with 1 and 3, before he crossed to Tattershall Drive. The likeliest reading is that **they were not yet built**.

## So what is it

1. **A misread or miswritten number.** The record flags the heading *as the page writes it*, which is the honest form. A 1 with a following letter, a 16, a 70 - only the image settles it, and it is the first thing to check.
2. **A house that is gone.** Park Drive's houses have been converted and its gardens built on; Ashley House's garden alone has since taken a bungalow and a pair of semis.
3. **The number is real and the street was renumbered.** 1, 2, 3, 4, 6, 7, 9 is not a run down one side; it is a sequence round a triangle, and one that has been edited at least once - **Ashley House is 8**, which A. Hagues settled, and the 1939 round still writes *8 Park Drive* for it.

**The precedent matters.** The 1939 enumerator wrote *8 Park Drive* where the record keeps *Ashley House*, and that turned out to be the same building. **An enumerator numbering where the record names is exactly the shape of this problem** - so the question worth asking is not only "where is 10" but "which named house was 10".

**Clumber House is the only named house on the street left without a number** - but it is already taken at schedule 160, so if it is 10, the Dexters are somewhere else again.

**What would settle it:** the schedule 185 image, first; then a street directory for Park Drive in the 1880s, which would give the numbered run against the names in one column.

Links: [[park-drive-missing-numbers-5-8-and-10]], [[properties-carrying-two-house-numbers]], [[questions-for-a-walk-round-the-park]]."""}
if new['slug'] not in Q: d['questions'].append(new)

q = Q['park-drive-missing-numbers-5-8-and-10']
q['priority'] = 9
q['title'] = "Park Drive has no 5 or 10 - 8 is Ashley House, and the 1881 page still writes a 10"
q['detail'] = """**Corrected 8 October 2026. Number 8 is settled and the question is now about 5 and 10.**

**8 Park Drive is Ashley House.** A. Hagues settled it: there are no houses between 6 and Ashley House, so the *8 Park Drive* the 1939 enumerator writes at schedule 23 is the house the record names. #432 was created for it and is folded in and gone; the Howitt household of seven sits at **#238**.

**Park Drive now reads 1, 2, 3, 4, 6, 7, 9, with Ashley House as 8 and Clumber House unnumbered.** 5 and 10 are the gaps.

## 10 is the live one, and it holds fifteen people

The 1881 page heads schedule 185 **10 Park Drive** - **Richard J Dexter**, cigar manufacturer employing 200 girls, his wife, **nine sons**, two sisters and two servants. **A. Hagues has checked the run and says the walk works and there does not look to have been a number 10.** That household now has a question of its own: [[richard-j-dexter-and-the-number-ten-that-never-existed]].

## 5 has nothing at all

No page in any round heads a household at 5 Park Drive, and no name is waiting for the number. It may simply never have been used - 1, 2, 3, 4, 6, 7, 9 is a sequence round a triangle rather than a run down one side, and such sequences skip.

## What would settle either

A street directory for Park Drive in the 1880s or the 1930s, giving the numbered run against the house names in one column. Failing that, the rate books.

Links: [[richard-j-dexter-and-the-number-ten-that-never-existed]], [[properties-carrying-two-house-numbers]], [[questions-for-a-walk-round-the-park]]."""
json.dump(d, open('data/research_questions.json','w'), indent=1, ensure_ascii=False)
print('questions now', len(d['questions']))
