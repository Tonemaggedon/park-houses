# -*- coding: utf-8 -*-
"""Barrack Yard and the three cottages get the history the filings just proved."""
import json
d = json.load(open('data/all_props.json'))
P = {p['id']: p for p in d}

COMMON = (
 "\n\n**This cottage stands in Barrack Yard, and the record has written the place down six ways "
 "in seventy years:** *the Barracks* in 1871, *Pelham Cottage* in 1881, *Pelham Cottages* in 1891, "
 "*Barrack Yard* in 1911, *{n} Barrack Lane* in 1921 and *{n} Pelham Cottage* in 1939. "
 "A. Hagues put it that the barrack yard was a barracks and became these houses, and the record "
 "carries the proof - two families who each keep their own number straight through the name "
 "changes. See [[barrack-yard-is-the-pelham-cottages-and-two-families-prove-it]].")

P[449]['history'] = (P[449].get('history') or '').rstrip() + COMMON.format(n=1) + (
 "\n\n**1911** held **Joseph Blythe**, 50, a *sexton*, with his wife Annie, their children Arthur, "
 "Marjorie and Kathleen, and a boarder, **Ernest Bentley**, 18, a fitter - six people, returned at "
 "Barrack Yard without a number and placed here because the other two Barrack Yard households are "
 "fixed at 2 and 3 by their own people.")

P[450]['history'] = (P[450].get('history') or '').rstrip() + COMMON.format(n=2) + (
 "\n\n**One household holds this cottage across four rounds**, and it is what fixes the whole "
 "identification:\n\n"
 "| round | the page or index writes | who |\n|---|---|---|\n"
 "| **1901** | *Pelham Crescent* | **Elizabeth Baker**, 71, head, with her daughter Ann and "
 "son-in-law **Arthur William Smith**, 32, cabinet maker |\n"
 "| **1911** | *Barrack Yard, Barrack Lane* | the same three, aged 81, 43 and 42 |\n"
 "| **1921** | ***2* Barrack Lane** | Arthur William Smith, 52, cabinet maker, and Elizabeth Ann, 53 |\n"
 "| **1939** | ***2* Pelham Cottage** | Arthur William Smith, 70, widowed, *joiner* |\n\n"
 "**Born 23 January 1869, a cabinet maker for forty years, and the number 2 carried from the 1921 "
 "index into the 1939 Register.**")

P[451]['history'] = (P[451].get('history') or '').rstrip() + COMMON.format(n=3) + (
 "\n\n**The Hinds are here for fifty-eight years**, and the woman who proves it was two years old "
 "when the record first finds her:\n\n"
 "| round | the page or index writes | who |\n|---|---|---|\n"
 "| **1881** | *Pelham Cottage*, schedule 92 | **Fletcher Hind**, 32, *gardener*, Sarah, 32, Fred, "
 "3, and **Edith Annie, 2** |\n"
 "| **1911** | *Barrack Yard, Barrack Lane* | Fletcher, 61, now a *domestic coachman*, Sarah, 61, "
 "a lace hand drawer and finisher, and Edith Annie, 32, a hosiery machinist |\n"
 "| **1921** | ***3* Barrack Lane** | Edith Annie Hind, 42, head of the house |\n"
 "| **1939** | ***3* Pelham Cottage** | Edith Annie Hind, 60, single, hosiery shirt machinist |\n\n"
 "**Born 20 January 1879.** A gardener's daughter who stayed in the cottage she was born in, took "
 "it on when her parents were gone, and was still in it at sixty, machining shirts. "
 "**The record had her moving about the corner and coming back - she never moved; the filing did.**")

P[410]['history'] = (
 "**Not a house but a yard of cottages**, of the kind built behind a street frontage and reached "
 "through an entry - and A. Hagues confirms it survives. The three cottages standing in it are "
 "**1, 2 and 3 Pelham Cottage** (#449, #450, #451), which is why the yard's households have gone "
 "to them.\n\n"
 "**The yard has been written down six ways in seventy years:** *the Barracks* (1871), *Pelham "
 "Cottage* (1881), *Pelham Cottages* (1891), *Barrack Yard* (1911), *1, 2 and 3 Barrack Lane* "
 "(1921) and *1, 2 and 3 Pelham Cottage* (1939). The name on the ground today is **Pelham "
 "Cottages**, a street of its own off Pelham Crescent, with **Journey's End** and **Reveille** "
 "beside it - and Reveille, a bugle call to wake soldiers, is the name that says what the place "
 "was.\n\n"
 "**Dougal de Havilland was right.** His map carries a note reading \"Allegedly known as Barrack "
 "Yard\" exactly here, around Pelham Cottages and Reveille. The record had set that aside because "
 "his map is out by a median of 60 m and cannot place anything; the note did not need to place "
 "anything, because it was naming the right block.\n\n"
 "**Three households were returned here in 1911** and all three are now in their cottages: the "
 "Blythes at 1, Elizabeth Baker with the Smiths at 2, Fletcher Hind's family at 3. The 1921 "
 "**Allenfield Lodge** household - Maurice and Emma Mee and four more - stays filed here, on "
 "A. Hagues' word rather than on evidence, with the page's own wording kept beside it.\n\n"
 "**Five people sit here for 1911 with no age, no relationship and no source** - H Ernest and "
 "Alice Goddard, Mildred Jacklin, Annie Bernuctt and Rose Ella Sharman. Where they came from is "
 "not recorded, and they are not among the twelve the 1911 return describes.")
P[410]['sources']['position'] = (
 "Needs moving. The point now held was worked out from Barrack Lane's own numbering and placed at "
 "the foot of the lane. The yard is in fact the Pelham Cottages block, about 76 m south, where "
 "Dougal de Havilland's note always put it. The three cottages are positioned from their own "
 "OpenStreetMap footprints and the yard should be placed among them.")
json.dump(d, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
print("histories written for 410, 449, 450, 451")
