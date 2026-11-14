"""Shared conversion: game blueprints.json (ScDataDumper / scunpacked-data format) -> compact catalog."""
import re

W = {'Light': 'Light', 'Medium': 'Medium', 'Heavy': 'Heavy', 'LightArmor': 'Light'}


def out(b):
    o = b.get('Output')
    return o if isinstance(o, dict) else (o[0] if o else {})


def cls(o, key):
    t = o.get('Type') or ''; c = o.get('Class') or ''
    if t.startswith('Char_Armor') and t != 'Char_Armor_Undersuit':
        sub = {'Char_Armor_Torso': 'CORE', 'Char_Armor_Helmet': 'HELMETS', 'Char_Armor_Arms': 'ARMS',
               'Char_Armor_Legs': 'LEGS', 'Char_Armor_Backpack': 'BACKPACKS'}.get(t, 'CORE')
        if 'jacket' in c: sub = 'CORE'
        return 'A', sub
    if t == 'Char_Armor_Undersuit': return 'C', 'FLIGHT SUITS' if 'flightsuit' in c else 'UNDERSUITS'
    if t.startswith('Char_Clothing'): return 'C', 'CLOTHING'
    if t == 'WeaponPersonal':
        w = re.sub(r'^[a-z]+_', '', c).split('_')[0]
        return 'W', {'pistol': 'SIDEARMS', 'smg': 'SMGS', 'rifle': 'RIFLES', 'sniper': 'SNIPER RIFLES', 'shotgun': 'SHOTGUNS',
                     'lmg': 'LMGS', 'hmg': 'LMGS', 'crossbow': 'SPECIAL'}.get(w, 'OTHER')
    if t == 'WeaponAttachment': return 'M', 'MAGAZINES'
    if t == 'WeaponMining': return 'T', 'MINING LASERS'
    if t == 'MiningModifier': return 'T', 'MINING MODULES'
    if t == 'SalvageHead': return 'T', 'SALVAGE HEADS'
    if t == 'SalvageModifier': return 'T', 'SCRAPER MODULES'
    if t == 'TractorBeam': return 'T', 'TRACTOR BEAMS'
    if t in ('PowerPlant', 'Cooler', 'Shield', 'QuantumDrive', 'Radar'):
        return 'P', {'PowerPlant': 'POWER PLANTS', 'Cooler': 'COOLERS', 'Shield': 'SHIELDS', 'QuantumDrive': 'QUANTUM DRIVES', 'Radar': 'RADARS'}[t]
    if t == 'WeaponGun':
        m = re.search(r'_S0?(\d+)', key) or re.search(r's(\d+)$', c)
        return 'V', 'SIZE ' + (m.group(1) if m else '?')
    if t == 'Container': return 'X', 'ORE PODS'
    if t == 'DockingCollar': return 'X', 'FUEL NOZZLES'
    return 'O', 'MISSION ITEMS'


def size(o, key):
    t = o.get('Type') or ''
    if t.startswith('Char'): return W.get(o.get('Subtype'), '')
    m = re.search(r'_S0?(\d+)(_|$)', key)
    return ('S' + m.group(1)) if m else ''


def pool_name(k):
    if k.startswith('@'): return k
    h = re.sub(r'^BP_(MISSIONREWARD|REWARDS|REWARD)_', '', k).replace('_', ' ')
    h = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[a-zA-Z])(?=\d)', ' ', h)
    return re.sub(r'\s+', ' ', h).strip()


TYPE_WORD = {'COOL': 'Cooler', 'RADR': 'Radar', 'POWR': 'Power Plant', 'SHLD': 'Shield', 'QDRV': 'Quantum Drive'}
SHIP_WORD = {'890j': '890 Jump', 'polaris': 'Polaris', 'idris': 'Idris', 'reclaimer': 'Reclaimer', 'javelin': 'Javelin',
             'pioneer': 'Pioneer', 'lephari': 'Lephari'}
SUB_WORD = {'CORE': 'Core', 'HELMETS': 'Helmet', 'ARMS': 'Arms', 'LEGS': 'Legs', 'BACKPACKS': 'Backpack'}


def clean_name(n):
    n = (n or '').replace('\u00a0', ' ')
    return re.sub(r'\s+', ' ', n).strip()


def bad_name(n):
    return not n or n.startswith('@') or 'PLACEHOLDER' in n.upper()


def name_from_key(key, o):
    """Readable name for items the game left unnamed, e.g. BP_CRAFT_RADR_RSI_S04_Polaris -> 'Radar S4 (Polaris)'."""
    parts = re.sub(r'^BP_CRAFT_', '', key).split('_')
    typ = TYPE_WORD.get(parts[0].upper(), (o.get('Type') or 'Item'))
    size = next((p for p in parts if re.fullmatch(r'S0?\d+', p, re.I)), '')
    ship = [p for p in parts[1:] if not re.fullmatch(r'S0?\d+', p, re.I) and p.upper() not in ('SCITEM', 'TEMP') and len(p) > 4 or p.lower() in SHIP_WORD]
    ship = SHIP_WORD.get(ship[-1].lower(), ship[-1]) if ship else ''
    return f"{typ}{(' S' + str(int(size[1:]))) if size else ''}{(' (' + ship + ')') if ship else ''}"


def ship_token(key):
    for p in reversed(re.sub(r'^BP_CRAFT_', '', key).split('_')):
        if p.lower() in SHIP_WORD: return SHIP_WORD[p.lower()]
    return ''


def convert(bp):
    """Returns dict(pools, mods, mats, items) where items is the compact array format used by the page."""
    POOLS, PI, MODS, MI, MATS = [], {}, [], {}, {}

    def pool(k):
        h = pool_name(k)
        if h not in PI: PI[h] = len(POOLS); POOLS.append(h)
        return PI[h]

    def mod(m):
        k = (m['Name'], m.get('UnitFormat', ''))
        if k not in MI: MI[k] = len(MODS); MODS.append([m['Name'], m.get('UnitFormat', '')])
        return MI[k]

    def opts(g):
        r = []
        for ch in g.get('Children', []):
            if ch['Kind'] == 'group': r += opts(ch); continue
            n = ch['Name']; k = 'r' if ch['Kind'] == 'resource' else 'i'
            MATS.setdefault(n, {'k': k, 'u': 0}); MATS[n]['u'] += 1
            r.append([n, ch.get('QuantityScu') if k == 'r' else ch.get('Quantity'), ch.get('MinQuality', 0)])
        return r

    def mods(g):
        r = []
        for m in g.get('Modifiers', []):
            vt = m.get('ValueRangeType'); qr = m.get('QualityRange')
            if vt == 'linear' and m.get('ValueSegments'):
                # several quality bands (e.g. 0-500: x0.8-1.0, 501-1000: x1.0-1.2): one entry per band
                for x in m['ValueSegments']:
                    r.append([mod(m), x['QualityMin'], x['QualityMax'], x['ModifierAtStart'], x['ModifierAtEnd']])
            elif vt == 'linear' and isinstance(m.get('ModifierRange'), dict) and isinstance(qr, dict):
                r.append([mod(m), qr['Min'], qr['Max'], m['ModifierRange']['AtMinQuality'], m['ModifierRange']['AtMaxQuality']])
            elif vt == 'linear_integer_additive':
                r.append([mod(m), 'a', [[x['QualityMin'], x['QualityMax'], x['AdditiveAtStart'], x['AdditiveAtEnd']] for x in m.get('ValueSegments', [])]])
        return r

    # 1) group blueprints by the item they make (UUID), so two blueprints for one item become one entry
    groups_by_item = {}
    for b in bp:
        o = out(b)
        if not o and not b.get('Key'): continue
        uid = (o.get('UUID') or '') or ('key:' + b.get('Key', ''))
        groups_by_item.setdefault(uid, []).append(b)
    # 2) names: clean, fill missing, make duplicates (different items, same in-game name) unique
    entries = []
    for uid, bs in groups_by_item.items():
        b = bs[0]; o = dict(out(b)); key = b.get('Key', '')
        if not o.get('Type'):
            o['Type'] = {'COOL': 'Cooler', 'RADR': 'Radar', 'POWR': 'PowerPlant', 'SHLD': 'Shield', 'QDRV': 'QuantumDrive'}.get(re.sub(r'^BP_CRAFT_', '', key).split('_')[0].upper(), '')
        gname = clean_name(o.get('Name'))
        nn = bad_name(gname)
        name = name_from_key(key, o) if nn else gname
        entries.append({'uid': uid, 'bs': bs, 'o': o, 'key': key, 'n': name, 'gn': '' if nn else gname, 'nn': nn})
    by = {}
    for e in entries: by.setdefault(e['n'].lower(), []).append(e)
    for same in by.values():
        if len(same) < 2: continue
        info = [(cls(e['o'], e['key']), size(e['o'], e['key']), ship_token(e['key'])) for e in same]
        for idx, e in enumerate(same):
            (c, sub), z, ship = info[idx]
            if len({x[0] for x in info}) > 1: tag = SUB_WORD.get(sub, sub.title())
            elif len({x[1] for x in info}) > 1 and z: tag = z
            elif len({x[2] for x in info}) > 1 and ship: tag = ship
            else: tag = 'v' + str(idx + 1)
            e['n'] = f"{e['n']} ({tag})"
    cat = {}
    for e in entries:
        n = e['n']; o = e['o']; b = e['bs'][0]
        pools = []; default = False
        for bb in e['bs']:
            av = bb.get('Availability') or {}
            own = 'BP_REWARD_' + re.sub(r'^BP_CRAFT_', '', bb.get('Key') or '')
            # a pool made just for this one blueprint (e.g. 4.10.3 Raider Camo) says nothing about where it drops
            pools += [pool('@special' if p['Key'].lower() == own.lower() else p['Key']) for p in av.get('RewardPools') or []]
            default = default or bool(av.get('Default'))
        pools = sorted(set(pools))
        av = {'Default': default}
        c, s = cls(o, b.get('Key', ''))
        t = (b.get('Tiers') or [{}])[0]
        groups = []
        for g in (t.get('Requirements') or {}).get('Children', []):
            groups.append([g['Name'], g.get('RequiredCount', 1), opts(g), mods(g)])
        dm = b.get('Dismantle') or {}
        cat[n] = {'gn': e['gn'] if e['gn'] != n else '', 'nn': e['nn'], 'u': (o.get('UUID') or '').replace('-', '')[:12], 'n': n, 'c': c, 's': s, 'z': size(o, b.get('Key', '')),
                  'g': o.get('Grade') or '', 't': t.get('CraftTimeSeconds', 0), 'r': groups, 'p': pools, 'def': bool(av.get('Default')),
                  'x': [[x['Name'], x.get('QuantityScu') if x['Kind'] == 'resource' else x.get('Quantity'), 'r' if x['Kind'] == 'resource' else 'i'] for x in dm.get('Returns', [])],
                  'xt': dm.get('TimeSeconds', 0)}
    items = []
    for n, e in sorted(cat.items(), key=lambda x: x[0].lower()):
        items.append([e['n'], e['c'], e['s'], e['z'], e['g'], e['t'], e['r'], e['p'], 1 if e['def'] else 0, e['x'], e['xt'], e['u'], e['gn'], 1 if e['nn'] else 0])
    return {'pools': POOLS, 'mods': MODS, 'mats': {k: [v['k'], v['u']] for k, v in sorted(MATS.items())}, 'items': items}


VER_RE = re.compile(r'(\d+\.\d+(?:\.\d+)?)-(LIVE|PTU|EPTU|HOTFIX|TECH-PREVIEW)\.(\d+)', re.I)


def parse_version(s):
    """'4.10.2-LIVE.12881860' -> ('4.10.2','LIVE',12881860) or None"""
    m = VER_RE.search(s or '')
    return (m.group(1), m.group(2).upper(), int(m.group(3))) if m else None


def wiki_sig(here):
    """Short hash of which picture each name uses in the wiki cache (ignores 'checked' timestamps)."""
    import hashlib, json, os
    p = os.path.join(here, 'wiki', 'index.json'); sp = os.path.join(here, 'shop', 'index.json')
    d = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    s = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}   # in-game shop pictures count too
    fp = os.path.join(here, 'fab', 'index.json')
    fb = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}   # and fabricator pictures
    if not d and not s and not fb: return ''
    sig = {k: v.get('f') for k, v in d.items()}; sig.update({'shop:' + k: (v.get('f'), v.get('sharp')) for k, v in s.items()})
    sig.update({'fab:' + k: (v.get('f'), v.get('sharp')) for k, v in fb.items()})
    return hashlib.sha1(json.dumps(sig, sort_keys=True).encode()).hexdigest()[:12]


def add_game_icons(here, data, cat_mats):
    """Put in-game UI icons (tools/game_icons/out, made by game_icons/make.py from Data.p4k) into imgdata:
    material icons win over wiki photos; 'subs' = category icons for items that have no picture."""
    import json, os
    d = os.path.join(here, 'game_icons', 'out')
    if not os.path.exists(os.path.join(d, 'mats.json')): return data
    M = json.load(open(os.path.join(d, 'mats.json'), encoding='utf-8'))
    S = json.load(open(os.path.join(d, 'subs.json'), encoding='utf-8'))
    generic = M.get('Iron') and M.get('Silicon')  # Silicon uses the generic "mineral" icon
    pos = {u: i for i, u in enumerate(data['thumbs'])}
    for m, (kind, *_r) in cat_mats.items():
        u = M.get(m) or (generic if kind == 'r' else None)   # unknown new ore -> generic mineral icon
        if not u: continue
        if u not in pos: pos[u] = len(data['thumbs']); data['thumbs'].append(u)
        data['mats'][m] = pos[u]
    data['subs'] = S
    return data
