#!/usr/bin/env python3
"""Photo list for ShoGy: blueprints whose kiosk picture is missing or only shows the base model,
grouped by the word to type into the in-game shop SEARCH, with where they are sold (tools/shops/).
Writes foto/index.html (unlisted page, not linked from the site)."""
import json, os, re, html
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
img = json.load(open(os.path.join(HERE, 'imgdata.json'), encoding='utf-8'))['img']
cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
shops = {}
p = os.path.join(HERE, 'shops', 'index.json')
if os.path.exists(p):
    for u, e in json.load(open(p, encoding='utf-8')).items(): shops[e.get('n')] = e.get('shops') or []
CATN = {'A': 'Oklop', 'C': 'Odjeća', 'W': 'Oružje', 'T': 'Rudarenje', 'M': 'Streljivo', 'P': 'Komponente', 'V': 'Brodsko oružje', 'X': 'Teret', 'O': 'Misije'}
groups = {}
for it in cat['items']:
    st = img.get(it[0])
    if st and not st[1]: continue
    n = it[0]; key = re.split(r'[\s"\'(]+', n.strip())[0] or n
    groups.setdefault(key, []).append({'n': n, 'c': CATN.get(it[1], it[1]), 's': it[2], 'v': 1 if st else 0,
                                        'sh': [[s['t'], s['l'], s['s'], s['p']] for s in shops.get(n, [])[:4]],
                                        'k': 1 if n in shops else 0})
G = [{'q': k, 'items': sorted(v, key=lambda x: x['n'])} for k, v in groups.items()]
G.sort(key=lambda g: (-sum(1 for x in g['items'] if x['sh']), -len(g['items']), g['q']))
data = json.dumps({'v': cat['v'], 'groups': G}, ensure_ascii=False, separators=(',', ':'))
page = open(os.path.join(HERE, 'photo_list_src.html'), encoding='utf-8').read().replace('/*DATA*/null', data)
os.makedirs(os.path.join(ROOT, 'foto'), exist_ok=True)
open(os.path.join(ROOT, 'foto', 'index.html'), 'w', encoding='utf-8').write(page)
tot = sum(len(g['items']) for g in G); sold = sum(1 for g in G for x in g['items'] if x['sh'])
print('photo list:', len(G), 'search words,', tot, 'items,', sold, 'sold in shops')
