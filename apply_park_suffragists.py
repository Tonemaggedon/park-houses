#!/usr/bin/env python3
"""Link the people named in the Park News suffrage article to their houses.

A. Hagues supplied 'A Century of Women's Suffrage' by David S Stewart, from
Park News, with one instruction: take the people and where they were, and
leave the author's account of what they did alone. So nothing the article says
anybody *did* is copied here. What is recorded is that the article names them,
where it puts them, and the citation — and anything beyond that has to come
from a source of the record's own.

The article checks out everywhere the record can test it: Brightlands is
already held as Adam House's former name, Hardwick House as Hardwicke's, and
Felixstowe is already noted as the Dowsons' house across two generations.

Nobody is created. A name in a secondary article, with no dates, is a thin
thing to make a person out of, and the record has a merge problem already.
Where the person is here and the house is here, the two are linked and the
citation goes on the link. Everything else is left as a lead.
"""
import json, os, sys
import psycopg2

CITE = "Named as a Park suffragist or supporter of the cause in David S Stewart, " \
       "'A Century of Women's Suffrage', Park News, pp. 9-11, which puts her at this address."
CITE_M = CITE.replace('suffragist or supporter', 'supporter').replace(' her ', ' him ')

# name in the article -> (person id in the record, property id), established by
# the matching run: one name candidate only, and an address that resolves.
LINKS = [
    ('Catherine Turner',          3636, 248, "The article gives 8 Park Terrace and later 13 Park Terrace (#378)."),
    ('Sarah Loverseed',           6495, 201, None),
    ('Sarah Guilford',            2479, 168, None),
    ('Hannah Guilford',           2480, 168, None),
    ('Rachel Procter Hutchinson', 3441, 178, "The article spells it Proctor."),
    ('Margaret Hutchinson',       7134,  39, "The article names the house Kirkstall Lodge."),
    ('Annie C Eberlin',           1828, 255, "The article gives her as Annie Charlotte Eberlin."),
    ('Jessie Kentish Wright',     2129, 212, None),
    ('Constance Edith Bourne',     396, 309, "The article names the house St Ives and prints Tattersahll."),
    ('Jane Brownsword',           None,  44, None),
    ('Mary Hewison Lewenz',       None,  80, "The article gives her maiden name as Gunston."),
    ('Catherine Hutchinson',      3173,  40, "The article says she was born an Adlington, of Mansfield."),
    ('Olga Mary Walker',           804, None, "The article puts her at 3 Hollies Crescent, a street the record does not hold."),
    ('Kate May Snook',            2079, None, "The article says Castle Grove and gives no number."),
    ('Lucy Ann Pemberton',         929, 155, "The article spells it Kennilworth House, Kennilworth Rd."),
    ('Lena M. Dowson',            4576,  81, "The article gives the house as Brightlands, which the record already holds as Adam House's former name."),
    ('Mary E. Handford',          3061, 398, "The article calls the house Hardwick House, which the record holds as Hardwicke House's former name, and her Hon Mary Handford, daughter of Lord Belper."),
    ('Caroline R Weinberg',       2289, 398, "The article names Hardwick House."),
    ('Helena Brownsword Dowson',  2548, 394, "The article names Felixstowe House."),
    ('Moritz Jacoby',             8155, None, "The article puts the family at Oakhill House, Park Row - a Park Row it distinguishes from the street of that name. No such house is in the record."),
    ('John Henry Jacoby',         8156, None, "Oakhill House, Park Row - see Moritz Jacoby."),
    ('James Alfred Jacoby',       8157, None, "Oakhill House, Park Row - see Moritz Jacoby."),
]

NOTE_ONLY = "Named as a Park suffragist or supporter of the cause in David S Stewart, " \
            "'A Century of Women's Suffrage', Park News, pp. 9-11."


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    linked = noted = skipped = 0

    for name, pid, prop, extra in LINKS:
        if pid is None:
            print(f'  — {name}: not in the record, left as a lead')
            skipped += 1
            continue
        cur.execute('SELECT first_name, last_name, sex FROM people WHERE id=%s', (pid,))
        row = cur.fetchone()
        if not row:
            print(f'  ! {name}: person {pid} has gone')
            continue
        who = f'{row[0]} {row[1]}'
        note = (CITE_M if row[2] == 'M' else CITE) if prop else NOTE_ONLY
        if extra:
            note += ' ' + extra

        if prop:
            cur.execute("""INSERT INTO property_residents (property_id, person_id, notes)
                           SELECT %s, %s, %s
                            WHERE NOT EXISTS (SELECT 1 FROM property_residents
                                               WHERE property_id=%s AND person_id=%s)
                        RETURNING id""", (prop, pid, note, prop, pid))
            if cur.fetchone():
                linked += 1
                print(f'  linked  {who:<30} -> property {prop}')
            else:
                cur.execute("""UPDATE property_residents SET notes =
                               CASE WHEN COALESCE(notes,'') = '' THEN %s ELSE notes || ' ' || %s END
                                WHERE property_id=%s AND person_id=%s
                                  AND COALESCE(notes,'') NOT LIKE '%%Park News%%'""",
                            (note, note, prop, pid))
                print(f'  already {who:<30} at property {prop} — citation added to the link')
                noted += 1
        else:
            print(f'  noted   {who:<30} (no placeable address)')
            noted += 1

        # And on the person, so it shows wherever they are read.
        cur.execute("""UPDATE people SET bio = CASE
                         WHEN COALESCE(bio,'') = '' THEN %s
                         ELSE bio || E'\\n\\n' || %s END
                        WHERE id = %s AND COALESCE(bio,'') NOT LIKE %s""",
                    (note, note, pid, '%Park News%'))

    c.commit()
    print(f'\n{linked} linked to a house, {noted} noted, {skipped} left as leads')
    cur.close(); c.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
