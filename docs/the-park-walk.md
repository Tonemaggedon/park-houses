# The Park Walk

*Written overnight, 8–9 October 2026, against A. Hagues' brief: "a fun app where it knows your
location… think of some other fun additions along the way… go wild."*

---

## What is built and working

At **`/walk`**. It is a web app, phone-first, and it installs to a home screen.

You say how long you have — fifteen minutes, half an hour, an hour, no limit — and what you are in
the mood for. It finds you, plots a route from where you are standing, and walks you round. Your
phone buzzes when you come within thirty metres of a stop and the stop opens.

**It draws on 327 stops, and not one of them was invented for the app:**

| | |
|---|---|
| **40** | open questions the record cannot answer from paper |
| **49** | notable residents, at the houses they lived in |
| **181** | houses with a named architect |
| **13** | houses that are gone |
| **44** | houses that once held twelve or more people under one roof |

**The question stops are the point.** You are standing in front of the house. The app asks what it
cannot find out — a name on a gatepost, a number on a door, whether the building is even still
there — and what you write goes straight back into the record against that question.

**Six moods**: a bit of everything · be useful (questions only) · who lived here · who built it ·
what is gone · full houses.

### Things it does that are worth knowing

- **One stop per house.** Nine Cavendish Crescent North has three reasons to stop; you get one.
- **It balances the mix.** Nearest-first alone gave thirteen stops in five hundred metres, eleven of
  them architects, because architects outnumber everything else four to one. The route now costs a
  kind more to pick the more it has already used.
- **It spreads out.** A stop right beside the last one is penalised, so half an hour is a walk
  rather than a shuffle round one corner.
- **It remembers what you have seen**, in the phone, and shows you new things next time.
- **It works in a dead spot.** A service worker keeps the page and the last list of stops.
- **Nothing about where you have been leaves the phone.** The only thing that is ever sent is an
  answer you choose to send.

---

## The subdomain

**It does not need one to work, and it should probably have one anyway.**

Right now it is `nottinghamparkhouses.com/walk`, which is free, already live, and shares the login
and the data. A subdomain would be `walk.nottinghamparkhouses.com`, and it is three steps:

1. In Railway, on the service: **Settings → Networking → Custom Domain**, add
   `walk.nottinghamparkhouses.com`. Railway gives you a target hostname.
2. At whoever holds the DNS for nottinghamparkhouses.com, add a **CNAME** record for `walk` pointing
   at that target.
3. Nothing in the code changes. Both names reach the same app; the walk is simply what you get at
   that one.

**The case for doing it:** `walk.nottinghamparkhouses.com` is a thing you can say out loud, put on a
poster in the Park Centre window, and print on a card. A QR code on a lamp post is a lot better with
a short name under it.

**The case against:** a second name is a second thing to renew and a second certificate to notice
when it expires. If the answer is "not this month", the path works perfectly.

---

## Where it should go next

### 1. Walk the enumerator's round

**This is the one.** Nothing else here is unique to this record; this is.

On the evening of 29 September 1939 a man walked The Park with a book, and the record holds the
order he did it in — schedule by schedule, door by door. **Put the phone in his hand.** You walk his
route, in his order, and at each door you get the household exactly as he met it: the names, the
ages, the trades, in the order he wrote them down.

The 1881 and 1911 rounds would do the same. And the walk is not the street order — the enumerator
doubles back, crosses to the other side, skips the lodge and comes to it later. **You would be
walking a real person's evening**, and you would feel the shape of it. That is a thing a museum
cannot do and a book cannot do.

It needs nothing new: the schedule order is already in `census_entries.census_household_num`, and
the positions are already in `coords`.

### 2. The year you were born

Enter a year. Every house you pass tells you who was in it on the census nearest that year. Walk
your own street in 1911. Walk it as a child would have seen it.

### 3. Then and now, under your feet

The site already carries the OS 25-inch sheets of the 1880s–1910s as a map layer. On the walk, fade
it in under your own blue dot and watch the gardens go and the flats arrive.

### 4. Standing where it stood

Thirteen houses in the record are gone. The app should say so plainly when you reach the spot:
*Broxtowe House stood here. Harts Hotel is on it now.* The Hermitage, Barrack Yard, Clumber Court,
Sunnyside. **A walk made only of absences** would be an extraordinary half hour.

### 5. The gas lamps at dusk — and the neighbours who have already done the hard part

**Struck out, and replaced with something better. [Park Lamps](https://parklamps.mczhang.net) already
exists.** A. Hagues pointed me at it: **Bethan and Weiran, two residents of The Park**, built it so
that reporting a faulty gaslight is simpler — you find the lamp you are standing next to, report the
fault, and see which lamps have already been reported. It is a proper app with a map, a search and a
home-screen install, and the lamps are all on it.

**So the record should not collect the lamps.** The idea here was a dusk walk that gathered them one
tap at a time over a fortnight; that work is done, by people who live on the street, and doing it
again would be both wasteful and rude.

**What to do instead, in order of how much it asks of anybody:**

1. **Link to them.** A dusk walk in this app should say, at the first lamp, that Park Lamps exists
   and that a broken one can be reported there in about fifteen seconds. That is the civic act the
   walk can offer that the record cannot.
2. **Ask before anything else.** Their data is theirs. There is no licence on the site, so the only
   correct next step is a conversation, not a scrape — and it is A. Hagues' conversation to have,
   as the Trust and as a neighbour, not something to arrange from a terminal at four in the morning.
3. **If they are willing**, the fit is almost too neat. Their lamps become stops on the walk, with
   the fault-reporting link in the card. The record's houses become the context on theirs — *this
   lamp stands outside Gartree Lodge, where a chauffeur lived over the stables in 1921.* Neither
   project has to hand over a database for that to work; a link each way would do most of it.
4. **And Weiran is a software developer in The Park who has already built a PWA for it**, which is
   a more useful fact than any amount of lamp data.

**What the record would still want from a lamp walk** is the thing Park Lamps has no reason to
carry: *when* the lamps came, who put them up, which are original and which are replacements. That
is a documentary question, and it is ours.

### 6. Read me a gatepost

A walk made entirely of the **118 house names** found on the modern map with no property in the
record, and the Land Registry names with no number. Each stop asks one question: *what does the
gatepost say?* That is the single biggest gap the record has, and it is the easiest to close, and it
can only be closed on foot.

### 7. The servants' walk

Gartree Lodge, Carnoustie Lodge, the Pelham Cottages, Barrack Yard, seven coach houses and a
stables. The people who made the big houses work, in the small houses behind them. **Edith Annie
Hind, born in 3 Pelham Cottage in 1879 and still there at sixty, machining shirts**, is a better
half hour than most of the big houses.

### 8. One street, three centuries

Pick a street. Walk it once. Hear it in 1881, then 1911, then 1939 — the same doors, three different
sets of people, and you watch the servants thin out and the flats begin.

### 9. Collect the architects

*You have now stood outside fourteen of T.C. Hine's sixty-one.* Not points, not badges — a count of
real things, which is the only kind of collecting this record should encourage.

### 10. Two of you, from opposite ends

Two people start at opposite gates. The app gives each a different half of the route and tells them
when they are about to meet. Somewhere near Lincoln Circus, probably.

### 11. Leave something for the next walker

A note on a house, for whoever comes past next. Moderated, obviously. But a hundred and eighty years
of people have left things on these walls and it would be in keeping.

### 12. Read it to me

The household spoken aloud as you approach, so you can keep walking and keep looking up. Fourteen
names and trades is a lot to read on a phone in the rain.

### 13. The houses that stood empty

On 29 September 1939 a number of houses in The Park were ticked and left blank — written in, and
nobody there. **A month into the war.** Walk those, and only those.

---

## What it does not do yet, and should

- **Notifications with the screen off** work on Android through the service worker; on iPhone they
  need the app added to the home screen first. The app should say so, once, at the right moment.
- **Routing is straight lines between stops**, multiplied by 1.32 for the fact that streets bend.
  Good enough to pick a route and badly wrong as a drawn line on the map. Real street geometry would
  fix the drawing.
- **No photographs.** A stop with a picture of the house in 1900 is worth three with none.
- **An answer sent from the pavement lands as a closed claim on the question**, which is honest but
  crude. It should become a proper contribution with the walker's name on it.
- **A link to [Park Lamps](https://parklamps.mczhang.net) is not in the app yet**, deliberately. It
  points at a neighbour's project and it should be their call as well as ours.

---

*A. Hagues' brief, and the whole point: "a bit like pokemon go for old people". The difference worth
keeping is that there is nothing to catch. Everything the app shows you was really there.*
