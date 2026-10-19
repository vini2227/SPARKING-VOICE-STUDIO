"""Validated reverse references from story/event properties and animation notifies."""
import json,re,hashlib,functools
from pathlib import Path
import core,game_references,game_installation

@functools.lru_cache(maxsize=1)
def reader_fingerprint():
 return hashlib.sha256(b''.join((Path(__file__).parent/name).read_bytes() for name in ('animation_voice_references.py','live_properties.py','zen_reference_reader.py'))).hexdigest()

PATTERN=re.compile(r'\d{4}_\d{2}_\d{4}')

def walk(value,path=''):
 if isinstance(value,dict):
  yield path,value
  for key,item in value.items():yield from walk(item,path+'.'+key)
 elif isinstance(value,(list,tuple)):
  for i,item in enumerate(value):yield from walk(item,path+'['+str(i)+']')

def voice_name(text):
 if not isinstance(text,dict):return None
 key=text.get('key','');name=key.removeprefix('ST_')
 if not PATTERN.fullmatch(name):return None
 actor=name[:-5]
 if text.get('namespace')=='ST_VOICE_TEXT' or text.get('table')=='/Game/SS/StringTables/Voice/Voice_'+actor+'.Voice_'+actor:return name
 return None

def property_hits(obj,relative,export):
 hits=[]
 for field,value in walk(obj):
  # A verified battle-conversation payload identifies the voice, not merely displayed text.
  conversation=value.get('BattleConversation') if value.get('IsBattleVoice')==1 else value if value.get('IsBattleVoice')==1 and 'Text' in value else None
  if isinstance(conversation,dict):
   name=voice_name(conversation.get('Text'))
   if name and not conversation.get('SoundNameSuffix') and not conversation.get('ConversationVoiceMap'):
    hits.append({'cue_name':name,'source_kind':'event_dialogue','property_path':field+'.Text','text_key':'ST_'+name,'export_name':export})
  if value.get('SheetType')==1 and value.get('SoundGroupType')==3:
   name=value.get('SoundCueName')
   if PATTERN.fullmatch(name or ''):hits.append({'cue_name':name,'cue_id':value.get('SoundCueID'),'source_kind':'event_sound','property_path':field+'.SoundCueName','export_name':export})
 return hits

def scan(cfg,progress=None):
 import live_voice_references as live
 from animation_voice_references import animation_hits
 game,digest=live.game(cfg);token=live.token(cfg);sources={};cues={};errors=[];counts={'files':0,'animation_files':0,'event_files':0,'references':0};seen=set()
 paths=sorted(p for p in game.entries if p.endswith('.uasset') and (
  p.startswith(('SS/Event/','SS/Scene/','SS/MasterDataAsset/Conversation/','SS/MasterDataAsset/DragonAdventure','SS/MasterDataAsset/ModeNAD/','SS/MasterDataAsset/NAD/')) or
  (p.startswith('SS/Characters/') and '/Animation/' in p)))
 def add(hit,rel,pkg):
  name=hit['cue_name'];context=dict(hit,action=('Evento/diálogo: ' if hit['source_kind']!='animation_notify' else 'Animação: ')+Path(rel).stem,root=rel,child=hit.get('child',rel),chain=hit.get('chain',[rel]),source_hashes=hit.get('source_hashes',{rel:hashlib.sha256(pkg['bytes']).hexdigest()}))
  marker=json.dumps(context,ensure_ascii=False,sort_keys=True)
  if marker in seen:return
  seen.add(marker);cues.setdefault(name,[]).append(context);sources.update(context['source_hashes']);counts['references']+=1
 for rel in paths:
  counts['files']+=1
  try:
   pkg=game.package(rel)
   for i,e in enumerate(pkg['exports']):
    try:cls=game.resolve_global(pkg,e['class_index'])
    except (ValueError,KeyError):continue
    if not cls or 'script' not in cls:continue
    script=cls['script']
    if script in ('AnimMontage','AnimSequence','AnimComposite'):
     counts['animation_files']+=1
     for hit in animation_hits(game,rel,i,report=errors):add(hit,rel,pkg)
    elif cls.get('module')=='/Script/SS' and script in game.schemas:
     try:
      p,c,obj,tail=game.properties(rel,i);counts['event_files']+=1
      for hit in property_hits(obj,rel,e['name']):add(hit,rel,pkg)
     except (ValueError,KeyError) as exc:errors.append({'asset':rel,'class':script,'error':str(exc)})
  except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:errors.append({'asset':rel,'error':str(exc)})
  if counts['files']%200==0:
   game.cache.clear()
   if progress:progress(dict(counts,total=len(paths)))
 if token!=live.token(cfg):raise ValueError('Game changed during extended analysis')
 result={'schema':1,'animation_scan_complete':True,'reader_fingerprint':reader_fingerprint(),'schema_hash':digest,'token':token,'sources':sources,'cues':cues,'counts':dict(counts,total=len(paths)),'errors':errors,'limits':['Animation native streams are opaque; only bounded reflected properties are decoded.','No claim of exclusive story usage.','Voice requests selected by native C++ require runtime diagnosis.']}
 core.write_json(core.APP/'Data/extended_voice_contexts.json',result);catalog.cache_clear();return result

@functools.lru_cache(maxsize=1)
def catalog():
 try:return json.loads((core.APP/'Data/extended_voice_contexts.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}

def contexts(cfg,bank_name,acb):
 import live_voice_references as live
 data=catalog();out=[];byid,byname=live.cue_index(acb)
 if data.get('schema')!=1 or data.get('schema_hash')!=live.schema_data()[1]:return out
 for name,ids in byname.items():
  for entry in data.get('cues',{}).get(name,[]):
   if entry.get('bank') and entry['bank']!=bank_name:continue
   expected=entry.get('cue_id')
   if expected is not None and expected not in ids:continue
   try:
    if not entry.get('source_hashes') or not all(live.asset_hash(cfg,rel)==digest for rel,digest in entry['source_hashes'].items()):continue
   except (OSError,ValueError):continue
   for id in ids if expected is None else [expected]:out.append(dict(entry,cue_id=id,cue_name=name,reference_validation='extended_source_assets'))
 return out

def animation_cache(cfg,schema_hash):
 import live_voice_references as live
 data=catalog()
 if not data.get('animation_scan_complete') or data.get('reader_fingerprint')!=reader_fingerprint() or data.get('schema_hash')!=schema_hash or data.get('token')!=live.token(cfg):return None
 if data.get('counts',{}).get('files')!=data.get('counts',{}).get('total'):return None
 hits={}
 for entries in data.get('cues',{}).values():
  for entry in entries:
   if entry.get('source_kind')=='animation_notify':hits.setdefault(entry['root'],[]).append(entry)
 return {'hits':hits,'errors':{e['asset'] for e in data.get('errors',[])}}

def covered_animation(cache,rel):
 if cache is None or rel in cache['errors']:return False
 return rel.startswith(('SS/Event/','SS/Scene/','SS/MasterDataAsset/Conversation/','SS/MasterDataAsset/DragonAdventure','SS/MasterDataAsset/ModeNAD/','SS/MasterDataAsset/NAD/')) or (rel.startswith('SS/Characters/') and '/Animation/' in rel)
