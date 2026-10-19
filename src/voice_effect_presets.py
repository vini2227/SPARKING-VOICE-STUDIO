"""Named personal effect settings, separate from built-in presets and audio."""
import json,threading,uuid
import core,voice_effects
_lock=threading.RLock()
def path():return core.APP/'voice_effect_presets.json'
def load():
 p=path()
 if not p.exists():return {}
 if p.stat().st_size>256*1024:raise ValueError('Arquivo de presets inválido.')
 data=json.loads(p.read_text(encoding='utf-8'))
 if not isinstance(data,dict) or data.get('schema')!=1 or not isinstance(data.get('presets'),dict) or len(data['presets'])>100:raise ValueError('Arquivo de presets inválido.')
 result={}
 for key,item in data['presets'].items():
  if not isinstance(key,str) or not key.startswith('user:') or not isinstance(item,dict):raise ValueError('Arquivo de presets inválido.')
  raw_name=item.get('name','')
  if not isinstance(raw_name,str):raise ValueError('Arquivo de presets inválido.')
  # Older personal presets may have no name; keep them selectable and deletable.
  name=valid_name(raw_name) if raw_name.strip() else ''
  result[key]={'name':name,'settings':voice_effects.validated(item['settings'])}
 return result
def valid_name(name):
 name=str(name).strip()
 if not name or len(name)>60 or any(ord(c)<32 for c in name):raise ValueError('Use um nome de 1 a 60 caracteres para o preset.')
 return name
def save(name,settings):
 name=valid_name(name);settings=voice_effects.validated(settings)
 with _lock:
  presets=load()
  if len(presets)>=100:raise ValueError('Limite de 100 presets pessoais atingido.')
  names=list(voice_effects.PRESETS)+[item['name'] for item in presets.values()]
  if name.casefold() in {value.casefold() for value in names}:raise ValueError('Esse nome já está em uso. Escolha outro.')
  key='user:'+uuid.uuid4().hex;presets[key]={'name':name,'settings':settings}
  core.write_json(path(),{'schema':1,'presets':presets})
  return key

def delete(key):
 with _lock:
  presets=load()
  if key not in presets:return False
  del presets[key]
  core.write_json(path(),{'schema':1,'presets':presets})
  return True
