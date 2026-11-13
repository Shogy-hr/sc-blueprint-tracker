#!/usr/bin/env python3
"""Build tools/catalog.json from a LIVE blueprints.json.
Usage: python3 build_catalog.py [--src blueprints.json] [--version 4.10.2-LIVE.12881860] [--date 2026-10-28]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import convert, parse_version
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--src', default=os.path.join(HERE, 'blueprints.json'))
ap.add_argument('--version', default=os.environ.get('SC_DATA_VERSION', ''))
ap.add_argument('--date', default=os.environ.get('SC_DATA_DATE', ''))
ap.add_argument('--prev', default=os.path.join(HERE, 'catalog.json'), help='catalog of the previous build (for the "new in this patch" list)')
a = ap.parse_args()
if not parse_version(a.version):
    raise SystemExit('Give --version like 4.10.2-LIVE.12881860 (see the scunpacked-data commit message)')
C = convert(json.load(open(a.src, encoding='utf-8')))
C = {'v': a.version, 'date': a.date, **C}
# "new in this patch": blueprints that were not in the previous patch's catalog. A rebuild or hotfix of
# the same patch keeps the list (and adds anything new); a new patch starts a fresh list.
try: old = json.load(open(a.prev, encoding='utf-8'))
except Exception: old = None
if old:
    key = lambda it: (it[11] if len(it) > 11 and it[11] else it[0].lower())
    oldk = {key(it) for it in old['items']}; added = [it[0] for it in C['items'] if key(it) not in oldk]
    pv, ov = parse_version(a.version)[0], (parse_version(old.get('v', '')) or ('',))[0]
    if pv == ov:
        C['nwv'] = old.get('nwv', pv); keep = set(old.get('nw', [])) | set(added)
        C['nw'] = [it[0] for it in C['items'] if it[0] in keep]
    else:
        C['nwv'] = pv; C['nw'] = added
s = json.dumps(C, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(HERE, 'catalog.json'), 'w', encoding='utf-8').write(s)
print('catalog', a.version, len(C['items']), 'blueprints', len(s), 'bytes')
