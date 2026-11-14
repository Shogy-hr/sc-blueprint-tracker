#!/usr/bin/env python3
"""Build labels/index.html (Label Forge) from tools/labels_src.html, borrowing the site chrome
(fonts, colours, header, flags, footer styles) from the home page so both stay in step."""
import os, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
home = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
css = home[home.index('<style>') + 7:home.index('</style>')]
keep = []
for line in css.split('\n'):
    if re.match(r'^(@font-face|:root|\*\{|html|body|\.frame|header|\.logo|\.sp\{|\.flags|footer|\.hnote)', line):
        keep.append(line.replace('url(assets/', 'url(../assets/'))
keep.append('@media (max-width:760px){body{padding:6px}.frame{padding:12px;box-shadow:0 0 0 3px #1b1c1d}.logo b{font-size:24px}.logo-img{width:50px;height:50px}.sp{display:none}.hello h1{font-size:24px}.vt td:nth-child(4){display:none}}')
m = re.search(r'var FLAGS=\{.*?\};', home, re.S)
src = open(os.path.join(HERE, 'labels_src.html'), encoding='utf-8').read()
out = src.replace('/*BASECSS*/', '\n'.join(keep)).replace('/*FLAGS*/', m.group(0))
os.makedirs(os.path.join(ROOT, 'labels'), exist_ok=True)
open(os.path.join(ROOT, 'labels', 'index.html'), 'w', encoding='utf-8').write(out)
print('labels/index.html', len(out), 'bytes')
