# Finding a census record

*What works, what does not, and why the 1911 census behaves differently from all the others.*

---

## The one that catches everybody: 1911 is not arranged like the rest

**1841 to 1901** are the **enumerator's books**. A clerk walked a district, copied every household
into a bound book in the order he walked it, and the unit is the **enumeration district**. That is
why a street runs continuously down the page, and why finding one household on a street gives you
the rest of it by turning the page.

**1911 is the householders' own schedules.** Each family filled in its own form, in its own hand,
and signed it. There is no book. The forms are filed as **RG14 piece number + schedule number**, and
the piece is what corresponds to an enumeration district.

**So the *Enumeration district number* box does not work for 1911.** It exists for the earlier
censuses. For 1911 it is usually empty in the index, so filling it either does nothing or returns
nothing. Searching registration district 430, sub-district 1, enumeration district 11 returned
**38,140 results** - which is the whole of sub-district 1, not a district of a few hundred houses.
The enumeration district filter was simply being ignored.

**A sanity check worth doing every time:** an enumeration district holds a few hundred households,
so somewhere between 1,000 and 2,000 people. Any result in the tens of thousands means a filter is
not biting.

---

## For 1911, search the street

The 1911 index carries the address, so this is the direct route and it needs no district numbers
at all:

| field | value |
|---|---|
| **Street** | Newcastle Drive |
| **County** | Nottinghamshire |
| *everything else* | **clear it** |

That returns the street, and it can be worked down house by house against the gap list.

## Or the piece number, for a whole round

To fetch an entire 1911 walk rather than one street:

1. Open the transcript of a household already found on that round.
2. Read the **piece number** from the details - the image reference reads `RG14/` and five digits.
3. Search on **piece number alone**.

That returns the whole round in schedule order. Schedule numbers are close together within a
street: 5, 7 and 9 Newcastle Drive came back as schedules 11, 14 and 18, with the coach house
behind number 5 at 17.

---

## The Park is not one district

There is no single round that covers the estate. Three different 1911 references are already in
this record:

| registration district | sub-district | enumeration district |
|---|---|---|
| 430 | 1 | 11 |
| 430 | 6 | 16 |
| 430 | 6 | 66 |

So the estate is split across at least two sub-districts and several districts. **Street by street
is less work than district by district**, and it has the advantage of matching the way the gap list
is organised.

---

## Reading a 1911 schedule

Things on a 1911 form that no earlier census gives:

- **The householder's own handwriting**, and his signature at the foot. The spellings are the
  family's own, which is worth more than an enumerator's ear.
- **Three questions to every married woman**: how many years the present marriage has lasted, how
  many children were born alive to it, and how many are still living. Those three numbers name a
  family's size even when the children are not in the house.
- **The number of rooms**, written at the foot by the householder.

**But the schedule carries no address.** Only the enumerator's summary book does. The address is on
the **cover** of the schedule - a separate image, filled in by the enumerator, giving the district
numbers, the head's name and the postal address. **Always look at the cover.** The coachman's
household behind 5 Newcastle Drive could not be placed at all from the form itself; the cover said
*Back of 5 Newcastle Drive*, written over a struck-through *Huntingdon Drive*.

### Always write down the schedule number

It is printed in the **top right corner of every schedule**, and it is the only thing that puts the
households of a piece in the order the enumerator walked them. **Write it down every time**, even
when the address is perfectly clear - it costs nothing at the time and cannot be recovered later
without opening every image again.

**Why it matters:** a household whose cover gives no number, or names a house the property list
does not hold, can still be placed by its *neighbours*. Schedule 71 and schedule 73 are the houses
either side of schedule 72 on the ground. Without the numbers, an unplaceable household stays
unplaceable; with them, it is boxed in between two known addresses.

The order the images are worked in is **not** a substitute. It records backtracking - going back
for a house that was skipped, or fetching one out of turn - and in the Park Valley and Tattershall
Drive rounds it did exactly that.

### And the enumerator's summary book places everything at once

The schedules are the return; the **summary book** for the same piece lists every schedule in order
with its address. One document places every household the covers could not - which on the 1911
round so far means Goddards Lodge, three unnumbered Tattershall Drive houses, a Park Valley house
given as 12 or 13, Clare Valley Lodge, Elmsdale and 5 North Road. **Fetch the summary book before
transcribing a long run**, not after.

---

## Reading an enumerator's book, 1841-1901

- **The house column is ruled down with ditto marks.** So is the surname column. A ditto is not a
  value: a transcription that reads one as a value produces people with a middle initial for a
  family name. See `post-import-checklist.md`, stage 4.
- **A household can run across a page turn.** The second half then begins with somebody who is not
  the head - often a boarder or a servant - and looks like a separate household with no head. It is
  not. Beechwood on the 1901 Hamilton Drive round is the example: fifteen people read as two
  households of five and nine until the page turn was spotted.
- **Schedule numbers are the enumerator's walk, not the street's numbering**, and he doubles back
  for back premises, coach houses and flats over stables. Do not infer a position from a schedule
  number when an address exists.
- **Streets change their names.** Newcastle Drive was Pelham Terrace, and the conversion is
  **Newcastle Drive number = 39 minus the Pelham Terrace number**.

---

## Cross-checking a reading

Three sources will usually settle a doubtful reading without going back to the image:

1. **The record's own neighbouring censuses.** A household in 1891 and again in 1911 fixes the
   spelling of every name in between.
2. **Wright's Directory of Nottingham**, already transcribed into this record, which prints
   householders by street and often by number.
3. **The index on the site you are searching**, which is a second person's reading of the same
   hand. Where it disagrees with mine, it is worth a third look - it caught Arthur Lewis's age,
   which I had read as 44 against the index's 41, and the record already held 41.
