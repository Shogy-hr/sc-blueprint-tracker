#!/usr/bin/env python3
"""Rebuild galaktopedija/i18n.js from en.json (source texts) + hr/de/pl/fr/es.json (index -> translation).
To add a text: append the English string to en.json and its translations under the new index in each language file."""
import json,os
HERE=os.path.dirname(os.path.abspath(__file__))
S=json.load(open(os.path.join(HERE,'en.json'),encoding='utf-8'))
langs=['hr','de','pl','fr','es']
T={l:json.load(open(os.path.join(HERE,f'{l}.json'),encoding='utf-8')) for l in langs}
D={}
for i,en in enumerate(S):
    row=[T[l].get(str(i),'') for l in langs]
    if any(row): D[en]=row
out=os.path.join(HERE,'..','..','galaktopedija','i18n.js')
open(out,'w',encoding='utf-8').write('/* Galactopedia translations: English text -> [hr, de, pl, fr, es]. Empty = keep English.\n   Source: tools/gal_i18n (edit there, then run build.py). */\nwindow.GAL_I18N='+json.dumps(D,ensure_ascii=False,separators=(',',':'))+';\n')
print('entries',len(D))
