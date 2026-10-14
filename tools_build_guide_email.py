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

P   = f'margin:0 0 13px;font-family:{SERIF};font-size:15px;line-height:1.6;color:{INK};word-break:break-word'
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
        if href.startswith(('http://', 'https://')):
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
               and not re.match(r'^([-*]\s|\d+\.\s|#{1,3}\s|\|)', lines[i + 1])):
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
<title>{html.escape(title)}</title></head>
<body style="margin:0;padding:0;background:{PAPER};word-break:break-word">
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


def main():
    with open(SRC, encoding='utf-8') as fh:
        md = fh.read()
    body, text = convert(md)

    full = wrap(body, "A contributor's guide — Nottingham Park Houses")
    invite_body = f'''<h1 style="margin:0 0 6px;font-family:{SERIF};font-size:25px;line-height:1.25;color:{INK}">A guide for contributors</h1>
<p style="{P}">The record of The Park's four hundred houses and the people who lived in them is
open to anybody who wants to work on it, and there is now a guide to what every page is for and
what you can do on it.</p>
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
    }
    for name, content in files.items():
        path = os.path.join(ROOT, 'docs', name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'{name:34} {len(content):>7,} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
