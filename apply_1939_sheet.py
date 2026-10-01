# -*- coding: utf-8 -*-
"""Apply the filled-in 1939 names sheet, binding by person id.

The sheet's "name as recorded" column goes stale the moment a name is put back,
so nothing here matches on names: column B is the person id and that is what
every change is tied to, in the database and in the import files.

  railway run python3 apply_1939_sheet.py                 # show
  railway run python3 apply_1939_sheet.py --apply         # do it
"""
import os, sys, glob, json, psycopg2, openpyxl

APPLY = '--apply' in sys.argv
SHEET = os.path.expanduser(next((a for a in sys.argv[1:] if not a.startswith('--')),
                                '~/Desktop/1939 names - fill in.xlsx'))


def split_later(text):
    out = []
    for part in str(text).replace(' then ', ',').split(','):
        part = part.strip()
        if part:
            out.append(part.rsplit(' ', 1)[-1])
    return out


def read_sheet(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    out, seen = [], set()
    for ws in wb.worksheets:
        head = [str(c.value or '').strip().lower() for c in ws[1]]
        try:
            col = {k: head.index(k) for k in
                   ('person', 'name as recorded', 'name on the night', 'amended to')}
        except ValueError:
            continue
        for row in ws.iter_rows(min_row=2, values_only=True):
            pid = row[col['person']]
            was = str(row[col['name on the night']] or '').strip()
            later = str(row[col['amended to']] or '').strip()
            if not pid or not was or pid in seen:
                continue
            seen.add(pid)
            was = was.replace('[Unknown]', '').strip()
            out.append((int(pid), was.rsplit(' ', 1)[0] if ' ' in was else '',
                        was.rsplit(' ', 1)[-1], split_later(later)))
    return out


def main():
    c = psycopg2.connect(os.environ.get('DATABASE_PUBLIC_URL') or os.environ['DATABASE_URL'])
    cur = c.cursor()
    work = read_sheet(SHEET)
    print(f"  {len(work)} rows filled in\n")
    files = {f: json.load(open(f)) for f in glob.glob('data/people_19*.json')}
    changed, skipped, missing = 0, 0, []

    for pid, fn, surname, names in work:
        cur.execute("SELECT first_name, last_name FROM people WHERE id=%s", (pid,))
        got = cur.fetchone()
        if not got:
            missing.append(pid); continue
        cfn, cln = got
        fn = fn or cfn
        cur.execute("SELECT LOWER(last_name) FROM person_alias WHERE person_id=%s", (pid,))
        have = {r[0] for r in cur.fetchall()}
        want = [n for n in names if n.lower() not in have]
        if cln == surname and cfn == fn and not want:
            skipped += 1; continue
        bits = []
        if (cfn, cln) != (fn, surname):
            bits.append(f"{cfn} {cln} -> {fn} {surname}")
        if want:
            bits.append("alias " + ", ".join(want))
        print(f"  #{pid:<5} " + "; ".join(bits))
        changed += 1
        if not APPLY:
            continue
        for i, later in enumerate(names):
            label = ('1939 amendment' if len(names) < 2 else
                     f"1939 amendment ({'latest' if i == len(names)-1 else str(i+1)} married name)")
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),%s
                           FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE a.person_id=%s
                             AND LOWER(a.last_name)=LOWER(%s))""",
                        (pid, fn, later, pid, label, pid, later))
        if not names and (cfn, cln) != (fn, surname):
            cur.execute("""INSERT INTO person_alias (person_id, first_name, last_name, born_year, made_by)
                           SELECT %s,%s,%s,(SELECT born_year FROM people WHERE id=%s),'earlier reading of the page'
                           FROM (SELECT 1) t WHERE NOT EXISTS
                           (SELECT 1 FROM person_alias a WHERE a.person_id=%s
                             AND LOWER(a.first_name)=LOWER(%s) AND LOWER(a.last_name)=LOWER(%s))""",
                        (pid, cfn, cln, pid, pid, cfn, cln))
        cur.execute("UPDATE people SET first_name=%s, last_name=%s, maiden_name=NULL WHERE id=%s",
                    (fn, surname, pid))
        note = ((f"; entered as {fn} {surname}, which is the name on the night"
                 + (f"; amended afterwards to {', '.join(names)}, which is what the online indexes "
                    f"show" if names else ", read again from the page")
                 + " - read by A. Hagues from the 1939 sheet"))
        cur.execute("""UPDATE census_entries SET source = COALESCE(source,'') || %s
                        WHERE person_id=%s AND census_year=1939
                          AND COALESCE(source,'') NOT LIKE %s""",
                    (note, pid, '%which is the name on the night%'))
        for f, d in files.items():
            for x in d.get('people', d if isinstance(d, list) else []):
                if x.get('id') != pid:
                    continue
                x['first_name'], x['last_name'] = fn, surname
                for ce in x.get('census', []):
                    if ce.get('census_year') == 1939 and 'name on the night' not in ce.get('source', ''):
                        ce['source'] = ce.get('source', '') + note

    if APPLY:
        for f, d in files.items():
            json.dump(d, open(f, 'w'), indent=1, ensure_ascii=False)
        c.commit()
    print(f"\n  {changed} changed, {skipped} already right"
          + (f", {len(missing)} no longer in the record: {missing}" if missing else ""))
    print("  committed" if APPLY else "  Nothing written. Add --apply.")


if __name__ == '__main__':
    main()
