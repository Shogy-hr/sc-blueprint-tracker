#!/usr/bin/env python3
"""Run by the GitHub Action (or by hand). Keeps the site in sync with the game:
 1. newest LIVE game data: tools/game/ (extracted from our own game install with extract_game_data.ps1 +
    import_game_data.py) when its build is newer, otherwise StarCitizenWiki/scunpacked-data (the backup)
 2. item images from jpcoombes-byte/Datapad
 3. optional PTU data you put in tools/ptu/ (blueprints.json + version.txt)
 4. which builds are on LIVE/PTU right now (RSI patch notes) -> data/status.json
Only rebuilds when something changed. Use --force to rebuild anyway."""
import json, os, re, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sclib import parse_version, wiki_sig
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..')); SITE = os.path.join(ROOT, 'blueprints')   # the kiosk lives in /blueprints/
DATA_REPO = 'https://github.com/StarCitizenWiki/scunpacked-data.git'
IMG_REPO = 'https://github.com/jpcoombes-byte/Datapad.git'
FORCE = '--force' in sys.argv


def run(*cmd, cwd=None):
    print('$', ' '.join(cmd)); r = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True); return r.stdout.strip()


def py(script, *args):
    print(run(sys.executable, os.path.join(HERE, script), *args))


def latest_data(tmp):
    d = os.path.join(tmp, 'scdata')
    run('git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', DATA_REPO, d)
    run('git', 'sparse-checkout', 'set', '--no-cone', '/blueprints.json', cwd=d)
    msg = run('git', 'log', '-1', '--format=%s', cwd=d); date = run('git', 'log', '-1', '--format=%cs', cwd=d)
    pv = parse_version(msg)
    if not pv: raise SystemExit(f'Unexpected data commit message: {msg!r}')
    ver = re.search(r'\d+\.\d+(?:\.\d+)?-LIVE\.\d+', msg).group(0)
    return ver, date, os.path.join(d, 'blueprints.json')


def own_game_data(ver, date, src):
    """Prefer tools/game/ (our own extraction) when its build is newer than scunpacked-data."""
    gv = os.path.join(HERE, 'game', 'version.txt'); gb = os.path.join(HERE, 'game', 'blueprints.json')
    if not (os.path.exists(gv) and os.path.exists(gb)): return ver, date, src
    lines = open(gv, encoding='utf-8').read().split()
    g = parse_version(lines[0] if lines else ''); s = parse_version(ver)
    if g and s and g[1] == 'LIVE' and g[2] > s[2]:
        print('own game data is newer:', lines[0], '>', ver)
        return lines[0], (lines[1] if len(lines) > 1 else date), gb
    print('scunpacked-data is up to date (own game data:', lines[0] if lines else '?', ')')
    return ver, date, src


def images(tmp, src):
    """(Re)build item images from Datapad + the Wiki cache."""
    dp = os.path.join(HERE, 'datapad')
    if not os.path.isdir(os.path.join(dp, 'img')):
        run('git', 'clone', '-q', '--depth', '1', IMG_REPO, os.path.join(tmp, 'datapad'))
        shutil.rmtree(dp, ignore_errors=True); shutil.copytree(os.path.join(tmp, 'datapad'), dp, ignore=shutil.ignore_patterns('.git'))
    shutil.copy(src, os.path.join(HERE, 'blueprints.json'))
    py('build_imgs.py')


def images_stale():
    """True when imgdata.json was built from a different wiki cache than the current one."""
    p = os.path.join(HERE, 'imgdata.json')
    if not os.path.exists(p): return True
    return json.load(open(p, encoding='utf-8')).get('wsig') != wiki_sig(HERE)


def main():
    cur = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))['v']
    changed = False
    with tempfile.TemporaryDirectory() as tmp:
        ver, date, src = latest_data(tmp)
        ver, date, src = own_game_data(ver, date, src)
        print('data in repo:', ver, date, '| site has:', cur)
        try:
            if ver != cur or FORCE:
                py('build_catalog.py', '--src', src, '--version', ver, '--date', date)
                images(tmp, src)
                changed = True
            # Wiki images for blueprints without an exact image (cached, so usually only new items are asked)
            if os.environ.get('SKIP_WIKI') != '1':
                r = subprocess.run([sys.executable, os.path.join(HERE, 'fetch_wiki_images.py')], capture_output=True, text=True)
                print(r.stdout.strip(), r.stderr.strip()[-500:])
                m = re.search(r'new images (\d+)', r.stdout)
                # rebuild when pictures were added OR removed/replaced (e.g. a filter dropped a wrong image)
                if (m and int(m.group(1)) > 0) or images_stale():
                    images(tmp, src); changed = True
            # where the items still without a proper picture are sold (for the photo list), cached weekly
            if os.environ.get('SKIP_SHOPS') != '1':
                r = subprocess.run([sys.executable, os.path.join(HERE, 'fetch_shops.py')], capture_output=True, text=True)
                print(r.stdout.strip()[-1500:], r.stderr.strip()[-500:])
        finally:
            shutil.rmtree(os.path.join(HERE, 'datapad'), ignore_errors=True)
            if os.path.exists(os.path.join(HERE, 'blueprints.json')): os.remove(os.path.join(HERE, 'blueprints.json'))
    # PTU
    pdir = os.path.join(HERE, 'ptu'); pbp = os.path.join(pdir, 'blueprints.json'); pv = os.path.join(pdir, 'version.txt')
    ptu_out = os.path.join(SITE, 'data', 'ptu.json')
    if os.path.exists(pbp) and os.path.exists(pv):
        pver = open(pv, encoding='utf-8').read().strip().splitlines()[0]
        old = json.load(open(ptu_out, encoding='utf-8')) if os.path.exists(ptu_out) else {}
        live_now = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))['v']
        pp, lp = parse_version(pver), parse_version(live_now)
        if pp and lp and pp[2] <= lp[2]:
            print('PTU build is not newer than LIVE data -> PTU data cleared'); py('build_ptu.py', '--clear')
        elif changed or old.get('version') != pver or old.get('live') != live_now or FORCE:
            py('build_ptu.py', '--src', pbp, '--version', pver, '--date', run('git', 'log', '-1', '--format=%cs', '--', pbp, cwd=ROOT) or '')
    elif os.path.exists(ptu_out):
        py('build_ptu.py', '--clear')
    # Always rebuild the page from tools/kiosk_src.html + catalog + imgdata, so edits to the
    # source (by you or by Claude) are published without ever touching the images.
    before = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read() if os.path.exists(os.path.join(SITE, 'index.html')) else ''
    py('build.py', os.path.join(SITE, 'index.html'))
    if open(os.path.join(SITE, 'index.html'), encoding='utf-8').read() != before: changed = True
    if changed or FORCE:
        sw = os.path.join(SITE, 'sw.js'); s = open(sw, encoding='utf-8').read()
        nv = json.load(open(os.path.join(HERE, 'catalog.json'), encoding='utf-8'))['v']
        s = re.sub(r'const VERSION = "[^"]*";', f'const VERSION = "bp-{nv}";', s); open(sw, 'w', encoding='utf-8').write(s)
    py('build_photo_list.py')
    py('check_versions.py')
    print('DONE', 'rebuilt' if changed else 'no data change')


if __name__ == '__main__':
    main()
