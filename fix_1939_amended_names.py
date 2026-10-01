# -*- coding: utf-8 -*-
"""The 1939 Register's amended surnames, put back the way the page had them.

The Register was not a census. It was an identity register, kept up to date for
decades, so a woman who married after 1939 has her married name written across
the original and the online indexes show the LATER name. Ivy Burton, cook at
Penrhyn House on 29 September 1939, is indexed as Ivy Luke because somebody
wrote LUKE over Burton years afterwards.

The rule this record follows: **a person is named as the page named them on the
night**. The amendment is a real and valuable fact - it dates a marriage - but
it is a fact about what happened later, not the name of the woman in the house.

So the name goes back to the one she had, every married name is kept as an alias
so a search for one still finds her and a re-import cannot make a second person,
and the census row says what the page does.

Some women were amended more than once - divorced or widowed, then married
again. Those carry a list, earliest first and the latest last, written on the
sheet as a comma: "Monsarrat, Hart". Each becomes an alias in its own right and
the order between them is kept, because that order is the only thing in the
record that says which marriage came first.

Usage:
  railway run python3 fix_1939_amended_names.py          # show
  railway run python3 fix_1939_amended_names.py --apply  # do it

Or take the names from the filled-in sheet (amended_names_worksheet.py writes it):
  railway run python3 fix_1939_amended_names.py --sheet "~/Desktop/1939 names - fill in.xlsx"
"""
import os, sys, psycopg2

APPLY = '--apply' in sys.argv
SHEET = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--sheet=')), None)
if not SHEET and '--sheet' in sys.argv:
    i = sys.argv.index('--sheet')
    SHEET = sys.argv[i + 1] if i + 1 < len(sys.argv) else None

# person, forename on the night, surname on the night, the names written over it
# (earliest first, latest last), where, and what the page shows
AMENDED = [
 (7519, "Ivy", "Burton", ["Luke"], "Penrhyn House, Clumber Road East",
  "the Register is amended to LUKE in a later hand, struck through Burton"),
 (7356, "Meryl Vera", "Wardle", ["Monsarrat", "Hart"], "5 Western Terrace",
  "the Register carries two later marriages written over the original, Monsarrat "
  "first and Hart after it, and the online indexes show the last of them"),
]


def split_later(text):
    """"Monsarrat, Hart" -> the surnames, earliest first, latest last."""
    out = []
    for part in str(text).replace(' then ', ',').split(','):
        part = part.strip()
        if part:
            out.append(part.rsplit(' ', 1)[-1])
    return out


def from_sheet(path):
    """Read the two filled-in columns off the worksheet.

    Only rows where both NAME ON THE NIGHT and AMENDED TO have been written are
    taken; everything left blank is simply a row nobody has looked at yet.
    """
    import openpyxl
    wb = openpyxl.load_workbook(os.path.expanduser(path), data_only=True)
    out, seen = [], set()
    for ws in wb.worksheets:
        head = [str(c.value or '').strip().lower() for c in ws[1]]
        try:
            col = {k: head.index(k) for k in
                   ('person', 'name as recorded', 'house', 'name on the night', 'amended to')}
        except ValueError:
            continue
        for row in ws.iter_rows(min_row=2, values_only=True):
            was = str(row[col['name on the night']] or '').strip()
            later = str(row[col['amended to']] or '').strip()
            pid = row[col['person']]
            if not (was and pid) or pid in seen:
                continue
            seen.add(pid)
            recorded = str(row[col['name as recorded']] or '').strip()
            first = was.rsplit(' ', 1)[0] if ' ' in was else recorded.rsplit(' ', 1)[0]
            surname = was.rsplit(' ', 1)[-1]
            names = split_later(later)
            if not names:
                note = 'read again from the page'
            elif len(names) < 2:
                note = 'the Register is amended in a later hand, struck through ' + surname
            else:
                note = ('the Register carries ' + str(len(names)) + ' later names written over '
                        'the original, ' + ', '.join(names) + ' in that order, struck through '
                        + surname)
            out.append((int(pid), first, surname, names,
                        str(row[col['house']] or '').strip(), note))
    return out


def alias_label(i, n):
    if n < 2:
        return '1939 amendment'
    return f'1939 amendment ({"latest" if i == n - 1 else ordinal(i + 1)} married name)'


def ordinal(n):
    return f'{n}' + {1: 'st', 2: 'nd', 3: 'rd'}.get(n if n < 20 else n % 10, 'th')


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    work = from_sheet(SHEET) if SHEET else AMENDED
    if SHEET:
        print(f"  {len(work)} rows filled in on {SHEET}\n")
    for pid, fn, was, names, where, note in work:
        if isinstance(names, str):
            names = split_later(names)
        cur.execute("SELECT first_name, last_name, maiden_name FROM people WHERE id=%s", (pid,))
        row = cur.fetchone()
        if not row:
            print(f"  #{pid}: no such person")
            continue
        cfn, cln, cmaiden = row
        cur.execute("SELECT LOWER(last_name) FROM person_alias WHERE person_id=%s", (pid,))
        have = {r[0] for r in cur.fetchall()}
        if cln == was and cfn == fn and all(n.lower() in have for n in names):
            print(f"  #{pid} {cfn} {cln}: already as the page has it")
            continue
        if names:
            kept = ', '.join(names)
            print(f"  #{pid} {cfn} {cln} (née {cmaiden})  ->  {fn} {was}, with {kept} kept as "
                  f"{'an alias' if len(names) < 2 else 'aliases, in that order'}")
        else:
            print(f"  #{pid} {cfn} {cln}  ->  {fn} {was}, read again from the page "
                  f"(no amendment - a correction)")
        if cfn != fn:
            print(f"      the forename goes too: {cfn} -> {fn}")
        print(f"      {where} - {note}")
        if not APPLY:
            continue
        if not names:
            # Nothing was written over the name; it was simply read wrong. The earlier
            # reading is kept so a search for what the indexes say still finds them.
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),'earlier reading of the page'
                           FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE a.person_id=%s
                             AND LOWER(a.first_name)=LOWER(%s) AND LOWER(a.last_name)=LOWER(%s))""",
                        (pid, cfn, cln, pid, pid, cfn, cln))
            cur.execute("UPDATE people SET first_name=%s, last_name=%s WHERE id=%s", (fn, was, pid))
            cur.execute("""UPDATE census_entries SET source = source || %s
                            WHERE person_id=%s AND census_year=1939 AND source NOT LIKE %s""",
                        (f"; read again from the page as {fn} {was}, having first been "
                         f"entered as {cfn} {cln}", pid, '%read again from the page as%'))
            continue
        for i, later in enumerate(names):
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),%s
                           FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE a.person_id=%s
                             AND LOWER(a.last_name)=LOWER(%s))""",
                        (pid, fn, later, pid, alias_label(i, len(names)), pid, later))
        cur.execute("UPDATE people SET first_name=%s, last_name=%s, maiden_name=NULL WHERE id=%s",
                    (fn, was, pid))
        tail = "" if "indexes" in note else ", and the online indexes show the later name"
        said = f"; entered as {fn} {was}, which is her name on the night; {note}{tail}"
        cur.execute("""UPDATE census_entries SET source = source || %s
                        WHERE person_id=%s AND census_year=1939 AND source NOT LIKE %s""",
                    (said, pid, '%which is her name on the night%'))
    print("\n  Nothing written. Add --apply." if not APPLY else "\n  done")
    if APPLY:
        c.commit()
        print("committed")


if __name__ == '__main__':
    main()
