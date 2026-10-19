"""Resolve UE5.1 script classes and package imports from installed IoStore metadata."""
import struct
from pathlib import Path
import core,native,game_references,game_installation
from live_properties import Reader

def names_batch(b,start=0):
 count,size=struct.unpack_from('<II',b,start);headers=start+16+count*8;cursor=headers+2*count;end=cursor+size
 if count>1000000 or end>len(b):raise ValueError('Invalid name batch')
 names=[]
 for i in range(count):
  a,z=b[headers+i*2:headers+i*2+2];wide=bool(a&128);n=((a&127)<<8)|z;n*=2 if wide else 1
  if cursor+n>end:raise ValueError('Truncated name batch')
  names.append(b[cursor:cursor+n].decode('utf-16le' if wide else 'utf-8'));cursor+=n
 if cursor!=end:raise ValueError('Invalid name batch length')
 return names,end

class MissingPackageReference(ValueError):
 """An absent asset dependency, independent of ACB/AWB integrity."""
 def __init__(self,source,package_id,export_hash):
  super().__init__('Imported package absent')
  self.details={'category':'missing_asset_dependency','source_asset':source,
                'package_id':f'{package_id:016x}','export_hash':f'{export_hash:016x}'}

class Game:
 def __init__(self,cfg,schemas,enums):
  self.cfg=cfg;self.schemas=schemas;self.enums=enums;self.root,self.entries=game_references.session(cfg);self.packages={};self.imports={};self.scripts={};self.cache={}
  stores={id(s):s for s,i in self.entries.values()}
  for rel,(s,i) in self.entries.items():
   if rel.endswith('.uasset'):self.packages[core.le(s.b,s.ids_pos+i*12,8)]=rel
  for s in stores.values():
   for i in range(s.count):
    if s.b[s.ids_pos+i*12+11]!=6:continue
    b=s.read_chunk(i)
    if len(b)<20 or core.le(b,0,4)!=0x496f436e or core.le(b,4,4) not in (1,2):raise ValueError('Unsupported container header')
    n=core.le(b,16,4);end=20+n*8
    if end+4>len(b):raise ValueError('Container package list truncated')
    ids=struct.unpack_from('<'+'Q'*n,b,20);size=core.le(b,end,4);data=b[end+4:end+4+size]
    if len(data)!=size or n*24>len(data):raise ValueError('Container store entries truncated')
    for j,pid in enumerate(ids):
     at=j*24+8;count,offset=struct.unpack_from('<II',data,at)
     if at+offset+count*8>len(data):raise ValueError('Invalid package import array')
     self.imports[pid]=list(struct.unpack_from('<'+'Q'*count,data,at+offset))
  g=Path(cfg['game'])/'SparkingZERO/Content/Paks/global.utoc';pak=core.Pak(cfg);s=native.IoStore.__new__(native.IoStore)
  try:
   try:s.__init__(g,pak)
   except ValueError:
    if core.le(s.b,48,4)!=0:raise
   hits=[i for i in range(s.count) if s.b[s.ids_pos+i*12+11]==5]
   if len(hits)!=1:raise ValueError('Missing script object metadata')
   b=s.read_chunk(hits[0]);names,end=names_batch(b);n=core.le(b,end,4)
   if end+4+n*32!=len(b):raise ValueError('Invalid script object table size')
   for i in range(n):
    at=end+4+i*32;index=core.le(b,at,4)&0x3fffffff
    if index>=len(names):raise ValueError('Invalid script object name')
    self.scripts[core.le(b,at+8,8)]=(names[index],core.le(b,at+16,8))
  finally:pak.f.close()
 def package(self,rel):
  if rel in self.cache:return self.cache[rel]
  if rel not in self.entries:raise ValueError('Asset absent: '+rel)
  p=self.root/'Content'/rel
  if p.is_file():b=p.read_bytes()
  else:
   store,chunk=self.entries[rel];b=store.read_chunk(chunk)
  if b[:4]!=b'\0'*4:raise ValueError('Versioned Zen package not supported')
  h=core.le(b,4,4);a,z,g=core.le(b,32,4),core.le(b,36,4),core.le(b,40,4)
  if not 44<=a<=z<=g<=h<=len(b) or (z-a)%72 or (g-z)%8:raise ValueError('Unsupported Zen export layout')
  names,_=names_batch(b,44);s,i=self.entries[rel];pid=core.le(s.b,s.ids_pos+i*12,8);exports=[]
  for at in range(a,z,72):
   nameindex=core.le(b,at+16,4)&0x3fffffff;number=core.le(b,at+20,4)
   if nameindex>=len(names):raise ValueError('Invalid export name')
   exports.append({'name':names[nameindex]+('_'+str(number-1) if number else ''),'class_index':core.le(b,at+32,8),'super_index':core.le(b,at+40,8),'outer':core.le(b,at+24,8),'hash':core.le(b,at+56,8),'size':core.le(b,at+8,8)})
  cursor=h;seen=set()
  for at in range(z,g,8):
   index,cmd=struct.unpack_from('<II',b,at)
   if index>=len(exports) or cmd not in (0,1):raise ValueError('Invalid serialize command')
   if cmd==1:
    if index in seen:raise ValueError('Duplicate serialize command')
    seen.add(index);e=exports[index];e['payload']=b[cursor:cursor+e['size']];cursor+=e['size']
    if len(e['payload'])!=e['size']:raise ValueError('Export payload truncated')
  if len(seen)!=len(exports) or cursor!=len(b):raise ValueError('Incomplete package serialization')
  value={'relative':rel,'path':p,'bytes':b,'names':names,'exports':exports,'pid':pid,'public_hashes':list(struct.unpack_from('<'+'Q'*((core.le(b,28,4)-core.le(b,24,4))//8),b,core.le(b,24,4))),'import_map':list(struct.unpack_from('<'+'Q'*((a-core.le(b,28,4))//8),b,core.le(b,28,4)))}
  self.cache[rel]=value;return value
 def resolve_global(self,pkg,index):
  kind=index>>62
  if index==0xffffffffffffffff:return None
  if kind==1:
   name,outer=self.scripts[index];return {'script':name,'module':self.scripts.get(outer,('',None))[0]}
  if kind==0:
   if index>=len(pkg['exports']):raise ValueError('Invalid export reference')
   return {'relative':pkg['relative'],'export':int(index)}
  if kind==2:
   pidx=(index&0x3fffffffffffffff)>>32;hidx=index&0xffffffff;ids=self.imports.get(pkg['pid'],[])
   if pidx>=len(ids) or hidx>=len(pkg['public_hashes']):raise ValueError('Invalid package import reference')
   rel=self.packages.get(ids[pidx])
   if not rel:raise MissingPackageReference(pkg['relative'],ids[pidx],pkg['public_hashes'][hidx])
   target=self.package(rel);expected=pkg['public_hashes'][hidx];hits=[i for i,e in enumerate(target['exports']) if e['hash']==expected]
   if len(hits)!=1:raise ValueError('Ambiguous imported export')
   return {'relative':rel,'export':hits[0]}
  raise ValueError('Unknown object index type')
 def resolve(self,pkg,index):
  if not index:return None
  if index>0:return self.resolve_global(pkg,index-1)
  if -index>len(pkg['import_map']):raise ValueError('Invalid local import index')
  return self.resolve_global(pkg,pkg['import_map'][-index-1])
 def decoded(self,rel,index=0):
  pkg=self.package(rel);e=pkg['exports'][index];cls=self.resolve_global(pkg,e['class_index'])
  if not cls or 'script' not in cls or cls['module']!='/Script/SS':raise ValueError('Unsupported reference export class')
  r=Reader(e['payload'],pkg['names'],self.schemas,self.enums);obj=r.obj(cls['script'])
  # UObject's serialized GUID-present flag is the only permitted trailer.
  tail=r.raw(len(r.b)-r.p)
  if cls['script']=='KoratSequenceSoundPlayer' and tail not in (b'',b'\0'*4):
   trailer=Reader(tail,pkg['names'],self.schemas,self.enums)
   if trailer.num('i')!=0 or trailer.num('i')!=1:raise ValueError('Unsupported actor GUID/label trailer')
   trailer.string()
   if trailer.p!=len(tail):raise ValueError('Unconsumed actor trailer')
   tail=b''
  if tail not in (b'',b'\0'*4):raise ValueError('Unconsumed export properties: '+cls['script']+' '+str(len(tail)))
  return pkg,cls['script'],obj

 def properties(self,rel,index=0):
  """Read bounded property prefixes; animation native streams remain explicitly opaque."""
  pkg=self.package(rel);e=pkg['exports'][index];cls=self.resolve_global(pkg,e['class_index'])
  if not cls or 'script' not in cls:raise ValueError('Unknown blueprint export schema')
  if cls['module'] not in ('/Script/SS','/Script/Engine','/Script/CriWareRuntime'):raise ValueError('Unsupported property module')
  r=Reader(e['payload'],pkg['names'],self.schemas,self.enums);obj=r.obj(cls['script']);tail=e['payload'][r.p:]
  if cls['script'] not in ('AnimSequence','AnimMontage','AnimComposite') and tail not in (b'',b'\0'*4):
   if cls['script']=='KoratSequenceSoundPlayer':return self.decoded(rel,index)+(0,)
   raise ValueError('Unconsumed properties: '+cls['script'])
  return pkg,cls['script'],obj,len(tail)
