#!/usr/bin/env python3
"""Download page images from the Star Citizen Wiki (starcitizen.tools) for blueprints that have
no exact image from Datapad. Results are cached in tools/wiki/ so each item is only asked for once
(misses are re-checked after RECHECK_DAYS). Run by update.py inside the GitHub Action.
Usage: python3 fetch_wiki_images.py [--limit N] [--all]"""
import hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sclib import clean_name
API = os.environ.get('WIKI_API', 'https://starcitizen.tools/api.php')
UA = os.environ.get('WIKI_UA', 'SC-Blueprint-Tracker/1.0 (fan site; github.com) python-urllib')
RECHECK_DAYS = 5      # new items get their wiki pictures a few days after a patch, so look again soon
WDIR = os.path.join(HERE, 'wiki'); IDIR = os.path.join(WDIR, 'img'); IDX = os.path.join(WDIR, 'index.json')
BAD_IMG = re.compile(r'(logo|icon|placeholder|no[_ -]?image|\.svg$)', re.I)
BAD_MAT = re.compile(r'(logo|placeholder|no[_ -]?image|cargo[_ -])', re.I)   # generic cargo-box pictures are not the material


def mat_titles(m):
    base = re.sub(r'\s*\((ore|raw|mineral)\)\s*$', '', m, flags=re.I).strip()
    t = [m, base, base.replace('Aluminum', 'Aluminium'), base + ' (Ore)', base + ' (Raw)', base + ' (Mineral)', base + ' (gem)']
    out = []
    for x in t:
        if x not in out: out.append(x)
    return out


def icon_titles(m):
    base = re.sub(r'\s*\((ore|raw|mineral)\)\s*$', '', m, flags=re.I).strip()
    out = []
    for b in (base, base.replace('Aluminum', 'Aluminium')):
        for t in (f'File:{b} icon.svg', f'File:{b} icon.png'):
            if t not in out: out.append(t)
    return out


TOK = re.compile(r"[a-z0-9]+")
GENERIC = {'png', 'jpg', 'jpeg', 'webp', 'file', 'shop', 'display', 'cutout', 'ingame', 'in', 'game', 'render', 'front',
           'side', 'image', 'promo', 'the', 'a', 'of', 'and', 'small', 'large', 'crop', 'cropped', 'scitem', 'v', '1', '01'}
# words that may be added to an item's name for its own category ("Agni quantum drive.jpg" is still the Agni,
# but "Bolt rifle" is not the Bolt quantum drive)
CAT_WORDS = {'QUANTUM DRIVES': 'quantum drive', 'COOLERS': 'cooler', 'POWER PLANTS': 'power plant powerplant',
             'SHIELDS': 'shield generator', 'RADARS': 'radar', 'MINING LASERS': 'mining laser', 'MINING MODULES': 'mining module',
             'TRACTOR BEAMS': 'tractor beam', 'SALVAGE HEADS': 'salvage head', 'SCRAPER MODULES': 'scraper module',
             'HELMETS': 'helmet flight armor armour', 'CORE': 'core armor armour', 'ARMS': 'arms armor armour', 'LEGS': 'legs armor armour',
             'BACKPACKS': 'backpack', 'UNDERSUITS': 'undersuit', 'FLIGHT SUITS': 'flight suit', 'SIDEARMS': 'pistol',
             'RIFLES': 'rifle', 'SNIPER RIFLES': 'sniper rifle', 'SMGS': 'smg', 'SHOTGUNS': 'shotgun', 'LMGS': 'lmg',
             'MAGAZINES': 'magazine', 'SIZE 1': 'cannon repeater gun', 'SIZE 2': 'cannon repeater gun', 'SIZE 3': 'cannon repeater gun',
             'SIZE 4': 'cannon repeater gun', 'SIZE 5': 'cannon repeater gun', 'SIZE 6': 'cannon repeater gun'}


def toks(s):
    return [t for t in TOK.findall(re.sub(r'([a-z])([A-Z])', r'\1 \2', s).lower().replace('_', ' ')) if t]


def close_match(want, got, extra=1, ok=()):
    """every word of the item name is in the found title, plus at most `extra` other words
    (generic photo words and the item's own category words don't count)"""
    w = set(toks(want)); g = [t for t in toks(got) if t not in GENERIC and t not in ok]
    return w and w <= set(g) and len(set(g) - w) <= extra


def search(title, ns):
    d = get_json({'action': 'query', 'format': 'json', 'formatversion': '2', 'list': 'search', 'srsearch': title,
                  'srnamespace': str(ns), 'srlimit': '5', 'srprop': ''})
    return [x['title'] for x in d.get('query', {}).get('search', [])]


def find_by_search(title, ok=()):
    """Second chance for items whose exact page has no picture: a page with a slightly different name
    (e.g. 'Tailwind Flight Helmet Raider Camo'), or an uploaded file named after the item."""
    try:
        for t in search(title, 0):
            if t != title and close_match(title, t, 0, ok):
                r = query([t])
                if t in r and not BAD_IMG.search(r[t][1] or ''): return r[t]
        for f in search(title, 6):
            if BAD_IMG.search(f) or not close_match(title, f.split(':', 1)[-1].rsplit('.', 1)[0], 0, ok): continue
            r = query_files([f])
            if f in r: return (r[f][0], f.split(':', 1)[-1], r[f][1])
    except Exception as ex:
        print('  search failed', title, ex)
    return None


def query_files(titles):
    """File:... title -> (file title, rendered thumbnail url) via imageinfo"""
    d = get_json({'action': 'query', 'format': 'json', 'formatversion': '2', 'redirects': '1', 'prop': 'imageinfo',
                  'iiprop': 'url', 'iiurlwidth': '256', 'titles': '|'.join(titles)})
    q = d.get('query', {}); pages = {p['title']: p for p in q.get('pages', [])}; res = {}
    for t in titles:
        tt = t
        for n in q.get('normalized', []):
            if n['from'] == tt: tt = n['to']
        p = pages.get(tt)
        if p and not p.get('missing') and p.get('imageinfo'):
            ii = p['imageinfo'][0]; url = ii.get('thumburl') or ii.get('url')
            if url: res[t] = (tt, url)
    return res


def query(titles):
    """title -> (page title, pageimage, thumbnail url) for titles that have a page image"""
    d = get_json({'action': 'query', 'format': 'json', 'formatversion': '2', 'redirects': '1', 'prop': 'pageimages',
                  'piprop': 'thumbnail|name', 'pithumbsize': '600', 'titles': '|'.join(titles)})
    q = d.get('query', {}); pages = {p['title']: p for p in q.get('pages', [])}; res = {}
    for t in titles:
        tt = t
        for n in q.get('normalized', []):
            if n['from'] == tt: tt = n['to']
        for r in q.get('redirects', []):
            if r['from'] == tt: tt = r['to']
        p = pages.get(tt)
        if p and not p.get('missing') and p.get('thumbnail'):
            res[t] = (tt, p.get('pageimage', '') or '', p['thumbnail']['source'])
    return res


def get_json(params):
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_bytes(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def save_images(raw, key):
    from PIL import Image
    im = Image.open(io.BytesIO(raw)); im.load()
    im = im.convert('RGBA') if im.mode in ('P', 'LA', 'RGBA') else im.convert('RGB')
    L = im.copy(); L.thumbnail((560, 560)); L.save(os.path.join(IDIR, key + '-l.webp'), 'WEBP', quality=80, method=6)
    S = im.copy(); S.thumbnail((120, 120)); S.save(os.path.join(IDIR, key + '-s.webp'), 'WEBP', quality=75, method=6)


def main():
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 10 ** 9
    os.makedirs(IDIR, exist_ok=True)
    idx = json.load(open(IDX, encoding='utf-8')) if os.path.exists(IDX) else {}
    cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
    have = set()
    if os.path.exists(os.path.join(HERE, 'imgdata.json')) and '--all' not in sys.argv:
        have = {n for n, v in json.load(open(os.path.join(HERE, 'imgdata.json'), encoding='utf-8'))['img'].items() if not v[1] and len(v) > 3 and v[3] == 'd'}
    now = time.time()
    todo = []
    for it in cat['items']:
        name = it[0]; title = clean_name((it[12] if len(it) > 12 and it[12] else '') or name)
        if name in have or (len(it) > 13 and it[13]): continue
        e = idx.get(title)
        if e and (e.get('f') or now - e.get('checked', 0) < RECHECK_DAYS * 86400): continue
        if title not in todo: todo.append(title)
    todo = todo[:limit]
    print('wiki: asking for', len(todo), 'titles')
    got = 0
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        try:
            d = get_json({'action': 'query', 'format': 'json', 'formatversion': '2', 'redirects': '1', 'prop': 'pageimages',
                          'piprop': 'thumbnail|name', 'pithumbsize': '600', 'titles': '|'.join(batch)})
        except Exception as ex:
            print('wiki API error:', ex); break
        q = d.get('query', {})
        back = {}
        for n in q.get('normalized', []): back[n['to']] = back.get(n['from'], n['from'])
        for r in q.get('redirects', []): back[r['to']] = back.get(r['from'], r['from'])
        pages = {p['title']: p for p in q.get('pages', [])}
        for t in batch:
            # follow requested title -> normalized -> redirect target
            tt = t
            for n in q.get('normalized', []):
                if n['from'] == tt: tt = n['to']
            for r in q.get('redirects', []):
                if r['from'] == tt: tt = r['to']
            p = pages.get(tt)
            entry = {'checked': int(now)}
            if p and not p.get('missing') and p.get('thumbnail') and not BAD_IMG.search(p.get('pageimage', '') or ''):
                src = p['thumbnail']['source']
                key = hashlib.sha1(src.encode()).hexdigest()[:16]
                try:
                    if not os.path.exists(os.path.join(IDIR, key + '-s.webp')):
                        save_images(get_bytes(src), key); time.sleep(0.25)
                    entry.update({'f': key, 'page': tt, 'file': p.get('pageimage', ''), 'url': src}); got += 1
                except Exception as ex:
                    print('  image failed', t, ex)
            idx[t] = entry
        time.sleep(1.0)
        json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    # second chance: search the wiki for a similarly named page or an uploaded picture of the item
    titles = []; sub = {}
    for it in cat['items']:
        t = clean_name((it[12] if len(it) > 12 and it[12] else '') or it[0])
        if it[0] not in have and not (len(it) > 13 and it[13]) and t not in titles: titles.append(t); sub[t] = it[2]
    misses = [t for t in titles if t in idx and not idx[t].get('f') and now - idx[t].get('s', 0) > RECHECK_DAYS * 86400][:300]
    print('wiki: searching for', len(misses), 'titles without a page image')
    for t in misses:
        hit = find_by_search(t, set(CAT_WORDS.get(sub.get(t), '').split())); idx[t]['s'] = int(now)
        if hit:
            page, fname, src = hit; key = hashlib.sha1(src.encode()).hexdigest()[:16]
            try:
                if not os.path.exists(os.path.join(IDIR, key + '-s.webp')):
                    save_images(get_bytes(src), key); time.sleep(0.25)
                idx[t].update({'f': key, 'page': page, 'file': fname, 'url': src, 'search': 1}); got += 1
                print('  found by search:', t, '<-', page, fname)
            except Exception as ex:
                print('  image failed', t, ex)
        time.sleep(0.6)
    if misses:
        json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    # ---- materials (ores, gems, items used in recipes)
    def mat_done(m):
        e = idx.get('mat:' + m, {})
        if e.get('f') and not BAD_MAT.search(e.get('file', '') or ''): return True
        return not e.get('f') and now - e.get('checked', 0) < RECHECK_DAYS * 86400 and e.get('v') == 2
    mtodo = [m for m in cat.get('mats', {}) if not mat_done(m)]
    print('wiki: asking for', len(mtodo), 'materials')
    for i in range(0, len(mtodo), 7):
        chunk = mtodo[i:i + 7]; titles = [t for m in chunk for t in mat_titles(m)]
        try: found = query(titles)
        except Exception as ex: print('wiki API error:', ex); break
        for m in chunk:
            entry = {'checked': int(now)}
            for t in mat_titles(m):
                if t in found and not BAD_MAT.search(found[t][1]):
                    page, fname, src = found[t]; key = hashlib.sha1(src.encode()).hexdigest()[:16]
                    try:
                        if not os.path.exists(os.path.join(IDIR, key + '-s.webp')):
                            save_images(get_bytes(src), key); time.sleep(0.25)
                        entry.update({'f': key, 'page': page, 'file': fname, 'url': src}); got += 1
                    except Exception as ex:
                        print('  image failed', m, ex)
                    break
            entry['v'] = 2
            idx['mat:' + m] = entry
        # fallback: the official commodity icon from the wiki (e.g. "File:Laranite icon.svg")
        missing = [m for m in chunk if not idx['mat:' + m].get('f')]
        if missing:
            try: icons = query_files([t for m in missing for t in icon_titles(m)])
            except Exception as ex: icons = {}; print('wiki icon query error:', ex)
            for m in missing:
                for t in icon_titles(m):
                    if t in icons:
                        ftitle, src = icons[t]; key = hashlib.sha1(src.encode()).hexdigest()[:16]
                        try:
                            if not os.path.exists(os.path.join(IDIR, key + '-s.webp')):
                                save_images(get_bytes(src), key); time.sleep(0.25)
                            idx['mat:' + m].update({'f': key, 'page': ftitle, 'file': ftitle.replace('File:', ''), 'url': src, 'icon': 1}); got += 1
                        except Exception as ex:
                            print('  icon failed', m, ex)
                        break
        time.sleep(1.0)
    json.dump(idx, open(IDX, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    print('wiki: new images', got, '| cached entries', len(idx), '| with image', sum(1 for e in idx.values() if e.get('f')))


if __name__ == '__main__':
    main()
