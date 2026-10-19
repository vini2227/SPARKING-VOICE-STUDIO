"""Read original Zen package bytes without reconstructing their Unreal headers."""
import ctypes, io, struct, zlib
from pathlib import Path
import core

def parse_directory(data,chunk_count):
    """Validate the entire directory before accepting old plaintext encrypted containers."""
    r=io.BytesIO(data)
    def exact(n):
        if n<0 or n>len(data)-r.tell():raise ValueError('Índice IoStore incompleto.')
        return r.read(n)
    def u():return struct.unpack('<I',exact(4))[0]
    def fs():
        n=struct.unpack('<i',exact(4))[0]
        if not n:raise ValueError('String vazia no índice IoStore.')
        value=exact(abs(n)*(2 if n<0 else 1))
        if not value.endswith(b'\0\0' if n<0 else b'\0'):raise ValueError('String inválida no índice IoStore.')
        return value.decode('utf-16le' if n<0 else 'utf-8').rstrip('\0')
    def records(width):
        count=u()
        if count>(len(data)-r.tell())//(width*4):raise ValueError('Tabela inválida no índice IoStore.')
        return [struct.unpack('<'+'I'*width,exact(width*4)) for _ in range(count)]
    mount=fs()
    if not mount.startswith('../../../') or not mount.endswith('/') or '\x00' in mount:raise ValueError('Mount point IoStore inválido.')
    dirs=records(4);files=records(3);count=u()
    if count>(len(data)-r.tell())//5:raise ValueError('Strings inválidas no índice IoStore.')
    strings=[fs() for _ in range(count)]
    tail=r.read()
    if any(tail) and (len(tail)>15 or tail!=data[:len(tail)]):raise ValueError('Dados extras no índice IoStore.')
    if not dirs:raise ValueError('Índice IoStore sem diretórios.')
    result={};seen_dirs=set();seen_files=set();none=0xffffffff
    def visit(index,parent):
        if index>=len(dirs) or index in seen_dirs:raise ValueError('Diretório inválido no índice IoStore.')
        seen_dirs.add(index);d=dirs[index]
        if d[0]!=none and d[0]>=len(strings):raise ValueError('Nome de diretório IoStore inválido.')
        folder=parent+(strings[d[0]]+'/' if d[0]!=none else '')
        f=d[3]
        while f!=none:
            if f>=len(files) or f in seen_files:raise ValueError('Arquivo inválido no índice IoStore.')
            seen_files.add(f);name,nextfile,userdata=files[f]
            if name>=len(strings) or userdata>=chunk_count:raise ValueError('Chunk inválido no índice IoStore.')
            path=mount+folder+strings[name]
            if path in result:raise ValueError('Arquivo duplicado no índice IoStore.')
            result[path]=userdata;f=nextfile
        child=d[1]
        while child!=none:
            visit(child,folder);child=dirs[child][2]
    visit(0,'')
    if len(seen_dirs)!=len(dirs) or len(seen_files)!=len(files):raise ValueError('Entradas sem referência no índice IoStore.')
    return mount,result

class IoStore:
    def __init__(self,toc_path,pak):
        self.path=Path(toc_path);self.pak=pak;self.b=self.path.read_bytes();b=self.b
        if b[:16]!=b"-==--==--==--==-":raise ValueError("UTOC inválido.")
        self.count=core.le(b,24,4);self.blocks=core.le(b,28,4);self.flags=b[80]
        self.blocksize=core.le(b,44,4);p=core.le(b,20,4)
        self.ids_pos=p;p+=self.count*12;self.offsets_pos=p;p+=self.count*10
        if b[16]>=4:p+=core.le(b,84,4)*4
        if b[16]>=5:p+=core.le(b,96,4)*4
        self.blocks_pos=p;p+=self.blocks*core.le(b,32,4)
        mc=core.le(b,36,4);mw=core.le(b,40,4)
        self.methods=["None"]+[b[p+i*mw:p+(i+1)*mw].split(b"\0")[0].decode("ascii") for i in range(mc)]
        p+=mc*mw
        if self.flags&4:p+=4+core.le(b,p,4)*2+self.blocks*20
        size=core.le(b,48,4)
        if p+size>len(b):raise ValueError('Índice IoStore truncado.')
        directory=b[p:p+size];self.directory_plaintext=False
        if self.flags&2:
            try:
                self.mount,self.files=parse_directory(directory,self.count)
                self.directory_plaintext=True
            except (ValueError,UnicodeError,struct.error):
                if size%16:raise ValueError('Índice IoStore inválido: não está alinhado para AES e não contém um diretório legível.')
                self.mount,self.files=parse_directory(pak.decrypt(directory),self.count)
        else:self.mount,self.files=parse_directory(directory,self.count)
    def read_chunk(self,index):
        b=self.b;p=self.offsets_pos+index*10
        offset=core.be(b,p,5);length=core.be(b,p+5,5)
        if length<=0:raise ValueError("Chunk Unreal vazio.")
        chunks=[]
        with self.path.with_suffix(".ucas").open("rb") as f:
            for bi in range(offset//self.blocksize,(offset+length-1)//self.blocksize+1):
                p=self.blocks_pos+bi*12
                pos=core.le(b,p,5);csize=core.le(b,p+5,3);usize=core.le(b,p+8,3);method=b[p+11]
                f.seek(pos);packed=f.read((csize+15)//16*16 if self.flags&2 else csize)
                if self.flags&2:packed=self.pak.decrypt(packed)[:csize]
                codec=self.methods[method]
                if codec=="None":raw=packed[:usize]
                elif codec=="Zlib":raw=zlib.decompress(packed)
                elif codec=="Oodle":
                    dst=ctypes.create_string_buffer(usize)
                    got=self.pak.decomp(packed,len(packed),dst,usize,1,1,0,None,0,None,None,None,0,3)
                    if got!=usize:raise ValueError("Falha ao ler o pacote original.")
                    raw=dst.raw
                else:raise ValueError("Codec IoStore não suportado: "+codec)
                chunks.append(raw)
        start=offset%self.blocksize
        return b"".join(chunks)[start:start+length]
    def asset(self,name,language):
        suffix=f"/SS/Sounds/Battle_VOICE/{language}/{name}.uasset"
        candidates=[i for p,i in self.files.items() if p.endswith(suffix)]
        if len(candidates)!=1:return None
        return self.read_chunk(candidates[0])
def original_asset(bank,pak):
    import game_references
    return game_references.asset(bank.cfg,f"SS/Sounds/Battle_VOICE/{bank.language}/{bank.name}.uasset").read_bytes()

def seal_directory(toc_path,pak):
    """UnrealReZen encrypts chunk data but emits its directory index as plaintext."""
    path=core.owned(toc_path);b=bytearray(path.read_bytes())
    if not b[80]&2:return
    count=core.le(b,24,4);blocks=core.le(b,28,4)
    p=core.le(b,20,4)+count*22
    if b[16]>=4:p+=core.le(b,84,4)*4
    if b[16]>=5:p+=core.le(b,96,4)*4
    p+=blocks*core.le(b,32,4)+core.le(b,36,4)*core.le(b,40,4)
    if b[80]&4:p+=4+core.le(b,p,4)*2+blocks*20
    size=core.le(b,48,4);directory=bytes(b[p:p+size])
    # Verify the exact mount-point string before changing anything.
    if directory[:14]!=struct.pack("<I",10)+b"../../../\0":
        if size%16:raise ValueError("Índice criptografado do mod não está alinhado.")
        return
    from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
    padded=directory+b"\0"*((-len(directory))%16)
    enc=Cipher(algorithms.AES(pak.key),modes.ECB()).encryptor()
    sealed=enc.update(padded)+enc.finalize()
    b[p:p+size]=sealed
    struct.pack_into("<I",b,48,len(sealed))
    path.write_bytes(b)

