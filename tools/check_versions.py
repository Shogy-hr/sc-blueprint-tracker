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
OUT = os.path.join(HERE, '..', 'blueprints', 'data', 'status.json')
UA = 'Mozilla/5.0 (compatible; SC-Blueprint-Tracker/1.0; fan site update check)'
SOURCES = [
    ('RSI Spectrum (Patch Notes)', 'https://robertsspaceindustries.com/spectrum/community/SC/forum/190048'),
    ('RSI Roadmap', 'https://robertsspaceindustries.com/roadmap/progress-tracker'),
    ('patchbot.io', 'https://patchbot.io/games/star-citizen'),
]
STATUS_URL = 'https://status.robertsspaceindustries.com/'   # official RSI server status (cState)
SEV = {'ok': 0, 'notice': 1, 'disrupted': 2, 'down': 3}


def norm_sev(v):
    v = str(v or 'ok').strip().lower()
    if v in SEV: return v
    if 'operational' in v or v in ('up', 'online'): return 'ok'
    if 'maint' in v or 'notice' in v: return 'notice'
    if 'major' in v or 'down' in v or 'offline' in v: return 'down'
    return 'disrupted'


def server_status():
    """Official RSI status page -> {'summary': ok|notice|disrupted|down, 'systems': [{name,status}]}.
    cState offers a read-only JSON API at /index.json; fall back to reading the HTML."""
    try:
        j = json.loads(fetch(STATUS_URL + 'index.json'))
        systems = [{'name': x.get('name', ''), 'status': norm_sev(x.get('status'))} for x in j.get('systems', [])]
        worst = max((x['status'] for x in systems if x['status'] in SEV), key=SEV.get, default='ok')
        summ = norm_sev(j.get('summaryStatus')) if j.get('summaryStatus') else ''
        summ = max(summ, worst, key=lambda v: SEV.get(v, -1)) if summ in SEV else worst
        return {'summary': summ, 'systems': systems, 'source': STATUS_URL}
    except Exception as e:
        err = str(e)[:120]
    try:
        html = fetch(STATUS_URL)
        systems = []
        for name in ('Platform', 'Persistent Universe', 'Arena Commander'):
            m = re.search(re.escape(name) + r'.{0,400}?\b(Operational|Disrupted|Degraded|Down|Outage|Maintenance|Notice)\b', html, re.S | re.I)
            if m:
                w = m.group(1).lower()
                st = 'ok' if w == 'operational' else 'down' if w in ('down', 'outage') else 'notice' if w in ('maintenance', 'notice') else 'disrupted'
                systems.append({'name': name, 'status': st})
        if systems:
            return {'summary': max((x['status'] for x in systems), key=SEV.get), 'systems': systems, 'source': STATUS_URL}
    except Exception as e:
        err = str(e)[:120]
    return {'summary': 'unknown', 'systems': [], 'source': STATUS_URL, 'error': err}
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


HIST = os.path.join(HERE, 'patch_history.json')


def next_patch(status, today=None):
    """Remember when each version reached PTU / LIVE and estimate the next LIVE date as
    first-PTU-date + median PTU duration of earlier patches of the same kind."""
    import datetime as dt, statistics
    today = today or dt.date.today()
    try: h = json.load(open(HIST, encoding='utf-8'))
    except Exception: h = {}
    live = (status.get('live') or {}).get('version'); ptu = (status.get('ptu') or {}).get('version')
    if ptu: h.setdefault(ptu, {}).setdefault('ptu', today.isoformat())
    if live: h.setdefault(live, {}).setdefault('live', today.isoformat())
    json.dump(h, open(HIST, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if not ptu or ptu == live: return None
    e = h.get(ptu, {})
    kind = lambda v: 'major' if v.count('.') < 2 or v.endswith('.0') else 'minor'
    d = lambda s: dt.date.fromisoformat(s)
    durs = [(d(x['live']) - d(x['ptu'])).days for k, x in h.items() if isinstance(x, dict) and x.get('ptu') and x.get('live') and kind(k) == kind(ptu) and d(x['live']) > d(x['ptu'])]
    out = {'version': ptu, 'ptuSince': e.get('ptu')}
    if e.get('target'):
        out.update(eta=e['target'], basis='official')
    elif durs and e.get('ptu'):
        med = int(round(statistics.median(durs)))
        eta = d(e['ptu']) + dt.timedelta(days=med)
        out.update(eta=eta.isoformat(), basis='estimate', days=med, samples=len(durs), overdue=eta < today)
    return out


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
    # the game data we ship is a LIVE build too: if it is at least as new, trust its version label
    if dv and (not status['live'] or dv[2] >= (status['live'].get('build') or 0)):
        status['live'] = {'version': dv[0], 'build': dv[2], 'source': 'game data', 'url': ''} if not status['live'] or dv[2] > (status['live'].get('build') or 0) else dict(status['live'], version=dv[0])
    # PTU that is older than or equal to LIVE is not "upcoming"
    if status['ptu'] and status['live'] and status['live']['build'] and status['ptu']['build'] <= status['live']['build']:
        status['ptu'] = None
    status['server'] = server_status()
    try: status['next'] = next_patch(status)
    except Exception as e: status['next'] = None; print('next patch estimate failed:', e)
    pj = os.path.join(HERE, '..', 'blueprints', 'data', 'ptu.json')
    if os.path.exists(pj):
        p = json.load(open(pj, encoding='utf-8'))
        status['ptuData'] = {'version': p['version'], 'date': p.get('date', ''), 'added': len(p['added']), 'changed': len(p['changed']), 'removed': len(p['removed'])}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(status, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: status[k] for k in ('data', 'live', 'ptu', 'ptuData', 'server', 'next')}, ensure_ascii=False))
    print('sources:', status['sources'])


if __name__ == '__main__':
    main()
