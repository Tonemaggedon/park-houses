# Outstanding — Nottingham Park Houses

A working tick list. Tick items off as you go (`- [ ]` → `- [x]`).
Last checked against the live site: **9 September 2026**.

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

## 3. The big data gap

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

## 4. Offered, not yet started

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

## 5. Property questions

- [ ] **Clumber Court (#399)** — marked demolished, but has **no residents linked
      and no census years**. Either the links are missing or the record is a stub.
- [ ] **The Hermitage (#392)** — my coordinate and your placement are **48m apart**.
      Yours is on the map; this is only a note that they disagree.
- [ ] **Belwood** and **Dudley Lodge** — visible on your OS sheets, no records exist.
- [ ] **Penrhyn Cottage** — the site has *Penrhyn House* (#84). Same building under
      two names, or two buildings?

---

## 6. Known weak spot in the code

- [ ] **Two sources of truth for property positions.** `data/all_props.json` holds a
      base coordinate for each property; roughly **396 manual placements** live in
      the database and are served by `/api/coords`. The manual ones are yours and
      are what the map draws.

      **This has caused a wrong bug report before** — measuring against the JSON
      alone made your own corrections look like faults. Anyone touching
      coordinates must check `/api/coords` first. Reconciling the two into one
      source would remove the trap for good.

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
