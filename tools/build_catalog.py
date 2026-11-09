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
a = ap.parse_args()
if not parse_version(a.version):
    raise SystemExit('Give --version like 4.10.2-LIVE.12881860 (see the scunpacked-data commit message)')
C = convert(json.load(open(a.src, encoding='utf-8')))
C = {'v': a.version, 'date': a.date, **C}
s = json.dumps(C, ensure_ascii=False, separators=(',', ':'))
open(os.path.join(HERE, 'catalog.json'), 'w', encoding='utf-8').write(s)
print('catalog', a.version, len(C['items']), 'blueprints', len(s), 'bytes')
