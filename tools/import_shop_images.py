#!/usr/bin/env python3
"""Pictures from in-game shop terminals (screenshots or videos recorded by ShoGy).
Finds every card (QUICK BUY button + name), reads the name (tesseract), matches it to the kiosk,
keeps the sharpest crop per item and saves tools/shop/img/<f>-s.webp (120 px) and -l.webp (360 px).
Only items whose kiosk picture is missing or only a base-model variant are imported (--all: every match).
Usage: python3 import_shop_images.py file.jpg|file.mp4|folder ... [--all] [--dry]
Needs: tesseract, pytesseract, Pillow, numpy, scipy, ffmpeg (videos). Runs locally, not in the GitHub Action."""
import glob, hashlib, json, os, re, subprocess, sys, tempfile, time, difflib
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from scipy import ndimage
import pytesseract
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'shop'); IMG = os.path.join(OUT, 'img'); IDX = os.path.join(OUT, 'index.json')
QW = ('QUICK', 'QUIGK', 'OUICK', 'QUIOK')

# ---------- card detection
def quick_buys(im):
    g = ImageOps.grayscale(im)
    for img in (g, ImageOps.invert(g)):      # blue terminals: light text; orange terminals: dark text
        d = pytesseract.image_to_data(img, config='--psm 11', output_type=pytesseract.Output.DICT)
        q = [(d['left'][i], d['top'][i]) for i, t in enumerate(d['text']) if t.strip().upper() in QW]
        if q: return q
    a = np.asarray(im).astype(int); r, g2, b = a[..., 0], a[..., 1], a[..., 2]   # orange buttons by colour
    lab, n = ndimage.label((r > 200) & (g2 > 140) & (g2 < 215) & (b < 130))
    return [(sl[1].start + 38, sl[0].start + 13) for sl in ndimage.find_objects(lab)
            if 150 < sl[1].stop - sl[1].start < 220 and 30 < sl[0].stop - sl[0].start < 60]

def name_at(im, qx, qy):
    x0, y0 = qx + 100, qy - 225
    g = ImageOps.grayscale(im.crop((x0, y0, qx + 560, qy - 140))); g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
    for img in (ImageOps.invert(g), g):
        d = pytesseract.image_to_data(img, config='--psm 6', output_type=pytesseract.Output.DICT)
        ws = [(d['text'][i], d['left'][i], d['top'][i], d['line_num'][i], d['block_num'][i]) for i in range(len(d['text']))
              if d['text'][i].strip() and float(d['conf'][i]) > 20]
        if not ws: continue
        line = [w for w in ws if (w[4], w[3]) == (ws[0][4], ws[0][3])]
        txt = ' '.join(w[0] for w in line).strip()
        if len(txt) >= 3 and not txt.upper().startswith('VOLUME'):
            return txt, x0 + line[0][1] // 2, y0 + line[0][2] // 2
    return None

def cards(im):
    out = []
    for qx, qy in quick_buys(im):
        r = name_at(im, qx, qy)
        if not r: continue
        txt, nx, ny = r
        right, top, bottom = nx - 20, ny - 10, qy - 20
        if bottom - top < 120: continue
        k = 7   # stay inside the card frame
        out.append((txt, (right - (bottom - top) + k, top + k, right - k, bottom - k)))
    return out

# ---------- name matching
cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
norm = lambda s: re.sub(r'\s+', ' ', re.sub(r'[^A-Z0-9 ]', '', s.upper())).strip()
UP = {norm(i[0]): i[0] for i in cat['items']}
VOC = {w for n in UP for w in n.split()}

def match(t):
    toks = norm(t).split()
    while toks and len(toks[-1]) <= 2 and toks[-1] not in VOC: toks = toks[:-1]   # OCR junk ("|", "BA")
    while toks and len(toks[0]) <= 2 and toks[0] not in VOC: toks = toks[1:]
    c = ' '.join(toks)
    if c in UP: return UP[c]
    m = difflib.get_close_matches(c, list(UP), 1, 0.9)
    return UP[m[0]] if m else None

def sharpness(c):
    return float(ndimage.laplace(np.asarray(c.convert('L')).astype(float)).var())

def finish(c, size):
    c = c.resize((size, size), Image.LANCZOS)
    if size > 200: c = c.filter(ImageFilter.GaussianBlur(0.6)).filter(ImageFilter.UnsharpMask(1.6, 85, 3))
    return c

# ---------- input
def frames(paths, tmp):
    for p in paths:
        if os.path.isdir(p):
            yield from frames(sorted(glob.glob(os.path.join(p, '*'))), tmp); continue
        ext = p.lower().rsplit('.', 1)[-1]
        if ext in ('jpg', 'jpeg', 'png', 'webp', 'bmp'): yield p, p
        elif ext in ('mp4', 'mkv', 'mov', 'webm', 'avi'):
            d = tempfile.mkdtemp(dir=tmp)
            subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vf', 'fps=4', '-q:v', '1', os.path.join(d, 'f%05d.jpg')], check=True)
            for f in sorted(glob.glob(os.path.join(d, '*.jpg'))): yield f, p + '@' + os.path.basename(f)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    allm, dry = '--all' in sys.argv, '--dry' in sys.argv
    imgdata = json.load(open(os.path.join(HERE, 'imgdata.json'), encoding='utf-8'))['img']
    idx = json.load(open(IDX, encoding='utf-8')) if os.path.exists(IDX) else {}
    best, seen, skipped = {}, set(), set()
    with tempfile.TemporaryDirectory() as tmp:
        for f, label in frames(args, tmp):
            im = Image.open(f).convert('RGB')
            for txt, box in cards(im):
                n = match(txt)
                if not n: skipped.add(norm(txt)); continue
                seen.add(n)
                st = imgdata.get(n)
                if not allm and st and not st[1] and n not in idx: continue   # already has its own picture
                c = im.crop(box); s = sharpness(c)
                if n not in best or s > best[n][0]: best[n] = (s, c, label)
    os.makedirs(IMG, exist_ok=True); new = 0
    for n, (s, c, label) in sorted(best.items()):
        old = idx.get(n)
        if old and old.get('sharp', 0) >= s: continue
        f = hashlib.sha1(n.encode()).hexdigest()[:16]
        if not dry:
            finish(c, 120).save(os.path.join(IMG, f + '-s.webp'), quality=88)
            finish(c, 360).save(os.path.join(IMG, f + '-l.webp'), quality=88)
            idx[n] = {'f': f, 'sharp': round(s, 1), 'src': os.path.basename(label), 'date': time.strftime('%Y-%m-%d')}
        new += 1; print('  +', n, f'(sharp {s:.0f})')
    if not dry: json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    print(f'shop images: {len(seen)} kiosk items recognised, {new} new/better pictures, {len(idx)} in total')
    if skipped: print('  not in the kiosk (no blueprint):', ', '.join(sorted(skipped))[:600])

if __name__ == '__main__':
    main()
