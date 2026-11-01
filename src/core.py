"""Read-only Sparking ZERO resources; all generated files live under the app root."""
from __future__ import annotations
import copy, ctypes, hashlib, io, json, math, os, re, shutil, struct, subprocess, tempfile, threading, time, wave
from pathlib import Path
import numpy as np
import audio_levels
import audio_variations
import audio_format_verification
import cpu_jobs
from package_key import encryption_key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

APP = Path(__file__).resolve().parent.parent
CREATE_NO_WINDOW = 0x08000000
MAIN_HCA_KEY = 13238534807163085345
SILENCE_DURATION = 0.5
DEFAULTS = {"project":"", "game":"", "pak_key_file":"", "unreal_editor":"", "ui_language":"en", "function_language":"en", "voice_text_language":"en", "cpu_mode":"auto"}
def character_names(cfg=None,language='pt'):
    """Read official names for the requested game language; no worksheet guessing."""
    import game_characters
    names=game_characters.bundled(language)
    try:names.update(game_characters.load(cfg or config(),language)['names'])
    except (OSError,ValueError,KeyError):pass
    return names

def character_id(bank_name):
    match=re.fullmatch(r"BTLCV_(\d{4}_\d{2})(?:_[A-Z])?_(?:US|JP)",bank_name)
    return match.group(1) if match else ""

def config():
    p=APP/"settings.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else DEFAULTS.copy()
def owned(path):
    p=Path(path).resolve()
    if not p.is_relative_to(APP): raise ValueError("Os arquivos gerados devem ficar dentro da pasta do aplicativo.")
    return p
_json_write_lock=threading.RLock()

def write_json(path, obj):
    p=owned(path);p.parent.mkdir(parents=True,exist_ok=True)
    payload=json.dumps(obj,ensure_ascii=False,indent=2)
    fd,name=tempfile.mkstemp(prefix=p.name+'.',suffix='.tmp',dir=p.parent)
    tmp=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:stream.write(payload)
        with _json_write_lock:
            for attempt in range(4):
                try:os.replace(tmp,p);break
                except PermissionError:
                    if attempt==3:raise
                    time.sleep(.02*(attempt+1))
    finally:tmp.unlink(missing_ok=True)
def run(args, cwd=None):
    args,options=cpu_jobs.subprocess_options(args)
    p=subprocess.run(args,cwd=str(owned(cwd or APP)),
        capture_output=True,creationflags=CREATE_NO_WINDOW,timeout=180,**options)
    if p.returncode: raise RuntimeError((p.stderr+p.stdout).decode("utf-8","replace")[-2500:])
    return p
def be(b,p,n): return int.from_bytes(b[p:p+n],"big")
def le(b,p,n): return int.from_bytes(b[p:p+n],"little")
def zstr(b,p):
    e=b.index(0,p);return bytes(b[p:e]).decode("utf-8","replace")

class UTF:
    widths=[1,1,2,2,4,4,8,8,4,8,4,8]
    def __init__(self,b,base=0):
        if b[base:base+4]!=b"@UTF": raise ValueError("Tabela CRI inválida.")
        self.b=b;self.base=base;self.size=be(b,base+4,4)+8
        self.rowoff=base+8+be(b,base+8,4)
        self.stroff=base+8+be(b,base+12,4)
        self.dataoff=base+8+be(b,base+16,4)
        self.name=zstr(b,self.stroff+be(b,base+20,4))
        self.ncols=be(b,base+24,2);self.rowlen=be(b,base+26,2);self.nrows=be(b,base+28,4)
        self.cols=[];p=base+32
        for i in range(self.ncols):
            flag=b[p];name=zstr(b,self.stroff+be(b,p+1,4));p+=5
            typ=flag&15;storage=flag&240
            self.cols.append((name,typ,storage,p))
            if storage==0x30:p+=self.widths[typ]
        self.rows=[];self.cells=[]
        for i in range(self.nrows):
            p=self.rowoff+i*self.rowlen;row={};cells={}
            for name,typ,storage,cp in self.cols:
                q=cp if storage==0x30 else p
                cells[name]=(q,typ,storage)
                if storage in (0,0x10): v=0
                elif typ==10:v=zstr(b,self.stroff+be(b,q,4))
                elif typ==11:v=(self.dataoff+be(b,q,4),be(b,q+4,4))
                elif typ in (8,9):v=struct.unpack_from(">f" if typ==8 else ">d",b,q)[0]
                else:v=be(b,q,self.widths[typ])
                row[name]=v
                if storage==0x50:p+=self.widths[typ]
            self.rows.append(row);self.cells.append(cells)
    def child(self, field):
        value=self.rows[0].get(field)
        return UTF(self.b,value[0]) if isinstance(value,tuple) and value[1] else None

class Awb:
    def __init__(self,b):
        if not b:raise ValueError("O AWB deste banco está vazio (0 bytes). Não há áudio original disponível neste arquivo.")
        if len(b)<16 or b[:4]!=b"AFS2":raise ValueError("AWB inválido.")
        self.b=b;self.count=le(b,8,4);self.offset_width=b[5];self.id_width=b[6]
        self.align=le(b,12,2);self.subkey=le(b,14,2)
        table=16+self.count*self.id_width
        self.header_len=table+(self.count+1)*self.offset_width
        self.ids=[le(b,16+i*self.id_width,self.id_width) for i in range(self.count)]
        self.offsets=[le(b,table+i*self.offset_width,self.offset_width) for i in range(self.count+1)]
        self.entries={}
        for i,id in enumerate(self.ids):
            start=((self.offsets[i]+self.align-1)//self.align)*self.align
            end=self.offsets[i+1]
            if start>end or end>len(b):raise ValueError("Offsets de AWB inválidos.")
            self.entries[id]=bytes(b[start:end])
    @property
    def key(self):
        return (MAIN_HCA_KEY*((self.subkey<<16)|((~self.subkey+2)&65535)))&((1<<64)-1)
    def rebuild(self, entries):
        if set(entries)!=set(self.ids):raise ValueError("IDs do AWB foram alterados.")
        header=bytearray(self.b[:16])
        for id in self.ids:header+=id.to_bytes(self.id_width,"little")
        first=self.header_len
        offsets=[first];payload=bytearray();cursor=first
        for id in self.ids:
            aligned=((cursor+self.align-1)//self.align)*self.align
            payload+=b"\0"*(aligned-cursor)+entries[id]
            cursor=aligned+len(entries[id]);offsets.append(cursor)
        for v in offsets:header+=v.to_bytes(self.offset_width,"little")
        return bytes(header+payload)

class Pak:
    def __init__(self,cfg,path=None):
        self.cfg=cfg;self.official_default=path is None
        self.path=Path(path) if path is not None else Path(cfg["game"])/"SparkingZERO/Content/Paks/pakchunk0-Windows.pak"
        self.f=self.path.open("rb")
        self.key=encryption_key(cfg)
        self.f.seek(-512,2);footer=self.f.read(512);m=footer.index(b"\xe1\x12\x6f\x5a")
        self.version=le(footer,m+4,4)
        if self.version!=11:raise ValueError("Versão de pacote não suportada: "+str(self.version))
        off=le(footer,m+8,8);size=le(footer,m+16,8)
        index=self.decrypt(self.read(off,size))
        if hashlib.sha1(index).digest()!=footer[m+24:m+44]:raise ValueError("Não foi possível ler o pacote com a chave integrada. Confira a instalação do jogo e a integridade dos arquivos.")
        r=io.BytesIO(index)
        def u(n):return int.from_bytes(r.read(n),"little")
        def fs():
            n=struct.unpack("<i",r.read(4))[0]
            return r.read(abs(n)*(2 if n<0 else 1)).decode("utf-16le" if n<0 else "utf-8").rstrip("\0")
        self.mount=fs();self.count=u(4);u(8)
        if u(4):r.read(36)
        if not u(4):raise ValueError("Pacote sem índice de diretórios.")
        off=u(8);size=u(8);digest=r.read(20)
        self.encoded=r.read(u(4))
        directory=self.decrypt(self.read(off,size))
        if hashlib.sha1(directory).digest()!=digest:raise ValueError("Hash do diretório inválido.")
        r=io.BytesIO(directory);self.entries={}
        for i in range(u(4)):
            folder=fs()
            for j in range(u(4)):
                name=fs();loc=u(4)
                self.entries[self.mount+folder+name]=loc
        self.dll=ctypes.CDLL(str(APP/"Tools/oo2core_9_win64.dll"))
        self.decomp=self.dll.OodleLZ_Decompress
        self.decomp.restype=ctypes.c_int64
        self.decomp.argtypes=[ctypes.c_void_p,ctypes.c_int64,ctypes.c_void_p,ctypes.c_int64,
            ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_int64,
            ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int64,ctypes.c_int]
        self.lock=threading.Lock()
    def __del__(self):
        handle=getattr(self,"f",None)
        if handle is not None:handle.close()
    def decrypt(self,b):
        d=Cipher(algorithms.AES(self.key),modes.ECB()).decryptor()
        return d.update(b)+d.finalize()
    def read(self,off,size):
        self.f.seek(off);b=self.f.read(size)
        if len(b)!=size:raise ValueError("Pacote incompleto.")
        return b
    def bank(self,name):
        if self.official_default:
            import game_references
            return game_references.bank_audio(self.cfg,name)
        return self.file(self.mount+"SparkingZERO/Content/CriWareData/"+name+".awb")
    def file(self,target):
        if target not in self.entries:raise ValueError("Arquivo não encontrado no jogo: "+target)
        with self.lock:
            r=io.BytesIO(self.encoded);r.seek(self.entries[target])
            def u(n):return int.from_bytes(r.read(n),"little")
            flags=u(4);blocksize=(flags&63)*2048
            if flags&63==63:blocksize=u(4)
            method=(flags>>23)&63
            off=u(4 if flags&(1<<31) else 8)
            rawsize=u(4 if flags&(1<<30) else 8)
            size=u(4 if flags&(1<<29) else 8) if method else rawsize
            encrypted=bool(flags&(1<<22));nblocks=(flags>>6)&65535
            # UE5.1 omits the packed block size for single-block entries.
            if nblocks==1:blocksize=rawsize
            header=53+(4+16*nblocks if method else 0)
            if not method:
                b=self.read(off+header,((size+15)//16)*16 if encrypted else size)
                return self.decrypt(b)[:size] if encrypted else b
            if method!=1 or encrypted:raise ValueError("Compressão de áudio não suportada.")
            hdr=self.read(off,header);parts=[]
            if le(hdr,48,4)!=nblocks:raise ValueError("Quantidade de blocos inválida.")
            for i in range(nblocks):
                a=le(hdr,52+i*16,8);z=le(hdr,60+i*16,8)
                packed=self.read(off+a,z-a);want=min(blocksize,rawsize-sum(map(len,parts)))
                dst=ctypes.create_string_buffer(want)
                got=self.decomp(packed,len(packed),dst,want,1,1,0,None,0,None,None,None,0,3)
                if got!=want:raise ValueError("Não foi possível descompactar o áudio.")
                parts.append(dst.raw)
            result=b"".join(parts)
            if len(result)!=rawsize:raise ValueError("Não foi possível descompactar o áudio.")
            return result

def cooked_summary(data):
    """Read legacy UE5 package summary, including custom version entries."""
    if len(data)<40 or data[:4]!=b"\xc1\x83\x2a\x9e" or struct.unpack_from("<i",data,4)[0]!=-8:
        raise ValueError("Cabeçalho Unreal cooked não reconhecido.")
    versions=le(data,24,4)
    if versions>1024:raise ValueError("Tabela de versões Unreal inválida.")
    base=28+versions*20
    if base+8>len(data):raise ValueError("Cabeçalho Unreal incompleto.")
    header_size=le(data,base,4)
    length=struct.unpack_from("<i",data,base+4)[0]
    summary=base+12+abs(length)*(2 if length<0 else 1)
    if not 0<header_size<=len(data) or summary+32>header_size:
        raise ValueError("Tamanho do cabeçalho Unreal inválido.")
    return header_size,summary

def cooked_exports(data):
    header,summary=cooked_summary(data)
    nameoff=le(data,summary+4,4)
    candidates=[]
    # Cooked and FModel summaries differ in optional localization/UE5 fields.
    for at in range(summary+8,min(nameoff-7,header-7)):
        count,offset=le(data,at,4),le(data,at+4,4)
        if not 1<=count<=256 or not nameoff<=offset or offset+count*96>header:continue
        entries=[offset+i*96 for i in range(count)]
        cursor=header
        for entry in entries:
            size,start=le(data,entry+28,8),le(data,entry+36,8)
            if start!=cursor or not 0<size<2**32:break
            cursor+=size
        else:candidates.append(entries)
    if len(candidates)!=1:raise ValueError("Mapa de exports Unreal não identificado com segurança.")
    return candidates[0]

def embedded_asset_supported(data):
    if b"@UTF" not in data:return False
    if data[:4]==b"\xc1\x83\x2a\x9e":
        header,_=cooked_summary(data)
        return data.find(b"@UTF")>=header
    return len(data)>=40 and le(data,36,4)-le(data,32,4)==72

def standalone_acb(data):
    """The reference extractor copies the UTF table plus trailing padding/footer."""
    root=UTF(data)
    trailing=data[root.size:]
    if trailing.endswith(b"\xc1\x83\x2a\x9e"):trailing=trailing[:-4]
    if any(trailing):raise ValueError("O ACB contém dados adicionais não reconhecidos.")
    return bytes(data[:root.size])

def asset_names(path):
    b=Path(path).read_bytes()
    if b[:4]==b'\0'*4:
        # UE5.1 FZenPackageSummary (44 bytes), followed by LoadNameBatch.
        start=44;count=le(b,start,4);size=le(b,start+4,4)
        headers=start+16+count*8;strings=headers+count*2;end=strings+size
        if not 0<count<65536 or end>le(b,24,4) or end>len(b):raise ValueError('Mapa de nomes Zen inválido.')
        names=[];cursor=strings
        for i in range(count):
            h=b[headers+i*2:headers+i*2+2];wide=bool(h[0]&128);length=((h[0]&127)<<8)|h[1]
            length*=2 if wide else 1
            if cursor+length>end:raise ValueError('Nome Zen truncado.')
            names.append(b[cursor:cursor+length].decode('utf-16le' if wide else 'utf-8'));cursor+=length
        if cursor!=end:raise ValueError('Tamanho do mapa de nomes Zen inválido.')
        return names
    _,off=cooked_summary(b)
    count=le(b,off,4);p=le(b,off+4,4);names=[]
    for i in range(count):
        n=struct.unpack_from("<i",b,p)[0];p+=4
        size=abs(n)*(2 if n<0 else 1)
        names.append(b[p:p+size].decode("utf-16le" if n<0 else "utf-8").rstrip("\0"))
        p+=size+4
    return names
def pattern_functions(cfg):
    import game_references
    path,b=game_references.pattern(cfg)
    names=asset_names(path)
    if b[:6]!=b"\x00\x03\x00\x00\x00\x00":raise ValueError("Cabeçalho de funções não suportado.")
    count=le(b,6,4);p=10;result={}
    for i in range(count):
        idx=le(b,p,4);p+=8;h=le(b,p,2);p+=2
        if not h&256 or h>>9!=2:raise ValueError("Registro de função não suportado.")
        mask=b[p] if h&128 else 0
        if h&128:p+=1
        values=[]
        for j in range(2):
            values.append(0 if mask&(1<<j) else le(b,p,4))
            if not mask&(1<<j):p+=4
        result[values[1]]=names[idx]
    return result

ENGLISH_DESCRIPTIONS={
    "小やられ":"Light damage","中やられ":"Medium damage","大やられ":"Heavy damage",
    "小ガード":"Light guard","中ガード":"Medium guard","大ガード":"Heavy guard",
    "ボディーブローやられ":"Body blow damage","吹き飛びやられ":"Knockback damage",
    "UBやられ_恐怖":"Ultimate blast damage / fear","UBやられ_叫び":"Ultimate blast damage / scream",
    "カウンター成立やられ":"Counter hit reaction","気絶やられ":"Stun reaction",
    "ガードクラッシュ":"Guard break","ジャンプ":"Jump","スキル１":"Skill 1","スキル２":"Skill 2",
    "インパクト勝利":"Impact victory","ステップ":"Step","ドラゴンダッシュ":"Dragon dash",
    "交代登場":"Switch entrance","Zバーストダッシュ":"Z burst dash","Sparking！チャージ":"Sparking charge",
}
ENGLISH_DESCRIPTIONS.update({'小打撃': 'Light attack',
 '中打撃': 'Medium attack',
 '中打撃２': 'Medium attack variation',
 '大打撃': 'Heavy attack',
 'ライトニングアタック1P': 'Lightning attack',
 '舞空脚': 'Bukukyaku attack',
 'ローリングハンマー': 'Rolling hammer',
 'エネルギーストーム': 'Energy storm',
 '奇襲': 'Surprise attack',
 'バーストラッシュ': 'Burst rush',
 '体勢を直す（仰け反り）': 'Recovery from leaning back',
 '体勢を直す（起き上がり）': 'Recovery from knockdown',
 '体勢を直す（受け身）': 'Breakfall recovery',
 'バウンド': 'Bounce impact reaction',
 '壁激突': 'Wall collision reaction',
 'カウンター成立させる': 'Successful counter',
 'ドラゴンホーミング': 'Dragon homing',
 '息切れ': 'Exhaustion / out of breath',
 '怯み': 'Flinch reaction (original tag: IMPATIENCE)',
 'ソニックスウェイ1PST': 'Sonic sway start',
 'ソニックスウェイ1PFN': 'Sonic sway finish',
 'つかみ': 'Throw / grab',
 'つかみかかり': 'Grab attempt',
 'つかまれ': 'Being grabbed',
 'ダウンつかみかかり': 'Grounded grab attempt',
 'ダウンつかみ': 'Grounded throw / grab',
 'ダウンつかまれ': 'Being grabbed while down',
 'リベンジカウンター発生': 'Revenge counter start',
 '断末魔': 'Death cry / final scream',
 'Zサーチ_解除': 'Z search: target lost',
 'Zサーチ_索敵': 'Z search: searching',
 'Zサーチ_感知': 'Z search: sensing',
 'Zサーチ_発見': 'Z search: target found',
 '交代退場': 'Switch exit',
 '変身_IN': 'Transformation: IN',
 '変身_OT': 'Transformation: OT',
 'actFSN3_パートナーリップシンク用': 'Fusion partner lip sync',
 '気溜め': 'Energy charge',
 'Sparking！': 'Sparking activation',
 '投げ抜けられ': 'Throw escaped by opponent',
 '投げ抜け': 'Throw escape',
 '残体力１０％以下になった': 'Health at or below 10%',
 '残体力６０％以下になった': 'Health at or below 60%',
 'タイム残りわずか（優勢）': 'Time running low while ahead',
 'タイム残りわずか（劣勢）': 'Time running low while behind',
 '汎用感情ボイス\u3000強がり': 'Emotion: bravado (original tag: REGRETTABLE)',
 '汎用感情ボイス\u3000焦り': 'Emotion: impatience / anxiety',
 '汎用感情ボイス\u3000煽り': 'Emotion: provocation',
 '汎用感情ボイス\u3000驚き': 'Emotion: surprise',
 '汎用感情ボイス\u3000気合い': 'Emotion: enthusiasm / fighting spirit',
 '汎用感情ボイス\u3000哀': 'Emotion: sorrow',
 '汎用感情ボイス\u3000楽': 'Emotion: joy',
 '汎用感情ボイス\u3000喜': 'Emotion: happiness',
 '汎用感情ボイス\u3000恐怖': 'Emotion: fear',
 '汎用感情ボイス\u3000怒': 'Emotion: anger',
 'ブラストインパクト IN': 'Blast impact: start',
 'ブラストインパクト Battle': 'Blast impact: clash',
 'ブラストインパクト Battle（優勢）': 'Blast impact: clash while ahead',
 'ブラストインパクト Battle（劣勢）': 'Blast impact: clash while behind',
 'ブラストインパクト FN_ATK': 'Blast impact: winning attack',
 'パワーインパクト IN': 'Power impact: start',
 'パワーインパクト Battle': 'Power impact: clash',
 'パワーインパクト Battle（優勢）': 'Power impact: clash while ahead',
 'パワーインパクト Battle（劣勢）': 'Power impact: clash while behind',
 'パワーインパクト FN_ATK': 'Power impact: winning attack',
 'スピードインパクト IN': 'Speed impact: start',
 'スピードインパクト Battle': 'Speed impact: clash',
 'スピードインパクト Battle（優勢）': 'Speed impact: clash while ahead',
 'スピードインパクト Battle（劣勢）': 'Speed impact: clash while behind',
 'スピードインパクト FN_ATK': 'Speed impact: winning attack',
 'クラッシュインパクト IN': 'Crash impact: start',
 'クラッシュインパクト ATK': 'Crash impact: attack',
 'クラッシュインパクト GRD': 'Crash impact: guard',
 'クラッシュインパクト DMG': 'Crash impact: damage',
 'クラッシュインパクト FN_ATK': 'Crash impact: winning attack',
 '小打撃 ZjMWU9Tx7Xi5': 'Light attack (original variant)',
 '小打撃 PLz3QqaVZQdZ': 'Light attack (original variant)',
 '中打撃 ZjMWU9Tx7Xi5': 'Medium attack (original variant)',
 '中打撃 PLz3QqaVZQdZ': 'Medium attack (original variant)',
 'クラッシュインパクト ATK\u30003nCnEA8y7vtTn': 'Crash impact: attack (original variant)',
 'クラッシュインパクト GRD\u30003nCnEA8y7vtTn': 'Crash impact: guard (original variant)'})

def description(original):
    return ENGLISH_DESCRIPTIONS.get(original,"Unclassified")

_original_cache_guard=threading.Lock()
_original_cache_locks={}

def original_cache_lock(path):
    key=str(Path(path).resolve()).casefold()
    with _original_cache_guard:return _original_cache_locks.setdefault(key,threading.Lock())

def _checked_bank_read(method):
    # Runtime import avoids the core/reference parser import cycle.
    import functools
    @functools.wraps(method)
    def read(self,cfg,*args,**kwargs):
        import live_voice_references
        with live_voice_references.bank_read_scope(cfg):return method(self,cfg,*args,**kwargs)
    return read

class Bank:
    @_checked_bank_read
    def __init__(self,cfg,pak,name,source=None):
        self.external=bool(source);self.source=source;self.file_kind="cooked"
        self.name=name;self.cfg=cfg;self.pak=pak;self.language=name[-2:]
        import game_installation
        self.game_identity=game_installation.identity(cfg) if not source else None
        import game_references
        self.asset=Path(source["asset"]) if source else game_references.asset(cfg,f"SS/Sounds/Battle_VOICE/{self.language}/{name}.uasset")
        self.uexp_path=Path(source["uexp"]) if source and source.get("uexp") else self.asset.with_suffix(".uexp")
        if self.uexp_path.exists():
            self.uexp=self.uexp_path.read_bytes()
            if source and source.get("import_kind")=="inline_cooked":self.file_kind="inline_cooked"
        elif source or self.asset.read_bytes()[:4]==b"\0"*4:
            self.file_kind="zen";self.uexp=self.asset.read_bytes()
            exportmap=le(self.uexp,32,4)
            if le(self.uexp,36,4)-exportmap!=72:
                raise ValueError("O asset precisa do .uexp correspondente, ou ser um .uasset Zen completo suportado.")
        else:raise ValueError("Arquivo .uexp não encontrado.")
        try:self.acb_start=self.uexp.index(b"@UTF")
        except ValueError:raise ValueError("O asset selecionado não contém um ACB atribuído.")
        root_full=UTF(self.uexp,self.acb_start)
        self.acb=bytes(self.uexp[self.acb_start:self.acb_start+root_full.size])
        self.root=UTF(self.acb)
        if source and source.get("acb") and standalone_acb(Path(source["acb"]).read_bytes())!=self.acb:
            raise ValueError("O .acb selecionado difere do ACB atribuído ao asset. Selecione o conjunto correspondente.")
        self.stream_bytes=Path(source["awb"]).read_bytes() if source else pak.bank(name);self.stream=Awb(self.stream_bytes)
        hash_table=self.root.child("StreamAwbHash")
        blob=hash_table.rows[0]["Hash"]
        expected=self.acb[blob[0]:blob[0]+blob[1]]
        self.compatible=hashlib.md5(self.stream_bytes).digest()==expected
        ab=self.root.rows[0].get("AwbFile")
        self.memory=Awb(self.acb[ab[0]:ab[0]+ab[1]]) if ab and ab[1] else None
        self.tables={k:self.root.child(k) for k in ("CueTable","CueNameTable","WaveformTable",
            "SynthTable","SequenceTable","TrackTable","TrackEventTable","CommandTable")}
        try:self.functions=pattern_functions(cfg)
        except (FileNotFoundError,ValueError):
            if not source:raise
            self.functions={}
        self.rows=[];self.wave_rows={}
        waveform=self.tables["WaveformTable"]
        for i,w in enumerate(waveform.rows):
            streamed=bool(w["Streaming"]);id=w["StreamAwbId"] if streamed else w["MemoryAwbId"]
            key=("S" if streamed else "M")+str(id)
            if key not in self.wave_rows:
                row={"key":key,"id":id,"streaming":streamed,"wave_indices":[],"cue_names":[],
                    "cue_ids":[],"functions":[],"pattern_names":[],"rate":w["SamplingRate"],"channels":w["NumChannels"],
                    "samples":w["NumSamples"]}
                self.wave_rows[key]=row;self.rows.append(row)
            self.wave_rows[key]["wave_indices"].append(i)
        cues=self.tables["CueTable"];names=self.tables["CueNameTable"]
        self.unresolved=[]
        for entry in names.rows:
            ci=entry["CueIndex"];cue=cues.rows[ci]
            resolved=self.resolve(cue["ReferenceType"],cue["ReferenceIndex"],set())
            if not resolved and cue["Length"]!=0:self.unresolved.append(entry["CueName"])
            for wi in resolved:
                w=waveform.rows[wi];key=("S" if w["Streaming"] else "M")+str(w["StreamAwbId"] if w["Streaming"] else w["MemoryAwbId"])
                row=self.wave_rows[key];row["cue_names"].append(entry["CueName"]);row["cue_ids"].append(cue["CueId"])
                fn=self.functions.get(cue["CueId"])
                if fn and fn not in row["pattern_names"]:row["pattern_names"].append(fn)
                if entry["CueName"].startswith("PTN_") and entry["CueName"] not in row["functions"]:row["functions"].append(entry["CueName"])
        for row in self.rows:
            row["cue_names"]=list(dict.fromkeys(row["cue_names"]));row["cue_ids"]=list(dict.fromkeys(row["cue_ids"]))
            row["filename"]=f'{row["id"]:05d}'+("_streaming" if row["streaming"] else "")+".hca"
            row["duration"]=row["samples"]/max(1,row["rate"])
            row["english"]=[description(fn) for fn in row["pattern_names"]]
            awb=self.stream if row["streaming"] else self.memory
            row["available"]=bool(awb and row["id"] in awb.entries)
        import voice_context
        voice_context.attach(self.rows,self.name,self.acb,cfg)
        import attack_context
        attack_context.attach(self.name,self.acb,self.rows,cfg)
        import audio_function_equivalences
        audio_function_equivalences.attach(self)
        import voice_origin_details
        voice_origin_details.attach(self)
        import game_installation
        if not source and self.game_identity!=game_installation.identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a abertura do banco. Aguarde a atualização terminar e tente novamente.')
        self.cache=owned(APP/"Cache"/name/hashlib.sha256(self.acb+self.stream_bytes).hexdigest()[:16])
        self.cache.mkdir(parents=True,exist_ok=True)
    def blob(self,blob):return self.acb[blob[0]:blob[0]+blob[1]]
    def resolve(self,typ,idx,seen):
        key=(typ,idx)
        if key in seen:return set()
        seen=seen|{key}
        if typ==1:return {idx} if idx<len(self.tables["WaveformTable"].rows) else set()
        if typ==7:
            # CRI insideLinkSequence stores a SequenceTable index, not a CueTable index.
            # Composite voices (Mighty Mask) use it to chain the individual speakers.
            return self.resolve(3,idx,seen)
        if typ==2:
            t=self.tables["SynthTable"]
            if not t or idx>=len(t.rows):return set()
            b=self.blob(t.rows[idx]["ReferenceItems"]);out=set()
            for p in range(0,len(b),4):out|=self.resolve(be(b,p,2),be(b,p+2,2),seen)
            return out
        if typ==3:
            t=self.tables["SequenceTable"]
            if not t or idx>=len(t.rows):return set()
            b=self.blob(t.rows[idx]["TrackIndex"]);out=set()
            for p in range(0,len(b),2):out|=self.track(be(b,p,2),seen)
            return out
        return set()
    def track(self,idx,seen):
        tracks=self.tables["TrackTable"];events=self.tables["TrackEventTable"] or self.tables["CommandTable"]
        if not tracks or not events or idx>=len(tracks.rows):return set()
        ei=tracks.rows[idx]["EventIndex"]
        if ei>=len(events.rows):return set()
        b=self.blob(events.rows[ei]["Command"]);p=0;out=set()
        while p+3<=len(b):
            opcode=be(b,p,2);n=b[p+2];data=b[p+3:p+3+n];p+=3+n
            if opcode==2000 and len(data)>=4:out|=self.resolve(be(data,0,2),be(data,2,2),seen)
        return out
    def original(self,row):
        wav=self.cache/(row["key"]+"_original.wav")
        # Different Bank instances can share this cache (preview, levels, project writer).
        with original_cache_lock(wav):
            awb=self.stream if row["streaming"] else self.memory
            if not awb or row["id"] not in awb.entries:raise ValueError("Áudio original indisponível nesta versão do jogo.")
            encoded=awb.entries[row["id"]]
            def valid(path):
                try:
                    with wave.open(str(path),"rb") as audio:
                        actual=(audio.getframerate(),audio.getnchannels(),audio.getnframes())
                        # Truncated cache files must not be mistaken for complete WAVs.
                        complete=len(audio.readframes(audio.getnframes()))==audio.getnframes()*audio.getnchannels()*audio.getsampwidth()
                    if not complete or actual[:2]!=(row["rate"],row["channels"]):return False
                    if actual[2]==row["samples"]:return True
                    # Some official M0 banks declare 2389 samples; HCA contains 2390.
                    # Accept exactly one sample only when independently confirmed by HCA.
                    import bank_migration
                    return abs(actual[2]-row["samples"])==1 and actual==bank_migration.hca_format(encoded)
                except (OSError,ValueError,EOFError,wave.Error):return False
            if wav.exists() and valid(wav):return wav
            work=self.cache/row["key"];work.mkdir(exist_ok=True)
            hca=work/row["filename"];hca.write_bytes(encoded)
            (work/".hcakey").write_bytes(awb.key.to_bytes(8,"big"))
            pending=work/("decoded_"+os.urandom(5).hex()+".wav")
            try:
                run([APP/"Tools/vgmstream-cli/vgmstream-cli.exe","-i",hca,"-o",pending],work)
                if not valid(pending):
                    raise ValueError("O áudio original não corresponde aos metadados da referência.")
                # Validation closes the WAV before Windows is asked to move/delete it.
                for attempt in range(5):
                    try:os.replace(pending,wav);break
                    except PermissionError:
                        if attempt==4:raise
                        time.sleep(.05*(attempt+1))
            finally:pending.unlink(missing_ok=True)
            return wav


def imported_is_original(bank,row):
    """Only verified equality can classify an external voice as original."""
    if not bank.external:return False
    source=bank.source or {};key=row['key']
    return (source.get('audio_comparison',{}).get(key)=='unchanged'
            or key in source.get('unchanged_original_keys',[])
            or source.get('audio_similarity',{}).get(key,{}).get('exact') is True)

def imported_can_preview(bank,row,allow_uncertain=True):
    """Allow listening to unverified audio without treating it as a replacement."""
    if not bank.external or imported_is_original(bank,row):return False
    source=bank.source or {};key=row['key']
    status=source.get('audio_similarity',{}).get(key,{}).get('status','uncertain')
    return status=='different' or (allow_uncertain and status=='uncertain')

def preserve_unreplaced(bank,row,requested=False):
    """Never mute imported audio unless it was confirmed identical to the reference."""
    if requested:return True
    if not bank.external:return False
    source=getattr(bank,'source',None) or {}
    return row['key'] not in source.get('unchanged_original_keys',[])

def reference_row(bank,reference,row):
    if reference is None:return None
    if not bank.external:return reference.wave_rows.get(row['key'])
    source=getattr(bank,'source',None) or {}
    if source.get('audio_comparison_reference')!=reference.name:return None
    key=source.get('reference_wave_map',{}).get(row['key'])
    return reference.wave_rows.get(key) if key else None

def same_pcm(a,b):
    """Exact decoded audio comparison; lossy differences remain protected."""
    with wave.open(str(a),'rb') as x,wave.open(str(b),'rb') as y:
        if (x.getnchannels(),x.getsampwidth(),x.getframerate(),x.getnframes())!=(y.getnchannels(),y.getsampwidth(),y.getframerate(),y.getnframes()):return False
        while True:
            chunk=x.readframes(65536)
            if chunk!=y.readframes(65536):return False
            if not chunk:return True

def classify_imported_audio(bank,reference):
    if not bank.external:return
    unchanged=[];wave_map={};comparison={};perceptual={}
    if reference is not None:
        import bank_migration
        if bank_migration.infer_reference(bank)!=reference.name:reference=None
    if reference is not None:
        mapping=bank_migration.plan_rows(reference.rows,bank.rows,bank_migration.identities(reference),bank_migration.identities(bank))
        for item in mapping['rows']:
            key=item['target_key'];comparison[key]='unmapped'
            if item['status']!='matched':continue
            row=bank.wave_rows[key];original=reference.wave_rows[item['source_key']]
            wave_map[key]=original['key']
            # Display current verified descriptions, without changing imported cue IDs/tags.
            for field in ('english','interactions','emotes','attack_contexts'):row[field]=copy.deepcopy(original.get(field,[]))
            imported_awb=bank.stream if row['streaming'] else bank.memory
            original_awb=reference.stream if original['streaming'] else reference.memory
            if not imported_awb or not original_awb or row['id'] not in imported_awb.entries or original['id'] not in original_awb.entries:
                comparison[key]='unavailable';continue
            identical=imported_awb.entries[row['id']]==original_awb.entries[original['id']]
            if not identical and all(row[field]==original[field] for field in ('rate','channels','samples')):
                try:identical=same_pcm(bank.original(row),reference.original(original))
                except (OSError,ValueError,RuntimeError,wave.Error):comparison[key]='unavailable';continue
            comparison[key]='unchanged' if identical else 'different'
            if identical:
                unchanged.append(key);perceptual[key]={'status':'similar','exact':True}
            else:
                try:
                    import audio_similarity
                    perceptual[key]=audio_similarity.compare(bank.original(row),reference.original(original))
                except (OSError,ValueError,RuntimeError,wave.Error):perceptual[key]={'status':'uncertain'}
    bank.source['unchanged_original_keys']=unchanged
    bank.source['audio_comparison_reference']=reference.name if reference is not None else None
    bank.source['reference_wave_map']=wave_map
    bank.source['audio_comparison']=comparison
    bank.source['audio_similarity']=perceptual

def legacy_reference_name(acb,language):
    name=UTF(acb).rows[0].get("Name","")
    if re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}",name):return name+"_"+language
    if re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}_"+language,name):return name
    raise ValueError("Não foi possível identificar a referência do banco antigo.")

def reconcile_legacy_bank(bank):
    """Reconcile an editor bank from the old tool after validating its actual HCAs."""
    legacy_reference_name(bank.acb,bank.language)
    expected_ids={row["id"] for row in bank.rows if row["streaming"]}
    if set(bank.stream.ids)!=expected_ids or len(bank.stream.ids)!=len(expected_ids):
        raise ValueError("Os IDs do AWB não correspondem às faixas do ACB antigo.")
    pak=Pak(bank.cfg)
    data=bytearray(bank.acb);wt=UTF(data).child("WaveformTable");counts={};rates={}
    for row in bank.rows:
        awb=bank.stream if row["streaming"] else bank.memory
        if not awb or row["id"] not in awb.entries:raise ValueError("Faixa ausente no AWB antigo.")
        hca=awb.entries[row["id"]]
        if len(hca)<24 or bytes(x&127 for x in hca[:4])!=b"HCA\0":raise ValueError("O banco antigo contém uma faixa HCA inválida.")
        end=be(hca,6,2)
        if not 24<=end<=len(hca):raise ValueError("Cabeçalho HCA incompleto.")
        header=bytes(x&127 for x in hca[:end]);at=header.find(b"fmt\0")
        if at<0 or at+16>end:raise ValueError("Metadados HCA não encontrados.")
        channels=hca[at+4];rate=be(hca,at+5,3)
        samples=be(hca,at+8,4)*1024-be(hca,at+12,2)-be(hca,at+14,2)
        if not 1<=channels<=8 or not 8000<=rate<=192000 or samples<=0:raise ValueError("Formato HCA não suportado.")
        counts[row["key"]]=samples;rates[row["key"]]=rate
        for wi in row["wave_indices"]:
            for field,value in (("SamplingRate",rate),("NumChannels",channels)):
                if wt.rows[wi][field]==value:continue
                cell,typ,storage=wt.cells[wi][field]
                if storage!=0x50:raise ValueError("Formato compartilhado de HCA não editável: "+field)
                data[cell:cell+wt.widths[typ]]=value.to_bytes(wt.widths[typ],"big")
    data=bytearray(update_durations(bank,data,counts,rates))
    root=UTF(data);pos,size=root.child("StreamAwbHash").rows[0]["Hash"]
    data[pos:pos+size]=hashlib.md5(bank.stream_bytes).digest()
    field=root.rows[0].get("StreamAwbAfs2Header")
    if field:
        table=root.child("StreamAwbAfs2Header");pos,size=table.rows[0]["Header"]
        header=bank.stream_bytes[:bank.stream.header_len]
        if len(header)>size:raise ValueError("Cabeçalho do AWB antigo incompatível.")
        data[pos:pos+size]=header+b"\0"*(size-len(header))
    folder=owned(APP/"Imports"/bank.name/("legacy_"+hashlib.sha256(data+bank.stream_bytes).hexdigest()[:24]));folder.mkdir(parents=True,exist_ok=True)
    clone=copy.copy(bank);clone.file_kind="cooked" if bank.file_kind=="inline_cooked" else bank.file_kind
    inject_cooked(clone,data,folder)
    awb=folder/(bank.name+".awb");awb.write_bytes(bank.stream_bytes)
    acb=folder/(bank.name+".acb");acb.write_bytes(data)
    source={"asset":str(folder/(bank.name+".uasset")),"awb":str(awb),"acb":str(acb),"original_paths":bank.source["original_paths"],"legacy_reconciled":True}
    if bank.file_kind!="zen":source["uexp"]=str(folder/(bank.name+".uexp"))
    if bank.file_kind=="inline_cooked":source["import_kind"]="inline_cooked"
    return Bank(bank.cfg,pak,bank.name,source)

def attach_legacy_acb(bank,acb):
    root=UTF(acb)
    if root.child("CueNameTable").rows!=bank.tables["CueNameTable"].rows or [c["CueId"] for c in root.child("CueTable").rows]!=[c["CueId"] for c in bank.tables["CueTable"].rows]:
        raise ValueError("O ACB selecionado não corresponde aos cues do uasset antigo.")
    folder=owned(APP/"Imports"/bank.name/("attached_"+hashlib.sha256(acb+bank.uexp).hexdigest()[:24]));folder.mkdir(parents=True,exist_ok=True)
    clone=copy.copy(bank);clone.file_kind="cooked"
    inject_cooked(clone,acb,folder)
    path=folder/(bank.name+".acb");path.write_bytes(acb)
    source={**bank.source,"asset":str(folder/(bank.name+".uasset")),"uexp":str(folder/(bank.name+".uexp")),"acb":str(path)}
    return Bank(bank.cfg,bank.pak,bank.name,source)

def import_external_bank(cfg,asset,awb,acb=None,uexp=None,bank_name=None,package_origin=None):
    """Snapshot external input bytes under the app; never modify the selected sources."""
    if asset is None:
        if not acb:raise ValueError("Selecione o ACB e o AWB correspondentes.")
        companion=Path(acb).with_suffix(".uasset")
        if companion.exists():
            raw=companion.read_bytes()
            if embedded_asset_supported(raw) and raw[:4]==b"\xc1\x83\x2a\x9e" and le(raw,12,4):
                return import_external_bank(cfg,companion,awb,acb)
        return import_acb_bank(cfg,acb,awb,bank_name)
    asset=Path(asset).resolve();name=asset.stem
    standard_name=bool(re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}_(JP|US)",name))
    files={"asset":asset,"awb":Path(awb).resolve()}
    companion=Path(uexp).resolve() if uexp else asset.with_suffix(".uexp")
    if companion.exists():files["uexp"]=companion
    if acb:files["acb"]=Path(acb).resolve()
    payloads={key:path.read_bytes() for key,path in files.items()}
    if package_origin is None and asset.parent.exists():
        import package_import
        package_origin=package_import.loose_pair_origin(cfg,asset,files['awb'])
    if not standard_name:
        import package_import
        package_import.validate_custom_origin(cfg,asset,files['awb'],package_origin or {})
    inline=False
    if "uexp" not in payloads and payloads["asset"][:4]==b"\xc1\x83\x2a\x9e":
        header,summary=cooked_summary(payloads["asset"])
        if b"@UTF" not in payloads["asset"][header:]:
            raise ValueError("Este .uasset contém somente o cabeçalho. Selecione também seu .uexp ou ACB.")
        cooked_exports(payloads["asset"])
        payloads["uexp"]=payloads["asset"][header:]
        payloads["asset"]=payloads["asset"][:header]
        inline=True
    digest=hashlib.sha256(b"".join(key.encode()+hashlib.sha256(data).digest() for key,data in sorted(payloads.items()))).hexdigest()[:24]
    folder=owned(APP/"Imports"/name/digest);folder.mkdir(parents=True,exist_ok=True)
    source={"original_paths":{key:str(path) for key,path in files.items()}}
    if inline:source["import_kind"]="inline_cooked"
    for key,data in payloads.items():
        extension={"asset":".uasset","awb":".awb","acb":".acb","uexp":".uexp"}[key]
        dest=folder/(name+extension)
        if dest.exists():
            if dest.read_bytes()!=data:raise ValueError("Cópia de importação inconsistente.")
        else:dest.write_bytes(data)
        source[key]=str(dest)
    legacy_editor=inline and bool(le(payloads["asset"],12,4))
    if legacy_editor and "acb" in source:
        selected_acb=standalone_acb(payloads["acb"])
        original_paths=source["original_paths"]
        source={key:value for key,value in source.items() if key!="acb"}
        bank=Bank(cfg,None,name,source)
        if selected_acb!=bank.acb:bank=attach_legacy_acb(bank,selected_acb)
    else:bank=Bank(cfg,None,name,source)
    legacy_package=bool(package_origin and package_origin.get('legacy_iostore_plaintext') and package_origin.get('iostore_version')==3)
    custom_package=bool(package_origin and str(package_origin.get('voice_asset_path') or '').startswith('SparkingZERO/Mods/'))
    # Some cooked custom-character banks retain their source bank's stale AWB hash.
    # Reconcile only after the existing strict ID-set and HCA-header checks succeed.
    if legacy_editor or ((legacy_package or custom_package) and not bank.compatible):bank=reconcile_legacy_bank(bank)
    if package_origin:bank.source['package_origin']=package_origin
    missing=[row for row in bank.rows if not row['available']]
    if not bank.compatible and missing:
        expected=sum(bool(row['streaming']) for row in bank.rows)
        raise ValueError('O ACB espera {expected} faixas no AWB, mas o arquivo selecionado contém {actual}; faltam {missing}.\nSelecione o UASSET/ACB antigo que acompanhava esse AWB. Não é seguro associar as vozes usando somente a posição dos arquivos.'.format(expected=expected,actual=len(bank.stream.ids),missing=len(missing)))
    if not bank.compatible:raise ValueError("O AWB selecionado não corresponde ao hash do ACB atribuído ao asset.")
    if any(not row["available"] for row in bank.rows):raise ValueError("O AWB/ACB não contém todas as faixas referenciadas.")
    return bank

def acb_bank_name(acb,awb,language=None):
    pattern=r"BTLCV_[0-9]{4}_[0-9]{2}_(JP|US)"
    candidates=[Path(path).stem for path in (acb,awb) if re.fullmatch(pattern,Path(path).stem)]
    if len(set(candidates))>1:raise ValueError("Os nomes do ACB e do AWB indicam bancos diferentes.")
    if candidates:return candidates[0]
    name=UTF(Path(acb).read_bytes()).rows[0].get("Name","")
    if re.fullmatch(pattern,name):return name
    if re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}",name) and language in ("JP","US"):return name+"_"+language
    raise ValueError("Não foi possível identificar o banco e idioma. Use o nome original BTLCV_####_##_JP/US ou selecione o idioma.")

def import_acb_bank(cfg,acb,awb,name=None):
    """Attach a standalone ACB to a read-only template inside the app."""
    acb_path=Path(acb).resolve();awb_path=Path(awb).resolve()
    name=name or acb_bank_name(acb_path,awb_path)
    if not re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}_(JP|US)",name):raise ValueError("Nome do banco inválido.")
    acb_bytes=standalone_acb(acb_path.read_bytes());awb_bytes=awb_path.read_bytes();root=UTF(acb_bytes)
    ht=root.child("StreamAwbHash")
    if not ht:raise ValueError("ACB sem hash do AWB; associação não pôde ser verificada.")
    pos,size=ht.rows[0]["Hash"]
    if acb_bytes[pos:pos+size]!=hashlib.md5(awb_bytes).digest():raise ValueError("O AWB selecionado não corresponde ao ACB.")
    Awb(awb_bytes)
    try:reference=Bank(cfg,Pak(cfg),name)
    except (OSError,ValueError,KeyError) as error:
        raise ValueError("Referência BTLCV necessária para atribuir este ACB ao asset não está disponível: "+name) from error
    if root.rows[0].get("Name")!=reference.root.rows[0].get("Name"):raise ValueError("O ACB não pertence ao BTLCV de referência escolhido.")
    names=root.child("CueNameTable");cues=root.child("CueTable")
    if not names or not cues or names.rows!=reference.tables["CueNameTable"].rows or [c["CueId"] for c in cues.rows]!=[c["CueId"] for c in reference.tables["CueTable"].rows]:
        raise ValueError("Os nomes ou IDs dos cues diferem do template. Importe o asset completo para preservar essa estrutura.")
    digest=hashlib.sha256(acb_bytes+awb_bytes+reference.asset.read_bytes()+reference.uexp).hexdigest()[:24]
    folder=owned(APP/"Imports"/name/("acb_"+digest));folder.mkdir(parents=True,exist_ok=True)
    inject_cooked(reference,acb_bytes,folder)
    ca=folder/(name+".acb");wa=folder/(name+".awb");ca.write_bytes(acb_bytes);wa.write_bytes(awb_bytes)
    source={"asset":str(folder/(name+".uasset")),"uexp":str(folder/(name+".uexp")),"acb":str(ca),"awb":str(wa),
        "import_kind":"acb_awb","template_bank":name,"original_paths":{"acb":str(acb_path),"awb":str(awb_path)}}
    bank=Bank(cfg,reference.pak,name,source)
    if any(not row["available"] for row in bank.rows):raise ValueError("O AWB/ACB não contém todas as faixas referenciadas.")
    return bank

def zen_bulk_size(bank,original,pos):
    stored=le(original,pos-16,4)
    if stored!=le(original,pos-12,4) or stored<len(bank.acb) or stored-len(bank.acb)>1048576 or pos+stored>len(original):
        raise ValueError('Cabeçalho BulkData Zen não reconhecido.')
    if any(original[pos+len(bank.acb):pos+stored]):raise ValueError('Dados extras não reconhecidos após o ACB Zen.')
    return stored

def edit_zen(bank,acb):
    original=bank.uexp;pos=bank.acb_start;delta=len(acb)-len(bank.acb)
    result=patch_cue_infos(bank,original,pos,acb)
    stored=zen_bulk_size(bank,original,pos)
    result[pos:pos+len(bank.acb)]=acb
    struct.pack_into("<I",result,pos-16,stored+delta);struct.pack_into("<I",result,pos-12,stored+delta)
    exportmap=le(original,32,4)
    if le(original,36,4)-exportmap!=72:raise ValueError("Quantidade de exports Zen não suportada.")
    struct.pack_into("<Q",result,exportmap+8,le(original,exportmap+8,8)+delta)
    return result

def prepare_wav_samples(source,rate,channels,variation=1):
    a,inrate=audio_levels.read_pcm(source);inc=a.shape[1]
    if channels==1:a=a.mean(axis=1,keepdims=True)
    elif inc==1:a=np.repeat(a,channels,axis=1)
    elif inc!=channels:raise ValueError("Use WAV mono ou estéreo.")
    original_duration=len(a)/inrate
    if inrate!=rate and len(a):a=audio_format_verification.resample(a,inrate,rate)
    a=audio_variations.apply(a,rate,variation) if len(a) else a
    samples=len(a)
    if not samples:raise ValueError("O WAV customizado deve conter áudio.")
    return a,rate,original_duration

def normalize_wav(source,dest,rate,channels,samples,gain_db=0.0,variation=1):
    a,rate,original_duration=prepare_wav_samples(source,rate,channels,variation)
    samples=len(a)
    a=audio_levels.apply_gain(a,gain_db)
    pcm=np.clip(np.round(a*32768),-32768,32767).astype("<i2").tobytes()
    dest=owned(dest);dest.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(dest),"wb") as w:w.setparams((channels,2,rate,samples,"NONE","not compressed"));w.writeframes(pcm)
    # Every import and export must deliver PCM16 to the HCA encoder.
    audio_format_verification.wav_format(dest,{"rate":rate,"channels":channels})
    return {"source_duration":original_duration,"export_duration":samples/rate,
            "samples":samples,"trimmed":False}
def silent_wav(path,row):
    path=owned(path)
    samples=max(1,round(row["rate"]*SILENCE_DURATION))
    with wave.open(str(path),"wb") as w:
        w.setparams((row["channels"],2,row["rate"],samples,"NONE","not compressed"))
        w.writeframes(b"\0"*(samples*row["channels"]*2))
def replace_root_blob(acb,field,replacement):
    root=UTF(acb);start,size=root.rows[0][field];end=start+size
    delta=len(replacement)-size
    out=bytearray(acb[:start]+replacement+acb[end:])
    q,typ,storage=root.cells[0][field]
    if storage not in (0x30,0x50) or typ!=11:raise ValueError("Campo de ACB não editável.")
    struct.pack_into(">I",out,q+4,len(replacement))
    if delta:
        struct.pack_into(">I",out,4,be(acb,4,4)+delta)
        for name,typ,storage,cp in root.cols:
            if typ!=11 or storage not in (0x30,0x50):continue
            cell=root.cells[0][name][0]
            bloboff=root.rows[0][name][0]
            if bloboff>=end:struct.pack_into(">I",out,cell,be(acb,cell,4)+delta)
    return out
def update_durations(bank,acb,sample_counts,sample_rates=None):
    sample_rates=sample_rates or {}
    """Change only physical sample counts and affected cue lengths, preserving control data."""
    out=bytearray(acb);root=UTF(out);wt=root.child("WaveformTable");ct=root.child("CueTable")
    changed=set()
    def put(table,index,field,value):
        q,typ,storage=table.cells[index][field]
        if storage!=0x50 or typ!=4:raise ValueError("Duração não possui armazenamento individual: "+field)
        struct.pack_into(">I",out,q,value)
    for key,samples in sample_counts.items():
        for wi in bank.wave_rows[key]["wave_indices"]:
            if samples!=wt.rows[wi]["NumSamples"] or sample_rates.get(key,wt.rows[wi]["SamplingRate"])!=bank.tables["WaveformTable"].rows[wi]["SamplingRate"]:
                put(wt,wi,"NumSamples",samples);changed.add(wi)
    for ci,cue in enumerate(ct.rows):
        refs=bank.resolve(cue["ReferenceType"],cue["ReferenceIndex"],set())
        if not refs.intersection(changed):continue
        original=bank.tables["WaveformTable"].rows
        oldmax=max(original[i]["NumSamples"]*1000//original[i]["SamplingRate"] for i in refs)
        overhead=cue["Length"]-oldmax
        if overhead and (len(refs)!=1 or overhead<0):
            raise ValueError("Cue com duração sequencial não suportada: "+str(cue["CueId"]))
        # A single referenced waveform can have an additional cue duration.
        # Preserve that original interval; do not alter its sequence commands.
        newmax=max(sample_counts.get(("S" if original[i]["Streaming"] else "M")+
            str(original[i]["StreamAwbId"] if original[i]["Streaming"] else original[i]["MemoryAwbId"]),
            original[i]["NumSamples"])*1000//sample_rates.get(("S" if original[i]["Streaming"] else "M")+str(original[i]["StreamAwbId"] if original[i]["Streaming"] else original[i]["MemoryAwbId"]),original[i]["SamplingRate"]) for i in refs)
        put(ct,ci,"Length",newmax+overhead)
    return out

def patch_cue_infos(bank,data,acb_start,acb):
    """Locate each changed FString + FTimespan pair in the serialized CueInfos prefix."""
    out=bytearray(data);newcues=UTF(acb).child("CueTable").rows
    for entry in bank.tables["CueNameTable"].rows:
        index=entry["CueIndex"];old=bank.tables["CueTable"].rows[index]["Length"];new=newcues[index]["Length"]
        if old==new:continue
        name=entry["CueName"].encode("utf-8")+b"\0"
        signature=struct.pack("<i",len(name))+name+struct.pack("<q",old*10000)
        prefix=bytes(out[:acb_start]);at=prefix.find(signature)
        if at>=0 and prefix.count(signature)==1:
            struct.pack_into("<q",out,at+4+len(name),new*10000)
            continue
        # Editor uassets serialize CueInfos with tagged FTimespan properties.
        names=asset_names(bank.asset)
        cue_string=struct.pack("<i",len(name))+name
        cue_at=prefix.find(cue_string)
        if cue_at<0 or prefix.count(cue_string)!=1 or not all(n in names for n in ("Duration","StructProperty","Timespan")):
            raise ValueError("Duração CueInfos não identificada com segurança: "+entry["CueName"])
        tag=struct.pack("<QQIIQ",names.index("Duration"),names.index("StructProperty"),8,0,names.index("Timespan"))
        begin=cue_at+len(cue_string);at=prefix.find(tag,begin,begin+256)
        value_at=at+49
        if at<0 or prefix[at+32:at+49]!=b"\0"*17 or value_at+8>len(prefix) or struct.unpack_from("<q",prefix,value_at)[0]!=old*10000:
            raise ValueError("Duração CueInfos não identificada com segurança: "+entry["CueName"])
        struct.pack_into("<q",out,value_at,new*10000)
    return out

def inject_cooked(bank,acb,destination):
    if bank.file_kind=="zen":
        dst=owned(destination);dst.mkdir(parents=True,exist_ok=True)
        result=edit_zen(bank,acb);(dst/(bank.name+".uasset")).write_bytes(result)
        return result,None
    uexp=patch_cue_infos(bank,bank.uexp,bank.acb_start,acb);start=bank.acb_start;oldlen=len(bank.acb);delta=len(acb)-oldlen
    # Inline FByteBulkData header precedes the UTF payload: flags, count, disk size, offset.
    pos=start-20
    storedlen=le(uexp,pos+4,4)
    if storedlen<oldlen or le(uexp,pos+8,4)!=storedlen or start+storedlen>len(uexp)-4:
        raise ValueError("Cabeçalho BulkData diferente do formato validado; exportação interrompida.")
    if any(uexp[start+oldlen:start+storedlen]):
        raise ValueError("Dados adicionais não reconhecidos no BulkData do ACB.")
    delta=len(acb)-storedlen
    uexp[start:start+storedlen]=acb
    struct.pack_into("<I",uexp,pos+4,len(acb));struct.pack_into("<I",uexp,pos+8,len(acb))
    uasset=bytearray(bank.asset.read_bytes())
    header,_=cooked_summary(uasset)
    entries=cooked_exports(uasset)
    exportoff=min(entries)
    absolute_start=header+start
    for entry in entries:
        serialsize,offset=le(uasset,entry+28,8),le(uasset,entry+36,8)
        if offset<=absolute_start<offset+serialsize:
            if absolute_start+storedlen>offset+serialsize:
                raise ValueError("O ACB ultrapassa o limite do export Unreal.")
            struct.pack_into("<Q",uasset,entry+28,serialsize+delta)
        elif offset>=absolute_start+storedlen:
            struct.pack_into("<Q",uasset,entry+36,offset+delta)
    # BulkDataStartOffset follows guid/generation/engine summary; locate the original combined end uniquely.
    oldend=len(uasset)+len(bank.uexp)-4
    hits=[i for i in range(exportoff) if uasset[i:i+8]==struct.pack("<Q",oldend)]
    for i in hits:struct.pack_into("<Q",uasset,i,oldend+delta)
    dst=owned(destination);dst.mkdir(parents=True,exist_ok=True)
    source_name=getattr(bank,"reference_name",bank.name)
    if source_name!=bank.name:
        uasset=uasset.replace(source_name.encode("ascii"),bank.name.encode("ascii"))
        uexp[:start]=uexp[:start].replace(source_name.encode("ascii"),bank.name.encode("ascii"))
    (dst/(bank.name+".uasset")).write_bytes(uasset+uexp if bank.file_kind=="inline_cooked" else uasset)
    if bank.file_kind!="inline_cooked":(dst/(bank.name+".uexp")).write_bytes(uexp)
    return uasset,uexp

def export_destination(destination,cfg):
    path=Path(destination).expanduser().resolve()
    protected=[Path(cfg[key]).resolve() for key in ("project","game") if str(cfg.get(key) or "").strip()] + [
        Path(r"C:\Program Files\Epic Games\UE_5.1\SBSZEngine\DBSZEngine").resolve()]
    if any(path.is_relative_to(ref) for ref in protected):
        raise ValueError("Escolha uma pasta de saída fora das referências e da instalação do jogo.")
    if path.exists() and not path.is_dir():raise ValueError("O destino deve ser uma pasta.")
    return path

def deliver_export(bank,out,destination,make_package,audio_package=False):
    """Stage verified outputs, replace previous exports, and roll back on failure."""
    target=export_destination(destination,bank.cfg)
    import export_delivery
    destinations=export_delivery.validate_paths(bank,target,make_package,audio_package)
    if make_package:
        sources=sorted((out/"Package").glob("*"))
        sources=[p for p in sources if p.suffix in (".pak",".utoc",".ucas")]
        if len(sources)!=3:raise ValueError("Pacote incompleto.")
    else:
        voice=out/"Assets/SparkingZERO/Content"/f"SS/Sounds/Battle_VOICE/{bank.language}"
        sources=[voice/(bank.name+".uasset")]
        if not audio_package and bank.file_kind not in ("zen","inline_cooked"):sources.append(voice/(bank.name+".uexp"))
        sources.extend([out/(bank.name+".acb"),out/"Assets/SparkingZERO/Content/CriWareData"/(bank.name+".awb")])
    if audio_package:sources.append(out/"Package"/("Voice_"+bank.name+"_P.pak"))
    # Reports are named per bank so different characters can share a destination.
    pairs=[(source,target/destinations[source.name]) for source in sources]
    pairs.extend((out/name,target/destinations[bank.name+"_"+name]) for name in ("manifest.json","validation.json"))
    for source,dest in pairs:
        if not source.is_file():raise ValueError("Arquivo de saída ausente: "+source.name)
        if not dest.resolve().is_relative_to(target):raise ValueError("Destino redirecionado para fora da pasta selecionada.")
        if dest.is_symlink() or (dest.exists() and not dest.is_file()):
            raise ValueError("O destino do arquivo não é um arquivo regular: "+str(dest))
    target.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".voice-export-",dir=target) as temporary:
        stage=Path(temporary);prepared=[];published=[]
        for index,(source,dest) in enumerate(pairs):
            fresh=stage/(str(index)+".new");shutil.copyfile(source,fresh)
            if hashlib.sha256(fresh.read_bytes()).digest()!=hashlib.sha256(source.read_bytes()).digest():
                raise IOError("Falha na verificação de cópia: "+dest.name)
            backup=None
            if dest.exists():
                backup=stage/(str(index)+".previous");shutil.copy2(dest,backup)
            prepared.append((fresh,dest,backup))
        try:
            for fresh,dest,backup in prepared:
                dest.parent.mkdir(parents=True,exist_ok=True)
                os.replace(fresh,dest);published.append((dest,backup))
        except Exception:
            for dest,backup in reversed(published):
                if backup is not None:os.replace(backup,dest)
                else:dest.unlink(missing_ok=True)
            raise
    return target

def validate_export_name(name,language):
    name=str(name).strip()
    if not re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}_"+re.escape(language),name):
        raise ValueError("Use o formato BTLCV_####_##_"+language+" para o nome de saída.")
    return name

def voice_package_path(bank):
    """Preserve the imported voice asset's actual package mount for voice-only overrides."""
    origin=(bank.source or {}).get('package_origin',{}) if bank.external else {}
    path=origin.get('voice_asset_path')
    if not path:return Path('SparkingZERO/Content')/f'SS/Sounds/Battle_VOICE/{bank.language}'/(bank.name+'.uasset')
    from pathlib import PurePosixPath
    relative=PurePosixPath(path)
    if relative.is_absolute() or any(p in ('..','') or ':' in p for p in relative.parts) or relative.parts[0]!='SparkingZERO' or relative.name!=bank.name+'.uasset':
        raise ValueError('Caminho original do banco de voz inválido.')
    return Path(*relative.parts)

def export_bank(bank,replacements,progress=lambda s:None,make_package=True,destination=None,preserve_imported=None,gains=None,variations=None,export_name=None,audio_package=False,replacer_folder_name=None,operation=None):
    import export_operations
    def notify(text):
        if operation is not None:operation.report(text)
        progress(text)
    try:
        if operation is not None:operation.checkpoint()
        return _export_bank(bank,replacements,notify,make_package,destination,preserve_imported,gains,variations,export_name,audio_package,replacer_folder_name,operation)
    except export_operations.Cancelled:
        if operation is not None:operation.cleanup(APP)
        raise

def _export_bank(bank,replacements,progress=lambda s:None,make_package=True,destination=None,preserve_imported=None,gains=None,variations=None,export_name=None,audio_package=False,replacer_folder_name=None,operation=None):
    import bank_version
    bank_version.ensure_current(bank)
    if make_package and replacer_folder_name is not None:
        bank=copy.copy(bank);bank.cfg=dict(bank.cfg,replacer_folder_name=replacer_folder_name)

    if audio_package and not str(bank.cfg.get('project') or '').strip():
        raise ValueError('Para exportar Custom, configure o CustomProject e a Custom Engine do Sparking Zero com CriWare. Replacer pode usar somente a instalação do jogo.')
    if export_name and not make_package:
        original_name=bank.name;bank=copy.copy(bank)
        bank.name=validate_export_name(export_name,bank.language)
        bank.reference_name=original_name
    variations=dict(variations or {})
    if set(variations)-set(replacements):raise ValueError("Há variações sem voz importada correspondente.")
    for value in variations.values():audio_variations.valid(value)
    gains=dict(gains or {})
    if set(gains)-set(replacements):raise ValueError("Há ajustes de volume sem voz importada correspondente.")
    for key,value in gains.items():
        gain=audio_levels.valid_gain(value)
        if gain>0:
            peak=audio_levels.analyze(replacements[key])["peak_dbfs"]
            if peak is not None and peak+gain>20*math.log10(32767/32768)+1e-8:
                raise ValueError("O ganho causa clipping. Reduza o volume ou use Igualar ao original.")
    if destination is not None:
        selected=export_destination(destination,bank.cfg)
        if bank.external and any(selected==Path(path).parent.resolve() for path in list(bank.source["original_paths"].values())+list(bank.source.get("package_origin",{}).get("original_paths",{}).values())):
            raise ValueError("Exporte em outra pasta para preservar os arquivos importados.")
        import export_delivery
        export_delivery.validate_paths(bank,selected,make_package,audio_package)
    if not bank.compatible:raise ValueError("O AWB desta instalação diverge do BTLCV. Use um par da mesma versão.")
    if set(replacements)-set(bank.wave_rows):raise ValueError("O projeto contém IDs de áudio que não existem neste banco.")
    if bank.unresolved:raise ValueError("Existem cues sem mapeamento: "+", ".join(bank.unresolved[:5]))
    out=owned(APP/"Cache/ExportBuilds"/(bank.name+"_"+time.strftime("%Y%m%d_%H%M%S")+"_"+os.urandom(2).hex()))
    work=out/"Work";work.mkdir(parents=True)
    if operation is not None:operation.work_dir=out
    streams=dict(bank.stream.entries);mem=dict(bank.memory.entries) if bank.memory else {}
    preserve_imported=bool(bank.external) if preserve_imported is None else bool(preserve_imported)
    report=[];encoded_cache=cpu_jobs.SingleFlight();sample_counts={}
    def convert_row(row):
        if operation is not None:operation.checkpoint()
        source=replacements.get(row["key"])
        wav=work/(row["key"]+".wav");hca=work/(row["key"]+".hca")
        if not source and preserve_unreplaced(bank,row,preserve_imported):
            original_payload=(bank.stream if row["streaming"] else bank.memory).entries[row["id"]]
            audio_format_verification.hca_format(original_payload,row,tolerance=1)
            return row,None,row["samples"],{**row,"export_samples":row["samples"],"export_duration":row["duration"],"replacement":None,"action":"keep_imported" if bank.external else "keep_original"}
        if source:normalize_wav(source,wav,row["rate"],row["channels"],row["samples"],gains.get(row["key"],0.0),variations.get(row["key"],1))
        else:silent_wav(wav,row)
        samples=audio_format_verification.wav_format(wav,row)[2]
        awb=bank.stream if row["streaming"] else bank.memory
        fingerprint=(hashlib.sha256(wav.read_bytes()).hexdigest(),awb.key)
        def encode():
            run([APP/"Tools/VGAudioCli.exe",wav,hca,"--keycode",str(awb.key),"--no-loop"],work)
            if not hca.exists():raise RuntimeError("O encoder não produziu o HCA.")
            return hca.read_bytes()
        payload=encoded_cache.get(fingerprint,encode)
        audio_format_verification.hca_format(payload,row,samples);hca.write_bytes(payload)
        return row,payload,samples,{**row,"export_samples":samples,"export_duration":samples/row["rate"],"replacement":str(source) if source else None,"gain_db":gains.get(row["key"],0.0) if source else 0.0,"variation":variations.get(row["key"],1) if source else 1,"action":"replace" if source else "silence"}
    # Workers own distinct WAV/HCA paths. Only this coordinator assembles the bank.
    def converted(done,total,row):progress(f'Convertendo {done}/{total}: {row["filename"]}')
    for row,payload,samples,entry in cpu_jobs.map_ordered(convert_row,bank.rows,bank.cfg,converted,operation.checkpoint if operation is not None else None):
        sample_counts[row["key"]]=samples;report.append(entry)
        if payload is not None:(streams if row["streaming"] else mem)[row["id"]]=payload
    newawb=bank.stream.rebuild(streams)
    acb=bytearray(bank.acb)
    if bank.memory:
        newmem=bank.memory.rebuild(mem)
        acb=replace_root_blob(acb,"AwbFile",newmem)
    root=UTF(acb);ht=root.child("StreamAwbHash");q,n=ht.rows[0]["Hash"]
    acb[q:q+n]=hashlib.md5(newawb).digest()
    blob=root.rows[0].get("StreamAwbAfs2Header")
    if blob and blob[1]:
        header=newawb[:bank.stream.header_len]
        wrapper=root.child("StreamAwbAfs2Header")
        hp,hn=wrapper.rows[0]["Header"]
        if len(header)>hn:raise ValueError("O tamanho do cabeçalho AWB não corresponde à referência.")
        acb[hp:hp+hn]=header+b"\0"*(hn-len(header))
    acb=update_durations(bank,acb,sample_counts)
    content=out/"Assets"/"SparkingZERO"/"Content"
    voice=(out/"Assets"/voice_package_path(bank).parent) if make_package else content/f"SS/Sounds/Battle_VOICE/{bank.language}"
    inject_cooked(bank,acb,voice)
    audio=content/"CriWareData";audio.mkdir(parents=True)
    (audio/(bank.name+".awb")).write_bytes(newawb)
    (out/(bank.name+".acb")).write_bytes(acb)
    write_json(out/"manifest.json",{"bank":bank.name,"source_bank":getattr(bank,"reference_name",bank.name),"source_awb_md5":hashlib.md5(bank.stream_bytes).hexdigest(),
        "original_acb_sha256":hashlib.sha256(bank.acb).hexdigest(),"original_files_untouched":True,
        "voice_asset_path":voice_package_path(bank).as_posix() if make_package else None,
        "voice_only":True,
        "export_mode":"package" if make_package else "asset_audio_pak" if audio_package else "uasset_acb_awb",
        "destination":str(Path(destination).resolve()) if destination is not None else str(out),
        "imported_source":bank.source if bank.external else None,
        "unreplaced_policy":("keep_imported" if bank.external else "keep_original") if preserve_imported else "mute_confirmed_original_only" if bank.external else "silence",
        "shared_audio_policy":"One replacement per physical waveform; all associated cues share the replacement.",
        "duration_policy":"Preserve full custom duration without trimming or padding; retain original sample rate and channels. See unreplaced_policy for unchanged entries.",
        "rows":report})
    progress("Verificando áudios e metadados...")
    validate_export(bank,out,replacements,preserve_imported)
    if make_package:
        progress("Empacotando arquivos .pak / .utoc / .ucas...")
        pack(bank,out)
    if audio_package:
        import editor_asset
        progress("Criando e verificando asset editável na Unreal...")
        import project_names
        mount=project_names.export_project_name(destination) if destination is not None else "VoiceMod"
        verification=editor_asset.build(APP,bank.cfg,out/(bank.name+".acb"),voice/(bank.name+".uasset"),mount,
            awb=audio/(bank.name+".awb"))
        validation=json.loads((out/"validation.json").read_text(encoding="utf-8"))
        validation.update(verification);write_json(out/"validation.json",validation)
        manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
        manifest["export_mode"]="editor_asset_audio_pak";write_json(out/"manifest.json",manifest)
        progress("Empacotando AWB sem compressão...")
        pack_audio_only(bank,out)
    if operation is not None:operation.begin_publish()
    else:progress("Salvando arquivos verificados...")
    result=deliver_export(bank,out,destination,make_package,audio_package) if destination is not None else out
    if operation is None:progress("Exportação concluída: "+str(result))
    return result
def validate_export(bank,out,replacements,preserve_imported=None):
    preserve_imported=bool(bank.external) if preserve_imported is None else bool(preserve_imported)
    content=out/"Assets/SparkingZERO/Content"
    acb=(out/(bank.name+".acb")).read_bytes();r=UTF(acb)
    for field in ("CueNameTable","SynthTable","SequenceTable","TrackTable","TrackEventTable"):
        old=bank.root.rows[0].get(field);new=r.rows[0].get(field)
        if old and new and bank.acb[old[0]:old[0]+old[1]]!=acb[new[0]:new[0]+new[1]]:
            raise ValueError("Metadados originais alterados: "+field)
    duration_changes=0
    for field,allowed in (("CueTable","Length"),("WaveformTable","NumSamples")):
        oldtable=bank.root.child(field);newtable=r.child(field)
        oldblob=bytearray(bank.blob(bank.root.rows[0][field]));newstart,newsize=r.rows[0][field]
        newblob=bytearray(acb[newstart:newstart+newsize])
        if len(oldblob)!=len(newblob):raise ValueError("Estrutura de tabela alterada: "+field)
        for i,oldrow in enumerate(oldtable.rows):
            if oldrow[allowed]!=newtable.rows[i][allowed]:duration_changes+=1
            for table,blob in ((oldtable,oldblob),(newtable,newblob)):
                q,typ,storage=table.cells[i][allowed]
                if storage!=0x50:raise ValueError("Duração compartilhada não suportada.")
                q-=table.base;blob[q:q+table.widths[typ]]=b"\0"*table.widths[typ]
        if oldblob!=newblob:raise ValueError("Nomes, IDs ou tags alterados: "+field)
    ab=(content/"CriWareData"/(bank.name+".awb")).read_bytes()
    ht=r.child("StreamAwbHash");q,n=ht.rows[0]["Hash"]
    if acb[q:q+n]!=hashlib.md5(ab).digest():raise ValueError("Hash AWB incorreto na exportação.")
    parsed=Awb(ab)
    if parsed.ids!=bank.stream.ids:raise ValueError("IDs originais de AWB foram alterados.")
    memory_blob=r.rows[0].get("AwbFile")
    memory=Awb(acb[memory_blob[0]:memory_blob[0]+memory_blob[1]]) if memory_blob and memory_blob[1] else None
    waveform=r.child("WaveformTable").rows
    for row in bank.rows:
        archive=parsed if row["streaming"] else memory
        if archive is None or row["id"] not in archive.entries:raise ValueError('Formato do áudio exportado inválido.')
        tolerance=1 if row["key"] not in replacements and preserve_unreplaced(bank,row,preserve_imported) else 0
        for index in row["wave_indices"]:
            metadata=waveform[index]
            expected=dict(row,rate=metadata["SamplingRate"],channels=metadata["NumChannels"],samples=metadata["NumSamples"])
            audio_format_verification.hca_format(archive.entries[row["id"]],expected,tolerance=tolerance)
    write_json(out/"validation.json",{"sample_rates_channels_samples_verified":True,"audio_formats_verified":len(bank.rows),"names_ids_tags_unchanged":True,"duration_fields_updated":duration_changes,"awb_ids_unchanged":True,
        "awb_hash_verified":True,"replaced":len(replacements),"silenced":sum(row["key"] not in replacements and not preserve_unreplaced(bank,row,preserve_imported) for row in bank.rows),
        "kept_original":len(bank.rows)-len(replacements) if not bank.external and preserve_imported else 0,
        "kept_imported":sum(row["key"] not in replacements and preserve_unreplaced(bank,row,preserve_imported) for row in bank.rows) if bank.external else 0,
        "in_game_test":"Not performed"})
def pack_audio_only(bank,out):
    """Guide step 6: one uncompressed .pak containing the finalized AWB."""
    package=out/"Package";package.mkdir(exist_ok=True)
    name="Voice_"+bank.name+"_P.pak"
    awb=out/"Assets/SparkingZERO/Content/CriWareData"/(bank.name+".awb")
    response=out/"audio_pak_response.txt"
    response.write_text('"'+str(awb)+'" "../../../SparkingZERO/Content/CriWareData/'+bank.name+'.awb"\n',encoding="utf-8")
    run([APP/"Tools/UnrealPak/UnrealPak.exe",package/name,"-Create="+str(response),"-NoLog","-Unattended","-stdout"],out)
    if not (package/name).is_file():raise ValueError("O pacote AWB não foi gerado.")
    verify=owned(out/"VerifyAudioPak");verify.mkdir(exist_ok=True)
    run([APP/"Tools/UnrealPak/UnrealPak.exe",package/name,"-Extract",verify,"-NoLog","-Unattended","-stdout"],out)
    extracted=[p for p in verify.rglob("*") if p.is_file()]
    if len(extracted)!=1 or extracted[0].name!=awb.name or hashlib.sha256(extracted[0].read_bytes()).digest()!=hashlib.sha256(awb.read_bytes()).digest():
        raise ValueError("O pacote de áudio não preservou o AWB finalizado.")
    validation=json.loads((out/"validation.json").read_text(encoding="utf-8"))
    validation.update({"audio_pak_only":True,"audio_pak_roundtrip_verified":True,"audio_pak_compression":"None","audio_pak_mount":"SparkingZERO/Content/CriWareData/"})
    write_json(out/"validation.json",validation)

def pack(bank,out):
    package=out/"Package";package.mkdir(exist_ok=True)
    key=encryption_key(bank.cfg).hex()
    name="Voice_"+bank.name+"_P"
    assets=out/"Assets"
    iostore_assets=out/"IoStoreAssets"
    import native
    if bank.pak is None:bank.pak=Pak(bank.cfg)
    if bank.file_kind=="inline_cooked":
        # Match SparkingZeroAudioTool's complete-uasset packaging workflow.
        native_edited=(assets/voice_package_path(bank)).read_bytes()
    else:
        if bank.file_kind=="zen":native_original=bank.uexp
        else:
            lookup=copy.copy(bank);lookup.name=getattr(bank,"reference_name",bank.name)
            native_original=native.original_asset(lookup,bank.pak)
            if bank.external:
                reference=Bank(bank.cfg,bank.pak,getattr(bank,"reference_name",bank.name))
                if asset_names(bank.asset)!=asset_names(reference.asset):
                    raise ValueError("O mapa de nomes do asset importado difere da referência Zen; exporte como Asset.")
                at=native_original.find(reference.acb);start=at-reference.acb_start
                if at<0 or start<0 or native_original[start:]!=reference.uexp[:-4]:
                    raise ValueError("O layout do asset externo não corresponde ao pacote Zen de referência; exporte como Asset.")
                native_original=bytearray(native_original[:start]+bank.uexp[:-4])
                exportmap=le(native_original,32,4)
                struct.pack_into("<Q",native_original,exportmap+8,len(bank.uexp)-4)
                native_original=bytes(native_original)
        pos=native_original.find(bank.acb)
        if pos<0 or native_original.count(bank.acb)!=1:
            raise ValueError("O ACB de referência não corresponde ao pacote Zen original.")
        new_acb=(out/(bank.name+".acb")).read_bytes()
        delta=len(new_acb)-len(bank.acb)
        native_original_patched=patch_cue_infos(bank,native_original,pos,new_acb)
        native_edited=bytearray(native_original_patched[:pos]+new_acb+native_original_patched[pos+len(bank.acb):])
        stored=zen_bulk_size(bank,native_original,pos)
        struct.pack_into("<I",native_edited,pos-16,stored+delta)
        struct.pack_into("<I",native_edited,pos-12,stored+delta)
        exportmap=le(native_original,32,4)
        if le(native_original,36,4)-exportmap!=72:
            raise ValueError("Quantidade de exports Zen diferente do formato validado.")
        struct.pack_into("<Q",native_edited,exportmap+8,le(native_original,exportmap+8,8)+delta)
    native_dir=owned(iostore_assets/voice_package_path(bank).parent)
    native_dir.mkdir(parents=True,exist_ok=True)
    (native_dir/(bank.name+".uasset")).write_bytes(native_edited)
    (native_dir/(bank.name+".uexp")).unlink(missing_ok=True)
    origin=(bank.source or {}).get('package_origin',{}) if bank.external else {}
    custom_mount=voice_package_path(bank).as_posix().startswith('SparkingZERO/Mods/')
    rezen_source=Path(bank.cfg["game"])/"SparkingZERO/Content/Paks"
    if custom_mount:
        container=origin.get('container_snapshot',{}).get('.utoc') or origin.get('original_paths',{}).get('.utoc')
        if not container or not Path(container).is_file():raise ValueError('O pacote original do personagem customizado é necessário para exportar a voz.')
        rezen_source=Path(container).parent
    run([APP/"Tools/UnrealReZen/UnrealReZen.exe","--content-path",iostore_assets,
        "--compression-format","Zlib","--engine-version","GAME_UE5_1","--game-dir",
        rezen_source,"--output-path",package/(name+".utoc"),
        "--aes-key",key],APP/"Tools/UnrealReZen")
    native.seal_directory(package/(name+".utoc"),bank.pak)
    # UnrealReZen handles UObject assets. Loose CRI streaming banks must be in the .pak too.
    response=out/"pak_response.txt"
    awb=assets/"SparkingZERO/Content/CriWareData"/(bank.name+".awb")
    response.write_text('"'+str(awb)+'" "../../../SparkingZERO/Content/CriWareData/'+bank.name+'.awb"\n',encoding="utf-8")
    run([APP/"Tools/UnrealPak/UnrealPak.exe",package/(name+".pak"),"-Create="+str(response),
        "-NoLog","-Unattended","-stdout"],out)
    for ext in (".utoc",".ucas",".pak"):
        if not (package/(name+ext)).exists():raise ValueError("Arquivo de mod não gerado: "+ext)
    store=native.IoStore(package/(name+".utoc"),bank.pak)
    expected='../../../'+voice_package_path(bank).as_posix()
    if set(store.files)!={expected}:raise ValueError('O pacote deve conter somente o asset de voz no caminho original.')
    index=store.files[expected]
    origin=(bank.source or {}).get('package_origin',{}) if bank.external else {}
    original_chunk=origin.get('voice_chunk_id')
    if original_chunk and store.b[store.ids_pos+index*12:store.ids_pos+(index+1)*12].hex()!=original_chunk:
        raise ValueError('O identificador do pacote de voz customizado não foi preservado.')
    roundtrip=store.read_chunk(index)
    if roundtrip!=native_edited:raise ValueError("O pacote gerado não preservou o BTLCV completo.")
    validation=json.loads((out/"validation.json").read_text(encoding="utf-8"))
    validation.update({"native_package_roundtrip_verified":True,"native_package_bytes":len(native_edited),"voice_only_asset_verified":True,"voice_asset_path":expected})
    write_json(out/"validation.json",validation)
def available_banks(cfg):
    import game_installation
    if game_installation.identity(cfg) or not str(cfg.get("project") or "").strip():
        if not str(cfg.get("game") or "").strip():return []
        import game_references
        return game_references.banks(cfg)
    root=Path(cfg["project"])/"Content/SS/Sounds/Battle_VOICE"
    return sorted(p.stem for p in root.glob("*/*.uasset") if p.with_suffix(".uexp").exists())


def bank_voice_catalog(cfg):
    """Count unique physical waveforms from reference ACBs without opening game audio."""
    import game_references
    base=game_references.reference_root(cfg)/"Content/SS/Sounds/Battle_VOICE"
    cache_path=APP/"Cache/bank_catalog.json"
    try:cached=json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError,ValueError):cached={}
    previous=cached.get("entries",{}) if cached.get("project")==str(base.resolve()) else {}
    result={};entries={}
    names=available_banks(cfg)
    # Reuse counts only when every cached reference has the exact saved stamp.
    # The base folder is tied to the current installed-container identity.
    cached_counts={}
    for name in names:
        asset=base/name[-2:]/(name+".uasset")
        path=asset.with_suffix(".uexp") if asset.with_suffix(".uexp").exists() else asset
        item=previous.get(name)
        try:stamp=path.stat()
        except OSError:break
        if not item or item.get("signature")!=[stamp.st_size,stamp.st_mtime_ns] or not isinstance(item.get("voices"),int):break
        cached_counts[name]=item["voices"]
    if names and len(cached_counts)==len(names):
        import game_installation
        if not str(cfg.get("game") or "").strip() or base.parents[3].name==game_installation.identity(cfg):
            return cached_counts
    paths=game_references.assets(cfg,[f"SS/Sounds/Battle_VOICE/{name[-2:]}/{name}.uasset" for name in names])
    for name in names:
        asset=paths[f"SS/Sounds/Battle_VOICE/{name[-2:]}/{name}.uasset"]
        path=asset.with_suffix(".uexp") if asset.with_suffix(".uexp").exists() else asset
        stamp=path.stat();signature=[stamp.st_size,stamp.st_mtime_ns]
        item=previous.get(name)
        if item and item.get("signature")==signature and isinstance(item.get("voices"),int):
            count=item["voices"]
        else:
            try:
                data=path.read_bytes();root=UTF(data,data.index(b"@UTF"));table=root.child("WaveformTable")
                count=len({(bool(w["Streaming"]),w["StreamAwbId"] if w["Streaming"] else w["MemoryAwbId"]) for w in table.rows})
            except (OSError,ValueError,KeyError,AttributeError,IndexError):count=None
        result[name]=count;entries[name]={"signature":signature,"voices":count}
    write_json(cache_path,{"project":str(base.resolve()),"entries":entries})
    return result
