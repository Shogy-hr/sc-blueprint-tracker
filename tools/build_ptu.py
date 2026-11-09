#!/usr/bin/env python3
"""Compare a PTU blueprints.json with the LIVE catalog and write ../data/ptu.json.
Usage: python3 build_ptu.py --src ptu/blueprints.json --version 4.10.3-PTU.13132336 [--date 2026-11-06]
       python3 build_ptu.py --clear      (remove PTU data, e.g. when the PTU patch went LIVE)"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import convert, parse_version
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'ptu.json')


def comparable(it, pools, mods):
    n, c, s, z, g, t, r, p, d, x, xt, u = it[:12]
    rec = [[gr[0], gr[1], sorted((o[0], o[1], o[2]) for o in gr[2]),
            sorted([mods[m[0]][0]] + [json.dumps(v) for v in m[1:]] for m in gr[3])] for gr in r]
    return {'name': n, 'recipe': json.dumps(rec, sort_keys=True), 'time': t,
            'sources': sorted(pools[i] for i in p) + (['DEFAULT'] if d else []),
            'dismantle': json.dumps(sorted(map(tuple, x)) + [xt]), 'cat': (c, s)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join(HERE, 'ptu', 'blueprints.json'))
    ap.add_argument('--version', default='')
    ap.add_argument('--date', default='')
    ap.add_argument('--clear', action='store_true')
    a = ap.parse_args()
    if a.clear:
        if os.path.exists(OUT): os.remove(OUT)
        print('PTU data removed'); return
    if not parse_version(a.version) or parse_version(a.version)[1] not in ('PTU', 'EPTU', 'TECH-PREVIEW'):
        raise SystemExit('Give --version like 4.10.3-PTU.13132336')
    live = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
    ptu = convert(json.load(open(a.src, encoding='utf-8')))
    L = {(i[11] or i[0]): i for i in live['items']}
    P = {(i[11] or i[0]): i for i in ptu['items']}
    Lby = {i[0].lower(): i for i in live['items']}
    added, changed, removed = [], [], []
    seen = set()
    for k, it in P.items():
        li = L.get(k) or Lby.get(it[0].lower())
        if not li: added.append(it); continue
        seen.add(li[11] or li[0])
        A = comparable(li, live['pools'], live['mods']); B = comparable(it, ptu['pools'], ptu['mods'])
        kinds = [f for f in ('name', 'recipe', 'time', 'sources', 'dismantle', 'cat') if A[f] != B[f]]
        if kinds:
            changed.append({'u': li[11], 'n': li[0], 'k': kinds, 'old': {'n': li[0], 't': li[5]}, 'item': it})
    for k, it in L.items():
        if k not in seen and k not in P and it[0].lower() not in {i[0].lower() for i in ptu['items']}:
            removed.append({'u': it[11], 'n': it[0]})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    res = {'version': a.version, 'date': a.date, 'live': live['v'], 'pools': ptu['pools'], 'mods': ptu['mods'], 'mats': ptu['mats'],
           'added': added, 'changed': changed, 'removed': removed}
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'PTU {a.version}: +{len(added)} new, ~{len(changed)} changed, -{len(removed)} removed')


if __name__ == '__main__':
    main()
