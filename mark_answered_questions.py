# -*- coding: utf-8 -*-
"""The public Open Questions page shows 294 questions. A third of them are answers.

Questions are written up in place: when one is settled the title is rewritten to
say so and the detail opens with the answer. Nothing ever set `status`, so the
seed loads every one as open and the page offers a hundred finished write-ups as
things to go and find out.

Marked answered when the title says so outright, or the area is Answered, or the
first lines of the detail open with a settled marker. Everything else is left
open, because a question wrongly closed is worse than one wrongly left open.
"""
import json, re, sys
apply = '--apply' in sys.argv
TITLE = re.compile(r'^\s*(ANSWERED|SUPERSEDED|SETTLED|SOLVED)\b', re.I)
OPENER = re.compile(r'\*\*(ANSWERED|Settled|SETTLED|Found\b|Answered|Done\b)', re.I)
d = json.load(open('data/research_questions.json'))
marked, kept = [], []
for q in d['questions']:
    head = q['detail'][:260]
    is_done = bool(TITLE.search(q['title'])) or q.get('area') == 'Answered' or bool(OPENER.search(head))
    (marked if is_done else kept).append(q)
    if apply:
        q['status'] = 'answered' if is_done else 'open'
print(f"  {len(marked)} answered, {len(kept)} still open, of {len(d['questions'])}")
print("\n  a sample of what is being closed:")
for q in marked[:8]:
    print(f"    [{q.get('area')}] {q['title'][:78]}")
print("\n  a sample of what stays open:")
for q in kept[:8]:
    print(f"    [{q.get('area')}] {q['title'][:78]}")
if apply:
    json.dump(d, open('data/research_questions.json', 'w'), indent=1, ensure_ascii=False)
    print("\n  written")
else:
    print("\n  preview only - pass --apply")
