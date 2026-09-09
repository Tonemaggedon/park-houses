# Outstanding — Nottingham Park Houses

A working tick list. Tick items off as you go (`- [ ]` → `- [x]`).
Last checked against the live site: **9 September 2026** (second pass).

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

- [ ] **Edith Curnow's birth year.** Her record (#457) says **1872**; the 1939
      Register says **1 August 1870**. The import left the 1872 alone rather than
      writing a date that contradicted it, so she currently has no birth date at
      all. Which is right?
- [ ] **White Cottage or Amelia House?** You said schedule 231 is White Cottage.
      The site records 19 Cavendish Crescent South as **Amelia House**. The 1939
      people are linked to that property but I have not renamed it. Add White
      Cottage as a former name, replace Amelia House, or leave it?
- [ ] **Henry H Goddard junior.** Father and son share a name at 17 Cavendish
      Crescent South. Name-matching would have merged them, so the son is entered
      as first name **"Henry H jnr"**. Rename him on his page if you would rather
      it read differently.
- [ ] **Brownsword cousins.** You said Arthur Brownsword (#49) and Helena
      Brownsword Dowson (#2548) are cousins. Say the word and I will record it in
      the relationships table — I left it out rather than guess the degree.

---

## 3. Misfiled census records

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
- [ ] **#25 — 9 Cavendish Crescent North** — 22 people, **14 surnames**, 1911
- [ ] **#379 — 19 Park Terrace** — 21 people, **17 surnames**, 1921
- [ ] **#85 — Westwood, Clumber Road East** — 20 people, **13 surnames**, 1921
- [ ] **#201 — Gladstone House, Lincoln Circus** — 16 people, 12 surnames, 1921
      (10 here in 1911)
- [ ] **#121 — 8 Hamilton Drive** — 16 people, 8 surnames, 1921

The full list of 21 is on the page, and it recalculates as you fix things.

Not every one is wrong: 10 Barrack Lane holds 17 people under only 6 surnames in 1911, which
is plausibly one family with staff. A boarding house or a school will show here legitimately.

Tools: **Dashboard → Admin tools → Move a household to another property** for a whole
household, or the **property picker on each census record** on a person's page for one-offs.

### Records filed against no property at all

- [ ] **245 census records sit at no property** — 154 in 1921, 82 in 1911, 8 in 1901, 1 in 1891.
      They are invisible on the map, invisible on `/crowding`, and are the other half of the
      same problem: the Pembertons' three 1921 records were among them. The Unresolved Census
      page is where these get assigned.

---

## 4. The big data gap

- [ ] **1911 birth places.** Only **330 of 902** people in the 1911 census have a
      birth place recorded (37%), against **1,272 of 1,289** for 1921 (99%). This
      is the hole in the origins map, and it is the spreadsheet you are working
      through by hand.

Other gaps, for reference rather than action:

| | Count |
|---|---|
| People with an unresolved census entry | 240 |
| People with no property link at all | 302 |
| People with no birth year | 48 |
| Person records carrying a birth place | 511 of 2,550 |

---

## 5. Offered, not yet started

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

## 6. Property questions

- [ ] **Clumber Court (#399)** — marked demolished, but has **no residents linked
      and no census years**. Either the links are missing or the record is a stub.
- [ ] **The Hermitage (#392)** — my coordinate and your placement are **48m apart**.
      Yours is on the map; this is only a note that they disagree.
- [ ] **Belwood** and **Dudley Lodge** — visible on your OS sheets, no records exist.
- [ ] **Penrhyn Cottage** — the site has *Penrhyn House* (#84). Same building under
      two names, or two buildings?

---

## 7. Known weak spots in the code

- [ ] **Two sources of truth for property positions.** `data/all_props.json` holds a
      base coordinate for each property; roughly **396 manual placements** live in
      the database and are served by `/api/coords`. The manual ones are yours and
      are what the map draws.

      **This has caused a wrong bug report before** — measuring against the JSON
      alone made your own corrections look like faults. Anyone touching
      coordinates must check `/api/coords` first. Reconciling the two into one
      source would remove the trap for good.

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
- [x] The Pemberton household moved from 1 to 3 Kenilworth Road — four of the five;
      see Emily Purden above.
- [x] Census records can be moved between properties at all — there was no way to,
      neither a picker on the record nor an endpoint that would accept it.
- [x] Map links from a person, an architect, or the dashboard's recent changes opened
      the whole map instead of the property: five links used `?id=` where the map read
      only `?prop=`. It now accepts either.
- [x] `/api/census/:year` swallowed any word, so `/api/census/crowding` was parsed as a
      year; and an unknown `/api/` path answered 200 with the map, which is what hid it.
