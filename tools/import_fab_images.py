#!/usr/bin/env python3
"""Pictures from the in-game Fabrication Kiosk (screenshots or videos recorded by ShoGy).
The right half of the kiosk shows a 3D preview of the selected blueprint above its name and "Fabrication Time".
Finds "Fabrication Time" (tesseract), reads the name left of it, cuts the item out of the preview,
keeps the sharpest crop per item and saves tools/fab/img/<f>-s.webp (120 px) and -l.webp (360 px).
These pictures are the top image source of the kiosk (build_imgs.py, source 'f').
Usage: python3 import_fab_images.py file.jpg|file.zip|file.mp4|folder ... [--dry]
Needs: tesseract, pytesseract, Pillow, numpy, scipy, ffmpeg (videos). Runs locally, not in the GitHub Action."""
import glob, hashlib, json, os, re, subprocess, sys, tempfile, time, zipfile
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from scipy import ndimage
import pytesseract
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_shop_images import match, norm, sharpness, finish, frames as _frames
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'fab'); IMG = os.path.join(OUT, 'img'); IDX = os.path.join(OUT, 'index.json')
CATLINE = ('AMMO', 'ARMOR', 'WEAPONS', 'VEHICLES', 'OTHER', 'CLOTHING', 'UTILITY', 'TOOLS', 'FOOD', 'MEDICAL')
# component labels added by StarStrings / Label Forge ("QDRV -STL -2-B -BOLT"); the kiosk may show them twice
LABEL = re.compile(r'^(?:\s*\[?[A-Z]{3,5}\]?\s*-?\s*(?:[A-Z]{3}|-)?\s*-?\s*\d?\s*-?\s*[A-D]?\s*-\s*)+')


def anchor(im):
    """(x, y) of the word 'Fabrication' (scaled to the screenshot)."""
    W, H = im.size; s = 2560 / W
    g = ImageOps.grayscale(im.crop((W // 2, int(H * .3), W, int(H * .7))))
    if s != 1: g = g.resize((int(g.width * s), int(g.height * s)), Image.LANCZOS)
    d = pytesseract.image_to_data(g, config='--psm 11', output_type=pytesseract.Output.DICT)
    for i, t in enumerate(d['text']):
        if t.strip().lower().startswith('fabricat'):
            return W // 2 + d['left'][i] / s, int(H * .3) + d['top'][i] / s, 1 / s
    return None


def read_name(im, fx, fy, k):
    x0, y0 = int(fx - 640 * k), int(fy - 60 * k)
    g = ImageOps.grayscale(im.crop((x0, y0, int(fx - 20 * k), int(fy + 95 * k))))
    g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
    for img in (ImageOps.invert(g), g):
        d = pytesseract.image_to_data(img, config='--psm 6', output_type=pytesseract.Output.DICT)
        rows = {}
        for i in range(len(d['text'])):
            if d['text'][i].strip() and float(d['conf'][i]) > 20:
                rows.setdefault((d['block_num'][i], d['par_num'][i], d['line_num'][i]), []).append((d['text'][i], d['top'][i]))
        lines = [' '.join(w[0] for w in rows[r]).strip() for r in sorted(rows, key=lambda r: min(w[1] for w in rows[r]))]
        name = []
        for ln in lines:
            if norm(ln).split(' ')[0] in CATLINE: break
            name.append(ln)
        for j in range(len(name), 0, -1):
            t = ' '.join(name[:j]); c = LABEL.sub('', norm(t).replace(' - ', ' -'))
            tail = re.split(r'\s-\s?', t)[-1] if ' -' in t else ''
            cands = [t, c] + [' '.join(tail.split()[:w]) for w in range(len(tail.split()), 0, -1)]
            for cand in cands:
                n = match(cand) if cand.strip() else None
                if n: return n, t
        if name: return None, ' '.join(name)
    return None, ''


def item_box(im, fx, fy, k, region=None, minsize=120):
    """Square around the 3D model in the preview area (edges against the smooth teal background)."""
    X0, Y0, X1, Y1 = region or (int(fx - 600 * k), int(fy - 560 * k), int(fx + 290 * k), int(fy - 25 * k))
    a = np.asarray(im.crop((X0, Y0, X1, Y1)).convert('L')).astype(float)
    a = ndimage.gaussian_filter(a, 1.5)
    e = np.hypot(ndimage.sobel(a, 0), ndimage.sobel(a, 1))
    m = ndimage.binary_opening(e > 40, iterations=1)
    lab, n = ndimage.label(ndimage.binary_dilation(m, iterations=int(12 * k) or 1))
    if not n: return None
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    H_, W_ = m.shape; b = int(6 * k) + 1
    for i, sl in enumerate(ndimage.find_objects(lab)):      # panel frame, buttons, text: touch the border or are thin lines
        ys_, xs_ = np.nonzero((lab[sl] == i + 1) & m[sl])
        if not len(ys_): sizes[i] = 0; continue
        sl = (slice(sl[0].start + ys_.min(), sl[0].start + ys_.max() + 1), slice(sl[1].start + xs_.min(), sl[1].start + xs_.max() + 1))
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if sl[1].start < b or sl[1].stop > W_ - b or min(h, w) < 25 * k:
            sizes[i] = 0
    if sizes.max() <= 0: return None
    keep = [i + 1 for i, v in enumerate(sizes) if v > sizes.max() * .08]
    ys, xs = np.nonzero(np.isin(lab, keep) & m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    if max(x1 - x0, y1 - y0) < minsize * k: return None            # model rendered tiny (not loaded yet): would only be a blur
    side = int(max(x1 - x0, y1 - y0) * 1.12) + 8
    cx, cy = (x0 + x1) // 2 + X0, (y0 + y1) // 2 + Y0
    side = min(side, int((Y1 - Y0) * 1.05))
    W, H = im.size; side = min(side, W, H)
    l = min(max(cx - side // 2, 0), W - side); t = min(max(cy - side // 2, 0), H - side)   # keep the square inside the picture
    return (int(l), int(t), int(l) + side, int(t) + side)


def frames(paths, tmp):
    for p in paths:
        if p.lower().endswith('.zip'):
            d = tempfile.mkdtemp(dir=tmp); zipfile.ZipFile(p).extractall(d)
            yield from _frames([d], tmp)
        else: yield from _frames([p], tmp)


def manual(path, name):
    """A cropped/zoomed picture of the kiosk preview with a known name: --as "Name" file."""
    im = Image.open(path).convert('RGB'); W, H = im.size
    return item_box(im, 0, 0, max(W, H) / 1300, region=(0, 0, W, int(H * .78)), minsize=60)


def main():
    if '--as' in sys.argv:
        i = sys.argv.index('--as'); name = match(sys.argv[i + 1]); path = sys.argv[i + 2]
        if not name: sys.exit('not in the kiosk: ' + sys.argv[i + 1])
        im = Image.open(path).convert('RGB'); box = manual(path, name)
        if not box: sys.exit('no model found')
        c = im.crop(box); idx = json.load(open(IDX, encoding='utf-8')) if os.path.exists(IDX) else {}
        f = hashlib.sha1(('fab:' + name).encode()).hexdigest()[:16]; os.makedirs(IMG, exist_ok=True)
        finish(c, 120).save(os.path.join(IMG, f + '-s.webp'), quality=88); finish(c, 360).save(os.path.join(IMG, f + '-l.webp'), quality=88)
        idx[name] = {'f': f, 'sharp': round(sharpness(c), 1), 'src': os.path.basename(path), 'date': time.strftime('%Y-%m-%d'), 'manual': 1}
        json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
        print('  +', name, box, c.size); return
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    idx = json.load(open(IDX, encoding='utf-8')) if os.path.exists(IDX) else {}
    best, unknown, noanchor, tiny = {}, set(), 0, set()
    with tempfile.TemporaryDirectory() as tmp:
        for f, label in frames(args, tmp):
            im = Image.open(f).convert('RGB')
            a = anchor(im)
            if not a: noanchor += 1; continue
            n, raw = read_name(im, *a)
            if not n:
                if raw: unknown.add(raw)
                continue
            box = item_box(im, *a)
            if not box: tiny.add(n); continue
            c = im.crop(box); s = sharpness(c) * (c.width / 500) ** .5   # bigger model in the frame = more detail
            if n not in best or s > best[n][0]: best[n] = (s, c, label)
    os.makedirs(IMG, exist_ok=True); new = 0
    for n, (s, c, label) in sorted(best.items()):
        old = idx.get(n)
        if old and old.get('sharp', 0) >= s: continue
        f = hashlib.sha1(('fab:' + n).encode()).hexdigest()[:16]
        if not dry:
            finish(c, 120).save(os.path.join(IMG, f + '-s.webp'), quality=88)
            finish(c, 360).save(os.path.join(IMG, f + '-l.webp'), quality=88)
            idx[n] = {'f': f, 'sharp': round(s, 1), 'src': os.path.basename(label), 'date': time.strftime('%Y-%m-%d')}
        new += 1; print('  +', n, f'(sharp {s:.0f})')
    if not dry: json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    print(f'fabricator images: {len(best)} items recognised, {new} new/better, {len(idx)} in total'
          + (f', {noanchor} frames without the kiosk' if noanchor else ''))
    tiny -= set(best)
    if tiny: print('  model too small in every picture (take a closer one):', ', '.join(sorted(tiny)))
    if unknown: print('  name not matched:', ' | '.join(sorted(unknown))[:800])


if __name__ == '__main__':
    main()
