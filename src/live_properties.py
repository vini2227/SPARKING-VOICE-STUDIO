"""Bounded read-only unversioned property decoder for verified voice-reference schemas."""
import struct

class Reader:
 def __init__(self,data,names,schemas,enums):self.b=data;self.names=names;self.schemas=schemas;self.enums=enums;self.p=0;self.depth=0
 def raw(self,n):
  if n<0 or n>len(self.b)-self.p:raise ValueError('Property payload truncated')
  b=self.b[self.p:self.p+n];self.p+=n;return b
 def num(self,f):return struct.unpack('<'+f,self.raw(struct.calcsize('<'+f)))[0]
 def count(self):
  n=self.num('i')
  if not 0<=n<=100000:raise ValueError('Invalid property collection size')
  return n
 def name(self):
  i=self.num('I');number=self.num('I')
  if i>=len(self.names) or number>1000000:raise ValueError('Invalid FName')
  return self.names[i]+('_'+str(number-1) if number else '')
 def string(self):
  n=self.num('i')
  if not abs(n)<=1000000:raise ValueError('Invalid FString size')
  value=self.raw(abs(n)*(2 if n<0 else 1));ending=b'\0\0' if n<0 else b'\0'
  if n and not value.endswith(ending):raise ValueError('Unterminated FString')
  return value.decode('utf-16le' if n<0 else 'utf-8').rstrip('\0')
 def fields(self,name,seen=None):
  seen=set() if seen is None else seen
  if name in seen:raise ValueError('Schema inheritance cycle')
  seen.add(name);s=self.schemas[name];fs=[None]*s['count']
  for p in s['properties']:
   for i in range(p['array']):
    at=p['index']+i
    if at>=len(fs) or fs[at] is not None:raise ValueError('Invalid schema property index')
    fs[at]=(p['name'] if not i else p['name']+'_'+str(i),p['type'])
  if not all(fs):raise ValueError('Incomplete schema')
  if s['parent']:fs+=self.fields(s['parent'],seen)
  return fs
 def obj(self,name):
  self.depth+=1
  if self.depth>80:raise ValueError('Property nesting limit')
  try:return self._obj(name)
  finally:self.depth-=1
 def _obj(self,name):
  native={'Vector':('d',3),'Vector2D':('d',2),'Vector4':('d',4),'Rotator':('d',3),'Quat':('d',4),'LinearColor':('f',4),'Color':('B',4),'Guid':('I',4),'IntPoint':('i',2),'FrameNumber':('i',1),'DateTime':('q',1)}
  if name=='MovieSceneFrameRange':
   bounds=[]
   for _ in range(2):
    kind=self.num('B');value=self.num('i')
    if kind not in (0,1,2):raise ValueError('Invalid frame range bound')
    bounds.append({'type':kind,'value':value})
   return {'lower':bounds[0],'upper':bounds[1]}
  if name=='RichCurveKey':
   modes=[self.num('B') for _ in range(3)]
   if modes[0]>4 or modes[1]>3 or modes[2]>3:raise ValueError('Invalid rich curve mode')
   values=[self.num('f') for _ in range(6)]
   return dict(zip(('InterpMode','TangentMode','TangentWeightMode','Time','Value','ArriveTangent','ArriveTangentWeight','LeaveTangent','LeaveTangentWeight'),modes+values))
  if name=='SmartName':return {'DisplayName':self.name()}
  if name in native:
   f,n=native[name];return [self.num(f) for _ in range(n)]
  if name not in self.schemas:raise ValueError('Unknown schema: '+name)
  fs=self.fields(name);frags=[];zero=0;total=0
  while True:
   h=self.num('H');skip,count,hz=h&127,h>>9,bool(h&128);total+=skip+count
   if total>len(fs) or len(frags)>len(fs)+1:raise ValueError('Schema bounds: '+name)
   frags.append((skip,count,hz));zero+=count if hz else 0
   if h&256:break
  bits=int.from_bytes(self.raw(1 if zero<=8 else 2 if zero<=16 else ((zero+31)//32)*4),'little') if zero else 0
  index=zi=0;result={}
  for skip,count,hz in frags:
   index+=skip
   for _ in range(count):
    key,t=fs[index];iszero=bool(bits&(1<<zi)) if hz else False
    if hz:zi+=1
    try:result[key]=None if iszero else self.value(t)
    except (ValueError,KeyError,UnicodeError,struct.error) as e:raise ValueError(name+'.'+key+': '+str(e)) from e
    index+=1
  return result
 def value(self,t):
  k=t[0];numeric={0:'B',1:'B',2:'i',3:'f',4:'i',7:'d',12:'i',18:'Q',19:'I',20:'H',21:'q',22:'h',23:'b'}
  if k in numeric:return self.num(numeric[k])
  if k==5:return self.name()
  if k==10:return self.string()
  if k==11:
   flags=self.num('I');history=self.num('b')
   if history==11:return {'table':self.name(),'key':self.string()}
   if history==0:return {'namespace':self.string(),'key':self.string(),'source':self.string()}
   if history==-1:return {'empty':True,'culture':self.string() if self.num('i') else ''}
   raise ValueError('Unsupported FText history')
  if k==9:return self.obj(t[1])
  if k==8:return [self.value(t[1]) for _ in range(self.count())]
  if k in (24,25):
   if self.num('i')!=0:raise ValueError('Removed map/set entries not supported')
   n=self.count()
   return [(self.value(t[1]),self.value(t[2])) for _ in range(n)] if k==24 else [self.value(t[1]) for _ in range(n)]
  if k in (15,16,17):return {'package':self.name(),'asset':self.name(),'sub':self.string()}
  if k==26:
   if self.p+8<=len(self.b):
    i,num=struct.unpack_from('<II',self.b,self.p)
    if i<len(self.names) and num==0 and self.names[i].startswith(t[2]+'::'):return self.name()
   return self.value(t[1])
  if k==6:return [self.num('i'),self.name()]
  if k==13:return [[self.num('i'),self.name()] for _ in range(self.count())]
  raise ValueError('Unsupported property type: '+str(k))
