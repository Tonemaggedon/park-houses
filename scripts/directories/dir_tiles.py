"""Download Wright's directory page scans and cut each into four overlapping tiles.

usage: python3 dir_tiles.py <volume> <page> [<page> ...]
Tiles land in dirscans/<volume>/p<page>_{tl,tr,bl,br}.jpg — full resolution,
each half the page wide and a little over half tall, so no line is lost at a cut.
"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

OFF = {'1894-95': 164506, '1898-99': 165176, '1910-11': 165676, '1913-14': 166356, '1915-16': 347641}
HERE = os.path.dirname(os.path.abspath(__file__))


def fetch(vol, page):
    d = os.path.join(HERE, 'dirscans', vol)
    os.makedirs(d, exist_ok=True)
    full = os.path.join(d, f'p{page}.jpg')
    if not (os.path.exists(full) and os.path.getsize(full) > 50000):
        url = f'https://leicester.contentdm.oclc.org/iiif/2/p16445coll4:{OFF[vol] + page}/full/full/0/default.jpg'
        for _ in range(3):
            subprocess.run(['curl', '-sk', '--max-time', '90', '-o', full, url])
            if os.path.exists(full) and os.path.getsize(full) > 50000:
                break
    im = Image.open(full)
    w, h = im.size
    ox, oy = int(w * 0.04), int(h * 0.04)
    boxes = {'tl': (0, 0, w // 2 + ox, h // 2 + oy), 'tr': (w // 2 - ox, 0, w, h // 2 + oy),
             'bl': (0, h // 2 - oy, w // 2 + ox, h), 'br': (w // 2 - ox, h // 2 - oy, w, h)}
    for name, box in boxes.items():
        im.crop(box).convert('L').save(os.path.join(d, f'p{page}_{name}.jpg'), quality=82)
    return page


if __name__ == '__main__':
    vol, pages = sys.argv[1], [int(p) for p in sys.argv[2:]]
    with ThreadPoolExecutor(6) as ex:
        done = list(ex.map(lambda p: fetch(vol, p), pages))
    print(vol, 'tiled', len(done), 'pages')
