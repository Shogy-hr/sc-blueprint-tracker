"""Minimal reader for Star Citizen DataCore (Game2.dcb, version 8 and older 6/7 layout).
Only reads; record names, struct instances, pointers and references."""
import struct, sys
from functools import lru_cache
BOOL,I8,I16,I32,I64,U8,U16,U32,U64,STR,F32,F64,LOC,GUID,ENUM,CLS,SPTR,WPTR,REF=1,2,3,4,5,6,7,8,9,0xA,0xB,0xC,0xD,0xE,0xF,0x10,0x110,0x210,0x310
ISZ={BOOL:1,I8:1,I16:2,I32:4,I64:8,U8:1,U16:2,U32:4,U64:8,STR:4,F32:4,F64:8,LOC:4,GUID:16,ENUM:4,SPTR:8,WPTR:8,REF:20}
class DCB:
    def __init__(s, path, REC=None):
        b=s.b=open(path,'rb').read()
        h=struct.unpack_from('<30I',b,0)
        s.ver=h[1]
        if REC is None: REC=36 if s.ver>=8 else 32
        (nS,nP,nE,nM,nR,nB,nI8,nI16,nI32,nI64,nU8,nU16,nU32,nU64,nF,nD,nG,nSid,nL,nEn,nSp,nWp,nRef,nEo,tl,bl)=h[4:30]
        o=120
        s.structs=[struct.unpack_from('<IIHHI',b,o+16*i) for i in range(nS)]; o+=16*nS
        s.props=[struct.unpack_from('<IHHHH',b,o+12*i) for i in range(nP)]; o+=12*nP
        s.enums=[struct.unpack_from('<IHH',b,o+8*i) for i in range(nE)]; o+=8*nE
        s.maps=[struct.unpack_from('<II',b,o+8*i) for i in range(nM)]; o+=8*nM
        s.rec_off=o; s.nR=nR; s.REC=REC; o+=REC*nR
        def arr(n,sz):
            nonlocal o; r=o; o+=n*sz; return r
        s.a={}
        s.a[I8]=arr(nI8,1); s.a[I16]=arr(nI16,2); s.a[I32]=arr(nI32,4); s.a[I64]=arr(nI64,8)
        s.a[U8]=arr(nU8,1); s.a[U16]=arr(nU16,2); s.a[U32]=arr(nU32,4); s.a[U64]=arr(nU64,8)
        s.a[BOOL]=arr(nB,1); s.a[F32]=arr(nF,4); s.a[F64]=arr(nD,8); s.a[GUID]=arr(nG,16)
        s.a[STR]=arr(nSid,4); s.a[LOC]=arr(nL,4); s.a[ENUM]=arr(nEn,4)
        s.a[SPTR]=arr(nSp,8); s.a[WPTR]=arr(nWp,8); s.a[REF]=arr(nRef,20); s.eo=arr(nEo,4)
        s.text=o; o+=tl; s.blob=o; o+=bl
        s.data=o
        s.inst_off={}
        for cnt,si in s.maps:
            s.inst_off[si]=(o,cnt); o+=cnt*s.ssize(si)
        s.end=o
    def t(s,off): e=s.b.index(b'\0',s.text+off); return s.b[s.text+off:e].decode('utf-8','replace')
    def n(s,off): e=s.b.index(b'\0',s.blob+off); return s.b[s.blob+off:e].decode('utf-8','replace')
    @lru_cache(None)
    def allprops(s,si):
        name,par,pc,fp,_=s.structs[si]
        r=list(s.allprops(par)) if par!=0xFFFFFFFF else []
        return tuple(r+list(range(fp,fp+pc)))
    @lru_cache(None)
    def ssize(s,si):
        z=0
        for pi in s.allprops(si):
            _,psi,dt,ct,_=s.props[pi]
            if ct!=0: z+=8
            elif dt==CLS: z+=s.ssize(psi)
            else: z+=ISZ[dt]
        return z
    def sname(s,si): return s.n(s.structs[si][0])

def fmt_guid(a):
    # CIG GUID: two little-endian 64-bit halves
    h=a[7::-1].hex()+a[15:7:-1].hex()
    return f'{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}'
FMT={BOOL:'<?',I8:'<b',I16:'<h',I32:'<i',I64:'<q',U8:'<B',U16:'<H',U32:'<I',U64:'<Q',F32:'<f',F64:'<d'}
def _val(s,dt,o,psi):
    b=s.b
    if dt in FMT: return struct.unpack_from(FMT[dt],b,o)[0]
    if dt in (STR,LOC): return s.t(struct.unpack_from('<I',b,o)[0])
    if dt==ENUM: return s.t(struct.unpack_from('<I',b,o)[0])
    if dt==GUID: return fmt_guid(b[o:o+16])
    if dt in (SPTR,WPTR):
        si,ii=struct.unpack_from('<II',b,o)
        if si==0xFFFFFFFF: return None
        return ('ptr' if dt==SPTR else 'wptr',si,ii)
    if dt==REF:
        x=struct.unpack_from('<I',b,o)[0]; g=b[o+4:o+20]
        if g==bytes(16): return None
        return ('ref',fmt_guid(g))
    raise ValueError(dt)
DCB.val=_val
def _inst(s,si,ii,depth=0,follow=True):
    base,cnt=s.inst_off[si]
    return s.read(si,base+ii*s.ssize(si),depth,follow)
def _read(s,si,o,depth=0,follow=True):
    r={'_t':s.sname(si)}
    b=s.b
    for pi in s.allprops(si):
        pn,psi,dt,ct,_=s.props[pi]; name=s.n(pn)
        if ct!=0:
            cnt,first=struct.unpack_from('<II',b,o); o+=8
            if dt==CLS: v=[s.inst(psi,first+k,depth+1,follow) for k in range(cnt)]
            else:
                sz=ISZ[dt]; base=s.a[dt]
                v=[s.val(dt,base+(first+k)*sz,psi) for k in range(cnt)]
                if dt==SPTR and follow: v=[s.inst(x[1],x[2],depth+1,follow) if x else None for x in v]
        elif dt==CLS:
            v=s.read(psi,o,depth+1,follow); o+=s.ssize(psi)
        else:
            v=s.val(dt,o,psi); o+=ISZ[dt]
            if dt==SPTR and follow and v: v=s.inst(v[1],v[2],depth+1,follow)
        r[name]=v
    return r
DCB.inst=_inst; DCB.read=_read
def _records(s):
    out=[]
    for i in range(s.nR):
        o=s.rec_off+s.REC*i
        nm,fn,tg,si=struct.unpack_from('<IIII',s.b,o)
        g=s.b[o+s.REC-20:o+s.REC-4]; ii,oi=struct.unpack_from('<HH',s.b,o+s.REC-4)
        out.append(dict(name=s.n(nm),file=s.t(fn),si=si,guid=fmt_guid(g),ii=ii,raw=g))
    return out
DCB.records=_records
