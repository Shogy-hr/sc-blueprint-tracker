#!/usr/bin/env python3
"""Ikone iz datoteka igre (Data.p4k) -> male webp slike za kiosk.
Izvor: src/ (SVG/PNG izvuceni iz Data/UI/... u Data.p4k, (c) Cloud Imperium).
Pokretanje (lokalno, treba rsvg-convert + Pillow): python3 make.py
Izlaz: out/mats.json {materijal: data-uri}, out/subs.json {podkategorija: data-uri}."""
import base64, io, json, os, subprocess, tempfile
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
SRC, OUT = os.path.join(HERE, 'src'), os.path.join(HERE, 'out')

SPECIFIC = {'Aluminum': 'Aluminium', **{m: m for m in ['Aphorite', 'Beryl', 'Bexalite', 'Borase', 'Copper', 'Corundum', 'Dolivine', 'Gold', 'Hadanite',
            'Hephaestanite', 'Laranite', 'Quartz', 'Taranite', 'Titanium', 'Tungsten']}}
METAL = ['Agricium', 'Iron', 'Tin']   # generic in-game "metal" icon
# every other ore/gem gets the generic in-game "mineral" icon; non-minerals (e.g. Yormandi Eye) get none
NON_MINERAL = {'Yormandi Eye'}
SUBS = {'COOLERS': 'Engineering_Icon_ItemCooler.svg', 'POWER PLANTS': 'Engineering_Icon_ItemPowerPlant.svg',
        'SHIELDS': 'Engineering_Icon_ItemShieldGenerator.svg', 'QUANTUM DRIVES': 'Engineering_Icon_ItemQuantumDrive.svg',
        'RADARS': 'Engineering_Icon_ItemRadar.svg', 'V': 'Engineering_Icon_ItemGun.svg',
        'MINING LASERS': 'mining.svg', 'MINING MODULES': 'icon_common_mining_laser_power.svg',
        'TRACTOR BEAMS': 'icon_common_tractor_beam.svg', 'SALVAGE HEADS': 'salvage.svg',
        'SCRAPER MODULES': 'icon_hullscraping_tools_salvage.svg', 'FUEL NOZZLES': 'icon_services_refuel_a.svg'}


def load(name, px):
    p = os.path.join(SRC, name)
    if name.endswith('.svg'):
        svg = open(p, encoding='utf-8').read().replace('<svg', '<svg fill="#ffffff"', 1)
        with tempfile.TemporaryDirectory() as t:
            fi, fo = os.path.join(t, 'i.svg'), os.path.join(t, 'o.png')
            open(fi, 'w', encoding='utf-8').write(svg)
            subprocess.run(['rsvg-convert', '-w', str(px), '-h', str(px), '--keep-aspect-ratio', fi, '-o', fo], check=True)
            im = Image.open(fo).convert('RGBA')
    else:
        im = Image.open(p).convert('RGBA'); im.thumbnail((px, px), Image.LANCZOS)
    c = Image.new('RGBA', (px, px)); c.paste(im, ((px - im.width) // 2, (px - im.height) // 2)); return c


def tint(im, rgb):
    """Keep only the shape (alpha * brightness) and paint it one colour."""
    a = Image.eval(im.getchannel('A'), lambda v: v)
    lum = im.convert('L')
    a = Image.composite(a, Image.new('L', im.size, 0), Image.eval(lum, lambda v: 255 if v > 40 else 0))
    out = Image.new('RGBA', im.size, rgb + (0,)); out.putalpha(a); return out


def uri(im):
    b = io.BytesIO(); im.save(b, 'WEBP', lossless=True, quality=100, method=6)
    return 'data:image/webp;base64,' + base64.b64encode(b.getvalue()).decode()


def main(mats):
    os.makedirs(OUT, exist_ok=True)
    M = {}
    for m in mats:
        if m in NON_MINERAL: continue
        f = 'Inv_Icon_%s.svg' % SPECIFIC[m] if m in SPECIFIC else ('Metal_256.png' if m in METAL else 'Mineral_256.png')
        M[m] = uri(tint(load(f, 96), (255, 176, 122)))
    S = {k: uri(tint(load(f, 160), (255, 255, 255))) for k, f in SUBS.items()}
    json.dump(M, open(os.path.join(OUT, 'mats.json'), 'w'), separators=(',', ':'), sort_keys=True)
    json.dump(S, open(os.path.join(OUT, 'subs.json'), 'w'), separators=(',', ':'), sort_keys=True)
    print('game icons: mats', len(M), 'subs', len(S))


if __name__ == '__main__':
    main(json.load(open(os.path.join(HERE, '..', 'catalog.json'), encoding='utf-8'))['mats'])
