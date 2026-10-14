#!/usr/bin/env python3
"""Make a PDF of the contributor's guide.

docs/contributor-guide.md stays the one copy. The site renders it at /guide,
tools_build_guide_email.py turns it into something that survives a mail client,
and this lays it out for paper. Run it again after editing the guide.

    python3 tools_build_guide_pdf.py     →  public/contributors-guide.pdf, which the
                                            /guide page links to

It renders through the copy of Chrome already on the machine, in a throwaway
profile so it cannot disturb a Chrome the user has open, and with Chrome's own
header and footer turned off — the date and the file path it prints there do a
document no favours.
"""
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'docs', 'contributor-guide.md')
# It goes into public/ rather than docs/ so the site can hand it out: the /guide
# page links to it, and that link is the thing worth sending somebody who wants
# the guide on paper or on a train with no signal.
OUT = os.path.join(ROOT, 'public', 'contributors-guide.pdf')
SITE = 'https://nottinghamparkhouses.com'
CHROMES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    shutil.which('google-chrome') or '', shutil.which('chromium') or '',
]

CSS = """
@page { size: A4; margin: 20mm 18mm 18mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: Georgia, 'Times New Roman', serif; font-size: 10.5pt;
  line-height: 1.5; color: #2a2418; }

/* The title page is a page, not a cover: the guide is a working document and
   somebody is going to print it double-sided and staple it. */
.title { border-bottom: 2px solid #2f4d27; padding-bottom: 14px; margin-bottom: 22px; }
.title .brand { font-size: 9pt; letter-spacing: .14em; text-transform: uppercase;
  color: #6a5c44; margin-bottom: 7px; }
.title h1 { margin: 0 0 4px; font-size: 24pt; line-height: 1.15; }
.title .sub { color: #6a5c44; font-style: italic; font-size: 11pt; margin: 0; }
.title .when { color: #8a7a5a; font-size: 8.5pt; margin-top: 9px; }

.contents { background: #f6f2e7; border: 1px solid #e0d8c4; border-radius: 5px;
  padding: 13px 18px; margin: 0 0 26px; break-inside: avoid; }
.contents b { display: block; font-size: 8.5pt; letter-spacing: .12em;
  text-transform: uppercase; color: #6a5c44; margin-bottom: 7px; }
.contents ul { margin: 0; padding: 0; list-style: none; columns: 2; column-gap: 26px;
  font-size: 9.5pt; }
.contents li { margin-bottom: 3px; break-inside: avoid; }
.contents a { color: #2a2418; text-decoration: none; }

h2 { font-size: 14pt; margin: 22pt 0 7pt; padding-top: 9pt; border-top: 1px solid #e0d8c4;
  break-after: avoid; break-inside: avoid; }
h3 { font-size: 11.5pt; margin: 14pt 0 5pt; color: #25401f; break-after: avoid; }
p { margin: 0 0 8pt; orphans: 2; widows: 2; }
ul, ol { margin: 0 0 9pt; padding-left: 17px; }
li { margin-bottom: 3pt; }
a { color: #2f4d27; text-decoration: none; }
strong { color: #1f1a10; }
code { font-family: Menlo, Consolas, monospace; font-size: 8.8pt; background: #f1ece0;
  padding: 0 3px; border-radius: 2px; }
hr { border: 0; border-top: 1px solid #e0d8c4; margin: 14pt 0; }

blockquote { margin: 0 0 12pt; padding: 11px 15px; background: #fdf6e6;
  border: 1px solid #e3cf9e; border-left: 4px solid #a3741f; border-radius: 0 4px 4px 0;
  break-inside: avoid; }
blockquote p { margin: 0; font-size: 11pt; }
blockquote p + p { margin-top: 6pt; }

table { width: 100%; border-collapse: collapse; font-size: 9pt; margin: 0 0 12pt;
  border: 1px solid #e0d8c4; }
thead { display: table-header-group; }          /* repeat the heads over a page break */
th { text-align: left; background: #f3eee1; padding: 5px 8px; border-bottom: 1px solid #e0d8c4;
  font-weight: bold; }
td { padding: 5px 8px; border-bottom: 1px solid #f0ebdd; vertical-align: top; }
tr { break-inside: avoid; }
tr:last-child td { border-bottom: 0; }
td:first-child { white-space: nowrap; }
td:first-child:only-child, td { word-break: normal; }

.foot { margin-top: 20pt; padding-top: 9pt; border-top: 1px solid #e0d8c4;
  font-size: 8.5pt; color: #8a7a5a; break-inside: avoid; }
"""


def inline(text):
    t = html.escape(text, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)

    def link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith(('http://', 'https://', 'mailto:')):
            url = href
        elif href.startswith('/'):
            url = SITE + href           # on paper a site path has to be a full address
        elif href.startswith('#'):
            url = href
        else:
            url = f'https://github.com/Tonemaggedon/park-houses/blob/main/docs/{href}'
        return f'<a href="{html.escape(url, quote=True)}">{label}</a>'

    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', link, t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    t = re.sub(r'(^|[\s(])\*([^*\n]+)\*', r'\1<em>\2</em>', t)
    return t


def slug(s):
    return re.sub(r'^-|-$', '', re.sub(r'[^a-z0-9]+', '-', s.lower()))


def convert(md):
    lines = md.replace('\r', '').split('\n')
    out, heads = [], []
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
            out.append('<table><thead><tr>'
                       + ''.join(f'<th>{inline(c)}</th>' for c in cells(line))
                       + '</tr></thead><tbody>')
            i += 2
            while i < len(lines) and lines[i].startswith('|'):
                out.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in cells(lines[i])) + '</tr>')
                i += 1
            out.append('</tbody></table>')
            continue

        h = re.match(r'^(#{1,3})\s+(.*)$', line)
        if h:
            shut()
            level, text = len(h.group(1)), h.group(2)
            if level == 1:
                i += 1
                # The italic line under the title belongs to the title block, so
                # skip it here rather than printing it twice.
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if i < len(lines) and re.match(r'^\*[^*].*\*$', lines[i].strip()):
                    i += 1
                continue
            ident = slug(text)
            if level == 2:
                heads.append((ident, text))     # keep the section's own number
            out.append(f'<h{level} id="{ident}">{inline(text)}</h{level}>')
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
            out.append('<blockquote>' + ''.join(f'<p>{inline(p)}</p>' for p in paras) + '</blockquote>')
            continue

        if re.match(r'^(\*\*\*|---|___)\s*$', line):
            shut(); out.append('<hr>'); i += 1; continue

        bullet = re.match(r'^[-*]\s+(.*)$', line)
        number = re.match(r'^(\d+)\.\s+(.*)$', line)
        if bullet or number:
            want = 'ul' if bullet else 'ol'
            if in_list != want:
                shut(); out.append(f'<{want}>'); in_list = want
            text = bullet.group(1) if bullet else number.group(2)
            while i + 1 < len(lines) and re.match(r'^\s{2,}\S', lines[i + 1]):
                text += ' ' + lines[i + 1].strip()
                i += 1
            out.append(f'<li>{inline(text)}</li>')
            i += 1
            continue

        if not line.strip():
            shut(); i += 1; continue

        para = line
        while (i + 1 < len(lines) and lines[i + 1].strip()
               and not re.match(r'^([-*]\s|\d+\.\s|#{1,3}\s|\||>)', lines[i + 1])):
            para += ' ' + lines[i + 1].strip()
            i += 1
        out.append(f'<p>{inline(para.strip())}</p>')
        i += 1

    shut()
    return '\n'.join(out), heads


def page(body, heads, title, subtitle):
    when = date.today().strftime('%-d %B %Y')
    contents = ''.join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in heads)
    # heads carries the heading's own text, numbers and all
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<div class="title">
  <div class="brand">Nottingham Park Houses — The Park Conservation Trust</div>
  <h1>{html.escape(title)}</h1>
  <p class="sub">{html.escape(subtitle)}</p>
  <div class="when">As it stood on {when}. The current version is always at {SITE}/guide</div>
</div>
<div class="contents"><b>What is in it</b><ul>{contents}</ul></div>
{body}
<p class="foot">This guide is kept at {SITE}/guide and is rewritten as the site changes, so a
printed copy goes out of date. Anything in it that is wrong, or anything on the site that should
not be there, can be said at {SITE}/contact</p>
</body></html>"""


def find_chrome():
    for path in CHROMES:
        if path and os.path.exists(path):
            return path
    return None


def main():
    with open(SRC, encoding='utf-8') as fh:
        md = fh.read()
    title = re.search(r'^#\s+(.*)$', md, re.M).group(1)
    subtitle = re.search(r'^\*(.+?)\*\s*$', md, re.M).group(1)
    body, heads = convert(md)

    chrome = find_chrome()
    if not chrome:
        print('No Chrome, Chromium or Edge found to render with.', file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'guide.html')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write(page(body, heads, title, subtitle))
        cmd = [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
               f'--user-data-dir={os.path.join(tmp, "profile")}',   # never the user's own Chrome
               '--no-pdf-header-footer', '--print-to-pdf-no-header',
               f'--print-to-pdf={OUT}', 'file://' + src]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if r.returncode != 0 or not os.path.exists(OUT):
            print(r.stderr.strip()[-800:] or 'Chrome produced nothing.', file=sys.stderr)
            return 1

    size = os.path.getsize(OUT)
    print(f'public/contributors-guide.pdf  {size:,} bytes  ({len(heads)} sections)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
