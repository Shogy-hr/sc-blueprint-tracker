#!/usr/bin/env python3
"""Check which Star Citizen builds are on LIVE / PTU and write ../data/status.json.
Sources (first that answers wins per channel, all are recorded):
  1. RSI Spectrum - official Patch Notes forum
  2. RSI Roadmap progress tracker (official, version only)
  3. patchbot.io (community mirror of the RSI patch notes)"""
import json, os, re, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import parse_version, VER_RE
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'data', 'status.json')
UA = 'Mozilla/5.0 (compatible; SC-Blueprint-Tracker/1.0; fan site update check)'
SOURCES = [
    ('RSI Spectrum (Patch Notes)', 'https://robertsspaceindustries.com/spectrum/community/SC/forum/190048'),
    ('RSI Roadmap', 'https://robertsspaceindustries.com/roadmap/progress-tracker'),
    ('patchbot.io', 'https://patchbot.io/games/star-citizen'),
]
TITLE_RE = re.compile(r'Alpha\s+(\d+\.\d+(?:\.\d+)?)\s+(LIVE|PTU)\b[^<>{}"]{0,60}?\b(\d{8,9})\b', re.I)
HOTFIX_RE = re.compile(r'Alpha\s+(\d+\.\d+(?:\.\d+)?)\s+LIVE\s*-\s*Hotfix\s+(\d{8,9})', re.I)
ROADMAP_LIVE = re.compile(r'Live Version:\s*(\d+\.\d+(?:\.\d+)?)', re.I)
ROADMAP_PTU = re.compile(r'PTU Version:\s*Alpha\s*(\d+\.\d+(?:\.\d+)?)\s*[,-]\s*(\d{8,9})', re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/json'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', 'replace')


def scan(text):
    """Return list of (version, channel, build) found in a page."""
    found = []
    for m in VER_RE.finditer(text):
        found.append((m.group(1), m.group(2).upper(), int(m.group(3))))
    for m in TITLE_RE.finditer(text):
        found.append((m.group(1), m.group(2).upper(), int(m.group(3))))
    for m in HOTFIX_RE.finditer(text):
        found.append((m.group(1), 'LIVE', int(m.group(2))))
    m = ROADMAP_PTU.search(text)
    if m: found.append((m.group(1), 'PTU', int(m.group(2))))
    m = ROADMAP_LIVE.search(text)
    if m: found.append((m.group(1), 'LIVE', 0))
    return found


def main():
    cat = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))
    dv = parse_version(cat['v'])
    status = {'checked': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'data': {'version': cat['v'], 'build': dv[2] if dv else None, 'date': cat.get('date', '')},
              'live': None, 'ptu': None, 'ptuData': None, 'sources': []}
    best = {}
    for name, url in SOURCES:
        try:
            hits = scan(fetch(url))
            status['sources'].append({'name': name, 'ok': bool(hits), 'found': len(hits)})
            for ver, ch, build in hits:
                ch = 'PTU' if ch in ('PTU', 'EPTU') else ch
                if ch not in ('LIVE', 'PTU'): continue
                cur = best.get(ch)
                if not cur or build > cur['build'] or (build == cur['build'] and cur['source'] != name and name.startswith('RSI')):
                    best[ch] = {'version': ver, 'build': build, 'source': name, 'url': url}
        except Exception as e:
            status['sources'].append({'name': name, 'ok': False, 'error': str(e)[:120]})
    # a LIVE entry with build 0 only tells the version (roadmap); keep it only if nothing better
    status['live'] = best.get('LIVE'); status['ptu'] = best.get('PTU')
    # PTU that is older than or equal to LIVE is not "upcoming"
    if status['ptu'] and status['live'] and status['live']['build'] and status['ptu']['build'] <= status['live']['build']:
        status['ptu'] = None
    pj = os.path.join(HERE, '..', 'data', 'ptu.json')
    if os.path.exists(pj):
        p = json.load(open(pj, encoding='utf-8'))
        status['ptuData'] = {'version': p['version'], 'date': p.get('date', ''), 'added': len(p['added']), 'changed': len(p['changed']), 'removed': len(p['removed'])}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(status, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: status[k] for k in ('data', 'live', 'ptu', 'ptuData')}, ensure_ascii=False))
    print('sources:', status['sources'])


if __name__ == '__main__':
    main()
