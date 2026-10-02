# -*- coding: utf-8 -*-
"""Give every research question an area, so the list reads as work and not weather.

A hundred and ninety-six questions in one run is a wall. Sorted by what kind of
work they are, they become six short lists a person can pick up and put down.

  python3 tools_area_questions.py          # show the sort
  python3 tools_area_questions.py --write  # write it into the file
"""
import json, re, sys, collections

WRITE = '--write' in sys.argv
P = 'data/research_questions.json'

ANSWERED = re.compile(r'^(ANSWERED|PROVED|PART ANSWERED|ANSWERED in part)\b|^[A-Za-z].*: answered\b|— answered\b|- answered\b', re.I)

# Where a question's area is not what its kind suggests. Slug -> area.
BY_SLUG = {
 'questions-for-a-walk-round-the-park': 'On foot',
 'every-census-gap-and-where-to-start': 'Missing census',
 'notables-the-1939-register-brought-in': 'People',
 'broxtowe-house-which-hospital': 'People',
 'holland-sisters-duval-line': 'People',
 'the-vad-women-of-the-1939-register': 'People',
 'clumber-court-stub': 'Houses to find',
 'dougal-map-architect-colours': 'Birthplaces and maps',
 'birthplace-counties-wrong': 'Birthplaces and maps',
 'five-birthplaces-the-geocoder-sends-abroad': 'Birthplaces and maps',
 'winifred-goldsmith-born-shropshire-or-devizes': 'Birthplaces and maps',
}

# Words in a title that mean a missing census round rather than a missing house
CENSUS = ('gap in every census', 'schedules of', 'still unfiled', 'left unfiled',
          'has no 1921 household', 'no census household', 'stood empty on census night',
          'the record holds nothing at all', 'is still to read', 'round of its own',
          'placed off 1871', 'have no 1921 household', 'brought in who belong')

KIND_AREA = {
 'house-name': 'House names',
 'name':       'Names to settle',
 'people':     'People',
 'person':     'People',
 'data':       'The record itself',
 'record':     'The record itself',
 'reference':  'People',
 'document':   'Missing census',
 'date':       'The record itself',
 'address':    'Houses to find',
 'property':   'Houses to find',
 'building':   'Houses to find',
 'place':      'Houses to find',
 'house':      'Houses to find',
}

# A street whose numbers do not line up is a different morning's work from a
# house nobody can find: one is settled from a directory or a walk, the other
# from a census page.
NUMBERING = ('numbered', 'numbering', 'numbers', 'has no 5, 8 or 10', 'runs 1 to',
             'runs 1 and', 'jumps from', 'no 11, 12 or 13', 'no even numbers',
             'two house numbers', 'convert', 'is numbered', 'at numbers',
             'which end of', 'the number', 'house number', 'and then 14',
             'writes 38', 'stops at 30', 'past number 10', 'no 13 because',
             'got its numbers', 'is 1 to 13')

ORDER = ['Missing census', 'Houses to find', 'Street numbering', 'House names',
         'Names to settle', 'People', 'Birthplaces and maps', 'The record itself',
         'On foot', 'Answered']


def area_for(q):
    if q['slug'] in BY_SLUG:
        return BY_SLUG[q['slug']]
    if ANSWERED.search(q['title']):
        return 'Answered'
    low = q['title'].lower()
    if any(w in low for w in CENSUS):
        return 'Missing census'
    area = KIND_AREA.get(q.get('kind'), 'The record itself')
    if area == 'Houses to find' and any(w in low for w in NUMBERING):
        return 'Street numbering'
    return area


def main():
    d = json.load(open(P))
    for q in d['questions']:
        q['area'] = area_for(q)
    d['questions'].sort(key=lambda q: (ORDER.index(q['area']), q.get('priority', 999), q['slug']))
    counts = collections.Counter(q['area'] for q in d['questions'])
    for a in ORDER:
        print(f"  {a:<20} {counts[a]:>3}")
    print(f"  {'TOTAL':<20} {len(d['questions']):>3}")
    print(f"  {'still open':<20} {len(d['questions']) - counts['Answered']:>3}")
    if WRITE:
        d['note'] = (d['note'].split('\n\n')[0]
                     + "\n\n**Sorted by area.** Every question carries an `area`, and the file is "
                       "ordered by it, then by priority: "
                     + ', '.join(f'**{a}**' for a in ORDER)
                     + ". The areas are kinds of work, not kinds of subject - a person opens one of "
                       "them and finds a morning's worth of the same sort of thinking, rather than "
                       "a hundred and ninety-six of everything.")
        json.dump(d, open(P, 'w'), indent=2, ensure_ascii=False)
        print("\n  written")
    else:
        print("\n  Nothing written. Add --write.")


if __name__ == '__main__':
    main()
