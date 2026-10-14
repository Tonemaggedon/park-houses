#!/usr/bin/env python3
"""Build an emailable copy of the contributor's guide.

docs/contributor-guide.md is the one copy of the guide; the site renders it at
/guide and this turns the same file into something that survives a mail client.
Run it again after editing the guide.

Writes three files into docs/:
  contributor-guide-email.html  the whole guide, styles inlined, ready to paste
  contributor-guide-email.txt   the same as plain text, for the text part
  contributor-guide-invite.html a short covering note that links to /guide

Mail clients are not browsers. There is no stylesheet, no class, no flexbox and
no grid here: every rule is inlined on the element it applies to, and the layout
is a table, because Outlook still lays out with Word's engine.
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'docs', 'contributor-guide.md')
SITE = 'https://nottinghamparkhouses.com'

INK, SOFT, FAINT, RULE, PAPER, GREEN = '#2a2418', '#6a5c44', '#8a7a5a', '#e0d8c4', '#faf7ef', '#2f4d27'
SERIF = "Georgia,'Times New Roman',serif"

P   = f'margin:0 0 13px;font-family:{SERIF};font-size:15px;line-height:1.6;color:{INK};overflow-wrap:break-word'
H2  = f'margin:30px 0 10px;font-family:{SERIF};font-size:19px;line-height:1.3;color:{INK};border-top:1px solid {RULE};padding-top:16px'
H3  = f'margin:22px 0 7px;font-family:{SERIF};font-size:16px;line-height:1.3;color:#25401f'
LI  = f'margin:0 0 6px;font-family:{SERIF};font-size:15px;line-height:1.55;color:{INK}'
TH  = f'text-align:left;background:#f3eee1;padding:7px 11px;font-family:{SERIF};font-size:13px;color:{INK};border-bottom:1px solid {RULE}'
TD  = f'padding:7px 11px;font-family:{SERIF};font-size:13px;line-height:1.5;color:{INK};border-bottom:1px solid #f0ebdd;vertical-align:top'
COD = 'font-family:Menlo,Consolas,monospace;font-size:12px;background:#f1ece0;padding:1px 4px;border-radius:3px'


def inline(text):
    """Markdown's inline bits. Escape first, then put the markup back."""
    t = html.escape(text, quote=False)
    t = re.sub(r'`([^`]+)`', lambda m: f'<code style="{COD}">{m.group(1)}</code>', t)

    def link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith(('http://', 'https://', 'mailto:')):
            url = href
        elif href.startswith('/'):
            url = SITE + href          # a site path only works as a full address in an email
        else:
            url = f'https://github.com/Tonemaggedon/park-houses/blob/main/docs/{href}'
        return f'<a href="{html.escape(url, quote=True)}" style="color:{GREEN}">{label}</a>'

    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(^|[\s(])\*([^*\n]+)\*', r'\1<em>\2</em>', t)
    # A bare /path in running text is no use to somebody reading their mail.
    t = re.sub(r'(<code style="[^"]*">)(/[a-z0-9/-]*)(</code>)',
               lambda m: f'<a href="{SITE}{m.group(2)}" style="color:{GREEN};text-decoration:none">'
                         f'{m.group(1)}{m.group(2)}{m.group(3)}</a>', t)
    return t


def plain(text):
    t = re.sub(r'`([^`]+)`', r'\1', text)
    t = re.sub(r'\[([^\]]+)\]\(mailto:[^)\s]+\)', r'\1', t)   # the label is the address
    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'\1 (\2)', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
    t = re.sub(r'(^|[\s(])\*([^*\n]+)\*', r'\1\2', t)
    return t


def convert(md):
    lines = md.replace('\r', '').split('\n')
    out, txt = [], []
    i, in_list = 0, None

    def shut():
        nonlocal in_list
        if in_list:
            out.append(f'</{in_list}>')
            in_list = None

    while i < len(lines):
        line = lines[i]

        if line.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i + 1]):
            shut()
            cells = lambda r: [c.strip() for c in r.strip('|').split('|')]
            head = cells(line)
            out.append('<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
                       f'width="100%" style="border-collapse:collapse;table-layout:auto;'
                       f'border:1px solid {RULE};border-radius:6px;margin:0 0 18px"><tr>'
                       + ''.join(f'<th style="{TH}">{inline(c)}</th>' for c in head) + '</tr>')
            txt.append('  ' + ' | '.join(plain(c) for c in head))
            i += 2
            while i < len(lines) and lines[i].startswith('|'):
                row = cells(lines[i])
                out.append('<tr>' + ''.join(f'<td style="{TD}">{inline(c)}</td>' for c in row) + '</tr>')
                txt.append('  ' + ' | '.join(plain(c) for c in row))
                i += 1
            out.append('</table>')
            txt.append('')
            continue

        h = re.match(r'^(#{1,3})\s+(.*)$', line)
        if h:
            shut()
            level, text = len(h.group(1)), h.group(2)
            if level == 1:
                out.append(f'<h1 style="margin:0 0 6px;font-family:{SERIF};font-size:25px;'
                           f'line-height:1.25;color:{INK}">{inline(text)}</h1>')
                txt += [plain(text), '=' * len(plain(text)), '']
            else:
                out.append(f'<h{level} style="{H2 if level == 2 else H3}">{inline(text)}</h{level}>')
                txt += ['', plain(text), '-' * len(plain(text)), '']
            i += 1
            continue

        if line.startswith('>'):
            shut()
            quoted = []
            while i < len(lines) and lines[i].startswith('>'):
                quoted.append(re.sub(r'^>\s?', '', lines[i]))
                i += 1
            paras = [re.sub(r'\s+', ' ', par).strip()
                     for par in re.split(r'\n\s*\n', '\n'.join(quoted)) if par.strip()]
            inner = ''.join(
                f'<p style="{P};font-size:16px;margin:0 0 9px">{inline(par)}</p>' for par in paras)
            out.append(
                '<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
                'style="border-collapse:collapse;margin:0 0 18px"><tr>'
                '<td width="5" style="width:5px;background:#a3741f;font-size:0;line-height:0">&nbsp;</td>'
                '<td style="background:#fdf6e6;border:1px solid #e3cf9e;border-left:0;'
                f'padding:14px 18px">{inner}</td></tr></table>')
            txt += ['  ' + plain(par) for par in paras] + ['']
            continue

        if re.match(r'^(\*\*\*|---|___)\s*$', line):
            shut()
            out.append(f'<hr style="border:0;border-top:1px solid {RULE};margin:24px 0">')
            txt.append('')
            i += 1
            continue

        bullet = re.match(r'^[-*]\s+(.*)$', line)
        number = re.match(r'^(\d+)\.\s+(.*)$', line)
        if bullet or number:
            want = 'ul' if bullet else 'ol'
            if in_list != want:
                shut()
                out.append(f'<{want} style="margin:0 0 14px;padding-left:22px">')
                in_list = want
            text = bullet.group(1) if bullet else number.group(2)
            while i + 1 < len(lines) and re.match(r'^\s{2,}\S', lines[i + 1]):
                text += ' ' + lines[i + 1].strip()
                i += 1
            out.append(f'<li style="{LI}">{inline(text)}</li>')
            txt.append(('  - ' if bullet else f'  {number.group(1)}. ') + plain(text))
            i += 1
            continue

        if not line.strip():
            shut()
            i += 1
            continue

        para = line
        while (i + 1 < len(lines) and lines[i + 1].strip()
               and not re.match(r'^([-*]\s|\d+\.\s|#{1,3}\s|\||>)', lines[i + 1])):
            para += ' ' + lines[i + 1].strip()
            i += 1
        out.append(f'<p style="{P}">{inline(para.strip())}</p>')
        txt += [plain(para.strip()), '']
        i += 1

    shut()
    return '\n'.join(out), '\n'.join(txt)


def wrap(body, title):
    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<meta name="format-detection" content="telephone=no,address=no,date=no">
<title>{html.escape(title)}</title></head>
<body style="margin:0;padding:0;background:{PAPER}">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
       style="background:{PAPER}"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
       style="max-width:640px;background:#ffffff;border:1px solid {RULE};border-radius:8px">
  <tr><td style="background:#25401f;padding:16px 24px;border-radius:7px 7px 0 0">
    <div style="font-family:{SERIF};font-size:19px;color:#f2ecd8;font-weight:bold">Nottingham Park Houses</div>
    <div style="font-family:{SERIF};font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:#b9c9a8;padding-top:2px">The Park Conservation Trust — Historical Record</div>
  </td></tr>
  <tr><td style="padding:24px 26px 28px">
{body}
  </td></tr>
  <tr><td style="padding:14px 26px 20px;border-top:1px solid {RULE}">
    <p style="margin:0;font-family:{SERIF};font-size:12px;line-height:1.5;color:{FAINT}">
      This guide lives on the site at
      <a href="{SITE}/guide" style="color:{GREEN}">nottinghamparkhouses.com/guide</a>,
      where it is always the current one.</p>
  </td></tr>
</table>
</td></tr></table>
</body></html>
'''



# ── The letter to everybody who lives here ───────────────────────────────────
# A different audience from the guide: most people who read this will never
# edit anything, and the thing they most need told is what the record does
# *not* hold. So the reassurance comes before the asking, and the asking is one
# concrete thing — the name on the gatepost — rather than a list of jobs.
#
# Figures are from the live site on 14 October 2026. Check them before sending
# if it has been a while: nottinghamparkhouses.com/api/stats.
HOUSES, PEOPLE, WITH_PEOPLE, NAMED, PHOTOS = 439, '8,352', 414, 141, 351


def button(href, label):
    return (f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:0 0 18px"><tr><td style="background:#2f4d27;border-radius:6px">'
            f'<a href="{href}" style="display:inline-block;padding:11px 22px;font-family:{SERIF};'
            f'font-size:15px;color:#f2ecd8;text-decoration:none;font-weight:bold">{label}</a>'
            f'</td></tr></table>')


def residents_body():
    return f"""<h1 style="margin:0 0 6px;font-family:{SERIF};font-size:25px;line-height:1.25;color:{INK}">The Park, house by house</h1>
<p style="{P}">There is now a record of the estate — <strong>all {HOUSES} houses and the {PEOPLE}
people who lived in them</strong> between the first census in 1841 and the register taken in the
first weeks of the war in 1939. It is free, it is open to anybody, and your house is almost certainly
in it.</p>
{button(SITE, 'Find your house')}
<p style="{P}">On a house you will find when it was built and who built it, what the architects did
to it since, photographs — {PHOTOS} houses have one — and the households who lived there census by
census: their ages, where they were born, and what they did for a living. {WITH_PEOPLE} of the
{HOUSES} houses have people in them, and <strong>44 of them held twelve or more under one roof on
a single census night</strong> — a family, and the people who worked for them.</p>

{rule_box_residents()}

<h2 style="{H2}">Where it is wrong, we would like to know</h2>
<p style="{P}">A good deal of this was read off census pages written in pencil, in bad light, by a
man walking door to door in an evening, and then typed up by somebody else a century later. Names
are misspelt. Houses have been renumbered. Two houses have been made into one, and one house into
four flats. If the record has your house wrong — or has it on the wrong street — it takes a minute
to say so.</p>

<h2 style="{H2}">And the thing we most need is on your gatepost</h2>
<p style="{P}"><strong>Only {NAMED} of the {HOUSES} houses have a name recorded.</strong> The rest
have numbers and nothing else, though a great many of them carry a name on the gate, the gatepost,
a fanlight or the first page of the deeds. That is the single largest gap in the record, and it is
the one gap that cannot be closed in an archive — somebody has to stand in front of the house and
read it.</p>
<p style="{P}">If your house has a name, we would be glad of it. The same goes for old photographs,
deeds, sale particulars, a conveyance with a plan on it, or anything your family remembers about
who was here before you.</p>
{button(SITE + '/contact?kind=correction', 'Tell us something')}

<h2 style="{H2}">Or walk it</h2>
<p style="{P}">The record has a walk built into it. Tell it how long you have — fifteen minutes is
enough — and it finds you, plots a route from where you are standing, and tells you about the
houses as you reach them. One of the walks follows <strong>the enumerator's own round of the
evening of 29 September 1939</strong>, door by door, in the order he knocked. It is not the order
of the street: he doubles back, crosses over, and comes to the lodge last.</p>
{button(SITE + '/walk', 'Walk it')}

<h2 style="{H2}">If you would like to work on it properly</h2>
<p style="{P}">Anybody can. There is a guide to what every page is for, what you can do on it, and
where to start if you have an hour — and the first thing in it is what can and cannot go in.</p>
<p style="{P}"><a href="{SITE}/guide" style="color:{GREEN};font-weight:bold">Read the
contributor's guide</a> &nbsp;·&nbsp; <a href="{SITE}/join" style="color:{GREEN}">Join the
record</a></p>
<hr style="border:0;border-top:1px solid {RULE};margin:24px 0">
<p style="{P};font-size:14px;color:{SOFT}">[Your name]<br>[The Park Conservation Trust]</p>"""


def rule_box_residents():
    return f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
       style="border-collapse:collapse;margin:0 0 20px"><tr>
  <td width="5" style="width:5px;background:#a3741f;font-size:0;line-height:0">&nbsp;</td>
  <td style="background:#fdf6e6;border:1px solid #e3cf9e;border-left:0;padding:15px 18px">
    <p style="{P};font-size:16px;margin:0 0 9px"><strong>It stops in 1939, and it holds nobody
      living.</strong></p>
    <p style="{P};font-size:15px;margin:0 0 9px">The record is of people who have died. Nothing
      about anybody living is in it and nothing about anybody living will go in it — not who lives
      in a house now, not who owns one, not who is in a photograph. Where a house carries a name
      its owner uses today, the name goes in and the householder does not.</p>
    <p style="{P};font-size:15px;margin:0 0 9px">Photographs are of buildings, taken from the
      pavement. Never of people, never through a window, never over a wall.</p>
    <p style="{P};font-size:15px;margin:0"><strong>If you think something on the site should not be
      there</strong> — about you or about anybody else — say so and it comes down while it is
      looked at. You do not have to explain why, and you do not need an account.
      <a href="{SITE}/contact?kind=takedown" style="color:{GREEN}">Ask for something to be taken
      down.</a></p>
  </td></tr></table>"""


RESIDENTS_TEXT = f"""The Park, house by house
========================

There is now a record of the estate - all {HOUSES} houses and the {PEOPLE} people who lived in
them between the first census in 1841 and the register taken in the first weeks of the war in 1939.
It is free, it is open to anybody, and your house is almost certainly in it.

Find your house: {SITE}

On a house you will find when it was built and who built it, what the architects did to it since,
photographs - {PHOTOS} houses have one - and the households who lived there census by census:
their ages, where they were born, and what they did for a living. {WITH_PEOPLE} of the {HOUSES}
houses have people in them, and 44 of them held twelve or more under one roof on a single census
night - a family, and the people who worked for them.


IT STOPS IN 1939, AND IT HOLDS NOBODY LIVING

The record is of people who have died. Nothing about anybody living is in it and nothing about
anybody living will go in it - not who lives in a house now, not who owns one, not who is in a
photograph. Where a house carries a name its owner uses today, the name goes in and the
householder does not. Photographs are of buildings, taken from the pavement.

If you think something on the site should not be there - about you or about anybody else - say so
and it comes down while it is looked at. You do not have to explain why, and you do not need an
account: {SITE}/contact?kind=takedown


WHERE IT IS WRONG, WE WOULD LIKE TO KNOW

A good deal of this was read off census pages written in pencil, in bad light, by a man walking
door to door in an evening, and typed up by somebody else a century later. Names are misspelt.
Houses have been renumbered. If the record has your house wrong, it takes a minute to say so.


AND THE THING WE MOST NEED IS ON YOUR GATEPOST

Only {NAMED} of the {HOUSES} houses have a name recorded. The rest have numbers and nothing else,
though a great many carry a name on the gate, the gatepost, a fanlight or the first page of the
deeds. That is the largest gap in the record and the one that cannot be closed in an archive.

If your house has a name, we would be glad of it - and of old photographs, deeds, sale
particulars, or anything your family remembers about who was here before you.

Tell us something: {SITE}/contact?kind=correction


OR WALK IT

Tell it how long you have - fifteen minutes is enough - and it finds you, plots a route from where
you are standing, and tells you about the houses as you reach them. One walk follows the
enumerator's own round of the evening of 29 September 1939, door by door, in the order he knocked.

{SITE}/walk


IF YOU WOULD LIKE TO WORK ON IT PROPERLY

Anybody can. The guide says what every page is for and where to start:
{SITE}/guide
{SITE}/join

[Your name]
[The Park Conservation Trust]
"""


def main():
    with open(SRC, encoding='utf-8') as fh:
        md = fh.read()
    body, text = convert(md)

    full = wrap(body, "A contributor's guide — Nottingham Park Houses")
    rule_box = f"""<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
       style="border-collapse:collapse;margin:0 0 18px"><tr>
  <td width="5" style="width:5px;background:#a3741f;font-size:0;line-height:0">&nbsp;</td>
  <td style="background:#fdf6e6;border:1px solid #e3cf9e;border-left:0;padding:15px 18px">
    <p style="{P};font-size:16px;margin:0 0 9px"><strong>Before anything else: the record holds
      people who have died, and everything in it is public.</strong></p>
    <p style="{P};font-size:15px;margin:0 0 9px"><strong>Do not add a living person.</strong>
      Somebody new needs a name, a year of birth, a place of birth — and a year of death if they
      were born in the last hundred years. The form will not take them without it.</p>
    <p style="{P};font-size:15px;margin:0 0 9px"><strong>Do not record who lives in a house
      now</strong>, and do not write about a living person anywhere else either — not in a house's
      history, not in a discussion, not under a photograph. Photograph the building, from the
      pavement, never people or through windows.</p>
    <p style="{P};font-size:15px;margin:0">The census is different: everybody in it died long ago,
      and those records are published so they can be read.
      <a href="{SITE}/guide#what-you-can-and-cannot-add" style="color:{GREEN}">The full rule is at
      the top of the guide.</a> If you are not sure, ask before you add it — and if you think
      something on the site should not be there, about you or anybody else,
      <a href="{SITE}/contact?kind=takedown" style="color:{GREEN}">say so here</a> and it comes
      down while it is looked at.</p>
  </td></tr></table>"""

    invite_body = f'''<h1 style="margin:0 0 6px;font-family:{SERIF};font-size:25px;line-height:1.25;color:{INK}">A guide for contributors</h1>
<p style="{P}">The record of The Park's four hundred houses and the people who lived in them is
open to anybody who wants to work on it, and there is now a guide to what every page is for and
what you can do on it.</p>
{rule_box}
<p style="{P}"><a href="{SITE}/guide" style="color:{GREEN};font-weight:bold">Read the guide</a> —
it covers the working pages, the walk that takes the record out of doors, the discussion board,
and where to start if you have an hour.</p>
<p style="{P}">Three things worth knowing before you begin:</p>
<ul style="margin:0 0 14px;padding-left:22px">
  <li style="{LI}"><strong>If you have a question about a house, ask it.</strong> Open the house on
    the map and press <em>Ask about this house</em>. A guess typed into the record is
    indistinguishable from a fact a week later; a guess in a thread is a question somebody can
    answer.</li>
  <li style="{LI}"><strong>Needs work</strong> is a list of jobs somebody could finish in an
    evening, each saying what is missing and what would finish it.</li>
  <li style="{LI}"><strong>Walk it</strong> gives you the houses nearest to you and the questions
    that can only be settled standing in front of them. Fifteen minutes is enough to be useful.</li>
</ul>
<p style="{P}">You can read everything without an account. To change anything,
<a href="{SITE}/join" style="color:{GREEN}">join the record</a> and I will set you up.</p>'''
    invite = wrap(invite_body, 'A guide for contributors — Nottingham Park Houses')

    footer = f'\n\nThis guide lives at {SITE}/guide, where it is always the current one.\n'
    files = {
        'contributor-guide-email.html': full,
        'contributor-guide-email.txt': text.rstrip() + footer,
        'contributor-guide-invite.html': invite,
        'residents-letter.html': wrap(residents_body(), 'The Park, house by house'),
        'residents-letter.txt': RESIDENTS_TEXT.strip() + '\n',
    }
    for name, content in files.items():
        path = os.path.join(ROOT, 'docs', name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'{name:34} {len(content):>7,} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
