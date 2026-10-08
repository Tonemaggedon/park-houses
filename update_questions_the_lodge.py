# -*- coding: utf-8 -*-
"""The Lodge question is answered the other way round, and a new fault is recorded."""
import json
d = json.load(open('data/research_questions.json'))
Q = {q['slug']: q for q in d['questions']}

q = Q['the-lodge-on-tattershall-drive-is-not-gartree-lodge']
q['priority'] = 5
q['title'] = "ANSWERED - The Lodge on Tattershall Drive IS Gartree Lodge, and I argued against the record's own answer"
q['detail'] = """**Settled 8 October 2026 by A. Hagues: The Lodge does not exist as a separate house. It is Gartree Lodge.** #436 is folded into #404 and gone, the two Kerrs are filed at Gartree Lodge, 17a Tattershall Drive, and the 1939 empty mark that house was carrying has been lifted - it was never empty, its household was sitting under the other property.

**This question was wrong, and the way it went wrong is the point.**

## The record already held the answer

Gartree Lodge's own notes say it, and said it before this question was written:

> It is 17a Tattershall Drive and goes by The Lodge now, which A. Hagues has confirmed on the ground. The Lodge that HM Land Registry holds on this street is therefore this house, not the lodge by the tennis ground.

So does [[lr-tattershall-drive]], in as many words. I did not read either. I read the 1939 walk, built a case from it, and put the case up against a fact the record had already written down and attributed to the person asking.

## And the 444 metres was measured to a point I invented

The figures in this question - 444 metres apart, 45 metres from Charnwood, 18 metres from Carnoustie Lodge - are distances between **one confirmed position and one of my own guesses**. #436's position came from nothing but the schedule order. Its history said so, in bold: *the position is provisional*. By the next day the coordinates had been quoted back as corroborating evidence, with the caveat left behind in the prose where nobody measures.

**A provisional point cannot refute a confirmed one, and a distance is no stronger than the weaker of its two ends.** See [[a-guessed-position-is-indistinguishable-from-a-surveyed-one]].

## What the walk actually shows

Schedule 38 sits between 2 Albury Square and 10 Cavendish Crescent North, and I read that as the north end of the drive. It is where the book **crosses to the Crescent**, and the lodge it passes on the way is this one, at the Cavendish Road East end of Gartree House's garden. The order was never evidence of a second building; only of a turn.

## What the house is worth saying

**A chauffeur in 1921, a gardener in 1939.** John Raven Erwin Hatton, 28, over the stables; then George William Kerr, 62, *gardener, domestic*, with Mary Catherine Kerr. Eighteen years and the coach house of Gartree House is still quartering the staff of the big house - which is the whole reason The Park has houses called Lodge in the first place.

**And the empty mark carried its own tell.** It read *"the schedule number is not yet recorded against it"*. Schedule 38 was the missing number all along.

Links: [[named-houses-on-tattershall-drive-and-where-they-sit]], [[gartree-lodge-standing]], [[lr-coach-houses]], [[thirty-eight-house-names-the-site-does-not-show]]."""

q = Q['named-houses-on-tattershall-drive-and-where-they-sit']
q['title'] = "ANSWERED for The Lodge - and Lynwood, St Ives and Elmsdale were the numbered houses all along"
q['detail'] = """**All four of these named houses turned out to be houses the record already held.** Not one of them was new. Properties #433 to #436 are folded in and gone.

| named by 1939 | is | settled |
|---|---|---|
| **Lynwood** | 2 Tattershall Drive (#307) | 7 October 2026 |
| **St Ives** | 4 Tattershall Drive (#309) | 7 October 2026 |
| **Elmsdale** | 5 Clare Valley (#63) | 7 October 2026 |
| **The Lodge** | Gartree Lodge, 17a Tattershall Drive (#404) | 8 October 2026 |

**This question had the first three as 7, 9 and 11 Tattershall Drive** - numbers that do not exist - reasoning from an unbroken schedule run past 1, 3 and 5. The run was unbroken because the enumerator doubled back, which a schedule order cannot show. Richard Warwick Bond and Amy Constance are at 2 Tattershall Drive in 1921 and at Lynwood in 1939: the same couple, the same house, held twice.

**And this question's own reading of The Lodge was the error that stood longest.** It argued the north end of the drive from schedule 38 falling between Albury Square and Cavendish Crescent North, and ruled Gartree Lodge out for standing at the south end. That reading was then written up as a separate question and put to A. Hagues as firm. It was wrong both times, against an answer the record already carried. See [[the-lodge-on-tattershall-drive-is-not-gartree-lodge]].

**Three wrong 1939 empty marks came out of it**, on 2 and 4 Tattershall Drive and 5 Clare Valley, because the gaps list I built treated a named house and a numbered house as two. A fourth, on Gartree Lodge, came out of the same fault. All four are removed.

**What is left on this street** is Park Lodge, the last Land Registry name with no house against it - see [[lr-tattershall-drive]] - and Carnoustie Lodge, which is now the only lodge at the north end and wants nothing explaining.

Links: [[questions-for-a-walk-round-the-park]], [[house-names-live-in-prose]], [[park-drive-missing-numbers-5-8-and-10]], [[clare-valley-numbered-from-the-1891-walk]], [[a-transcription-with-no-address-is-invisible-to-a-street-check]]."""

new = {
 "slug": "a-guessed-position-is-indistinguishable-from-a-surveyed-one",
 "area": "Record keeping",
 "kind": "data",
 "priority": 9,
 "title": "A guessed position looks exactly like a surveyed one, and today one was quoted as evidence",
 "detail": """**A property's lat and lng say nothing about where they came from.** A point surveyed off an OS sheet, a point confirmed on the ground, and a point I calculated from a census walk are the same two numbers in the same two fields. There is no flag, no confidence, no distinction of any kind.

**That cost a house today.** The Lodge, Tattershall Drive was placed from nothing but a schedule order. Its history said so in bold - *the position is provisional*. A day later I measured from it, found Gartree Lodge **444 metres away**, and offered the distance to A. Hagues as proof the two were different houses. They were one house. The caveat was in the prose; the measurement reached for the field. See [[the-lodge-on-tattershall-drive-is-not-gartree-lodge]].

## How thin the provenance actually is

| | |
|---|---|
| properties in the list | **438** |
| carrying any note at all about where the position came from | **29** |
| of those, admitting in prose that the point is a guess | **21** |
| carrying nothing | **409** |

So **the record can tell a guess from a survey for 29 houses out of 438**, and only by reading a sentence. The `coords` table, which is what the site actually draws, stamps who placed a point and when - but a census-only property created in `all_props.json` never gets a `coords` row, so the houses most likely to be guessed are exactly the ones with the least provenance.

## What it would take

A `position_source` field on the property, or a confidence on it: **surveyed**, **confirmed on the ground**, **inferred**, **guessed**. Anything that travels with the numbers instead of beside them. Then a distance between two houses could say which of its ends to trust, and this assistant could not do again what it did today.

**Until then the rule has to be mine, not the record's**: never measure from a census-only property without reading its history first, and never offer a distance as evidence when either end is a point the record invented.

Links: [[all-props-json-positions-are-not-what-the-map-shows]], [[house-names-live-in-prose]], [[thirty-eight-house-names-the-site-does-not-show]]."""}

if 'a-guessed-position-is-indistinguishable-from-a-surveyed-one' not in Q:
    d['questions'].append(new)
json.dump(d, open('data/research_questions.json', 'w'), indent=1, ensure_ascii=False)
print('questions now', len(d['questions']))
