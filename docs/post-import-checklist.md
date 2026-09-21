# After every import

*The run-through that keeps the record clean. Work it in order — each stage depends on the one above it.*

Nothing here takes long. The point is that it is the **same list every time**, so a fault introduced by
one import is caught by the next person to read the page rather than three months later by accident.

Where a tool has a **Preview**, always press it first: it shows exactly what would happen and changes
nothing.

---

## Where everything is

Every page carries the same green bar at the top. The row of links along it —
Map, People, Notable, Architects, Census, Family trees, Insights, Origins,
Estate history, Archive, Open questions, Dashboard — is the public site, and it
never changes.

Two menus sit **above that row, at the right**, and only appear when you are
signed in:

- **Research** — the eighteen working pages. Everything in this checklist that is
  not an admin tool is in here: The working list, Unfiled records, Occupations to
  sort, Unresolved census, Split a house's census, Duplicate people, Crowded
  houses, Positions vs OpenStreetMap, Listed buildings, Gazette by person,
  Wikidata review, Dougal's map, Directories by street, Directories by surname,
  Architects & lace makers, Medal cards, Forename sex, Names to check.
- **Admin** — three entries: **Admin tools**, Users, and **Birthplaces**.

**Admin tools** is one long page with five chips across the top that jump to its
sections: *Bring files in*, *Move records*, *Fill gaps from the census*, *Clean
up after imports*, *The Gazette*. **Medal index cards has no chip** — it is the
last section, below The Gazette.

**Sign in on the Map first.** The Research and Admin menus are not drawn at all
until you do, so a bookmarked page will bounce you.

So a step written here as *Admin tools → Clean up after imports → Find rows that
are not people → `Check`* means: green bar → **Admin** → **Admin tools** → the
**Clean up after imports** chip → that tool's **Check** button. And one written
as *Occupations to sort* means: green bar → **Research** → **Occupations to
sort**.

---

## 0. Before you press Import

**Map → sign in as admin → Admin tools → Bring files in → Import people → `Preview`**

The preview names who would be added rather than counting them. Read the names. A household you
did not expect, or a name you recognise as somebody the record already holds, is the cheapest
moment to catch a problem there will ever be.

Then `Import`. Note what it says it added — you will want that figure again at stage 9.

---

## 1. Damage the spreadsheet did on the way in

**Admin tools → Clean up after imports**

| | tool | what it catches |
|---|---|---|
| 1.1 | **Find rows that are not people** → `Check` | A column heading imported as a person, or a blank name |
| 1.2 | **Recover the slipped source column** → `Preview` → `Run` | "Married, Female" sitting in the source field. Fills the sex, moves the marital status to its own column |
| 1.3 | **Clear occupations that are not occupations** → `Preview` → `Clear` | A sex, a relationship or a dash in the occupation field, skewing every count on the site |

Do these three before anything else. They move values into the right columns, and the stages below
read those columns.

---

## 2. Jobs

**Admin tools → Fill gaps from the census**

| | tool | |
|---|---|---|
| 2.1 | **Copy census occupations onto people** → `Preview` → `Run` | So they show on the People page, the group chips and the occupation filter |
| 2.2 | **Date occupations from the census** → `Preview` → `Date them` | Gives an undated job the years of the returns that name it |

Then **Occupations to Sort** (`/occupations`). Every spelling normalisation cannot place, commonest
first. One spelling can stand for ninety people, so the early clicks do the most work.

---

## 3. Sex

**Forename Sex Review** (`/name-sex`). One click per *name*, not per person — setting Mary covers
every Mary in the record.

Step 1.2 will already have filled the sex for anyone whose row carried it in the wrong column, so
run this after that, not before.

---

## 4. Names

**Names to Check** (`/name-review`). Question marks where a forename should be, bare initials, and
spellings one slip of the pen from an ordinary name.

**This is where a ditto mark read as a surname shows up.** An enumerator writes the family name
against the head and rules it down the column; a transcription that takes the mark as a value puts
people into the record with a middle initial for a family name — *Frank B.*, *Ellen T.* Nineteen of
them came in with the 1901 round. They are invisible everywhere except here.

---

## 5. Duplicates

In this order, because each one makes the next shorter.

| | where | |
|---|---|---|
| 5.1 | Admin tools → **Join up people entered under a census short form** → `Preview` → `Run` | *Geo. Parr* beside George Parr. **Repeat until the preview comes back empty** — it does one pair per person per run |
| 5.2 | **Duplicate People** (`/duplicates`) | Same surname letter-for-letter, same first forename, born within two years |
| 5.3 | Admin tools → **Remove census rows a second import left behind** → `Preview` → `Run` | One person with two rows for one year, one filed and one still on the unfiled page |
| 5.4 | Admin tools → **Remove duplicate resident links** → `Preview` → `Run` | The same person linked to the same house twice |
| 5.5 | Admin tools → **This census record is somebody else of the same name** → `Preview` → `Run` | Where an import has hung a servant on somebody who merely shares her name |

**5.6 — the ones no tool can see.** Both the tools above bucket on the surname *letter for letter*,
so a duplicate created by two spellings of a surname — Crendson beside Crewdson, Flersheim beside
Hersheim, Throsheim beside Frosheim, Slack beside Black — is invisible to them. Ask Claude to run
the variant-spelling check after every import; it comes back as a spreadsheet of pairs to confirm.

---

## 6. Birth places and the map

**6.1** Admin tools → Fill gaps from the census → **Copy birth places onto people** → `Preview` →
`Run`. Anyone whose returns disagree with each other is left alone and listed for you to settle.

**6.2** If the round brought Nottingham parish spellings in — *St Mary, Nottingham*, *Nottingham
(St Peter)* — flatten them first, or they geocode against a church:

```bash
railway run python3 fix_nottingham_parishes.py
```

then again with `--apply`.

**6.3** Then, in this order:

```bash
railway run python3 apply_geocode_cache.py --apply
```

```bash
railway run python3 geocode_birth_places.py
```

The first costs nothing and needs no network — it copies positions the record already knows onto
the new rows. The second only looks up what is genuinely new.

**6.4** Now check the answers, because the geocoder returns the best match **in the world**:

```bash
railway run python3 check_geocode_sanity.py
```

It flags anything outside the British Isles whose text names nowhere abroad — Lincoln in Nebraska,
Brighton in New Jersey, Wellington in New Zealand — and the reverse mistake.

**6.5** Position what it found by hand in `data/geocode_manual.json`, then:

```bash
railway run python3 force_geocode_manual.py --apply
```

```bash
railway run python3 apply_geocode_cache.py --apply
```

Both are needed. The server seeds that file at start-up but **will not overwrite a place the
geocoder marked `found`**, so a hand position alone sits inert against a wrong answer.

**6.6** **Birthplace Geocoding** (`/admin-birthplaces`) for whatever is still unplaced, then the
**Origins** map (`/origins`) for a look. A pin on the wrong continent is obvious there and nowhere
else.

---

## 7. Houses

| | where | |
|---|---|---|
| 7.1 | **Unfiled Census Records** (`/unfiled`) | Gathered by the address they carry, so a whole address settles in one click |
| 7.2 | **Crowded Houses** (`/crowding`) | An improbable number in one house is usually several households filed against one address |
| 7.3 | **Directories by Street** (`/directory-check`) | Sets the new households beside what Wright's prints on that street |

**7.4** And what the import closed, and what it did not:

```bash
railway run python3 census_gaps.py --year 1901
```

Every house the record holds before and after that year but not in it, with **the head of the
household when the record last saw the house** — which is what finds the family on the missing
return. A gap flanked by the same family is a transcription job; a gap flanked by two different
families is a move, and wants the directory. `--xlsx` writes it to the Desktop.

---

## 8. The outside world

New people mean new candidates. These search *only* people whose entry already suggests something,
so they stay cheap.

| | where | |
|---|---|---|
| 8.1 | Admin tools → The Gazette → **Extract Gazette references** → `Preview` → `Run` | Turns Gazette links written into biographies into proper citations |
| 8.2 | Admin tools → The Gazette → **Search The Gazette for honours** → `Preview` → `Search` | Only people whose entry suggests an honour or public office. Takes a few minutes; running it again picks up where it stopped |
| 8.3 | **Gazette notices** (`/gazette-review`) | Confirm or dismiss. A search cannot tell one John Smith from another |
| 8.4 | Admin tools → Medal index cards → `Preview` → `Search` | First World War cards at The National Archives, series WO 372, against anyone with a rank, a corps or a death in a war period |
| 8.5 | **Medal cards** (`/medals-review`) | A card gives no birth year, so nothing is written to anybody until you say so |
| 8.6 | **Wikidata Review** (`/wikidata-review`) | Every resident without a Wikipedia link, in one pass. A shared name is not an identification — open the article |
| 8.7 | **Notable Residents** (`/significant`) | Anyone the import brought in who belongs here. Twelve people carry the mark; a professor, a city architect or a mayor is worth the thirteenth |
| 8.8 | **Dougal's Map** (`/map-review`) | Only if the import brought house names in |

---

## 9. A last look

**9.1** **Insights** (`/stats`). The totals should have moved by roughly what the import said it
added at stage 0. If they have not, something did not land.

**9.2** **The Working List** (`/tasks`). Anything the import raised that nobody can finish today
belongs there, or in the research questions, rather than in somebody's head.

**9.3** Anything the round could not answer goes to Claude for a research question, with the
evidence that exists and the test that would settle it.

---

## What Claude does, unasked, after every import

So that none of the above waits on a reminder:

1. The **variant-spelling duplicate check** (5.6) — a spreadsheet of pairs.
2. The **ditto-mark surname check** (4) — every person whose surname is a bare initial, traced back
   to the head of the house they were returned in.
3. **`census_gaps.py`** for the year just imported (7.4) — what closed, what is still open, and the
   head of each house when the record last saw it.
4. A read of the new rows for **anyone of interest** — an unusual trade, a public office, a foreign
   birth, a household that does not behave like a household.
5. Whatever the round raised, written into `data/research_questions.json`.
