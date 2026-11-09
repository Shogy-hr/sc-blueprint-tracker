#!/usr/bin/env python3
"""Pick an image for every blueprint and write tools/imgdata.json + ../img/l-*.json.
Sources, best first:
  d  Datapad (jpcoombes-byte/Datapad): renders from the game files, matched by item UUID or exact name
  w  Star Citizen Wiki page image (downloaded by fetch_wiki_images.py into tools/wiki/)
  variant: the image of the base model (same category only), shown with a "temporary image" label
Needs: catalog.json, datapad/ (optional), wiki/ (optional), blueprints.json (optional, for class names)."""
import base64, glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sclib import out, clean_name, wiki_sig

cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
items = cat['items']
nk = lambda s: re.sub(r'\s+', ' ', clean_name(s).lower().replace('“', '"').replace('”', '"').replace('„', '"')).strip()

# ---- Datapad
DS, DL = {}, {}
for f in glob.glob(os.path.join(HERE, 'datapad', 'img', '*-s.json')): DS.update(json.load(open(f, encoding='utf-8')))
for f in glob.glob(os.path.join(HERE, 'datapad', 'img', '*-l-*.json')): DL.update(json.load(open(f, encoding='utf-8')))
D12 = {k.replace('-', '')[:12]: k for k in DS}
dp_names = {}
idx_html = os.path.join(HERE, 'datapad', 'index.html')
if os.path.exists(idx_html):
    for m in re.finditer(r'"name":"((?:[^"\\]|\\.)*)","mfr":"[^"]*","uuid":"([0-9a-f-]{36})"', open(idx_html, encoding='utf-8').read()):
        if m.group(2) in DS: dp_names.setdefault(nk(json.loads('"' + m.group(1) + '"')), m.group(2))

# ---- Wiki cache
W = {}
wiki_idx = os.path.join(HERE, 'wiki', 'index.json')
if os.path.exists(wiki_idx):
    WIDX = json.load(open(wiki_idx, encoding='utf-8'))
    _n = lambda x: re.sub(r'[^a-z0-9]', '', x.lower())
    FAM = {f for f in (_n(i[0].split(' ')[0]) for i in items) if len(f) >= 4}

    def wrong_model(title, fname):
        """Wiki page image that clearly shows another model (file name starts with another model, not this one)."""
        fn, own = _n(fname or ''), _n(title.split(' ')[0])
        return own[:5] not in fn and any(fn.startswith(f) and not f.startswith(own[:4]) for f in FAM)
    for name, e in WIDX.items():
        if e.get('f') and not name.startswith('mat:') and wrong_model(name, e.get('file', '')):
            print('  skip wiki image (other model):', name, '<-', e.get('file')); continue
        if e.get('f') and not name.startswith('mat:'):
            fs, fl = os.path.join(HERE, 'wiki', 'img', e['f'] + '-s.webp'), os.path.join(HERE, 'wiki', 'img', e['f'] + '-l.webp')
            if os.path.exists(fs):
                W[nk(name)] = ('w:' + e['f'], fs, fl if os.path.exists(fl) else fs)

# ---- classes (optional)
CLS = {}
bpf = os.path.join(HERE, 'blueprints.json')
if os.path.exists(bpf):
    for b in json.load(open(bpf, encoding='utf-8')):
        o = out(b); u = (o.get('UUID') or '').replace('-', '')[:12]
        if u: CLS[u] = o.get('Class') or ''

info = {i[0]: {'u': i[11], 'gn': i[12] if len(i) > 12 else '', 'cat': (i[1], i[2])} for i in items}


def exact(name):
    e = info[name]
    if e['u'] and e['u'] in D12: return ('d:' + D12[e['u']], 'd')
    for cand in (e['gn'], name):
        if cand and nk(cand) in dp_names: return ('d:' + dp_names[nk(cand)], 'd')
    for cand in (e['gn'], name):
        if cand and nk(cand) in W: return (W[nk(cand)][0], 'w')
    return None


def bases(n):
    out_ = []
    b = re.sub(r'\s*\([^)]*\)\s*', ' ', n).strip(); b = re.sub(r'\s+', ' ', b)
    q = re.sub(r'\s*["“”][^"“”]*["“”]\s*', ' ', b).strip(); q = re.sub(r'\s+', ' ', q)
    for x in (q, b):
        if x != n and x not in out_: out_.append(x)
    w = q.split(' ')
    for k in range(len(w) - 1, 1, -1):
        x = ' '.join(w[:k])
        if x not in out_: out_.append(x)
    return out_


res = {}
ex = {n: exact(n) for n in info}
by_nk = {nk(n): n for n in info}
for n, e in info.items():
    if ex[n]: res[n] = (ex[n][0], 0, ex[n][1]); continue
    for b in bases(e['gn'] or n):
        bn = by_nk.get(nk(b))
        if bn and ex.get(bn) and info[bn]['cat'] == e['cat']:
            res[n] = (ex[bn][0], 1, ex[bn][1]); break
    else:
        # same class family (colour variants), same category and same first word
        c = CLS.get(e['u'], '')
        parts = c.split('_')
        for k in range(len(parts) - 1, max(len(parts) - 3, 3), -1):
            pre = '_'.join(parts[:k])
            cands = [m for m, x in info.items() if ex.get(m) and CLS.get(x['u'], '').startswith(pre + '_') and x['cat'] == e['cat']
                     and m.split(' ')[0].lower() == n.split(' ')[0].lower()]
            if cands:
                res[n] = (ex[cands[0]][0], 1, ex[cands[0]][1]); break


def data_uri(path):
    return 'data:image/webp;base64,' + base64.b64encode(open(path, 'rb').read()).decode()


def small(key):
    if key.startswith('d:'): return DS[key[2:]]
    return data_uri(next(v[1] for v in W.values() if v[0] == key))


def large(key):
    if key.startswith('d:'): return DL.get(key[2:])
    return data_uri(next(v[2] for v in W.values() if v[0] == key))


# ---- material images (small only)
MATIMG = {}
if os.path.exists(wiki_idx):
    for m in cat.get('mats', {}):
        e = WIDX.get('mat:' + m, {})
        if re.search(r'cargo[_ -]', e.get('file', '') or '', re.I): continue
        fs = os.path.join(HERE, 'wiki', 'img', (e.get('f') or '') + '-s.webp')
        if e.get('f') and os.path.exists(fs): MATIMG[m] = ('w:' + e['f'], fs)
for k, fs in MATIMG.values():
    if all(v[0] != k for v in W.values()): W['__mat__' + k] = (k, fs, fs)
keys = sorted({v[0] for v in res.values()} | {v[0] for v in MATIMG.values()})
kidx = {k: i for i, k in enumerate(keys)}
thumbs = [small(k) for k in keys]
outdir = os.path.join(HERE, '..', 'img'); os.makedirs(outdir, exist_ok=True)
for f in glob.glob(os.path.join(outdir, 'l-*.json')): os.remove(f)
chunks, cur, size, loc = [], {}, 0, {}
for k in keys:
    L = large(k)
    if not L: continue
    if size > 900_000: chunks.append(cur); cur, size = {}, 0
    cur[str(kidx[k])] = L; size += len(L); loc[kidx[k]] = len(chunks)
chunks.append(cur)
for i, c in enumerate(chunks): json.dump(c, open(os.path.join(outdir, f'l-{i}.json'), 'w'), separators=(',', ':'))
img = {n: [kidx[k], v, loc.get(kidx[k], -1), s] for n, (k, v, s) in res.items()}
mats = {m: kidx[k] for m, (k, fs) in MATIMG.items()}
json.dump({'thumbs': thumbs, 'img': img, 'mats': mats, 'wsig': wiki_sig(HERE)}, open(os.path.join(HERE, 'imgdata.json'), 'w'), separators=(',', ':'))
st = {'datapad': sum(1 for v in res.values() if v[2] == 'd' and not v[1]), 'wiki': sum(1 for v in res.values() if v[2] == 'w' and not v[1]),
      'variant': sum(1 for v in res.values() if v[1]), 'none': len(info) - len(res)}
st['materials'] = len(mats)
print('images:', st, '| thumbs', len(thumbs), '| chunks', len(chunks))
