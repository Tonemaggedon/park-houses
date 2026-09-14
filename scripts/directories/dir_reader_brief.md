# Reading The Park's streets out of Wright's Directory of Nottingham

You are transcribing, from page scans, the street-directory listings for the roads of
The Park estate, Nottingham, in ONE volume of Wright's Directory. The result feeds a
local-history site that matches directory householders against census households, so
**a wrong entry is far worse than a missing one**. Never guess a number or a name you
cannot read — leave it null and say so.

## Files
- Scans: `scripts/directories/dirscans/<VOLUME>/p<page>_tl.jpg`, `_tr`, `_bl`, `_br` — four overlapping
  quarters of each page at full resolution (top-left, top-right, bottom-left, bottom-right).
  Pages run in two or three columns; a column continues from the bottom of one column to
  the top of the next, and from the last column of a page to the first column of the next page.
- Candidate pages per street: `scripts/directories/dir_read_plan3.json` → `["<VOLUME>"][street]`.
  The candidates are an estimate from the page headings; the street may start a page
  earlier or later. Streets are in alphabetical order through the volume (ignoring "The"),
  so if you see streets that sort before/after yours, move accordingly. If a page you need
  isn't downloaded, run: `python3 scripts/directories/dir_tiles.py <VOLUME> <page>` (from any directory).

## Streets to find (the Park's streets as the site names them)
Albury Square, Barrack Lane, Castle Grove, Cavendish Crescent North, Cavendish Crescent South,
Cavendish Road East, Clare Valley, Clifton Terrace, Clinton Terrace, Clumber Crescent North,
Clumber Crescent South, Clumber Road East, Clumber Road West, Derby Road, Derby Terrace,
Duke William Mount, Fish Pond Drive, Hamilton Drive, Hardwick Road, Hermitage Walk,
Holles Crescent, Hope Drive, Huntingdon Drive, Kenilworth Road, Lenton Avenue, Lenton Road,
Lincoln Circus, Maxtoke Road, Newcastle Circus, Newcastle Drive, Newcastle Terrace,
North Road, Park Drive, Park Ravine, Park Row, Park Terrace, Park Valley, Pelham Crescent,
Peveril Drive, South Road, Tattershall Drive, The Ropewalk, Tunnel Road, Western Terrace.

Notes:
- The directory may print "Cavendish crescent" with "North side"/"South side" sub-headings,
  or "Clumber road" with East/West. Record the site street name that applies; if the
  side is not stated, use the directory's own name in `street` and set `side_unclear: true`.
- Derby Road, Lenton Road and Park Row are long and run outside The Park. Transcribe the
  whole listing anyway; the site will filter by house number.
- "North Road" and "South Road" are common names — make sure the heading's locality
  bracket (e.g. "(Park)" / "(The Park)" or the connecting streets) fits The Park; record the
  bracket text in `heading_note` either way.
- A street absent from this volume is fine: list it in `not_found` with the pages you checked.

## What to record
For every line of a Park street's listing, in printed order:
- `no`: the house number as printed (string, e.g. "7", "33a"), or null.
- `house_name`: the italic house name if printed (e.g. "Gleadthorpe"), else null.
- `name`: the householder exactly as printed but with abbreviations kept (e.g. "Jno. M'Craith",
  "Mrs. Elizabeth Bailey").
- `occupation`: as printed, or null.
- `kind`: "resident" | "business" (a firm, school, church, club etc.) | "cross_street"
  (the italic "......Tunnel road......" style lines marking a side turning) | "note".
- `side`: the side/sub-heading in force ("North side", "odd numbers" …) or null.
- `unsure`: true if any part of the line is doubtful; add `note` saying what.
- `page` and `tile` where the line is.

Continuation lines (a line indented under the previous one) belong to the previous entry —
join them, don't make a new entry.

## Output
Write ONE JSON file: `scripts/directories/dir_read_<VOLUME>.json`:
```json
{
  "volume": "<VOLUME>",
  "streets": [
    {"street": "Cavendish Crescent North", "directory_heading": "Cavendish crescent (Tunnel road ...)",
     "heading_note": "...", "side_unclear": false, "pages": [44],
     "entries": [{"no": null, "house_name": "Gleadthorpe", "name": "Jno. M'...", "occupation": null,
                  "kind": "resident", "side": null, "unsure": false, "page": 44, "tile": "tr"}]}
  ],
  "not_found": [{"street": "Albury Square", "checked_pages": [18, 19]}],
  "notes": "anything the site owner should know"
}
```
Write the file incrementally (after each street) so work survives an interruption.
When done, reply with a short summary: streets found, entries per street, not found, and
anything doubtful. Do not reply with the transcription itself.
