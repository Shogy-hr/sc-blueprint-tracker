#!/usr/bin/env python3
"""Sastavlja index.html iz kiosk_src.html + catalog.json + imgdata.json."""
import os,sys
here=os.path.dirname(os.path.abspath(__file__))
src=open(os.path.join(here,'kiosk_src.html'),encoding='utf-8').read()
cat=open(os.path.join(here,'catalog.json'),encoding='utf-8').read().replace('<','\\u003c')
im=open(os.path.join(here,'imgdata.json'),encoding='utf-8').read().replace('<','\\u003c')
out=sys.argv[1] if len(sys.argv)>1 else os.path.join(here,'..','blueprints','index.html')
import json,time
sp=os.path.join(here,'shops','index.json');shops={'i':{},'d':''}
if os.path.exists(sp):
    sd=json.load(open(sp,encoding='utf-8'));names={i[0] for i in json.loads(cat.replace('\\u003c','<'))['items']}
    last=0
    for e in sd.values():
        L=sorted(e.get('shops') or [],key=lambda x:(x['p'],x['l']))
        if L and e.get('n') in names: shops['i'][e['n']]=[[x['t'],x['l'],x['s'],x['p'],x['d']] for x in L[:12]]
        last=max(last,e.get('checked') or 0)
    shops['d']=time.strftime('%Y-%m-%d',time.gmtime(last)) if last else ''
sh=json.dumps(shops,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
open(out,'w',encoding='utf-8').write(src.replace('__CATALOG__',cat).replace('__IMGS__',im).replace('__SHOPS__',sh))
print('OK ->',os.path.abspath(out))
