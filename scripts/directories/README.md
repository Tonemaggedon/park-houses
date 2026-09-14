# Rebuilding the trade-directory index

`data/directory_park_entries.json` is built from Wright's Directory of Nottingham page scans
held by the University of Leicester (Special Collections Online, collection p16445coll4).

1. `python3 dir_headers.py` — fetches each volume's page text once (cached in `dir_pages/`)
   and records every page's headings in `dir_headers.json`, used to find each street's pages.
2. `python3 dir_tiles.py <volume> <page> ...` — downloads a page scan and cuts it into four
   full-resolution quarters in `dirscans/<volume>/`.
3. Transcribe: `dir_reader_brief.md` is the brief each reader followed, one volume at a time.
   Output is `dir_read_<volume>.json` here — kept in the repo as the transcription of record.
4. `python3 dir_read_audit.py` — flags streets with too many entries, house numbers the site
   doesn't have, and a high share of doubtful lines.
5. `python3 dir_convert.py <volume> ...` — replaces those volumes in the index; any volume not
   named keeps what it had.

`dirscans/`, `dir_pages/` and `dir_headers.json` are working files and are not committed.
