#!/usr/bin/env python3
"""
Every census run the record holds, laid out in the enumerator's own order.

An enumerator walks a street and numbers the houses as he goes, so schedule
order IS geographical order. A household the record cannot place is therefore
bracketed by two it can: if schedule 154 is unfiled and 153 and 155 are both on
Cavendish Road East, 154 is between them. That is how the 1891 ditto run was
solved, and this sheet is that method applied to every round at once.

One sheet per census year. Each row is one household, in schedule order, with:
  the schedule number, the head of the house, how many were in it, and the
  house - number, name and street - where the record can name it.

Three kinds of row are not households, and they are the point of the exercise:
  UNFILED       the household is read but the house is not identified
  UNOCCUPIED    the enumerator wrote the house down as standing empty
  NOT READ      a schedule number missing from an otherwise continuous run,
                so nobody has transcribed it yet

1891 is walked by two enumerators whose schedule numbers both run through the
same range, so its district is carried in its own column.

Usage:
  railway run python3 census_runs_sheet.py
  railway run python3 census_runs_sheet.py --year 1891
"""

import os, re, sys, argparse, json
import psycopg2

ap = argparse.ArgumentParser()
ap.add_argument('--year', type=int)
ap.add_argument('--out')
args = ap.parse_args()


def database_url():
    for name in ('DATABASE_PUBLIC_URL', 'DATABASE_URL'):
        v = os.environ.get(name)
        if v and 'railway.internal' not in v:
            return v
    v = os.environ.get('DATABASE_URL')
    if not v:
        raise SystemExit('No DATABASE_URL. Run this with:  railway run python3 ' +
                         os.path.basename(__file__))
    return v


conn = psycopg2.connect(database_url())
cur = conn.cursor()

# The houses, straight from the property records.
PROPS = {p['id']: dict(p) for p in json.load(open('data/all_props.json'))}
cur.execute("SELECT id, data FROM property_data")
for pid, data in cur.fetchall():
    d = data if isinstance(data, dict) else json.loads(data or '{}')
    PROPS.setdefault(pid, {}).update(d)


def district(src):
    """1891 runs two enumerators through one range of schedule numbers."""
    m = re.search(r'schedule [^,]*? in the (.+?) district', str(src or ''))
    return m.group(1) if m else ''


def sub_no(src):
    m = re.search(r'sub number (\d+)', str(src or ''))
    return int(m.group(1)) if m else None


YEARS = [args.year] if args.year else [1871, 1881, 1891, 1901, 1911, 1921, 1939]

cur.execute("""SELECT c.census_year, c.census_household_num, c.property_id,
                      COALESCE(c.unresolved_address,'') , c.relationship,
                      p.first_name, p.last_name, c.occupation_at_census, c.source, c.id
               FROM census_entries c JOIN people p ON p.id = c.person_id
               WHERE c.census_year = ANY(%s)
               ORDER BY c.census_year, c.census_household_num NULLS LAST, c.id""", (YEARS,))
rows = cur.fetchall()

cur.execute("SELECT property_id, census_year, notes FROM census_unoccupied")
EMPTY = {}
for pid, yr, notes in cur.fetchall():
    m = re.search(r'schedule (\d+)', str(notes or ''))
    EMPTY.setdefault(yr, []).append((int(m.group(1)) if m else None, pid, notes))

# ── gather households ────────────────────────────────────────────────────────
# A schedule number is the household - but two things complicate it. Part of a
# household may have been filed to a house while the rest was not, which must
# not split it in two; and in 1891 two enumerators number their schedules
# through the same range, which must. So look first at how many different
# houses a schedule number touches, and only split where there really are two.
from collections import defaultdict
# Rows transcribed before the district was recorded carry none, so learn which
# district each house belongs to from the rows that do, and lend it to the rest.
# Without this a household is torn in half by an absence rather than a fact.
dist_of_house = {}
for (yr, sched, pid, unres, rel, fn, ln, occ, src, cid) in rows:
    if pid and district(src):
        dist_of_house.setdefault((yr, pid), district(src))

def dist_for(yr, pid, src):
    return district(src) or dist_of_house.get((yr, pid), '')

dists_of = defaultdict(set)
for (yr, sched, pid, unres, rel, fn, ln, occ, src, cid) in rows:
    d = dist_for(yr, pid, src)
    if sched is not None and d:
        dists_of[(yr, sched)].add(d)

houses = {}
for (yr, sched, pid, unres, rel, fn, ln, occ, src, cid) in rows:
    if sched is not None:
        # One schedule number means one household, EXCEPT where two enumerators
        # have used the same number - which in this record happens only in 1891,
        # where two districts both run through 146 to 177. Where a number is
        # claimed by two districts, keep them apart; otherwise hold the
        # household together even though only part of it may have been filed.
        split = len(dists_of[(yr, sched)]) > 1
        # Where it is split, the house is the better discriminator than the
        # district: rows transcribed before the district was recorded carry
        # none, and a household would be torn in half by its absence.
        grp = ('S', sched, dist_for(yr, pid, src) if split else None)
    elif pid:
        grp = ('P', pid)
    else:
        grp = ('A', (unres or '').strip().lower() or f'row{cid}')
    key = (yr, grp)
    h = houses.setdefault(key, dict(year=yr, dist='', sched=sched, pid=None,
                                    unres='', people=0, head=None, head_pid=None,
                                    head_occ=None, head_rank=99, filed=0))
    h['people'] += 1
    if pid:
        h['filed'] += 1
    if dist_for(yr, pid, src) and not h['dist']:
        h['dist'] = dist_for(yr, pid, src)
    if sched is not None and h['sched'] is None:
        h['sched'] = sched
    if pid and not h['pid']:
        h['pid'] = pid
    if unres and not h['unres']:
        h['unres'] = unres
    # Who heads the house. A census says so outright; the 1939 Register has no
    # relationship column at all, so its sub number 1 is the nearest thing.
    rank = 0 if (rel or '').strip().lower() == 'head' else (1 if sub_no(src) == 1 else 2)
    if rank < h['head_rank']:
        h['head_rank'] = rank
        h['head'] = f"{fn} {ln}".strip()
        h['head_occ'] = occ or ''
        h['head_pid'] = pid

# Schedule numbers actually read, per year. A number missing from the whole
# year is a sheet nobody has transcribed; a number missing from one district
# but present in another is not, and reporting it would be noise.
READ = defaultdict(set)
for h in houses.values():
    if h['sched'] is not None:
        READ[h['year']].add(h['sched'])

# ── write ────────────────────────────────────────────────────────────────────
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

HEAD = ['Schedule', 'District', 'Status', 'Head of the house', 'In the house',
        'No.', 'House name', 'Street', 'Property', 'As the page writes it', 'Head’s occupation']
WID  = [9, 30, 11, 28, 12, 7, 24, 26, 9, 40, 34]
FILL = {'UNFILED': 'FCE4D6', 'UNOCCUPIED': 'E2EFDA', 'NOT READ': 'FFF2CC',
        'PART FILED': 'FFD6D6'}

wb = Workbook(); wb.remove(wb.active)
summary = []
for yr in YEARS:
    # Schedule-numbered households walk in the enumerator's order; the rest
    # follow, sorted by street so they can at least be read.
    hs = sorted([h for k, h in houses.items() if h['year'] == yr],
                key=lambda h: (h['dist'], 0 if h['sched'] is not None else 1,
                               h['sched'] if h['sched'] is not None else 0,
                               (PROPS.get(h['pid'], {}).get('street') or h['unres'] or '').lower()))
    if not hs:
        continue
    ws = wb.create_sheet(str(yr))
    for i, (t, w) in enumerate(zip(HEAD, WID), 1):
        c = ws.cell(1, i, t); c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='2F4858')
        c.alignment = Alignment(vertical='center')
        ws.column_dimensions[get_column_letter(i)].width = w

    # Empty houses sit in the run where their schedule says, or at the end.
    empties = list(EMPTY.get(yr, []))
    def empty_rows_before(s):
        out = [e for e in empties if e[0] is not None and e[0] <= s]
        for e in out: empties.remove(e)
        return out

    out, counts = [], dict(filed=0, unfiled=0, empty=0, notread=0)
    prev = None
    for h in hs:
        s = h['sched']
        # A missing schedule number in an otherwise continuous run is a sheet
        # nobody has read. Only report short gaps - a jump of hundreds is the
        # edge of what was transcribed, not a hole in it.
        if prev is not None and s is not None and 1 < s - prev <= 25:
            for missing in [m for m in range(prev + 1, s) if m not in READ[yr]]:
                for e in empty_rows_before(missing):
                    out.append(('EMPTY', e)); counts['empty'] += 1
                out.append(('NOT READ', missing)); counts['notread'] += 1
        for e in empty_rows_before(s if s is not None else 10**6):
            out.append(('EMPTY', e)); counts['empty'] += 1
        out.append(('HOUSE', h))
        counts['filed' if h['pid'] else 'unfiled'] += 1
        if s is not None: prev = s
    for e in empties:
        out.append(('EMPTY', e)); counts['empty'] += 1

    r = 2
    dist_now = ''
    for kind, item in out:
        if kind == 'HOUSE' and item['dist']:
            dist_now = item['dist']
        if kind == 'HOUSE':
            h = item
            shown = h['head_pid'] or (h['pid'] if h['filed'] == h['people'] else None)
            p = PROPS.get(shown, {})
            status = ('filed' if h['filed'] == h['people'] else
                      'PART FILED' if h['filed'] else 'UNFILED')
            vals = [h['sched'], h['dist'], status, h['head'] or '', h['people'],
                    p.get('no', ''), p.get('name', '') or p.get('prev_house_name', '').split('\n')[0],
                    p.get('street', ''), shown or '', h['unres'], h['head_occ'] or '']
        elif kind == 'EMPTY':
            s, pid, notes = item; p = PROPS.get(pid, {})
            vals = [s or '', '', 'UNOCCUPIED', '- nobody in the house -', 0,
                    p.get('no', ''), p.get('name', ''), p.get('street', ''), pid,
                    (notes or '').split('.')[0], '']
        else:
            vals = [item, dist_now, 'NOT READ', '- no schedule of that number read -', '',
                    '', '', '', '', '', '']
        for i, v in enumerate(vals, 1):
            cell = ws.cell(r, i, v)
            if vals[2] in FILL:
                cell.fill = PatternFill('solid', fgColor=FILL[vals[2]])
        r += 1
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f"A1:{get_column_letter(len(HEAD))}{r-1}"
    summary.append((yr, counts, r - 2))

# ── the point of the exercise: what the neighbours place ─────────────────────
# An unfiled household with a filed house on either side of it, both on one
# street, sits between them. Where the two numbers leave exactly one house
# unaccounted for, the sheet can name it outright.
ws = wb.create_sheet('Placements', 0)
PH = ['Year', 'District', 'Schedule', 'Head of the house', 'In the house',
      'As the page writes it', 'The house before', 'The house after', 'So it should be']
for i, (t, w) in enumerate(zip(PH, [7, 28, 9, 26, 12, 34, 26, 26, 30]), 1):
    c2 = ws.cell(1, i, t); c2.font = Font(bold=True, color='FFFFFF')
    c2.fill = PatternFill('solid', fgColor='2F4858')
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = 'A2'

def num(p):
    m = re.match(r'^(\d+)$', str(p.get('no', '') or '').strip())
    return int(m.group(1)) if m else None

pr = 2
for yr in YEARS:
    hs = sorted([h for k, h in houses.items() if h['year'] == yr and h['sched'] is not None],
                key=lambda h: (h['dist'], h['sched']))
    for i, h in enumerate(hs):
        if h['head_pid']:
            continue
        before = next((x for x in reversed(hs[:i]) if x['head_pid'] and x['dist'] == h['dist']), None)
        after  = next((x for x in hs[i+1:]      if x['head_pid'] and x['dist'] == h['dist']), None)
        if not (before and after):
            continue
        pb, pa = PROPS.get(before['head_pid'], {}), PROPS.get(after['head_pid'], {})
        if not pb.get('street') or pb.get('street') != pa.get('street'):
            continue
        nb, na = num(pb), num(pa)
        # How many unfiled households sit between this same pair of houses? If
        # more than one, no single number can be offered for any of them.
        crowd = sum(1 for x in hs
                    if not x['head_pid'] and x['dist'] == h['dist']
                    and before['sched'] < x['sched'] < after['sched'])
        guess = ''
        if nb is not None and na is not None:
            lo, hi = sorted((nb, na))
            # A street numbered down one side steps by two, and a suggestion of
            # 17 between 18 and 16 is nonsense. Only offer numbers of the same
            # parity as the neighbours, and where the neighbours disagree on
            # parity the street is numbered straight through, so step by one.
            step = 2 if lo % 2 == hi % 2 else 1
            between = list(range(lo + step, hi, step))
            # A number already standing in this very round belongs to somebody
            # else, so it cannot be this house. Ruling those out is often what
            # turns two candidates into one.
            taken = {num(PROPS.get(x['head_pid'], {}))
                     for x in hs
                     if x['head_pid'] and x['dist'] == h['dist']
                     and (PROPS.get(x['head_pid'], {}).get('street') == pb.get('street'))}
            between = [n for n in between if n not in taken]
            if len(between) == 1 and crowd == 1:
                guess = f"{between[0]} {pb['street']}"
            elif between:
                guess = f"{pb['street']}, between {lo} and {hi}"
            else:
                guess = f"{pb['street']} - {lo} and {hi} are next to each other, so this house is not in the record"
        else:
            guess = pb['street']
        # Where the page itself gives a number and the neighbours point
        # somewhere else, say so. A suggestion that quietly contradicts the
        # source is worse than no suggestion at all.
        settled = bool(guess) and guess[:1].isdigit()
        written = re.match(r'^(\d+[a-z]?)\s+([A-Za-z].*?)(?: \(|,|$)', (h['unres'] or '').strip())
        clash = bool(settled and written and
                     written.group(1).lower() != guess.split(' ', 1)[0].lower())
        if clash:
            guess = f"DISAGREES - the page says {written.group(0).strip()}, the neighbours say {guess}"
        for j, v in enumerate([yr, h['dist'], h['sched'], h['head'], h['people'], h['unres'],
                               pb.get('address', ''), pa.get('address', ''), guess], 1):
            cell = ws.cell(pr, j, v)
            if j == 9 and settled:
                cell.font = Font(bold=True)
                cell.fill = PatternFill('solid', fgColor='F4CCCC' if clash else 'D9EAD3')
        pr += 1
print(f"\nPlacements the neighbours suggest: {pr-2}\n")

print(f"{'year':6}{'rows':>7}{'filed':>8}{'UNFILED':>9}{'empty':>8}{'not read':>10}")
for yr, c_, n in summary:
    print(f"{yr:<6}{n:>7}{c_['filed']:>8}{c_['unfiled']:>9}{c_['empty']:>8}{c_['notread']:>10}")

out = args.out or os.path.expanduser(
    f'~/Desktop/Census runs{" " + str(args.year) if args.year else ""}.xlsx')
wb.save(out)
print(f"\nWritten to {out}")
