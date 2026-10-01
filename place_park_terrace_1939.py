# -*- coding: utf-8 -*-
"""Tower House and The Lodge, which the 1939 page puts on Park Terrace.

**Tower House is settled, and the 1921 round settles it.** The register has
"Tower House, Park Terrace" holding Henry M Stanley, 46, *hospital house
governor and secretary*. The record's Tower House is 53 Park Row, and in 1921
it held Peter Morrison Maccoll, 47, *house governess and secretary* - the same
office at the same house eighteen years earlier. It is a house tied to the post
at the General Hospital, and the enumerator has written the street he walked in
rather than the one the house is addressed on. The schedule before it is the
hospital's own Lodge. So schedule 135 goes to #395, and Park Terrace is kept on
the property as a street the house has been called by.

**The Lodge is not settled.** Schedule 134 holds Bert Geddes, 47, chauffeur,
and Hannah Geddes. It is made as its own property, because naming it would be a
guess - see the research question.

  railway run python3 place_park_terrace_1939.py --apply
"""
import os, sys, json, psycopg2

APPLY = '--apply' in sys.argv
DATA = 'data/people_1939_rmgc_the_park.json'
TOWER, LODGE = 395, 441


def retarget(cur, d, sched, prop, addr, extra):
    cur.execute("""SELECT c.id, p.first_name, p.last_name FROM census_entries c
                     JOIN people p ON p.id = c.person_id
                    WHERE c.census_year = 1939 AND c.census_household_num = %s""", (sched,))
    rows = cur.fetchall()
    for cid, fn, ln in rows:
        print(f"    row {cid} {fn} {ln}  ->  {addr}")
    if not APPLY:
        return
    cur.execute("""UPDATE census_entries
                      SET property_id = %s, unresolved_address = NULL, address = %s,
                          source = replace(source,
                            'the house is not identified in the record, so this row is left unfiled',
                            %s)
                    WHERE census_year = 1939 AND census_household_num = %s""",
                (prop, addr, extra, sched))
    for _, fn, ln in rows:
        for x in d['people']:
            if (x['first_name'], x['last_name']) != (fn, ln):
                continue
            cur.execute("SELECT id FROM people WHERE first_name=%s AND last_name=%s", (fn, ln))
            got = cur.fetchall()
            if len(got) == 1:
                x['id'] = got[0][0]
            for ce in x['census']:
                if ce.get('census_household_num') != sched:
                    continue
                ce.pop('unresolved_address', None)
                ce['property_id'] = prop
                ce['address'] = addr
                ce['source'] = ce['source'].replace(
                    'the house is not identified in the record, so this row is left unfiled', extra)


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    d = json.load(open(DATA))
    props = json.load(open('data/all_props.json'))

    print("  Tower House - schedule 135 to #395, 53 Park Row:")
    retarget(cur, d, 135, TOWER, "Tower House, 53 Park Row",
             "the page writes the street as Park Terrace and the house is 53 Park Row - the same "
             "house, settled by the office: the hospital's house governor and secretary lived at "
             "Tower House in 1921 as well")

    print("  The Lodge - schedule 134 to its own property #441:")
    retarget(cur, d, 134, LODGE, "The Lodge, Park Terrace",
             "the house is The Lodge, Park Terrace, as the page writes it, which the record now "
             "holds under that name - it may be East Lodge on Park Row and is not named so here")

    if APPLY:
        if not any(p['id'] == LODGE for p in props):
            props.append({
              "id": LODGE, "name": "The Lodge", "house_name": "The Lodge", "street": "Park Terrace",
              "no": "", "address": "The Lodge, Park Terrace", "desc": "",
              "history": "**Named by the 1939 Register and by nothing else in the record.** "
                         "Schedule 134 holds **Bert Geddes**, 47, chauffeur, and **Hannah Geddes**, "
                         "48 - a service household, which is what a lodge is for.\n\n"
                         "**It may be East Lodge on Park Row (#413), and the record does not say "
                         "so.** The enumerator takes the General Hospital's own Lodge, then this "
                         "house, then **Tower House** - and Tower House is 53 Park Row, which the "
                         "same page calls Park Terrace. East Lodge stands beside Tower House, is "
                         "listed with it, and has no household in this round. That is a good deal "
                         "of smoke; it is not the fire. See "
                         "[[the-lodge-on-park-terrace-is-probably-east-lodge]].\n\n"
                         "**The position is provisional**, set beside Tower House because that is "
                         "where the book puts it.",
              "date_built": "", "listed": "No", "census_only": True,
              "lat": 52.95160, "lng": -1.15655})
        for p in props:
            if p['id'] == TOWER:
                p['prev_house_name'] = "Tower House, Park Terrace"
                if 'In 1939' not in (p.get('history') or ''):
                    p['history'] = (p.get('history') or '') + (
                        " In 1939 the register writes the street as **Park Terrace** and the house "
                        "holds **Henry M Stanley**, 46, hospital house governor and secretary, with "
                        "Millicent A Stanley - the same office Peter Morrison Maccoll held here "
                        "eighteen years before, which is what settles the two street names on one "
                        "house.")
        props.sort(key=lambda p: p['id'])
        json.dump(props, open('data/all_props.json', 'w'), indent=1, ensure_ascii=False)
        json.dump(d, open(DATA, 'w'), indent=1, ensure_ascii=False)
        c.commit()
        print("\n  committed")
    else:
        print("\n  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
