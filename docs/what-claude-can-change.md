# What Claude can and cannot change

*The division of labour between import files and the site itself.*

Everything Claude adds to the record goes in as a JSON file under `data/`, which an admin then
imports from the dashboard. That route is deliberately conservative: it creates and it fills gaps,
but it never overwrites, never renames and never moves anything that is already placed. Those
actions stay with a contributor signed in to the site.

## The short version

| Task | Who does it | Why |
| --- | --- | --- |
| Add people, households, censuses | Claude, by import file | Creating is safe; nothing is displaced |
| Fill in blanks on existing records | Claude, by import file | Blank fields only, never a value you entered |
| Move a census row to a house | You, on the site | An import would add a second row, not move the first |
| Unfile a household | You, on the site | Same reason |
| Merge two people | You, on the site | Imports cannot delete or combine records |
| Correct a name | You, on the site | An import never renames anybody |
| Change a wrong value | You, on the site | An import never overwrites |
| Create a new property, or set its base fields | Claude, in the repo — **but only when asked** | Properties live in `data/all_props.json`, and a name is not a house |
| Edit a property through the site | You, on the site | Site edits go to a separate override layer |
| Research questions | Claude, by data file | They live in `data/research_questions.json` |
| Code, scripts, directory tooling | Claude, in the repo | Normal development, pushed to main |

## What an import file can do

### Create people

Forenames and surname, sex, birth year, date and place, death date, year and place, a biography,
maiden name, title, letters after the name, and a Wikipedia link. Anyone created this way is new;
nothing existing is touched.

### Attach to people already in the record

- **By number** — the surest way. The file quotes the id and the importer binds to that person.
- **By name and birth year** — matches only when both agree exactly. A year out and it will not
  match, which is why some people have to be merged by hand afterwards.
- **By name alone** — only when that name is unique in the record.

### Fill blanks, never overwrite

On a person: birth and death details, sex, biography and the rest — but only where the field is
empty. On a census row already in the record: relationship, age, occupation, birthplace, marital
status, address and source, again only where empty. An occupation reading merely "Male" or "Female"
counts as empty, since that is the sex written into the wrong column.

### Occupations, censuses, families, houses

- **Occupations** are keyed on the job title and its start year; a blank employer, note or end year
  gets filled.
- **Census rows** are keyed on person, year and house. A new row is added where none exists; where
  one exists, its blanks are filled.
- **Unplaced households** can be added with the address the return gives, so they arrive on the
  unfiled page named rather than in the "no address recorded" heap.
- **Relationships** — parent and child, spouse, sibling. The reverse link is written automatically,
  and siblings and grandparents are inferred from parent links.
- **Resident links** between a person and a house.

## What only a contributor on the site can do

- **File, move or unfile a census row.** This is the important one. If a house number is put on a
  row that is currently unfiled, the importer does not move it — it creates a *second* row at that
  house and leaves the unfiled one where it was.
- **Merge two records into one.**
- **Rename anyone**, or correct a name that came in wrong.
- **Change any value that is already filled in**, however plainly wrong it is.
- **Delete anything at all.**
- **Upload photographs.**
- **Press Import.** The dashboard's import button needs an admin session, and Claude never enters
  anybody's password. Every file Claude writes waits for A. Hagues to press it.

None of this is a permissions problem to be worked around: those endpoints need a contributor
login, and Claude does not use anyone's credentials.

## Properties are the exception, and they have two layers

Property records are not in the database the way people are. The base record of every house lives
in **`data/all_props.json`** in the repo, which is the file the map and the property list are served
from. Claude can edit that file directly, so **creating a property and setting its base fields is
something Claude can do** — The Cottage in the grounds of Lincoln House (#414) was added that way.

Edits made through the site go somewhere else: a `property_data` table in production, or
`data/property_overrides.json` when running on files. That store is keyed by property id and is read
for a single property's detail, not for the list. So the two layers sit side by side rather than one
overwriting the other, and a field edited on the site is held separately from the base record.

The practical consequence: ask for a new property, or a correction to a base field, and Claude can do
it in the repo. If a house has been edited on the site and the change does not appear, the override
layer is the place to look.

### But a name is not a house, and Claude never adds one unasked

Because the file is a file, adding a house is easy, which is exactly why it is not done. **A house
name arriving from a map, a residents' association, the Land Registry or a directory is a lead, not
a property.** It is written down as a lead and brought to A. Hagues with what is known; he decides
whether a house exists behind it.

Two things make this less obvious than it sounds. **The same name turns up on two different houses
in different eras** — Barton House is on Lenton Road on the map and is the house name of 1
Huntingdon Drive in the record, and both are right. And a name in use today may belong to a building
put up in 1990: of the names the Park residents' association supplied, eight matched houses already
in the record and fifty-six did not, and not one of the fifty-six was created.

## What the site will not accept, however it is asked

These are enforced in the server, not just in the form, so they hold whether a thing arrives from a
person, from Claude, or from a script.

- **A new person must be complete enough to show they are historical**: first name, surname, year of
  birth, place of birth — and a year of death if they were born in the last hundred years. The
  record is public and holds people who have died.
- **Editing an existing person is exempt**, because most people who came in with the census have no
  birth place and demanding one would block ordinary corrections. **Census imports are exempt** for
  the same reason: they are historical documents arriving whole.
- **The research tools that change many records at once are admin-only**, as is normalising
  occupations and merging people in bulk.
- **An account is limited in how fast it can write.** An ordinary contributor gets a handful of
  changes in a few seconds and a few hundred in an hour; an admin gets far more, because the bulk
  tools are theirs. Anything over the line raises an alert on the Activity page rather than
  disappearing silently.

## Five traps, all of which have bitten us

| What happens | How to avoid it |
| --- | --- |
| A house number on an unfiled person's row makes a duplicate census row instead of moving it | Such rows are left unfiled and the reassign step handed over. This is how Kneebone was handled. |
| The duplicates tool only offers people whose birth years match exactly | Where a record differs by a year — Herbert Bradley, William Henry Foster — it is flagged for a hand merge. |
| An import never renames, so a misspelling stays | John *Kenish* Wright is still waiting on a correction only the site can make. |
| Notes written in an import file never reach the database | They are documentation for the repo. Anything that must show on the site goes in a field or a research question. |
| A name on a map or a members' list read as a house that exists | It is a lead until something places it. Fifty-six of the residents' association's names are still leads. |
| A wrong value supplied cannot be corrected by a later import | Which is why uncertain readings are flagged rather than entered as a guess. |

## What Claude can do away from the record

- Write and change the site's code and push it.
- Add and edit research questions, which are data files and do appear on the site.
- Run the directory tooling — rebuilding the street index and the architects' and lace makers'
  watch list.
- Read the live site through its public API, which is how a house is checked before anything is
  written.
- Read the trade directory scans and the cached pages from Leicester.
- Write the contributor's guide, which is `docs/contributor-guide.md` and is rendered on the site at
  `/guide` from that one file. `tools_build_guide_email.py` turns the same file into the emailable
  copies; run it again after editing the guide.

## How a household normally travels

You send a transcription or a page image. Claude checks the house against the record and the
directories, looks for everyone already held, and writes the file — binding by number where a match
is certain, flagging it for a merge where it is close but not certain, and leaving the household
unfiled rather than guessing an address. It is pushed. You import, then do the parts only you can:
the reassigns, the merges, the property fields. Anything unresolved goes into the research questions
so it is not lost between you.
