# Outside sources worth wiring in

*What the record could pull from, and which of it actually answers when you knock. Checked
22 September 2026. Anything marked **verified** was called from this machine and returned
what it should; anything marked **unchecked** is real but its current address or terms need
confirming before you build on it.*

The test for including something here is not that it exists. It is that it would answer a
question this record is actually stuck on.

---

## Already in use

| source | what it gives | notes |
|---|---|---|
| **Nominatim** (OpenStreetMap) | birthplace positions | **verified**. Rate-limited to 1/second and that limit is enforced. `data/geocode_manual.json` exists because it answers Acton, Massachusetts when you mean Acton, Middlesex |
| **Wikidata SPARQL** | notable people born, died or resident in Nottingham | **verified**. No key |
| **The Gazette** | commissions, bankruptcies, probate notices | feeds Gazette review |
| **Historic England NHLE** | listed building text and grades | `data/nhle.json` |
| **Medal index cards** | First World War service | feeds Medal cards |

---

## The three that would change the most

### 1. National Library of Scotland historic maps — *the estate as it was, under the pins*

**unchecked** — the host answers but rejected the path tried here, so get the current tile
URL from `maps.nls.uk` rather than from this note.

The NLS publishes **georeferenced Ordnance Survey maps as standard XYZ tile layers**, which
Leaflet can take as a base layer with one line. For this record the useful ones are the OS
**six-inch and twenty-five-inch** sheets of the 1880s to 1910s — the estate at exactly the
moment the census rounds were taken.

**Why it matters more than it sounds.** Every unplaced household in the 1911 round is a house
that existed and had a name. The property list was built from modern numbers. **A period OS
sheet under the map shows the plots as they were**, with the lodges, the stables and the
gardens that later became separate houses — which is precisely what *Clare Valley Lodge*,
*Elmsdale*, *Goddards Lodge*, *The Lodge at Castle Grove* and the missing 1, 2 and 3 Castle
Grove need.

Free for non-commercial use with attribution. **Check the licence text yourself** before it
goes on a public page.

### 2. GB1900 gazetteer — *place names as they were written*

**unchecked.** A free, CC-BY download of **around 2.5 million place names transcribed from the
OS six-inch maps of about 1900**, each with a position.

**This is the fix for a fault this record hits constantly.** Birthplaces are written as the
householder knew them in 1911, and geocoded against a gazetteer of 2026. That is why
*Handsworth* had to be pinned by hand, why *Hammersmith, Middlesex* and *Montrose,
Forfarshire* needed manual positions, and why *Ferry Bogg*, *Humby Moor*, *Rickworth* and
*Dodderhope* all had to be puzzled out one at a time.

**A gazetteer contemporary with the census would match the spelling the census used.** It is a
download rather than an API, so it would live beside `geocode_manual.json` and be consulted
first.

### 3. National Archives Discovery API — *the paperwork behind the houses*

**verified.** Returns JSON, needs **no key**, and searches TNA's own catalogue plus around
2,500 other archives — **including Nottinghamshire Archives**.

```bash
curl -s -H "Accept: application/json" \
 "https://discovery.nationalarchives.gov.uk/API/search/records?sps.searchQuery=%22Park%20Estate%22%20Nottingham&sps.resultsPageSize=5"
```

The first result it returned when tested was a record titled **Nottingham Park Estate**.

**What it would answer:** deeds, leases, plans and estate papers name builders, architects and
first occupiers, which is how a house gets a date and a name that the census never gives. It
would also put a *Search the archives* button on a property page for nothing.

---

## For people the record loses track of

### Probate — the biggest single gain available

The record holds a death year for **133 people out of 4,527**. Probate calendars from 1858
give, for most people who left anything, **the date of death, the address at death and the
value of the estate** — three facts the census never supplies.

`gov.uk/search-will-probate` has **no API**, so this is a by-hand or scripted-carefully source
rather than something to wire in. But it is the answer to every *no death is recorded for her
and this gives a ten-year window* note in the 1911 round — Ellen S. Payne, Alice A. Howard,
Louisa H. Topham, Ernest B. Meldrum, Robert Dudley Walker, Lawrence Wilkins.

### General Register Office birth index

**unchecked, and the reason to look.** The GRO's own online index gives **the mother's maiden
name** for births, which the commercial indexes do not.

That is exactly what would settle [[wilkins-girls-named-twice]] — whether 4 Clare Valley held
Eleanor and Jessie or Joyce and Mary, or four girls. It would also settle the two Mary Saxbys.

### Commonwealth War Graves Commission

**unchecked — it returned 403 to a script**, so it wants a browser or an agreed route rather
than a crawl.

The record already holds medal cards. CWGC adds **the death, the unit, the cemetery and the
next of kin**, and next of kin is often the link that ties a soldier back to a house. Given
how many young men are in the 1911 round who would be of age in 1914, this is a real gap.

### FamilySearch

A genuine, documented API, but it **needs a developer key and an affiliation**. Worth knowing
exists; not worth building against on spec.

---

## For buildings and architects

- **RIBA Directory of British Architects 1834–1914** — not an API, but the reference that
  would turn [[albert-nelson-bromley-architect]] from one house into a list of them.
- **Picture the Past** (`picturethepast.org.uk`) — the Nottinghamshire and Derbyshire image
  archive, and the source of the photographs in the Civic Society's Bromley account. Worth a
  look for images of Park houses.
- **Nottingham Civic Society archive** — the Bromley account came from here. There are others.

---

## Two cautions

**Rate limits are real and the polite thing is also the safe thing.** Nominatim's one request
a second is enforced by blocking. Anything bulk belongs in a nightly job with a cache, not in
a page load.

**Licences differ and some of this is public.** The record is a public website. A source that
is free for personal research is not automatically free to republish. Check before a source's
data appears on a page rather than after.
