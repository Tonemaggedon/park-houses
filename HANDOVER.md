# Nottingham Park Houses — handover

A historical record of The Park estate, Nottingham, for The Park Conservation Trust.
Properties, residents, census returns, and the sources behind them.

- **Live:** https://park-houses-production.up.railway.app
- **Repo:** https://github.com/Tonemaggedon/park-houses (branch `main`)
- **Local:** `/Users/antonyhagues/Claude Projects/park-houses`
- **Host:** Railway — auto-deploys on push to `main`
- **Last verified:** 8 September 2026

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

- `server.js` — the whole backend. ~4,400 lines, 158 endpoints, Express 5.
- `public/*.html` — one file per page, no build step, no framework. Plain HTML/CSS/JS.
- `data/*.json` — seed and reference data. `all_props.json` is the property list
  (403 properties, including demolished ones).

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

Review queues: `/gazette-review`, `/name-sex`, `/census/unresolved`.

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
