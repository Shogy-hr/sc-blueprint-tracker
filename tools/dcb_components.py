#!/usr/bin/env python3
"""Ship components (coolers, power plants, shields, quantum drives, radars) from Game2.dcb:
localisation key -> [type, size, grade]. Used by the Label Forge page (labels/) to put the real
size and grade into component names. Usage: python3 dcb_components.py Game2.dcb -o components.json"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dcb import DCB
TYPES = {'Cooler': 'COOL', 'PowerPlant': 'POWR', 'Shield': 'SHLD', 'QuantumDrive': 'QDRV', 'Radar': 'RADR'}
ap = argparse.ArgumentParser(); ap.add_argument('dcb'); ap.add_argument('-o', default='components.json'); ap.add_argument('--version', default='')
a = ap.parse_args()
d = DCB(a.dcb); out = {}
for r in d.records():
    if d.sname(r['si']) != 'EntityClassDefinition': continue
    e = d.inst(r['si'], r['ii'], 0, False)          # shallow read first: cheap filter on the record name is not reliable
    for c in e.get('Components') or []:
        if not c or c[0] != 'ptr': continue
        if d.sname(c[1]) != 'SAttachableComponentParams': continue
        ad = d.inst(c[1], c[2], 0, True).get('AttachDef') or {}
        t = TYPES.get(ad.get('Type'))
        k = ((ad.get('Localization') or {}).get('Name') or '').lstrip('@').lower()
        g = ad.get('Grade') or 0
        if t and k and k not in ('loc_placeholder', 'loc_empty'):
            out[k] = [t, ad.get('Size'), 'ABCD'[g - 1] if 1 <= g <= 4 else '']
        break
json.dump({'v': a.version, 'items': dict(sorted(out.items()))}, open(a.o, 'w', encoding='utf-8'), separators=(',', ':'))
print('components', len(out), '->', a.o)
