#!/usr/bin/env python3
"""Build blueprints.json (same schema as StarCitizenWiki/scunpacked-data) straight from the game's Game2.dcb.
Usage: python3 build_bp.py Game2.dcb [global.ini] -o blueprints.json"""
import argparse, json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dcb import DCB

def load_ini(p):
    L = {}
    if not p: return L
    for line in open(p, encoding='utf-8-sig', errors='replace'):
        if '=' not in line: continue
        k, v = line.rstrip('\r\n').split('=', 1)
        L[k.split(',')[0].strip().lower()] = v
    return L

def secs(t):
    if not t: return 0
    return t.get('days', 0) * 86400 + t.get('hours', 0) * 3600 + t.get('minutes', 0) * 60 + t.get('seconds', 0)

def r6(x):
    x = round(float(x), 6)
    return int(x) if x == int(x) and abs(x) < 1e15 else x

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dcb'); ap.add_argument('ini', nargs='?'); ap.add_argument('-o', default='blueprints.json')
    a = ap.parse_args()
    d = DCB(a.dcb); L = load_ini(a.ini)
    R = d.records(); G = {r['guid']: r for r in R}
    def get(r, follow=True): return d.inst(r['si'], r['ii'], 0, follow)
    def loc(k, fb=''):
        if not k: return fb
        k2 = k.lstrip('@').lower()
        if k2 in L: return L[k2].strip()
        if k2 in ('loc_placeholder', 'loc_empty', ''): return fb
        return fb if fb else k
    def short(name): return name.split('.', 1)[1] if '.' in name else name
    cache = {}
    def ent(g):
        if g in cache: return cache[g]
        r = G.get(g); o = None
        if r:
            e = get(r)
            o = {'UUID': g, 'Class': short(r['name']).lower()}
            for c in e.get('Components') or []:
                if c and c.get('_t') == 'SAttachableComponentParams':
                    ad = c['AttachDef']
                    o['Type'] = ad.get('Type') or ''; o['Subtype'] = ad.get('SubType') or ''
                    o['Grade'] = str(ad.get('Grade', ''))
                    o['Name'] = loc((ad.get('Localization') or {}).get('Name'), short(r['name']))
                    break
            else:
                o['Name'] = short(r['name'])
        cache[g] = o; return o
    def resname(g):
        r = G.get(g)
        if not r: return g
        x = get(r, False)
        return loc(x.get('displayName'), short(r['name']))
    gpp = {}
    CUR = {}   # output item of the blueprint being built (for per-item-type stat names)
    def gppinfo(g):
        if g in gpp: return gpp[g]
        r = G[g]; x = get(r)
        k = short(r['name']); k = re.sub(r'^GPP_', '', k).lower()
        o = {'Key': k, 'Name': loc(x.get('propertyName'), k), 'Overrides': []}
        for ov in [v for v in (x.get('nameOverrides') or []) if v]:
            cnd = ov.get('condition') or {}
            o['Overrides'].append((set(cnd.get('matchItemTypes') or []), set(cnd.get('matchSubTypes') or []), loc(ov.get('propertyName'), o['Name'])))
        uf = loc(x.get('unitFormat'), '')
        if uf: o['UnitFormat'] = uf
        dt = x.get('displayTransformation')
        if dt and 'scale' in dt: o['DisplayScale'] = r6(dt['scale'])
        gpp[g] = o; return o
    def modifiers(ctx):
        out = []
        for c in [c for c in (ctx or []) if c]:
            if c.get('_t') != 'CraftingCostContext_ResultGameplayPropertyModifiers': continue
            for m in (c.get('gameplayPropertyModifiers') or {}).get('gameplayPropertyModifiers') or []:
                g = m['gameplayPropertyRecord'][1]; info = gppinfo(g)
                o = {'UUID': g, 'Key': info['Key']}
                vr = [v for v in (m.get('valueRanges') or []) if v]
                if not vr:
                    o.update({'QualityRange': [], 'ModifierRange': []})
                elif vr[0]['_t'].endswith('_Linear'):
                    v = vr[0]
                    o['QualityRange'] = {'Min': v['startQuality'], 'Max': v['endQuality']}
                    o['ModifierRange'] = {'AtMinQuality': r6(v['modifierAtStart']), 'AtMaxQuality': r6(v['modifierAtEnd'])}
                    o['ValueRangeType'] = 'linear'
                    if len(vr) > 1:
                        o['ValueSegments'] = [{'QualityMin': v['startQuality'], 'QualityMax': v['endQuality'], 'ModifierAtStart': r6(v['modifierAtStart']), 'ModifierAtEnd': r6(v['modifierAtEnd'])} for v in vr]
                else:
                    v = vr[0]
                    o['QualityRange'] = {'Min': v['startQuality'], 'Max': v['endQuality']}
                    o['ModifierRange'] = []
                    o['ValueRangeType'] = 'linear_integer_additive'
                    o['ValueSegments'] = [{'QualityMin': v['startQuality'], 'QualityMax': v['endQuality'], 'AdditiveAtStart': v.get('additiveModifierAtStart'), 'AdditiveAtEnd': v.get('additiveModifierAtEnd')} for v in vr]
                o['Name'] = info['Name']
                for ts, ss, nm in info['Overrides']:
                    if (not ts or CUR.get('Type') in ts) and (not ss or CUR.get('Subtype') in ss): o['Name'] = nm; break
                for k in ('UnitFormat', 'DisplayScale'):
                    if k in info: o[k] = info[k]
                out.append(o)
        return out
    def qmult(ctx):
        m = 1
        for c in [c for c in (ctx or []) if c]:
            if c.get('_t') == 'CraftingCostContext_QuantityMultiplier': m *= c.get('multiplier', 1)
        return m
    def cost(c, mult=1):
        t = c['_t']
        if t == 'CraftingCost_Select':
            ni = c.get('nameInfo') or {}
            o = {'Kind': 'group', 'Key': ni.get('debugName', ''), 'Name': loc(ni.get('displayName'), (ni.get('debugName') or '').title()),
                 'RequiredCount': c.get('count', 1)}
            ms = modifiers(c.get('context'))
            if ms: o['Modifiers'] = ms
            m2 = mult * qmult(c.get('context'))
            o['Children'] = [cost(x, m2) for x in c.get('options') or [] if x]
            return o
        if t == 'CraftingCost_Resource':
            g = c['resource'][1]
            o = {'Kind': 'resource', 'UUID': g, 'Name': resname(g), 'QuantityScu': r6(c['quantity']['standardCargoUnits'] * mult * qmult(c.get('context'))), 'MinQuality': c.get('minQuality', 0)}
            ms = modifiers(c.get('context'))
            if ms: o['Modifiers'] = ms
            return o
        if t == 'CraftingCost_Item':
            g = c['entityClass'][1]; e = ent(g) or {}
            o = {'Kind': 'item', 'UUID': g, 'Name': e.get('Name', g), 'Quantity': r6(c['quantity'] * mult * qmult(c.get('context'))), 'MinQuality': c.get('minQuality', 0)}
            ms = modifiers(c.get('context'))
            if ms: o['Modifiers'] = ms
            return o
        return {'Kind': 'unknown', 'Type': t}
    # globals
    gp = get([r for r in R if d.sname(r['si']) == 'CraftingGlobalParams'][0])
    default = {x[1] for x in (gp.get('defaultBlueprintSelection') or {}).get('blueprintRecords') or [] if x}
    bl_res = {x[1] for x in gp.get('dismantleBlacklistResources') or [] if x}
    bl_ent = {x[1] for x in gp.get('dismantleBlacklistEntityClasses') or [] if x}
    gen = None
    for r in R:
        if d.sname(r['si']) == 'CraftingBlueprintRecord':
            x = get(r)
            if (x.get('blueprint') or {}).get('_t') == 'GenericCraftingBlueprint':
                p = x['blueprint'].get('processSpecificData') or {}
                if p.get('_t') == 'GenericCraftingProcess_Dismantle': gen = p
    eff = gen['efficiency'] if gen else 0.5; dtime = secs(gen['dismantleTime']) if gen else 15
    pools = {}
    for r in R:
        if d.sname(r['si']) == 'BlueprintPoolRecord':
            for br in get(r).get('blueprintRewards') or []:
                if br.get('blueprintRecord'):
                    pools.setdefault(br['blueprintRecord'][1], []).append({'UUID': r['guid'], 'Key': short(r['name'])})
    out = []
    for r in R:
        if d.sname(r['si']) != 'CraftingBlueprintRecord': continue
        x = get(r); bp = x.get('blueprint') or {}
        if bp.get('_t') != 'CraftingBlueprint': continue
        psd = bp.get('processSpecificData') or {}
        kind = psd.get('_t', '').replace('CraftingProcess_', '').lower()
        o = ent(psd['entityClass'][1]) if psd.get('entityClass') else None
        CUR.clear(); CUR.update(o or {})
        b = {'UUID': r['guid'], 'Key': short(r['name']), 'Kind': kind,
             'CategoryUUID': bp['category'][1] if bp.get('category') else None,
             'Output': o or [],
             'Availability': {'Default': r['guid'] in default, 'RewardPools': sorted({p['UUID']: p for p in pools.get(r['guid'], [])}.values(), key=lambda p: p['Key'])},
             'Tiers': []}
        R2 = []
        for ti, t in enumerate(bp.get('tiers') or []):
            rc = (t.get('recipe') or {}).get('costs') or {}
            mc = rc.get('mandatoryCost')
            top = cost(mc) if mc else None
            if top and top['Kind'] == 'group' and top['RequiredCount'] < len(top['Children']):
                kids = [top]  # "pick N of M" (e.g. ASPECTS 2 of 3) stays a group
            else:
                kids = top['Children'] if top else []
            root = {'Kind': 'root', 'Children': kids}
            b['Tiers'].append({'TierIndex': ti, 'CraftTimeSeconds': r6(secs(rc.get('craftTime'))), 'Requirements': root})
            if ti == 0:
                def coll(n):
                    for c in n.get('Children', []):
                        if c['Kind'] == 'group': coll(c)
                        elif c['Kind'] in ('resource', 'item'):
                            if c['UUID'] in bl_res or c['UUID'] in bl_ent: continue
                            if c['Kind'] == 'resource': R2.append({'Kind': 'resource', 'UUID': c['UUID'], 'Name': c['Name'], 'QuantityScu': r6(c['QuantityScu'] * eff)})
                            elif int(c['Quantity'] * eff) > 0: R2.append({'Kind': 'item', 'UUID': c['UUID'], 'Name': c['Name'], 'Quantity': int(c['Quantity'] * eff)})
                coll(root)
        b['Dismantle'] = {'TimeSeconds': r6(dtime), 'Efficiency': r6(eff), 'Returns': R2}
        out.append(b)
    json.dump(out, open(a.o, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('blueprints', len(out), '->', a.o)

if __name__ == '__main__': main()
