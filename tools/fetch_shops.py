#!/usr/bin/env python3
"""Where can an item be bought in game, and for how much? Used by the photo list (items still without a
proper picture), the kiosk (shop prices) and Label Forge (shop price in the in-game item info).
All items of the game are asked about (UUIDs from tools/game/desckeys.json), a few hundred per run.
Source: api.star-citizen.wiki (prices reported by the UEX community). Shop data is no longer in the
game files, so this is community data. Cached in tools/shops/index.json; re-checked after RECHECK_DAYS.
Run by update.py inside the GitHub Action (the sandbox/visitors never call it).
Usage: python3 fetch_shops.py [--limit N]"""
import json, os, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
API = 'https://api.star-citizen.wiki/api/v2/items/'
UA = 'SC-Blueprint-Tracker/1.0 (fan site shogy-hr.com; github.com/Shogy-hr/sc-blueprint-tracker)'
RECHECK_DAYS = 7
MAX_PER_RUN = 600          # ~11 min at 60 requests/minute; the Action runs every 6 h
OUT = os.path.join(HERE, 'shops', 'index.json')


def need_photo():
    """name -> full output UUID for blueprints whose picture is missing or only a variant"""
    img = json.load(open(os.path.join(HERE, 'imgdata.json'), encoding='utf-8'))['img']
    src = os.path.join(HERE, 'game', 'blueprints.json')
    full = {}
    if os.path.exists(src):
        for b in json.load(open(src, encoding='utf-8')):
            o = b.get('Output') or {}
            if isinstance(o, dict) and o.get('UUID'): full[o['UUID'].replace('-', '')[:12]] = o['UUID']
    cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
    out = {}
    for it in cat['items']:
        st = img.get(it[0])
        if st and not st[1]: continue            # has its own picture
        u = full.get(it[11])
        if u: out[it[0]] = u
    return out


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 10 ** 9
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    idx = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    limit = min(limit, MAX_PER_RUN) if '--limit' not in sys.argv else limit
    now = int(time.time()); want = dict((u, n) for n, u in need_photo().items())   # photo list first
    dk = os.path.join(HERE, 'game', 'desckeys.json')
    if os.path.exists(dk):
        for nk, v in json.load(open(dk, encoding='utf-8')).items():
            if len(v) > 2 and v[2] not in want and v[1] and not v[1].startswith(('<=', '@')): want.setdefault(v[2], v[1])
    todo = [(n, u, idx.get(u, {}).get('checked', 0)) for u, n in want.items()
            if not idx.get(u) or now - idx[u].get('checked', 0) > RECHECK_DAYS * 86400]
    todo.sort(key=lambda x: x[2])                      # never asked first, then the oldest answers
    print('shops:', len(todo), 'items due,', min(len(todo), limit), 'this run')
    todo = [(n, u) for n, u, _ in todo[:limit]]
    ok = err = 0
    for i, (n, u) in enumerate(todo):
        try:
            req = urllib.request.Request(API + u, headers={'User-Agent': UA, 'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r: d = json.load(r).get('data') or {}
            shops = []
            for p in ((d.get('uex_prices') or {}).get('purchase') or []):
                if not p.get('price_buy'): continue
                loc = p.get('starmap_location') or {}
                shops.append({'t': p.get('terminal_name') or '', 'l': loc.get('name') or '', 's': loc.get('star_system_name') or '',
                              'p': p.get('price_buy'), 'd': (p.get('date_updated') or '')[:10]})
            shops.sort(key=lambda s: (s['s'] != 'Stanton', s['p']))
            idx[u] = {'n': n, 'checked': now, 'shops': shops}; ok += 1
        except urllib.error.HTTPError as ex:
            if ex.code == 404: idx[u] = {'n': n, 'checked': now, 'shops': []}; ok += 1
            else: err += 1; print('  ', n, ex)
            if ex.code == 429: time.sleep(30)
        except Exception as ex:
            err += 1; print('  ', n, ex)
        time.sleep(1.1)                      # the API allows 60 requests a minute
        if i % 50 == 49: json.dump(idx, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(idx, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    print('shops: ok', ok, 'errors', err, '| sold somewhere', sum(1 for e in idx.values() if e.get('shops')), 'of', len(idx))


if __name__ == '__main__':
    main()
