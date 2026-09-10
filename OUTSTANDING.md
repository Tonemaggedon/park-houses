# Outstanding — Nottingham Park Houses

A working tick list. Tick items off as you go (`- [ ]` → `- [x]`).
Last checked against the live site: **10 September 2026**.

**To see this list, just ask me for "the list"** — or "what's outstanding". I will read this file, check it against the live site, and show you what is left.

---

## 1. Files lost to the deploy bug — need re-uploading

Uploads used to be written to the container's own disk, which Railway rebuilds on
every deploy. Anything uploaded between two releases was destroyed. **Fixed on
9 September** — uploads now go to Cloudinary and survive. These were lost before
the fix and cannot be recovered; the only way back is to upload them again.

- [ ] **Albert Ball** — portrait (person #469)
- [ ] **Watson Fothergill** — portrait (person #467)
- [ ] **Jane Fraser** — portrait (person #471)
- [ ] **Samuel Waite Johnson** — portrait (person #24)
- [ ] **Herbert Durrant Snook** — portrait (person #351)
- [ ] **Marriott Ogle Tarbotton** — portrait (person #201)

Already done:

- [x] Helena Brownsword Dowson — blue plaque, Council House
- [x] Helena Brownsword Dowson — plaque, 100 years of women magistrates

To check whether one has stuck: a saved image's address should begin
`https://res.cloudinary.com/`. Anything beginning `/data/photos/` is still on
the old path and will not survive the next deploy.

---

## 2. Decisions only you can make

Each of these is a fork I deliberately did not take on your behalf.

- [x] ~~Edith Curnow's birth year~~ — **settled: 1872 is right, my transcription was wrong.**
      Her 1939 Register entry records her as **67**, which puts her birth in 1871 or 1872, not
      1870. I mis-read the year in the register image. Nothing to change; she could gain the
      birth date **1 August 1872** if you want it.
- [ ] **White Cottage or Amelia House?** You said schedule 231 is White Cottage; the site
      records 19 Cavendish Crescent South (#46) as **Amelia House**. Say the word and I will
      record White Cottage as a former name, exactly as The Lindens now sits on Linden House —
      or replace the name outright if Amelia House is the wrong one.
- [ ] **Henry H Goddard junior.** Father and son share a name at 17 Cavendish
      Crescent South. Name-matching would have merged them, so the son is entered
      as first name **"Henry H jnr"**. Rename him on his page if you would rather
      it read differently.
- [ ] **Brownsword cousins.** You said Arthur Brownsword (#49) and Helena
      Brownsword Dowson (#2548) are cousins. Say the word and I will record it in
      the relationships table — I left it out rather than guess the degree.

---

## 3. Houses named in the census that the record does not hold

Six house names appear in unfiled census addresses with no matching property. Each needs a
number, or creating as its own property the way Gartree Lodge was.

**I tried to deduce the Huntingdon Drive numbers and could not.** The four households appear in
no other census year at a numbered Huntingdon Drive address, so there is nothing to triangulate
from. These need your knowledge or a source.

**Solved — these now suggest themselves on `/unfiled`, outlined in green:**

- [ ] **Kenmore → #152, 10 Huntingdon Drive.** 6 records. The house is recorded as Kenmare
      House; the census spells it Kenmore. One click to file.
- [ ] **Allendale → #50, 23 Cavendish Road East.** 3 records — William C Church (50), a servant
      and a visitor. The house is recorded as Allandale; the census spells it Allendale. Parker
      Woodward held it in 1911 and had moved to #51 by 1921, so Church took it on.

- [x] ~~Gertrude House~~ → **#55, 33 Cavendish Road East (Redcliffe House)**. Confirmed
      against the return. Recorded, so it suggests itself on `/unfiled`.

**Two faults that household turned up, both needing you:**

- [ ] **File 8 of those 9 records to #55 — not Arthur Oscar Hanish.** The return does not have
      him at Redcliffe House. Simplest is to file all 9, then merge him on `/duplicates`, which
      reunites him at 5 Tattershall Drive where he belongs.
- [ ] **Emma Woodward, Frank's wife, had no 1921 record at all.** Prepared in
      `data/people_1921_redcliffe_house.json` — run **Import people** and she goes in at #55
      as Wife, aged 62, with the marriage recorded. One **Import people** run does every
      prepared file at once, so this, the Brownsword cousins and 19 Park Terrace all land
      together. Take the dry-run preview first — it now reports census records, relationships
      and any person number it could not find.

**Still unknown — narrowed from ten houses to four:**

Huntingdon Drive holds ten houses. #143 (Barton House) and #148 (Avoca) are occupied in 1921,
#145 has six people, and #152 is Kenmore. That leaves **2, 4, 8 and 9 Huntingdon Drive** — the
four with no name recorded and nobody in 1921 — for these three households. Nothing on the
estate resembles any of the three names under any spelling.

- [x] ~~Brampton~~ → **#151, 9 Huntingdon Drive**. Recorded; suggests itself on `/unfiled`.
- [x] ~~The Cottage~~ → **#405, 14 Huntingdon Drive**, created census-only. **The number is
      confirmed**: Dougal's map labels it "14 The Cottage" on the north-east side of the road.
      My note that the road stopped at 10 and the house might be gone was wrong on both counts.
      Position moved to opposite number 6, still provisional.
- [x] ~~5 Huntingdon Drive is Napier House~~ — already recorded as such.
- [ ] **Greendale, Huntingdon Drive** — 4 records, 1921. Joseph Spray (77), wife Martha (77),
      daughter Jessie (47), one servant. An elderly household. The last one unplaced. The
      unnamed numbers are 2, 4 and 8 — **but the road does not stop at 10**, so Greendale may
      not be among them at all.

- [ ] **Huntingdon Drive runs past number 10 and the record does not.** Dougal's map draws a
      second run on the north-east side, numbered back down the other way: **11 Burnham House,
      13 The Magpies, 14 The Cottage, 15 The Coach House, The Hunting Lodge, 17, and 18 The
      Round House (formerly The Spiral)**, with Birchwood beyond. Only The Cottage is in the
      record, and only because a census household carried its name. If these are houses rather
      than flats and coach houses, **the record is missing half a street** — and Greendale is
      as likely to be one of them as to be 2, 4 or 8. On `/research`.

---

## 3b. Open questions — `/research`

The questions in the record that no amount of reading will settle: which house a name belongs
to, whether a building still stands, what a colour on a map meant. **14 are seeded** from
`data/research_questions.json`, and a contributor presses *I'm looking into this* to put their
name against one so two people don't spend the same Saturday on the same gatepost. Answers are
recorded on the page — including "walked the road, found nothing", which saves the next person
the walk. Adding a question to the JSON file puts it on the site at the next deploy; an answer
or an edit made on the site is never overwritten by the file.

---

## 4. The three big piles

Each of these has a page now. They are the bulk of the "crap imported" and are worth doing in
this order.

- [ ] **`/unfiled` — 271 records at no property** (1921: 175, 1911: 87, 1901: 8, 1891: 1),
      across only ~22 addresses. Roughly 90 can go in six clicks: Peveril Drive (31), South Road
      (22), Felixstowe (21, but split the three households first), Park Drive (6), Tower House
      (6), Kenilworth House (4). Around 121 carry only a street and need the house; ~33 carry
      nothing at all. **This number rising is progress** — unfiling a misfiled household moves
      it here on the way to the right house.
- [ ] **`/duplicates` — 48 pairs.** The 1911 and 1921 spreadsheets were loaded separately and
      name people differently, so the same person exists twice: "Helena Brownsword Dowson" and
      "Helena Dowson", "Kate A Homberger" and "Kate Adeline Homberger". A split person has half
      their census history and appears at two addresses. **Merging cannot be undone**, so check
      each pair.
- [ ] **`/crowding` — 19 property-years** (was 21). Several households filed against one address. Use
      **"sort it"** on each row to split them, or **"This is correct"** where the house really
      did hold that many.

---

## 5. Misfiled census records

### Finish the Kenilworth move

- [ ] **Emily Purden (#932) is still at 1 Kenilworth Road.** The four Pembertons moved to No. 3;
      their servant did not — her 1911 record (entry 2555) is still filed against #153 while
      Samuel's is at #155. Different surname, so she was missed. Move her the same way.

### Houses holding improbably many people — `/crowding`

Across the whole record a household runs to a **median of 5**, and **95% hold 11 or fewer**.
A house showing twenty-odd in one year is usually several households filed against one address.
**The surname count is the tell** — one household is rarely more than two or three families.

21 property-years are currently flagged. The worst:

- [ ] **#227 — 39 Newcastle Drive (Priests House)** — 27 people, **22 surnames**, 1921
- [ ] **#310 — 5 Tattershall Drive** — 26 people, **16 surnames**, 1921
- [ ] **#25 — 9 Cavendish Crescent North (Peveril House)** — 22 people, **14 surnames**, 1911.
      **Solved, needs the clicks.** Three census schedules sit under one address. In import
      order — which is the enumerator's own order, running 1 → 3 → 5 → 7 → 9 up the crescent —
      they are: four servants with **no head** (entries 858–861), then the **Weinberg**
      household of 9 (862–870), then the **Smith** household of 9 (871–879). Weston Fulford
      Marriott Weston-Webb held the lease on Peveril House from at least 1911 and signed the
      schedule without being there on the night, which is why the first one is servants alone.
      **Only those four belong at #25.** Where the other two go is not proven: the schedules
      immediately after them run on up the crescent, and **10 (#26)** and **11, Gleadthorpe
      (#27)** hold no 1911 record at all, so they are the obvious candidates to check against
      the original. Both heads are lace manufacturers. `/reassign?prop=25&year=1911` already
      shows the three blocks separately with a "send all to" box on each.

### The modern map, by contrast, can be read to the metre

Reading a screenshot of the modern map against eight houses in the same frame whose positions
are already known — Gladstone House, Penrhyn House, Edale House and 25 to 33 Cavendish Road
East — those eight fit to **within a fifth of a metre** at 0.18 m per pixel. So a building
visible on it can be placed properly, which is how Penrhyn Cottage and Gees Lodge were done.

### Dougal's map is a diagram, not a survey

Measured against the 70 houses on it whose positions are known, the map is out by a **median
of about 60 metres**, and fitting it locally rather than globally makes it worse, not better.
So it settles **which** house and **in what order** — which is how The Cottage and Broxtowe
House were placed on their streets — but it cannot be used to set a coordinate. Positions
still want a human.
- [ ] **#84 — Penrhyn House** — 14 people, **7 surnames**, 1921. **Four schedules under one
      address**, in enumerator order: the **Houlton** household (2565–2568), the
      **Drinkwater** household (2569–2571), the **Shepherd** household (2572–2573), and the
      **Radford** household with two servants (2574–2578). The 1921 schedule header for the
      Drinkwaters gives their postal address as **"Gees Lodge, Tunnel Rd"** — Albert
      Drinkwater was a police constable of 36. **Gees Lodge is now #408**; send 2569–2571
      there on `/reassign?prop=84&year=1921`. The **Shepherds** (2572–2573) were at **The
      Cottage, Tunnel Road — now #409**; send those two there. That leaves the Houltons and
      the Radfords, and Penrhyn House was divided into flats, so one or both may genuinely
      belong. Three of the four schedules under this one address were somewhere else.
- [ ] **Two houses are called The Cottage** — #405 at 14 Huntingdon Drive and #409 on Tunnel
      Road, 400 m apart. Same hazard as the two Peveril Houses: a census address reading only
      "The Cottage" can be filed against either. Both records now say so. Automatic matching
      on Dougal's map had put *both* of that map's "Cottage" labels against #405.
- [ ] **#379 — 19 Park Terrace** — 21 people, **17 surnames**, 1921. **Solved by the schedule
      header.** Three schedules: the **Clark** household (2055–2059, five people, the real
      19 Park Terrace), then **nine resident doctors under Dr John Kneebone** (2060–2068),
      then the **Carr** household (2069–2075, seven people). The 1921 schedule for the middle
      one gives its postal address as **"Broxtow House, The Park, Nottingham"** — registration
      district 430, sub-district 6, enumeration district 66. **Broxtow House is in none of the
      405 properties, and on none of Dougal's map labels.** The import runs along the street —
      16, 17, then these three, then Sunnyside — and **20 Park Terrace (#257) holds no 1921
      record at all**, so it is the first candidate for one of the two strays. Sunnyside (#390)
      holds two schedules of its own in the same run, which may bear on where the third goes.
      **Broxtowe House is now #406**, created census-only. `/reassign?prop=379&year=1921`
      shows the three blocks separately — send the Kneebone block to **406**. The schedule
      spells it *Broxtow*, without the e; recorded as Broxtowe.
- [ ] **The nine at Broxtow House are worth a page of their own.** Aged 26–33, all surgeons or
      physicians, none related, born Dorset, Aberdeen, Kent, Yorkshire, Hertfordshire, London,
      Surrey, Perthshire and South Australia — a residents' house for junior hospital doctors,
      not a household. Nottingham General Hospital stands on the edge of The Park, and its own
      history records it acquiring houses in The Park and Park Terrace as doctors' residences
      — but dates that to **1969**, so this pushes the practice back nearly fifty years.
      **Five of the nine were women**: Dora Mason, Olive Sharp, Gwennon Mary Griffiths,
      Elizabeth Mary Ashby, Dorothy Jean Gallie. In 1921 that is remarkable.
- [ ] **#379 — 19 Park Terrace**, continued. Its **1911
      household is now prepared** in `data/people_1911_19_park_terrace.json` — the house held
      no 1911 record at all. Run **Import people**: William Froggatt Clark and his wife are
      already in the record from 1921 as **#1836** and **#1837**, so the file names them by
      number rather than by name and will not make second copies of them whatever you rename
      them to. Grace Cecily Clark and the three servants are new.
- [ ] **#85 — Westwood, Clumber Road East** — 20 people, **13 surnames**, 1921
- [ ] **#201 — Gladstone House, Lincoln Circus** — 16 people, 12 surnames, 1921
      (10 here in 1911)
- [ ] **#121 — 8 Hamilton Drive** — 16 people, 8 surnames, 1921

The full list of 21 is on the page, and it recalculates as you fix things.

A boarding house, a school or a large staff will show here legitimately, so not every one is
wrong. **But 10 Barrack Lane is not the example I gave it as.** I described its 17 people under
6 surnames in 1911 as "plausibly one family with staff". It is **four schedules** — the Derrys,
Elizabeth Baker with the Smiths, the Blythes with a boarder, and the Hinds — and **every one of
the other seventeen cottages on Barrack Lane holds no 1911 record at all**. That is the whole
lane's return filed on number 10.

- [ ] **#7 — 10 Barrack Lane, 1911.** Four schedules to split across a lane of eighteen
      cottages, all of them empty in the record. `/reassign?prop=7&year=1911`. **Solved.**
      Only the **Derrys** (630–634, plus the son being imported) belong at number 10. The
      other three schedules — **Elizabeth Baker and the Smiths** (635–637), the **Blythes**
      with their boarder (638–643) and the **Hinds** (644–646), twelve people — were at
      **Barrack Yard, Barrack Lane**, which is now **#410**. Send each of the three households
      to **410** with its "send all to" box. No need to unfile them.

Tools: **Dashboard → Admin tools → Move a household to another property** for a whole
household, or the **property picker on each census record** on a person's page for one-offs.

### Spellings the census gets wrong

- [ ] **Derry, not Denny — 10 Barrack Lane, 1911.** The transcription spells the household
      **Denny** for five of the six and **Derry** for the head. The record has them as Derry
      throughout and A. Hagues confirms Derry is right: George (65, jobbing gardener), Sarah
      (58), George (18), Elizabeth (26), Annie (15) and Mabel Sarah (7). Worth remembering
      when searching, because a lookup on Denny will find none of them.
- [ ] **George Derry the son had no record at all.** Prepared in
      `data/people_1911_10_barrack_lane.json` — run **Import people** and he goes in at #7 as
      Son, aged 18, a worker, with both parents recorded.

### Records filed against no property at all

- [ ] **245 census records sit at no property** — 154 in 1921, 82 in 1911, 8 in 1901, 1 in 1891.
      They are invisible on the map, invisible on `/crowding`, and are the other half of the
      same problem: the Pembertons' three 1921 records were among them. The Unresolved Census
      page is where these get assigned.
- [ ] **The rest of Cavendish Crescent North in 1911 is sitting in that queue.** The 1911
      import ran street by street: entries 826–901 are the whole crescent, but only 837–879
      were filed. Everything after the 9 Cavendish block — **880–901**, the Brewster, Hadden,
      McCaith and Walker households — is unfiled, and it is the continuation up the same
      street. Settle those and the two strays at #25 above should fall out with them.

---

## 5a. House names recorded from the crescent walk (10 Sep 2026)

Eleven names went straight into `prev_house_name`, where the site actually reads them:

| No. | Name | | No. | Name |
|---|---|---|---|---|
| 1 | Carisbrooke House ✓ | | 15 | Flixton |
| 3 | Cavendish Lodge ✓ | | 17 | Pendower |
| 5 | Blantyre House | | 19 | Normandon Lodge |
| 7 | Jardine House | | 20 | Castlemount (three flats, 2020) |
| 10 | Charnwood ✓ | | 22 | Ravenscourt |
| 12 | Hazlewood | | 24 | Thorsmore |

✓ = confirmed independently by that house's own listed-building description, which was already
in the record and had never been carried across to the name field. 9 (Peveril House), 11
(Gleadthorpe) and 14 (Park House) were already held. **22 and 24 are one property record
(#36)**, so it now carries both names.

Five things from the walk had no property to attach to and are questions on `/research`
rather than new records, per the rule below:

- **Yorke Mews** — the map puts it beside Yorke House, 6 North Road (#229), with "formerly
  Yorke Cottage" and The Coach House. A mews of that house, not a house on the crescent. The
  street headings in the walk mark where the side roads join the crescent; only Yorke Mews
  actually belongs to one of them.
- **16 Crescent Lodge**, and **18** — the record holds 16a and 18a but not 16 or 18, though
  number 20's own description names "Nos.16, 18" as part of a group of four.
- **8** — no house of that number, but an old door with 8 on it at the back of the house below.
- **6** — missing.
- **Western House School, 1874–1937** — given as 30 Western Terrace, but the record holds
  Western Terrace as 1 to 11 only.

- [ ] **Haddon House (#37) and Hardwicke House (#398) carry no number.** Both are on
      Cavendish Crescent North, confirmed, and both are already in the record. The walk offers
      **4** and **2** for their numbers, with the owner's own query against them; the crescent
      has neither number recorded, so both are free. Held as a suggestion in each property's
      sources until confirmed.

---

## 5b. When to create a property

**A house name on its own is not enough. Create a property only where there is census data
behind it** — a household returned at that address. That is how Gartree Lodge, The Cottage on
Tunnel Road, Gees Lodge, Broxtowe House and Barrack Yard all came in: each had people living
at it on a return, filed against the wrong house.

Names with no household behind them — Belwood, Pelham Cottages, Reveille, Burnham House, The
Magpies, the rest of the far side of Huntingdon Drive, and the 171 unmatched labels on Dougal's
map — stay as questions on `/research` until a record turns up. A name on a map is evidence
that something was called something. It is not evidence of who lived there, which is what this
record is for.

---

## 6. The big data gap

- [ ] **1911 birth places.** Only **330 of 902** people in the 1911 census have a
      birth place recorded (37%), against **1,272 of 1,289** for 1921 (99%). This
      is the hole in the origins map, and it is the spreadsheet you are working
      through by hand.

Other gaps, for reference rather than action:

| | Count |
|---|---|
| People in the record | 2,510 (was 2,552 — you have been merging) |
| People with an unresolved census entry | 262 |
| People with no property link at all | 314 |
| People with no birth year | 50 |
| Person records carrying a birth place | 510 of 2,510 — **the backfill job has not been run yet** |

---

## 7. Offered, not yet started

- [ ] **Backfill `born_place` onto people from census entries.** Only 511 person
      records hold a birth place while the census entries behind them hold far
      more — the same shape as the occupations gap that was backfilled on
      8 September. Likely to triple the coverage. Ask and I will build it.
- [ ] **Look for Sir Frank and Sir Harold Bowden.** The Gazette sweep found them;
      there are no Bowdens at all among the 2,550 people. Harold is named in
      William Henry Raven's biography (#295), so a check under variant spellings
      may be worth ten minutes.
- [ ] **The next 1939 Register page.** The transcribed page ended at 1 South Road,
      schedule 234. Arthur Black is schedule 237 at 3 South Road, so schedules
      235–236 are still missing between them.

---

## 8. Property questions

- [ ] **Clumber Court (#399)** — marked demolished, but has **no residents linked
      and no census years**. Either the links are missing or the record is a stub.
- [ ] **The Hermitage (#392)** — my coordinate and your placement are **48m apart**.
      Yours is on the map; this is only a note that they disagree.
- [ ] **Belwood** and **Dudley Lodge** — visible on your OS sheets, no records exist.
- [x] ~~Penrhyn Cottage~~ — **two buildings.** Created as **#407, Penrhyn Cottage,
      Cavendish Road East**, census-only. It stands at the bottom of the garden of Penrhyn
      House (#84) and takes its address from the road the garden backs onto — the Gartree
      Lodge arrangement. Dougal's map draws it as its own building beside Tunnel Lodge.
      **Position corrected** from the modern map — 26 m from my first guess. Answered by
      A. Hagues; still open on `/research` until somebody presses the button.
- [ ] **Gees Lodge (#408), Tunnel Road** — created census-only from the Drinkwaters' schedule
      header. It is one of the two small buildings by the mouth of the Park Tunnel; the
      northern is Penrhyn Cottage, the southern is now Tunnel Lodge, and Gees Lodge is
      recorded on the southern one as the likelier. **Which of the pair, and whether the name
      really reads Gees**, is on `/research`.

---

## 9. Known weak spots in the code

- [ ] **Two sources of truth for property positions.** `data/all_props.json` holds a
      base coordinate for each property; roughly **396 manual placements** live in
      the database and are served by `/api/coords`. The manual ones are yours and
      are what the map draws.

      **This has caused a wrong bug report before** — measuring against the JSON
      alone made your own corrections look like faults. Anyone touching
      coordinates must check `/api/coords` first. Reconciling the two into one
      source would remove the trap for good.

- [ ] **A slipped column put marital status and sex into the `source` field.** 41 census
      entries have a source reading "Single, Female", "Married, Male" and so on, instead of
      where the record came from. Same family of fault as the occupations one. The sex in them
      could be recovered into the `sex` column where a person has none — worth doing before
      clearing, since it is real information in the wrong place. Ask and I will build it.

- [ ] **Duplicate resident links are possible.** `property_residents` has no unique index on
      (person_id, property_id), so nothing stops the same person being linked to the same
      property twice — my first attempt at the household move wrote one. The move tool now
      checks explicitly, but older duplicates may already exist. A constraint cannot simply be
      added without first finding and clearing any. Ask and I will write the cleanup.

- [ ] **Search: "it either works, hangs or shuts the page".** I could not reproduce it. Map
      search worst case 79ms over 403 properties, People 72ms over 2,550, the census page 43ms
      for a whole word, and the server under a second. No memory leak across 60 rebuilds.
      **I need to know which page, what you typed, and what "shuts the page" looks like** —
      the tab closing, the property panel snapping shut, or jumping back to the map. Noted
      in passing: the census and family-tree searches have no debounce where the map and
      people pages have 300ms. Harmless at these sizes, but I can even them up.

---

## Recently closed

- [x] Person 1414, a spreadsheet header row filed as a resident — deleted, and the
      import now refuses header rows. A check on the dashboard confirms no others.
- [x] The 1939 Register import — 33 people across seven households on Cavendish
      Crescent South and South Road.
- [x] Richard Warwick Bond (#2263) identified against Wikidata.
- [x] Census years 1921 and 1939 reachable — the person form stopped at 1911, and
      the map slider could not reach 1921 at all, its largest year.
- [x] Uploads no longer destroyed by deploys; missing files now return a plain 404
      instead of silently serving the map.
- [x] Wikidata pool rebuilt from 451 to 718 people, and the query committed so it
      can be refreshed: `node build-wikidata-snapshot.js`.
- [x] Gartree Lodge created (#404, Tattershall Drive) — Gartree House's coach house, where the
      Hattons lived; it did not exist as a property.
- [x] The Lindens recorded as a former name of Linden House (#87).
- [x] Arthur Brownsword and Helena Brownsword Dowson recorded as cousins; the people import
      now understands relationships.
- [x] Birth places can be backfilled onto people from census entries (dashboard job).
- [x] Duplicate resident links can be cleaned up (dashboard job).
- [x] Occupations that are not occupations can be cleared (dashboard job) — 40 census values
      and 7 on people.
- [x] The People page property filter lists every property, not only occupied ones.
- [x] Census and family-tree searches debounced, as the map and People pages already were.
- [x] Sir Frank and Sir Harold Bowden — **looked for, not there.** No Bowden of any spelling
      among the 2,552 people; Harold's own Wikidata entry has no birthplace or residence. The
      Gazette found them through honours lists, not through The Park. Dead end unless a source
      turns up.
- [x] The Pemberton household moved from 1 to 3 Kenilworth Road — four of the five;
      see Emily Purden above.
- [x] Census records can be moved between properties at all — there was no way to,
      neither a picker on the record nor an endpoint that would accept it.
- [x] Map links from a person, an architect, or the dashboard's recent changes opened
      the whole map instead of the property: five links used `?id=` where the map read
      only `?prop=`. It now accepts either.
- [x] `/api/census/:year` swallowed any word, so `/api/census/crowding` was parsed as a
      year; and an unknown `/api/` path answered 200 with the map, which is what hid it.
