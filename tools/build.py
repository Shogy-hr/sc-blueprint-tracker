#!/usr/bin/env python3
"""Sastavlja index.html iz kiosk_src.html + catalog.json + imgdata.json."""
import os,sys
here=os.path.dirname(os.path.abspath(__file__))
src=open(os.path.join(here,'kiosk_src.html'),encoding='utf-8').read()
cat=open(os.path.join(here,'catalog.json'),encoding='utf-8').read().replace('<','\\u003c')
im=open(os.path.join(here,'imgdata.json'),encoding='utf-8').read().replace('<','\\u003c')
out=sys.argv[1] if len(sys.argv)>1 else os.path.join(here,'..','blueprints','index.html')
open(out,'w',encoding='utf-8').write(src.replace('__CATALOG__',cat).replace('__IMGS__',im))
print('OK ->',os.path.abspath(out))
