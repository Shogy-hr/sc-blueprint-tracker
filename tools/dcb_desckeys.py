#!/usr/bin/env python3
"""Which description key belongs to which item, from Game2.dcb (colour variants often share the
description of the base item, so it cannot be guessed from the name key).
Writes {name key (lower case): [description key (lower case), English name]} for every item.
Used by build_labels.py to put shop prices into the in-game item info (Label Forge).
Usage: python3 dcb_desckeys.py Game2.dcb global.ini -o desckeys.json"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dcb import DCB
ap = argparse.ArgumentParser(); ap.add_argument('dcb'); ap.add_argument('ini'); ap.add_argument('-o', default='desckeys.json')
a = ap.parse_args()
names = {}
for line in open(a.ini, encoding='utf-8-sig', errors='replace'):
    k, _, v = line.rstrip('\r\n').partition('=')
    if k.lower().startswith('item_name'): names[k.lower()] = v.strip()
d = DCB(a.dcb); out = {}
for r in d.records():
    if d.sname(r['si']) != 'EntityClassDefinition': continue
    e = d.inst(r['si'], r['ii'], 0, False)
    for c in e.get('Components') or []:
        if not c or c[0] != 'ptr' or d.sname(c[1]) != 'SAttachableComponentParams': continue
        loc = (d.inst(c[1], c[2], 0, True).get('AttachDef') or {}).get('Localization') or {}
        nk = (loc.get('Name') or '').lstrip('@').lower(); dk = (loc.get('Description') or '').lstrip('@').lower()
        if nk.startswith('item_name') and dk.startswith('item_desc') and nk in names: out[nk] = [dk, names[nk]]
        break
json.dump(dict(sorted(out.items())), open(a.o, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('desc keys', len(out), '->', a.o)
