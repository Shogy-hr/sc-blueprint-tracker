#!/usr/bin/env python3
"""Build labels/index.html (Label Forge) from tools/labels_src.html, borrowing the site chrome
(fonts, colours, header, flags, footer styles) from the home page so both stay in step."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
home = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
css = home[home.index('<style>') + 7:home.index('</style>')]
keep = []
for line in css.split('\n'):
    if re.match(r'^(@font-face|:root|\*\{|html|body|\.frame|header|\.logo|\.sp\{|\.flags|footer|\.hnote)', line):
        keep.append(line.replace('url(assets/', 'url(../assets/'))
keep.append('@media (max-width:760px){body{padding:6px}.frame{padding:12px;box-shadow:0 0 0 3px #1b1c1d}.logo b{font-size:24px}.logo-img{width:50px;height:50px}.sp{display:none}.hello h1{font-size:24px}.vt td:nth-child(4){display:none}}')
m = re.search(r'var FLAGS=\{.*?\};', home, re.S)
src = open(os.path.join(HERE, 'labels_src.html'), encoding='utf-8').read()
import json
# shop prices per description key: the item info in the game shows the description, and colour variants
# often share one; when only some of them are sold the line says so
byname = {}
sp = os.path.join(HERE, 'shops', 'index.json')
if os.path.exists(sp):
    for e in json.load(open(sp, encoding='utf-8')).values():
        P = [x['p'] for x in e.get('shops') or [] if x.get('p')]
        D = max((x.get('d') or '' for x in e.get('shops') or []), default='')
        if P and e.get('n'): byname[e['n'].strip().lower()] = (min(P), max(P), D[:7])
prices = {}
dkp = os.path.join(HERE, 'game', 'desckeys.json')
if byname and os.path.exists(dkp):
    groups = {}
    for nk, v in json.load(open(dkp, encoding='utf-8')).items(): groups.setdefault(v[0], []).append(v[1].strip().lower())
    for dk, nms in groups.items():
        got = [byname[n] for n in nms if n in byname]
        if got:   # 4th field 1 = only some of the items with this description are sold in shops
            prices[dk] = [min(g[0] for g in got), max(g[1] for g in got), max(g[2] for g in got)] + ([1] if len(got) < len(nms) else [])
print('shop prices for', len(prices), 'item descriptions')
out = src.replace('/*BASECSS*/', '\n'.join(keep)).replace('/*FLAGS*/', m.group(0)).replace('/*PRICES*/{}', json.dumps(prices, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c'))
os.makedirs(os.path.join(ROOT, 'labels'), exist_ok=True)
open(os.path.join(ROOT, 'labels', 'index.html'), 'w', encoding='utf-8').write(out)
print('labels/index.html', len(out), 'bytes')
