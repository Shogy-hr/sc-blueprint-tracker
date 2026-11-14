#!/usr/bin/env python3
"""Background removal for the kiosk pictures (one look for all sources: Datapad, wiki, shop, fabricator).
build_imgs.py lists the pictures without a cut-out in tools/cut/pending.json; this script removes the
background (rembg, model isnet-general-use), centres the item on a transparent square and caches
tools/cut/img/<hash>-s.webp (120 px) and -l.webp (360 px). Pictures where the cut fails stay original.
Then run build_imgs.py (or update.py) again. Runs locally (needs: pip install "rembg[cpu]").
Usage: python3 make_cutouts.py [--redo HASH ...] [--max N] | --recheck"""
import base64, io, json, os, sys, time
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
CUT = os.path.join(HERE, 'cut'); IMG = os.path.join(CUT, 'img'); CIDX = os.path.join(CUT, 'index.json')


def decode(uri):
    return Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1] if uri.startswith('data:') else uri))).convert('RGB')


def solid(a):
    """Most of the item must be opaque; ghost-like half-transparent cuts are worse than the original."""
    v = a[a > 10]
    return len(v) > 0 and (v > 200).mean() >= 0.6


def recheck(idx):
    n = 0
    for h, st in list(idx.items()):
        f = os.path.join(IMG, h + '-l.webp')
        if st == 'ok' and os.path.exists(f) and not solid(np.asarray(Image.open(f).convert('RGBA'))[..., 3]):
            idx[h] = 'bad'; n += 1
            for suf in ('s', 'l'): os.remove(os.path.join(IMG, f'{h}-{suf}.webp'))
    return n


def cutout(im, session, remove):
    o = remove(im, session=session)                       # RGBA
    a = np.asarray(o)[..., 3]
    m = a > 40
    cov = m.mean()
    if cov < 0.02 or cov > 0.80: return None, f'coverage {cov:.2f}'   # nothing found / background kept
    ys, xs = np.nonzero(m)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    W, H = o.size
    if (x0 <= 1 and x1 >= W - 2) and (y0 <= 1 and y1 >= H - 2): return None, 'touches every edge'
    # many separate blobs = a scene, not one item
    from scipy import ndimage
    lab, n = ndimage.label(m)
    if n > 1:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        if sizes.max() < m.sum() * 0.55 and n > 6: return None, f'{n} pieces'
    if not solid(a): return None, 'half transparent (dark item on dark background)'
    c = o.crop((x0, y0, x1 + 1, y1 + 1))
    side = int(max(c.size) * 1.14)
    sq = Image.new('RGBA', (side, side), (0, 0, 0, 0)); sq.paste(c, ((side - c.width) // 2, (side - c.height) // 2))
    return sq, 'ok'


def main():
    pend = json.load(open(os.path.join(CUT, 'pending.json'), encoding='utf-8'))
    idx = json.load(open(CIDX, encoding='utf-8')) if os.path.exists(CIDX) else {}
    if '--recheck' in sys.argv:
        n = recheck(idx); json.dump(idx, open(CIDX, 'w'), indent=0, sort_keys=True); print('recheck: kept original for', n); return
    if '--redo' in sys.argv:
        for h in sys.argv[sys.argv.index('--redo') + 1:]: idx.pop(h, None)
    mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10 ** 9
    os.makedirs(IMG, exist_ok=True)
    from rembg import new_session, remove
    ses = new_session('isnet-general-use')
    todo = [h for h in pend if h not in idx][:mx]
    ok = bad = 0; t0 = time.time()
    for i, h in enumerate(todo):
        try:
            sq, why = cutout(decode(pend[h]), ses, remove)
        except Exception as e:
            sq, why = None, str(e)[:80]
        if sq is None:
            idx[h] = 'bad'; bad += 1
        else:
            for size, suf in ((360, 'l'), (120, 's')):
                x = sq.resize((size, size), Image.LANCZOS)
                if size > 200: x = x.filter(ImageFilter.UnsharpMask(1.2, 60, 3))
                x.save(os.path.join(IMG, f'{h}-{suf}.webp'), quality=82 if size > 200 else 72, alpha_quality=60 if size > 200 else 50, method=6)
            idx[h] = 'ok'; ok += 1
        if i % 50 == 49:
            json.dump(idx, open(CIDX, 'w'), indent=0, sort_keys=True)
            print(f'  {i + 1}/{len(todo)}  ok {ok}  kept original {bad}  {time.time() - t0:.0f}s', flush=True)
    json.dump(idx, open(CIDX, 'w'), indent=0, sort_keys=True)
    print(f'cut-outs: {ok} new, {bad} kept original, {len([v for v in idx.values() if v == "ok"])} in total')


if __name__ == '__main__':
    main()
