"""Read-only uncompressed USMAP schema inspector; never assigns audio functions from names alone."""
import sys,struct,json,hashlib,re
from pathlib import Path

class Mapping:
 def __init__(self,path):
  self.path=Path(path);self.b=self.path.read_bytes();self.p=0
  assert self.num('H')==0x30c4
  self.version=self.num('B');assert self.version<=4
  self.package_version=None
  if self.version>=1 and self.num('i'):
   self.package_version=[self.num('i'),self.num('i')];count=self.num('i');self.raw(count*20);self.num('I')
  self.compression=self.num('B');compressed=self.num('I');size=self.num('I')
  assert self.compression==0,('compression',self.compression)
  assert compressed==size and size<=len(self.b)-self.p
  self.names=[self.raw(self.num('H' if self.version>=2 else 'B')).decode('utf-8') for _ in range(self.num('i'))]
  self.enums={}
  for _ in range(self.num('i')):
   name=self.name();values={}
   for ordinal in range(self.num('H' if self.version>=3 else 'B')):
    value=self.num('q') if self.version>=4 else ordinal;values[value]=self.name()
   self.enums[name]=values
  self.schemas={}
  for _ in range(self.num('i')):
   name,parent=self.name(),self.name();count,n=self.num('H'),self.num('H');props=[]
   for _ in range(n):
    index,array=self.num('H'),self.num('B');key=self.name();typ=self.typ();props.append(dict(index=index,array=array,name=key,type=typ))
   self.schemas[name]=dict(parent=parent,count=count,properties=props)
 def raw(self,n):
  assert 0<=n<=len(self.b)-self.p
  value=self.b[self.p:self.p+n];self.p+=n;return value
 def num(self,f):return struct.unpack('<'+f,self.raw(struct.calcsize('<'+f)))[0]
 def name(self):
  i=self.num('i');assert -1<=i<len(self.names)
  return self.names[i] if i>=0 else None
 def typ(self):
  t=self.num('B');assert t<=30
  if t==9:return [t,self.name()]
  if t==26:return [t,self.typ(),self.name()]
  if t in (8,25,28):return [t,self.typ()]
  if t==24:return [t,self.typ(),self.typ()]
  return [t]

