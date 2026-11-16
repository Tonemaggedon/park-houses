#!/usr/bin/env python3
"""Make a dossier PDF for one house out of photographed pages.

A. Hagues photographs a bound document — somebody's history of a house, a
sheaf of deeds, a folder from the Archives — and wants it back as one PDF that
reads properly rather than sixteen loose snapshots.

    python3 tools_build_house_dossier.py <folder>

The folder holds the page images and a dossier.json beside them:

    {
      "title":    "A History of Mevell House",
      "subtitle": "7 Newcastle Circus, The Park, Nottingham",
      "property_id": 204,
      "credit":   "Compiled by …, photographed by A. Hagues",
      "note":     "anything to say about the document as a whole",
      "pages": [
        { "file": "P1210730.jpeg", "caption": "Cover",
          "text": "the transcription, if there is one" }
      ]
    }

Pages with a transcription get the text set beside the image, which is the
point: a photograph of a typed page is not searchable and a transcription is.
Pages without one are reproduced with their caption and nothing invented.

Renders through the Chrome already on the machine, in a throwaway profile.
"""
import html
import json
import os
import shutil
import subprocess
import sys
import tempfile
from base64 import b64encode
from datetime import date

CHROMES = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    shutil.which('google-chrome') or '', shutil.which('chromium') or '',
]
SERIF = "Georgia, 'Times New Roman', serif"

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin:0; font-family: Georgia,'Times New Roman',serif; font-size:10.5pt;
  line-height:1.55; color:#2a2418; }
.title { border-bottom:2px solid #2f4d27; padding-bottom:16px; margin-bottom:20px; }
.title .brand { font-size:8.5pt; letter-spacing:.14em; text-transform:uppercase;
  color:#6a5c44; margin-bottom:8px; }
.title h1 { margin:0 0 4px; font-size:23pt; line-height:1.15; }
.title .sub { margin:0; color:#6a5c44; font-size:12pt; font-style:italic; }
.title .meta { margin-top:10px; font-size:8.5pt; color:#8a7a5a; }
.note { background:#f6f2e7; border:1px solid #e0d8c4; border-left:4px solid #a3741f;
  border-radius:0 5px 5px 0; padding:11px 15px; margin:0 0 20px; font-size:9.5pt; }
.note p { margin:0 0 7px; } .note p:last-child { margin:0; }
.contents { margin:0 0 24px; }
.contents b { display:block; font-size:8.5pt; letter-spacing:.12em; text-transform:uppercase;
  color:#6a5c44; margin-bottom:6px; }
.contents ol { margin:0; padding-left:18px; font-size:9.5pt; columns:2; column-gap:24px; }
.page { break-inside:avoid; break-before:page; padding-top:4pt; }
.page:first-of-type { break-before:auto; }
.page h2 { font-size:12.5pt; margin:0 0 3pt; }
.page .n { font-size:8pt; color:#8a7a5a; letter-spacing:.1em; text-transform:uppercase; }
.plate { margin:8pt 0 0; text-align:center; }
.plate img { max-width:100%; max-height:150mm; border:1px solid #d8cfb4;
  background:#fff; box-shadow:0 1px 3px rgba(0,0,0,.12); }
.plate .src { font-size:7.5pt; color:#a09070; margin-top:4pt; font-family:Menlo,monospace; }
.text { margin-top:10pt; font-size:10pt; white-space:pre-wrap; }
.text.none { color:#8a7a5a; font-style:italic; white-space:normal; }
.foot { margin-top:22pt; padding-top:9pt; border-top:1px solid #e0d8c4;
  font-size:8.5pt; color:#8a7a5a; break-inside:avoid; }
"""


def data_uri(path):
    ext = os.path.splitext(path)[1].lower()
    mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.gif': 'image/gif', '.webp': 'image/webp', '.tif': 'image/tiff',
            '.tiff': 'image/tiff'}.get(ext, 'application/octet-stream')
    with open(path, 'rb') as fh:
        return f'data:{mime};base64,' + b64encode(fh.read()).decode()


def build(folder):
    spec_path = os.path.join(folder, 'dossier.json')
    with open(spec_path, encoding='utf-8') as fh:
        spec = json.load(fh)
    pages = spec.get('pages') or []
    if not pages:
        print('dossier.json lists no pages.', file=sys.stderr)
        return None

    e = lambda s: html.escape(str(s or ''), quote=False)
    body = []
    contents = []
    for i, p in enumerate(pages, 1):
        f = os.path.join(folder, p['file'])
        if not os.path.exists(f):
            print(f'  missing: {p["file"]}', file=sys.stderr)
            continue
        cap = p.get('caption') or p['file']
        contents.append(f'<li>{e(cap)}</li>')
        text = (p.get('text') or '').strip()
        body.append(
            f'<section class="page"><div class="n">Page {i} of {len(pages)}</div>'
            f'<h2>{e(cap)}</h2>'
            f'<div class="plate"><img src="{data_uri(f)}" alt="{e(cap)}">'
            f'<div class="src">{e(p["file"])}</div></div>'
            + (f'<div class="text">{e(text)}</div>' if text else
               '<div class="text none">Not transcribed. The page is reproduced above as '
               'photographed; nothing has been read into it.</div>')
            + '</section>')

    when = date.today().strftime('%-d %B %Y')
    note = spec.get('note')
    doc = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>{e(spec.get('title', 'A house dossier'))}</title><style>{CSS}</style></head><body>
<div class="title">
  <div class="brand">Nottingham Park Houses — The Park Conservation Trust</div>
  <h1>{e(spec.get('title', ''))}</h1>
  <p class="sub">{e(spec.get('subtitle', ''))}</p>
  <div class="meta">{e(spec.get('credit', ''))}{' · ' if spec.get('credit') else ''}
    Assembled {when}{f" · property #{spec['property_id']}" if spec.get('property_id') else ''}</div>
</div>
{f'<div class="note"><p>{e(note)}</p></div>' if note else ''}
<div class="contents"><b>The pages</b><ol>{''.join(contents)}</ol></div>
{''.join(body)}
<p class="foot">Reproduced from photographs of the original document. Where a page carries a
transcription it was read from the photograph; where it does not, the page stands as the only
record of what it says.</p>
</body></html>"""

    out = os.path.join(folder, (spec.get('filename') or 'dossier') + '.pdf')
    chrome = next((c for c in CHROMES if c and os.path.exists(c)), None)
    if not chrome:
        print('No Chrome found to render with.', file=sys.stderr)
        return None
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, 'dossier.html')
        with open(src, 'w', encoding='utf-8') as fh:
            fh.write(doc)
        r = subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
                            f'--user-data-dir={os.path.join(tmp, "profile")}',
                            '--no-pdf-header-footer', f'--print-to-pdf={out}',
                            'file://' + src], capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not os.path.exists(out):
            print(r.stderr.strip()[-600:] or 'Chrome produced nothing.', file=sys.stderr)
            return None
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    out = build(sys.argv[1])
    if not out:
        return 1
    print(f'{out}  {os.path.getsize(out):,} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
