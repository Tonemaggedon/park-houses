# Nottingham Park Houses — handover

A historical record of The Park estate, Nottingham, for The Park Conservation Trust.
Properties, residents, census returns, and the sources behind them.

- **Live:** https://park-houses-production.up.railway.app
- **Repo:** https://github.com/Tonemaggedon/park-houses (branch `main`)
- **Local:** `/Users/antonyhagues/Claude Projects/park-houses`
- **Host:** Railway — auto-deploys on push to `main`
- **Last verified:** 13 September 2026

---

## Security rules — these are not negotiable

- **Never commit a secret.** No API keys, no passwords, no database URLs in any tracked
  file — including this one. Every secret lives in Railway → Variables.
- **Never write the `DATABASE_URL` down.** Not here, not in a note, not in a chat. The app
  reads it from the environment. If it has been pasted somewhere, rotate it in Railway.
- The Google Maps key is `GOOGLE_MAPS_KEY` in Railway Variables, nowhere else.
- **Tony pushes.** Changes reach production when he runs `git push`, not before.

### Environment variables (names only — values live in Railway)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection. Unset locally → JSON fallback (see below). |
| `SESSION_SECRET` | Signs session cookies. **Changing it logs everyone out.** |
| `ADMIN_USER` / `ADMIN_PASS` | Admin login. Production refuses to start on the default password. |
| `NODE_ENV` | Must be `production` on Railway — it gates secure cookies, `trust proxy`, and error masking. |
| `GOOGLE_MAPS_KEY` | Map tiles. |
| `CLOUDINARY_*` | Photo/video uploads. Optional — uploads fall back to local disk. |
| `PORT` | Set by Railway. |

---

## Running it locally

```bash
npm install
npm start
```

With no `DATABASE_URL`, the server falls back to JSON files in `data/`. Pages render and
the map works, but **anything Postgres-backed returns 500** — people, census, the admin
jobs. That is expected, not a bug.

To exercise the real thing, point `DATABASE_URL` at a throwaway local Postgres. Never at
production.

---

## Shape of the thing

- `server.js` — the whole backend. ~7,650 lines, 222 endpoints, Express 5.
- `public/*.html` — 34 files, one per page, no build step, no framework. Plain HTML/CSS/JS.
- `public/img/` — one asset: a 2400px render of Dougal's map, shown on `/map-review`.
- `data/*.json` — seed and reference data. `all_props.json` is the property list
  (413 properties, including demolished ones). 77 files in all.

### Two sources of truth for property positions — read this before touching coordinates

`data/all_props.json` holds a **base** coordinate for each property. Separately, roughly
396 **manual placements** live in the database and are served by `/api/coords`; those are
Tony's corrections and they win on the map.

Comparing a property against `all_props.json` alone will tell you it is in the wrong place
when it is not. **Always check `/api/coords` first.** This has caused a wrong bug report
before.

---

## Conventions worth keeping

**Suggest, don't assign.** Every external source — Historic England, Wikidata, The Gazette
— produces *suggestions* a human confirms. A national record returns a different person of
the same name for most residents, so nothing external is ever written in as fact. The
review pages (`/gazette-review`) exist for exactly this.

**Every job previews first.** Admin jobs take `{ "dryRun": true }` and the preview must
report precisely what the real run will do. Two of them once over-reported; both were
fixed. If you add a job, make the dry run exact.

**Jobs are idempotent.** Running one twice must not duplicate anything.

**Escape at assignment.** Pages build markup with `innerHTML`, so every value goes through
`esc()` *where it is assigned*, not where it is concatenated. Escaping late has silently
failed here before — a payload still fired through a local variable. Inline `onerror` /
`onclick` in `innerHTML` markup **does not run**; attach listeners instead.

---

## Admin tools (dashboard, admin only)

| Tool | What it does |
|---|---|
| Import bibliographies | Loads a prepared works list from `data/` onto a person. |
| Backfill census occupations | Copies occupations off census entries onto people. |
| Extract Gazette references | Turns Gazette links in biographies into proper citations. |
| Search The Gazette for honours | Sliced search (6 at a time — the whole run times out). |
| Import people | Adds people prepared in `data/`, matched by name. |
| Find rows that are not people | Lists header rows and blanks that survived an import. |
| Remove duplicate census rows | Cleans rows a re-run created before the dedupe was fixed. |
| Split a conflated person | Lifts a census record off the wrong person onto a new one. |
| Merge abbreviated names | Joins "Geo. Parr" to George Parr, keeping the fuller record. |
| Medal index cards | Searches The National Archives (WO 372) for people with a rank, a corps, or a war-period death. |

Review queues — every one of these suggests and never assigns:
`/gazette-review`, `/wikidata-review`, `/name-sex`, `/name-review`, `/census/unresolved`,
`/duplicates`, `/map-review` (Dougal's map), `/medals-review` (WO 372 medal cards),
`/directory-check` (Wright's Directory by street).

### Trade directories

`data/directory_park_entries.json` holds every householder Wright's Directory of Nottingham
prints on a Park street in 1894-95, 1898-99, 1910-11, 1913-14 and 1915-16. `read_from_scans`
names the volumes transcribed from the page images at Leicester Special Collections; any other
volume is the older machine reading of the page text and is marked as such on the pages.
Three places read it:

- `/unfiled` — each unfiled head of household is looked up by surname in the directory years
  nearest its census; a match on the street the return names becomes a suggestion.
- `/directory-check` (`/api/directory/street-check`) — every entry placed on a house by its
  printed number or a house name the record knows (including a second address such as
  "1 Clinton Terrace (127 Derby Road)"), then set beside the nearest census: agrees / elsewhere /
  new / different / unplaced.
- Each house's timeline (`/api/property/:id/directory`).

- `/directory-people` (`/api/directory/people-check`) — the same lines matched to census
  people anywhere in The Park, grouped by surname, with each person's census and directory
  sightings in date order. Forenames and any middle initial must agree; servants, visitors
  and boarders are never matched. Same person / Not them decisions live in
  `directory_person_review` and change nothing else.
- `/directory-watch` (`/api/directory/watch`, `data/directory_watch.json`) — architects and lace
  makers followed through their own alphabetical entries in every Wright's Nottingham volume
  (1858–1915-16), wherever they lived, flagging the first address in The Park. Built from
  the page text by `scripts/directories/dir_watch.py`; rerun it after adding architects or
  lace makers to the record.

Derby Road, Lenton Road and Park Row run well past The Park; only the numbers and house names
the record has on them are kept. Rebuild with the scripts in `scripts/directories/` (see its
README).

---

## Outstanding

**Data**
- **1911 birth places are 36.5% populated**, against 98.1% for 1921 — the origins map is
  missing two-thirds of that year. Tony is correcting the 1911 spreadsheet by hand,
  record by record, as he did for 1921.
- **Cedar Lodge and Clumber Court** are flagged `census_only` but have no census entries.
- **Two records are both called Parkdale** (297 and 299), 46m apart. Likely one property.
- **The Hermitage** — the placement and the OS-sheet position are 48m apart.
- Properties visible on the OS sheets with no record yet: Penrhyn Cottage, Belwood,
  The Lodge, Dudley Lodge, and a gap near Carnoustie Lodge.

**Code**
- Reconcile the `all_props.json` base coordinates against the manual placements, so there
  is one source of truth rather than two (see the warning above).
- `server.js` is a 4,400-line monolith. It works, and splitting it is a real risk to a
  live site — but it is the main thing standing between this and easy maintenance.
- `/api/person/:id` with a non-numeric id returns 500 from Postgres rather than 400.

---

## Deploying

```bash
git add <files>
git commit -m "message"
git push
```

Railway builds on push. After a deploy touching routes, check a page, the catch-all
(`/nonsense` should return the map, not a 404), and that an unauthenticated
`POST /api/admin/import-people` still returns 401.
