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
from io import BytesIO
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


LONG_EDGE = 1800          # plenty for a printed page; keeps the PDF sendable
JPEG_QUALITY = 80


def data_uri(path, crop=None, rotate=0, trim=None):
    """Embed a page image, downsampled first.

    A phone photograph of a typescript page is 7-9 MB, and sixteen of those
    embedded whole made a 121 MB PDF that no mail server would carry. At 1800 px
    on the long edge the typing is still comfortably readable on screen and in
    print, and the file comes back to a few megabytes.
    """
    ext = os.path.splitext(path)[1].lower()
    try:
        from PIL import Image, ImageOps
    except ImportError:
        mime = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
                '.gif': 'image/gif', '.webp': 'image/webp', '.tif': 'image/tiff',
                '.tiff': 'image/tiff'}.get(ext, 'application/octet-stream')
        with open(path, 'rb') as fh:
            return f'data:{mime};base64,' + b64encode(fh.read()).decode()

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)      # honour the camera's rotation flag
        if im.mode not in ('RGB', 'L'):
            im = im.convert('RGB')
        if crop in ('page', 'tight'):
            im = im.crop(auto_crop(im, tight=(crop == 'tight')))
        if trim:
            # A fraction of the page, kept deliberately: used where the rest of
            # the sheet names people who may be living.
            x0, y0, x1, y1 = trim
            im = im.crop((int(x0 * im.width), int(y0 * im.height),
                          int(x1 * im.width), int(y1 * im.height)))
        if rotate:
            im = im.rotate(-rotate, expand=True)
        if max(im.size) > LONG_EDGE:
            scale = LONG_EDGE / max(im.size)
            im = im.resize((max(1, round(im.width * scale)),
                            max(1, round(im.height * scale))),
                           Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, 'JPEG', quality=JPEG_QUALITY, optimize=True,
                progressive=True)
    return 'data:image/jpeg;base64,' + b64encode(buf.getvalue()).decode()



def _span(profile, floor):
    hits = [i for i, v in enumerate(profile) if v > floor]
    return (hits[0], hits[-1]) if hits else (0, len(profile) - 1)


def auto_crop(im, tight=False, pad=0.015):
    """Find the sheet in a photograph of a page, and optionally the ink on it.

    The photographs are of a bound book on a desk: there is carpet round the
    edges, a comb binding down one side, and a lot of margin. Stage one keeps
    the bright part, which is the paper. Stage two, for a map, keeps only what
    is printed on it, so the plate is the map rather than the desk it sat on.
    """
    from PIL import Image, ImageFilter
    small = im.convert('L').resize((max(8, im.width // 8), max(8, im.height // 8)),
                                   Image.BILINEAR)
    small = small.filter(ImageFilter.MedianFilter(3))
    w, h = small.size
    px = small.load()

    hi = sorted(px[x, y] for y in range(0, h, 3) for x in range(0, w, 3))
    white = hi[int(len(hi) * 0.97)]
    papery = max(40, int(white * 0.62))
    x0, x1 = _span([sum(1 for y in range(h) if px[x, y] > papery) / h for x in range(w)], 0.45)
    y0, y1 = _span([sum(1 for x in range(w) if px[x, y] > papery) / w for y in range(h)], 0.45)

    if tight:
        ix = max(1, int((x1 - x0) * 0.02))
        iy = max(1, int((y1 - y0) * 0.02))
        bx0, bx1, by0, by1 = x0 + ix, x1 - ix, y0 + iy, y1 - iy
        if bx1 - bx0 > 10 and by1 - by0 > 10:
            inner = sorted(px[x, y] for y in range(by0, by1) for x in range(bx0, bx1))
            dark = int(inner[int(len(inner) * 0.80)] * 0.78)
            cx0, cx1 = _span([sum(1 for y in range(by0, by1) if px[x, y] < dark)
                              / (by1 - by0) for x in range(bx0, bx1)], 0.02)
            cy0, cy1 = _span([sum(1 for x in range(bx0, bx1) if px[x, y] < dark)
                              / (bx1 - bx0) for y in range(by0, by1)], 0.02)
            if cx1 - cx0 > 8 and cy1 - cy0 > 8:
                x0, x1, y0, y1 = bx0 + cx0, bx0 + cx1, by0 + cy0, by0 + cy1

    sx, sy = im.width / w, im.height / h
    px0, py0, px1, py1 = int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy)
    dx, dy = int((px1 - px0) * pad), int((py1 - py0) * pad)
    return (max(0, px0 - dx), max(0, py0 - dy),
            min(im.width, px1 + dx), min(im.height, py1 + dy))

HISTORY_CSS = """
@page { size: A4; margin: 20mm 18mm 16mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
:root {
  --paper:#FCFBF7; --ink:#1E1B16; --muted:#71684F; --rule:#E4DDCC;
  --blue:#2E4A68; --blue-soft:#EDF1F6; --blue-rule:#C6D4E2;
}
body { margin:0; background:var(--paper); color:var(--ink);
  font-family: Georgia,'Times New Roman',serif; font-size:10.5pt; line-height:1.62; }
a { color:var(--blue); text-decoration:none; border-bottom:1px solid var(--blue-rule); }

/* ---- title page ---- */
.title { break-after:page; padding-top:14mm; }
.brand { font-size:8pt; letter-spacing:.2em; text-transform:uppercase;
  color:var(--muted); margin-bottom:14px; }
.title h1 { margin:0 0 6px; font-size:30pt; line-height:1.1; letter-spacing:-.01em;
  text-wrap:balance; }
.title .sub { margin:0; font-size:13pt; font-style:italic; color:var(--muted); }
.title .rule { height:3px; background:var(--blue); width:64px; margin:20px 0 18px; }
.title .meta { font-size:9pt; color:var(--muted); line-height:1.8; }
.title .meta b { color:var(--ink); font-weight:normal; }

.note { background:var(--blue-soft); border-left:3px solid var(--blue);
  padding:13px 17px; margin:22px 0 0; font-size:9.5pt; line-height:1.55; }
.note p { margin:0 0 8px; } .note p:last-child { margin:0; }
.note b { letter-spacing:.06em; }

.toc { margin-top:26px; }
.toc .lab, .plates-lab { font-size:8pt; letter-spacing:.2em; text-transform:uppercase;
  color:var(--muted); border-bottom:1px solid var(--rule); padding-bottom:6px;
  margin-bottom:10px; }
.toc ol { margin:0; padding:0; list-style:none; font-size:10pt; }
.toc li { display:flex; justify-content:space-between; gap:12px; padding:4px 0;
  border-bottom:1px dotted var(--rule); }
.toc li span:last-child { color:var(--muted); font-size:9pt; white-space:nowrap; }

/* ---- the text ---- */
.sec { break-before:page; }
.shead { border-bottom:1px solid var(--rule); padding-bottom:9px; margin-bottom:16px; }
.eyebrow { font-size:8pt; letter-spacing:.2em; text-transform:uppercase; color:var(--blue); }
.sec h2 { margin:4px 0 0; font-size:17pt; line-height:1.2; text-wrap:balance; }
.plateref { margin-top:7px; font-size:8.5pt; color:var(--muted); }
.bodytext { max-width:34em; }
.bodytext p { margin:0 0 11px; }
.bodytext p:last-child { margin:0; }

table.rows { width:100%; border-collapse:collapse; font-size:9.8pt; }
table.rows td { padding:7px 10px 7px 0; border-bottom:1px solid var(--rule);
  vertical-align:top; }
table.rows td.yr { width:23mm; white-space:nowrap; font-family:Menlo,Consolas,monospace;
  font-size:8.6pt; letter-spacing:-.02em; color:var(--blue); padding-top:9px; }
table.rows td.yr a { border:0; }
table.rows td.what b { font-weight:normal; }
table.rows .sub { display:block; color:var(--muted); font-size:9pt; margin-top:2px; }
table.rows tr.none td { color:var(--muted); font-style:italic; }

pre.verbatim { font-family:Menlo,Consolas,monospace; font-size:8.6pt; line-height:1.5;
  white-space:pre-wrap; background:#F6F4ED; border:1px solid var(--rule);
  padding:11px 13px; margin:0 0 13px; }

.ed { margin-top:16px; border-top:1px solid var(--rule); padding-top:10px;
  font-size:9pt; color:var(--muted); max-width:34em; }
.ed b { color:var(--blue); font-weight:normal; letter-spacing:.14em;
  text-transform:uppercase; font-size:7.5pt; display:block; margin-bottom:4px; }
.ed p { margin:0 0 7px; } .ed p:last-child { margin:0; }

/* ---- plates ---- */
.plate-page { break-before:page; break-inside:avoid; }
.pnum { font-size:8pt; letter-spacing:.2em; text-transform:uppercase; color:var(--blue); }
.plate-page h3 { margin:3px 0 10px; font-size:13pt; font-weight:normal;
  border-bottom:1px solid var(--rule); padding-bottom:8px; text-wrap:balance; }
.pimg { text-align:center; margin:7mm 0 0; }
.pimg img { max-width:100%; max-height:198mm; width:auto; height:auto;
  border:1px solid var(--rule); background:#fff; }
.pback { margin-top:7mm; padding-top:7px; border-top:1px solid var(--rule);
  font-size:8.5pt; color:var(--muted);
  display:flex; justify-content:space-between; gap:12px; }
.pback .file { font-family:Menlo,Consolas,monospace; font-size:7.5pt; }
.inline-plate { margin:0 0 15px; text-align:center; }
.inline-plate img { max-width:100%; max-height:118mm; border:1px solid var(--rule);
  background:#fff; }
.inline-plate .cap { font-size:8pt; color:var(--muted); margin-top:6px; }

.foot { break-before:page; font-size:9pt; color:var(--muted); max-width:34em; }
.foot h4 { font-size:8pt; letter-spacing:.2em; text-transform:uppercase; color:var(--blue);
  margin:0 0 9px; font-weight:normal; }
.foot p { margin:0 0 9px; }
"""

ORDINALS = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
            'Nine', 'Ten', 'Eleven', 'Twelve']


def paras(e, text):
    out = []
    for block in [b.strip() for b in (text or '').split('\n\n') if b.strip()]:
        out.append('<p>' + e(block).replace('\n', ' ') + '</p>')
    return ''.join(out)


def build_history(folder, spec):
    """A reading text, with the photographs gathered into plates at the back.

    The dossier layout puts each photograph above its transcription, which suits
    a working file. This one is for reading: the wording comes first, in order,
    and every section says which plate reproduces the page it was read from.
    A letter keeps its photograph beside its text, because the hand and the
    letterhead are half of what a letter is.
    """
    e = lambda s: html.escape(str(s or ''), quote=False)
    plates = spec.get('plates') or []
    sections = spec.get('sections') or []

    # Which section sends the reader to each plate, so the plate can point back.
    owner = {}
    for sec in sections:
        for pid in (sec.get('plates') or []):
            owner.setdefault(pid, sec)
    byid = {p['id']: p for p in plates}
    numbered = [p for p in plates if not p.get('inline_only')]
    pnum = {p['id']: i for i, p in enumerate(numbered, 1)}

    toc, body = [], []
    for n, sec in enumerate(sections, 1):
        ids = sec.get('plates') or []
        refs = ', '.join(f'<a href="#plate-{i}">Plate {pnum[i]}</a>'
                         for i in ids if i in pnum)
        nums = [pnum[i] for i in ids if i in pnum]
        if len(nums) > 2 and nums == list(range(nums[0], nums[-1] + 1)):
            refs = (f'<a href="#plate-{ids[0]}">Plates {nums[0]} to {nums[-1]}</a>')
        elif len(ids) > 1 and refs:
            bits = refs.rsplit(', ', 1)
            refs = bits[0] + ' and ' + bits[1] if len(bits) > 1 else bits[0]
        if nums:
            where = ('Plates ' if len(nums) > 1 else 'Plate ') + (
                f'{nums[0]}–{nums[-1]}' if len(nums) > 2
                and nums == list(range(nums[0], nums[-1] + 1))
                else ', '.join(str(n) for n in nums))
        else:
            where = 'With the text' if sec.get('inline_plate') else '—'
        toc.append(f'<li><span>{e(sec["heading"])}</span><span>{where}</span></li>')

        style = sec.get('style', 'prose')
        if style == 'rows':
            rows = []
            for r in sec.get('rows', []):
                yr, what, sub, pid = (list(r) + [None] * 4)[:4]
                cell = (f'<a href="#plate-{pid}">{e(yr)}</a>' if pid in pnum else e(yr))
                rows.append(f'<tr{" class=none" if not pid and sec.get("mark_missing") else ""}>'
                            f'<td class="yr">{cell}</td><td class="what">{e(what)}'
                            + (f'<span class="sub">{e(sub)}</span>' if sub else '')
                            + '</td></tr>')
            inner = f'<table class="rows">{"".join(rows)}</table>'
        elif style == 'verbatim':
            inner = f'<pre class="verbatim">{e(sec.get("text"))}</pre>'
        else:
            inner = f'<div class="bodytext">{paras(e, sec.get("text"))}</div>'

        if sec.get('verbatim_before'):
            inner = f'<pre class="verbatim">{e(sec["verbatim_before"])}</pre>' + inner
        if sec.get('intro'):
            inner = f'<div class="bodytext">{paras(e, sec["intro"])}</div>' + inner

        inline = ''
        ip = sec.get('inline_plate')
        if ip and ip in byid:
            p = byid[ip]
            f = os.path.join(folder, p['file'])
            inline = (f'<div class="inline-plate">'
                      f'<img src="{data_uri(f, p.get("crop"), p.get("rotate", 0), p.get("trim"))}" '
                      f'alt="{e(p.get("caption"))}">'
                      f'<div class="cap">{e(p.get("caption"))} · {e(p["file"])}</div></div>')

        ed = ''
        if sec.get('note'):
            ed = (f'<div class="ed"><b>A note from the record</b>'
                  f'{paras(e, sec["note"])}</div>')

        body.append(
            f'<section class="sec" id="sec-{e(sec["id"])}">'
            f'<div class="shead"><div class="eyebrow">{ORDINALS[n] if n < len(ORDINALS) else n}'
            f'</div><h2>{e(sec["heading"])}</h2>'
            + (f'<div class="plateref">Reproduced at {refs}</div>' if refs else
               '<div class="plateref">Shown with this section</div>' if inline else '')
            + f'</div>{inline}{inner}{ed}</section>')

    plate_pages = []
    for i, p in enumerate(numbered, 1):
        f = os.path.join(folder, p['file'])
        if not os.path.exists(f):
            print(f'  missing: {p["file"]}', file=sys.stderr)
            continue
        back = owner.get(p['id'])
        plate_pages.append(
            f'<section class="plate-page" id="plate-{e(p["id"])}">'
            f'<div class="pnum">Plate {i}</div><h3>{e(p.get("caption"))}</h3>'
            f'<div class="pimg"><img src="{data_uri(f, p.get("crop"), p.get("rotate", 0), p.get("trim"))}" '
            f'alt="{e(p.get("caption"))}"></div>'
            f'<div class="pback"><span>'
            + (f'Read in <a href="#sec-{e(back["id"])}">{e(back["heading"])}</a>'
               if back else 'Not transcribed')
            + f'</span><span class="file">{e(p["file"])}</span></div></section>')

    when = date.today().strftime('%-d %B %Y')
    note = spec.get('note')
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>{e(spec.get('title', 'A house history'))}</title><style>{HISTORY_CSS}</style></head><body>
<div class="title">
  <div class="brand">Nottingham Park Houses — The Park Conservation Trust</div>
  <h1>{e(spec.get('title', ''))}</h1>
  <p class="sub">{e(spec.get('subtitle', ''))}</p>
  <div class="rule"></div>
  <div class="meta">{e(spec.get('credit', ''))}<br>
    Transcribed and arranged {when}
    {f"&nbsp;·&nbsp; property <b>#{spec['property_id']}</b> in the record" if spec.get('property_id') else ''}
  </div>
  {f'<div class="note">{paras(e, note)}</div>' if note else ''}
  <div class="toc"><div class="lab">The text</div><ol>{''.join(toc)}</ol></div>
</div>
{''.join(body)}
<section class="sec" id="plates"><div class="shead">
  <div class="eyebrow">Appendix</div><h2>The pages photographed</h2>
  <div class="plateref">Every plate says which section was read from it.</div>
</div><div class="bodytext">{paras(e, spec.get('plates_intro'))}</div></section>
{''.join(plate_pages)}
<div class="foot"><h4>How this was made</h4>{paras(e, spec.get('colophon'))}</div>
</body></html>"""



def build(folder):
    spec_path = os.path.join(folder, 'dossier.json')
    with open(spec_path, encoding='utf-8') as fh:
        spec = json.load(fh)
    if spec.get('layout') == 'plates-at-back':
        return render(build_history(folder, spec), folder, spec)

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

    return render(doc, folder, spec)


def render(doc, folder, spec):
    """Print the assembled HTML through the Chrome already on the machine."""
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
                            'file://' + src], capture_output=True, text=True, timeout=600)
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
