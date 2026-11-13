#!/usr/bin/env python3
"""Import game data extracted from your own Star Citizen install (tools/extract_game_data.ps1).
Usage: python3 import_game_data.py SC_data_....zip --version 4.10.3
Writes tools/game/blueprints.json + tools/game/version.txt. update.py then prefers this data
whenever its build is newer than (or equal to) scunpacked-data, which stays as the backup."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('zip'); ap.add_argument('--version', required=True, help='patch label, e.g. 4.10.3')
ap.add_argument('--channel', default='LIVE')
a = ap.parse_args()
with tempfile.TemporaryDirectory() as t:
    with zipfile.ZipFile(a.zip) as z:
        for n in z.namelist():   # Windows Compress-Archive uses backslashes
            p = os.path.join(t, *re.split(r'[\\/]', n))
            if n.endswith(('/', '\\')): continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with z.open(n) as s, open(p, 'wb') as d: shutil.copyfileobj(s, d)
    find = lambda name, must='': next((os.path.join(r, f) for r, _, fs in os.walk(t) for f in fs if f.lower() == name and must in os.path.join(r, f).lower()), None)
    dcb, ini, bm = find('game2.dcb'), find('global.ini', 'english'), find('build_manifest.id')
    if not dcb: raise SystemExit('Game2.dcb not in the zip')
    m = json.load(open(bm, encoding='utf-8-sig'))['Data'] if bm else {}
    build = m.get('RequestedP4ChangeNum', '0'); date = ''
    if m.get('BuildDateStamp'):
        import datetime
        date = datetime.datetime.strptime(m['BuildDateStamp'], '%a %b %d %Y').strftime('%Y-%m-%d')
    out = os.path.join(HERE, 'game'); os.makedirs(out, exist_ok=True)
    args = [sys.executable, os.path.join(HERE, 'dcb_blueprints.py'), dcb] + ([ini] if ini else []) + ['-o', os.path.join(out, 'blueprints.json')]
    print(subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip())
    if not ini: print('WARNING: no global.ini -> names are internal keys')
ver = f'{a.version}-{a.channel.upper()}.{build}'
open(os.path.join(out, 'version.txt'), 'w', encoding='utf-8').write(f'{ver}\n{date}\n')
print('game data', ver, date)
