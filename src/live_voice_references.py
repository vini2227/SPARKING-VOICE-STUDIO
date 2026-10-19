"""Revalidate cue relationships against installed assets, independently of audio-bank bytes."""
import copy,functools
from contextlib import contextmanager
import struct
import hashlib,json,re,threading
from pathlib import Path
import core,game_installation,game_references
from zen_reference_reader import Game

SCHEMA=10
_lock=threading.RLock();_games={};_actors={};_hashes={}

def schema_data():
 path=core.APP/'Data/voice_reference_schemas.json';b=path.read_bytes();return json.loads(b),hashlib.sha256(b).hexdigest()

def _current_token(cfg):
 identity=game_installation.identity(cfg)
 folder=Path(str(cfg.get('game') or ''))/'SparkingZERO/Content/Paks'
 globals=[]
 for name in ('global.utoc','global.ucas'):
  p=folder/name
  if p.is_file():
   s=p.stat();globals.append((name,s.st_size,s.st_mtime_ns,s.st_ctime_ns))
 return hashlib.sha256(json.dumps([identity,globals],separators=(',',':')).encode()).hexdigest()[:24] if identity else None

def token(cfg):
 return game_installation.operation_value(cfg,'voice_reference_token',lambda:_current_token(cfg))

@contextmanager
def bank_read_scope(cfg):
 before=token(cfg)
 with game_installation.checked_inventory(cfg):
  yield
 if before!=token(cfg):raise ValueError('Game changed during bank reference validation')

def checked_bank_read(method):
 @functools.wraps(method)
 def read(self,cfg,*args,**kwargs):
  with bank_read_scope(cfg):return method(self,cfg,*args,**kwargs)
 return read

def relative(value):
 if not value:return None
 value=value.replace('\\','/')
 if value.startswith('/Game/'):value=value[6:]+('' if value.endswith('.uasset') else '.uasset')
 if value.startswith('Content/'):value=value[8:]
 if value.startswith('SS/') and '..' not in Path(value).parts:return value
 return None

def asset_hash(cfg,rel):
 t=token(cfg);key=(t,rel)
 if key not in _hashes:
  p=game_references.asset(cfg,rel);_hashes[key]=hashlib.sha256(p.read_bytes()).hexdigest()
 return _hashes[key]

def game(cfg):
 t=token(cfg);data,digest=schema_data();key=(t,digest)
 if key not in _games:
  _games.clear();_games[key]=Game(cfg,data['schemas'],data['enums'])
 return _games[key],digest

def text_cue(text,actor):
 if not isinstance(text,dict):return None
 key=text.get('key','')
 if not re.fullmatch('ST_'+re.escape(actor)+r'_\d{4}',key):return None
 if text.get('namespace')!='ST_VOICE_TEXT' and text.get('table')!='/Game/SS/StringTables/Voice/Voice_'+actor+'.Voice_'+actor:return None
 return key[3:]

def bound_dialogue_cue(text,bound_names):
 if not isinstance(text,dict):return None
 key=text.get('key','')
 match=re.fullmatch(r'ST_(\d{4}_\d{2})_(\d{4})',key)
 if not match:return None
 cue=key[3:]
 if cue not in bound_names:return None
 # A foreign speaker is accepted only when the exact logical cue exists in this bank.
 if text.get('namespace')!='ST_VOICE_TEXT' and text.get('table')!='/Game/SS/StringTables/Voice/Voice_'+match[1]+'.Voice_'+match[1]:return None
 return cue

def action_group(action):
 match=re.match(r'act(?:EXA\d+|SPM\d+|ULT\d*)(?=[A-Z_]|$)',action or '')
 return match[0] if match else action

def participant_text(payload):
 """Only explicit self battle-voice requests; never opponent damage or arbitrary subtitles."""
 cv=payload.get('BattleConversation') or {}
 if payload.get('IsBattleVoice')!=1 or (payload.get('TargetType') or 0)!=0 or (cv.get('BattleConversationMode') or 0)!=0 or cv.get('SoundNameSuffix') or cv.get('ConversationVoiceMap'):return None
 text=cv.get('Text') or {};key=text.get('key','')
 match=re.fullmatch(r'ST_(\d{4}_\d{2})_(\d{4})',key)
 if not match or (cv.get('CharacterID') or {}).get('Key') not in (None,match[1]):return None
 return text_cue(text,match[1])

def build_actor(cfg,actor):
 with _lock:
  requested_actor=actor
  if re.fullmatch(r'\d{4}_\d{2}_[A-Z]',actor):actor=actor[:7]
  t=token(cfg);schema,digest=schema_data();key=(t,digest,actor)
  if t is None:raise ValueError('No installed game available for reference validation')
  if key in _actors:return _actors[key]
  cache=core.APP/'Cache/LiveVoiceReferences'/t/(actor+'.json')
  if cache.is_file():
   try:
    value=json.loads(cache.read_text(encoding='utf-8'))
    if value.get('schema')==SCHEMA and value.get('schema_hash')==digest and value.get('token')==t and value.get('actor')==actor:_actors[key]=value;return value
   except (OSError,ValueError):pass
  g,_=game(cfg);result={'schema':SCHEMA,'schema_hash':digest,'token':t,'actor':actor,'banks':[],'contexts':[],'interactions':{},'errors':[],'sources':{}}
  def decode(rel,index=0):
   p,c,o=g.decoded(rel,index);result['sources'][rel]=hashlib.sha256(p['bytes']).hexdigest();return p,c,o
  def error(rel,e):
   item={'asset':rel,'error':str(e)}
   item.update(getattr(e,'details',{}))
   if item not in result['errors']:result['errors'].append(item)
  def target(pkg,index):
   ref=g.resolve(pkg,index)
   if not ref or 'relative' not in ref:raise ValueError('Expected package asset reference')
   return ref
  charrel='SS/MasterDataAsset/CharacterData/CharacterData_'+actor+'.uasset'
  try:
   charpkg,cls,obj=decode(charrel);record=obj.get('CharacterDataAssetRecord')
   if cls!='SSCharacterDataAsset' or not record or not re.fullmatch(r'\d{4}_\d{2}',record.get('AlNumId') or ''):raise ValueError('Invalid character identity')
   snd=target(charpkg,record.get('SoundDataAsset'));sp,sc,sd=decode(snd['relative'],snd['export'])
   if sc!='KoratSoundDataAsset':raise ValueError('Invalid character sound data class')
   bindings=[sd.get(k) or {} for k in ('VoiceCueSheet','VoiceCueSheetUS')]
   bindings += [v for k,v in (sd.get('EachCostumeVoiceCueSheetMap') or [])+(sd.get('EachCostumeVoiceCueSheetUSMap') or [])]
   for value in bindings:
    name=value.get('asset','')
    if re.fullmatch(r'BTLCV_\d{4}_\d{2}(?:_[A-Z])?_(JP|US)',name) and value.get('package')=='/Game/SS/Sounds/Battle_VOICE/'+name[-2:]+'/'+name:result['banks'].append(name)
   if not any(name[6:-3]==requested_actor for name in result['banks']):raise ValueError('Character sound data does not bind the requested bank')
   result['record_actor']=record['AlNumId'];result['cue_actor']=actor
  except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:
   error(charrel,e);record=None
  bound_names=set();bound_ids={}
  if record:
   for bank in result['banks']:
    try:
     bp=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+bank[-2:]+'/'+bank+'.uasset');raw=bp.read_bytes();at=raw.index(b'@UTF')
     cue_ids,cue_names=cue_index(raw[at:at+core.UTF(raw,at).size]);bound_names.update(cue_names)
     for cue_id,names in cue_ids.items():bound_ids.setdefault(cue_id,set()).update(names)
    except (OSError,ValueError,KeyError) as exc:error(str(bp) if 'bp' in locals() else bank,exc)
   fate=record.get('FateData') or {}
   def interaction(text,event,other=None,order=None):
    cue=text_cue(text,actor)
    if cue:result['interactions'].setdefault(cue,[]).append({'cue_name':cue,'actor_id':actor,'actor_name':actor,'event':event,'target_id':other,'target_name':other,'order':order,'source_asset':charrel})
   for event,value in fate.get('GeneralFateDataMap2') or []:
    name=event.split('::')[-1] if isinstance(event,str) else schema['enums'].get('EGeneralFateDataType',{}).get(str(event),'').split('::')[-1]
    if name:
     for text in (value or {}).get('VoiceTexts') or []:interaction(text,name)
   for field,event in (('IntroductionSpecialFateDataMap','Introduction'),('VictorySpecialFateDataMap','Victory'),('ChangeSpecialFateDataMap','Change')):
    for other,value in fate.get(field) or []:
     other=(other or {}).get('Key')
     if not other or not re.fullmatch(r'\d{4}_\d{2}',other):continue
     for text in (value or {}).get('VoiceTexts') or []:interaction(text,event,other,(value or {}).get('OrderType'))
   subtitle_records={};subtitle_rel=None
   try:
    ptr=(record.get('CommonAssets') or {}).get('SubtitlesData')
    if ptr:
     ref=target(charpkg,ptr);subpkg,subcls,subdata=decode(ref['relative'],ref['export']);subtitle_rel=ref['relative']
     if subcls!='SSCharacterSubtitlesDataAsset':raise ValueError('Character subtitle class mismatch')
     for pattern,value in subdata.get('Records') or []:
      label=(pattern or {}).get('Key')
      if not label:continue
      names=[]
      for text in value.get('SubtilesIDArray') or []:
       name=text.removeprefix('ST_')
       if re.fullmatch(re.escape(actor)+r'_\d{4}',name):names.append(name)
      subtitle_records[label]=names
      for name in names:result['contexts'].append({'action':'Subtitles: '+label,'cue_name':name,'root':charrel,'child':subtitle_rel,'chain':[subtitle_rel],'source_kind':'character_subtitles','subtitle_pattern':label,'subtitle_asset':subtitle_rel,'character_data':charrel,'sound_data':snd['relative']})
   except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:error(charrel,e)
   # The configured conditional table is read from this installation, not from a previous bank.
   condrel='SS/Blueprints/ConditonalPlayVoiceData.uasset'
   try:
    cp,cc,cd=decode(condrel)
    if cc!='SSConditionalPlayVoiceDataAsset':raise ValueError('Conditional voice class mismatch')
    for name,condition in cd.get('Records') or []:
     typ=condition.get('ConditionalTyoe') or 0
     if typ not in (0,1):continue
     action='Conditional: '+('RemainingHP' if typ==0 else 'RemainingTime')+' / SettingValue='+str(condition.get('SettingValue') or 0)
     if typ==1:action+=' / IsWinnerVoice='+str(bool(condition.get('IsWinnerVoice'))).lower()
     for cue_id in condition.get('SoundCueID') or []:
      result['contexts'].append({'action':action,'cue_id':cue_id,'root':condrel,'child':snd['relative'],'chain':['Records['+name+'].SoundCueID'],'source_kind':'conditional_voice','condition':condition,'condition_record':name,'action_categories':cd.get('ActionCategoryArray') or [],'usmap_sha256':schema['source_usmap_sha256']})
   except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:error(condrel,e)
   import extended_voice_references
   completed_animations=extended_voice_references.animation_cache(cfg,digest)
   nodes={};animations={};chain_records={};pattern_records={};sequence_participants={};participant_banks={};participant_groups={}
   def participant_bank(name):
    speaker=name[:7]
    if speaker not in participant_banks:
     found=None
     for language in ('US','JP'):
      rel='SS/Sounds/Battle_VOICE/'+language+'/BTLCV_'+speaker+'_'+language+'.uasset'
      try:
       path=game_references.asset(cfg,rel);raw=path.read_bytes();at=raw.index(b'@UTF');acb=raw[at:at+core.UTF(raw,at).size]
       _,names=cue_index(acb);found=(rel,set(names));result['sources'][rel]=hashlib.sha256(raw).hexdigest();break
      except (OSError,ValueError,KeyError):continue
     participant_banks[speaker]=found
    found=participant_banks[speaker]
    return found[0] if found and name in found[1] else None
   chainrel='SS/Blueprints/ChainPlaySoundData.uasset';patternrel='SS/Blueprints/PatternVoiceData.uasset'
   for source,expected,records in ((chainrel,'KoratChainPlaySoundDataAsset',chain_records),(patternrel,'KoratPatternVoiceDataAsset',pattern_records)):
    try:
     cp,cc,cd=decode(source)
     if cc!=expected:raise ValueError('Sound control class mismatch')
     records.update(cd.get('Records') or [])
    except (OSError,ValueError,KeyError) as exc:error(source,exc)
   def sound_hits(obj):
    hits=[]
    if obj.get('SheetType')!=1 or obj.get('SoundGroupType')!=3:return hits
    cue=obj.get('SoundCueID');name=obj.get('SoundCueName')
    if isinstance(cue,int) and cue>0 and (cue<880000 or len(bound_ids.get(cue,set()))==1):hits.append({'cue_id':cue,'cue_name':name or None})
    elif name in bound_names:hits.append({'cue_name':name})
    for key,branch in obj.get('SoundBranches') or []:
     if branch.get('SheetType')!=1:continue
     id=branch.get('CueId');name=branch.get('CueName')
     if isinstance(id,int) and id>0 and (id<880000 or len(bound_ids.get(id,set()))==1):hits.append({'cue_id':id,'cue_name':name or None,'source_kind':'sound_branch','sound_branch':(key or {}).get('Key')})
     elif name in bound_names:hits.append({'cue_name':name,'source_kind':'sound_branch','sound_branch':(key or {}).get('Key')})
    pattern=(obj.get('PatternName') or {}).get('Key');data=pattern_records.get(pattern) or {};id=data.get('DefaultCueID')
    if isinstance(id,int) and id>0 and (id<880000 or len(bound_ids.get(id,set()))==1):hits.append({'cue_id':id,'source_kind':'sound_pattern','sound_pattern':pattern,'reference_chain':[patternrel]})
    return hits
   def scan_sequence(rel,seen=None):
    seen=set() if seen is None else seen
    if rel in seen or len(seen)>24:return []
    if rel not in nodes:
     hits=[];links=[];sequence_participants[rel]=[]
     try:
      pkg=g.package(rel);result['sources'][rel]=hashlib.sha256(pkg['bytes']).hexdigest()
      for i,e in enumerate(pkg['exports']):
       try:cls=g.resolve_global(pkg,e['class_index'])
       except (ValueError,KeyError) as exc:
        error(rel,exc);continue
       if cls and cls.get('module')=='/Script/SS' and cls.get('script') in ('KoratSequenceSoundPlayer','KoratMovieSceneBattleSubtitleSection'):
        try:
         p,c,o=decode(rel,i)
         if c=='KoratSequenceSoundPlayer' and o.get('SheetType')==1 and o.get('SoundGroupType')==3:
          hits += [dict(hit,export_name=e['name']) for hit in sound_hits(o)]
          if o.get('bEnableChainPlaySound'):
           key=(o.get('ChainPlaySoundData') or {}).get('Key')
           for hit in sound_hits(chain_records.get(key) or {}):hits.append(dict(hit,source_kind='chain_sound',chain_sound_key=key,reference_chain=[chainrel]+hit.get('reference_chain',[])))
         if c=='KoratMovieSceneBattleSubtitleSection':
          for value in o.values():
           if not isinstance(value,dict) or 'KeyValues' not in value:continue
           if len(value.get('Times') or [])!=len(value.get('KeyValues') or []):raise ValueError('Subtitle key/time mismatch')
           for time,payload in zip(value.get('Times') or [],value.get('KeyValues') or []):
            cv=payload.get('BattleConversation') or {}
            participant=participant_text(payload)
            if participant:
             bank_asset=participant_bank(participant)
             if bank_asset:
              item={'actor':participant[:7],'cue_name':participant,'sequence_asset':rel,'bank_asset':bank_asset,'time_frame':time}
              if item not in sequence_participants[rel]:sequence_participants[rel].append(item)
            if payload.get('IsBattleVoice')!=1 or (payload.get('TargetType') or 0)!=0 or (cv.get('BattleConversationMode') or 0)!=0 or cv.get('SoundNameSuffix') or cv.get('ConversationVoiceMap') or (cv.get('CharacterID') or {}).get('Key') not in (None,actor):continue
            cue=bound_dialogue_cue(cv.get('Text'),bound_names)
            if cue:hits.append({'cue_name':cue,'source_kind':'battle_dialogue','text_key':'ST_'+cue,'target':'Myself','is_battle_voice':True,'time_frame':time,'speaker_actor':cue[:7],'shared_participant':cue[:7]!=actor})
            elif (cv.get('PatternName') or {}).get('Key') in subtitle_records:
             pattern=cv['PatternName']['Key']
             for name in subtitle_records[pattern]:hits.append({'cue_name':name,'source_kind':'battle_dialogue_pattern','text_key':'ST_'+name,'target':'Myself','is_battle_voice':True,'time_frame':time,'subtitle_pattern':pattern,'subtitle_asset':subtitle_rel})
        except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as exc:error(rel,exc)
      for imp in pkg['import_map']:
       try:
        if imp>>62!=2:continue
        pidx=(imp&0x3fffffffffffffff)>>32;ids=g.imports.get(pkg['pid'],[])
        if pidx>=len(ids):raise ValueError('Bad imported package index')
        path=g.packages.get(ids[pidx])
        # Only declared LevelSequence imports are followed.
        if path and path.startswith(('SS/Sounds/','SS/InGameComp/','SS/Effects/')):
         ref=g.resolve_global(pkg,imp);tp=g.package(ref['relative']);tc=g.resolve_global(tp,tp['exports'][ref['export']]['class_index'])
         if tc and tc.get('script')=='LevelSequence' and ref['relative']!=rel:links.append(ref['relative'])
       except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as exc:error(rel,exc)
     except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:error(rel,e)
     nodes[rel]=(hits,sorted(set(links)))
    hits,links=nodes[rel];out=[([rel],h) for h in hits]
    for link in links:
     for chain,hit in scan_sequence(link,seen|{rel}):out.append(([rel]+chain,hit))
     for item in sequence_participants.get(link,[]):
      if item not in sequence_participants[rel]:sequence_participants[rel].append(item)
    return out
   def visit(root,action,index,pkg,inheritance=None):
    try:
     ref=target(pkg,index);child,cls,obj=decode(ref['relative'],ref['export'])
     if cls=='KoratMLSDataAsset':arrays=[('MLS',(obj.get('MontageLevelSequence') or {}).get('MontageLevelSequences') or [])]
     elif cls=='KoratCombinationDataAsset':arrays=[('Oneself',obj.get('MontageLevelSequenceOneself') or [])]
     else:raise ValueError('Action asset class mismatch')
     for role,items in arrays:
      for item in items:
       montage=relative((item.get('Montage') or {}).get('package'))
       if montage:
        if montage not in animations:
         import animation_voice_references
         animations[montage]=completed_animations['hits'].get(montage,[]) if extended_voice_references.covered_animation(completed_animations,montage) else animation_voice_references.animation_hits(g,montage,report=result['errors'])
        for hit in animations[montage]:
         result['sources'].update(hit['source_hashes'])
         context=dict(hit,action=action,role=role,root=root,child=ref['relative'],character_data=charrel,sound_data=snd['relative'])
         result['contexts'].append(context)
       value=item.get('LevelSequence') or {};path=relative(value.get('package'))
       if not path:continue
       sequence_hits=scan_sequence(path)
       if not inheritance or len(inheritance)<2:
        members=participant_groups.setdefault(action_group(action),[])
        for item in sequence_participants.get(path,[]):
         if item not in members:members.append(item)
       for chain,hit in sequence_hits:
        context=dict(hit,action=action,role=role,root=root,child=ref['relative'],chain=chain+hit.get('reference_chain',[]),character_data=charrel,sound_data=snd['relative'])
        if not inheritance or len(inheritance)<2:context['action_participants']=sequence_participants.get(path,[])
        if inheritance and not context.get('source_kind'):context.update(source_kind='inherited_mls',inheritance=inheritance)
        result['contexts'].append(context)
    except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:error(root,e)
   def roots(rel,index=0,seen=None,inheritance=None):
    seen=set() if seen is None else seen
    if rel in seen or len(seen)>12:return
    try:
     pkg,cls,obj=decode(rel,index)
     if cls=='KoratCharacterMLSDataAsset':
      for action,ptr in obj.get('PtrRecordsByDataList') or []:
       if (action or {}).get('Key') and ptr:visit(rel,action['Key'],ptr,pkg,inheritance)
      default=(obj.get('DefaultCharacterData') or {}).get('Key')
      if default and re.fullmatch(r'\d{4}_\d{2}',default):
       other='SS/MasterDataAsset/MontageLevelSequence/MLS_'+default+'.uasset'
       if other!=rel:roots(other,seen=seen|{rel},inheritance=(inheritance or [actor])+[default])
     elif cls=='KoratCharacterCombinationDataAsset':
      for action,value in obj.get('Records') or []:
       for ptr in [value.get('DataAsset')]+[v for k,v in value.get('DesignatedDataList') or []]:
        if (action or {}).get('Key') and ptr:visit(rel,action['Key'],ptr,pkg)
     else:raise ValueError('Configured action root class mismatch')
    except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:error(rel,e)
   for field in ('CharacterMLS','CharacterCombination'):
    if not record.get(field):continue
    try:
     ref=target(charpkg,record.get(field));roots(ref['relative'],ref['export'])
    except (OSError,ValueError,KeyError,UnicodeError,IndexError,TypeError,struct.error) as e:error(charrel,e)
  # Stages of one declared attack share its participants; secondary attacks stay separate.
  groups=participant_groups if record else {}
  for context in result['contexts']:
   group=action_group(context.get('action'))
   for participant in context.get('action_participants',[]):
    items=groups.setdefault(group,[])
    if participant not in items:items.append(participant)
  for context in result['contexts']:
   participants=groups.get(action_group(context.get('action')),[])
   if participants:context['action_participants']=participants
  if token(cfg)!=t:raise ValueError('Game changed during voice-reference analysis')
  core.write_json(cache,result);_actors[key]=result
  # Keep metadata indexes, but release parsed package payloads after this actor.
  if hasattr(g,'cache'):g.cache.clear()
  return result

def cue_index(acb):
 root=core.UTF(acb);cues=root.child('CueTable').rows;names=root.child('CueNameTable').rows
 byid={};byname={}
 for entry in names:
  cue_id=cues[entry['CueIndex']]['CueId'];name=entry['CueName'];byid.setdefault(cue_id,set()).add(name);byname.setdefault(name,set()).add(cue_id)
 return byid,byname

def dependency_list(c):
 values=[c.get('root'),c.get('child'),c.get('character_data'),c.get('sound_data'),c.get('subtitle_asset')]+c.get('chain',[])
 for participant in c.get('action_participants',[]):values.extend([participant.get('sequence_asset'),participant.get('bank_asset')])
 if c.get('action_metadata'):values.append(c['action_metadata'].get('asset'))
 return sorted({r for v in values if (r:=relative(v))})

def _validated_contexts(cfg,bank_name,acb):
 actor=bank_name[6:-3];live=build_actor(cfg,actor);byid,byname=cue_index(acb);out=[];seen=set()
 if bank_name not in live['banks']:
  return [],live
 # Compare logical pairs against the current game as well as the opened/edited bank.
 p=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+bank_name[-2:]+'/'+bank_name+'.uasset');b=p.read_bytes();start=b.index(b'@UTF');current=b[start:start+core.UTF(b,start).size]
 current_ids,current_names=cue_index(current)
 byid={id:names&current_ids.get(id,set()) for id,names in byid.items()}
 byname={name:ids&current_names.get(name,set()) for name,ids in byname.items()}
 live=dict(live,current_cues={name:sorted(ids) for name,ids in byname.items() if ids})
 def add(c):
  marker=json.dumps(c,sort_keys=True,ensure_ascii=False)
  if marker not in seen:seen.add(marker);out.append(c)
 for context in live['contexts']:
  if context.get('bank') and context['bank']!=bank_name:continue
  cue_id=context.get('cue_id');cue_name=context.get('cue_name')
  if cue_name:
   if cue_id is not None and cue_name not in byid.get(cue_id,set()):continue
   ids=byname.get(cue_name,set()) if cue_id is None else {cue_id}
  else:ids={cue_id};cue_name=None
  for id in ids:
   for name in ([cue_name] if cue_name else sorted(byid.get(id,set()))):
    if name not in byid.get(id,set()):continue
    add(dict(context,cue_id=id,cue_name=name,reference_validation='live_assets'))
 import extended_voice_references
 for context in extended_voice_references.contexts(cfg,bank_name,acb):
  if context['cue_name'] in byid.get(context['cue_id'],set()):add(context)
 # Preserve previously verified paths individually when every source asset still matches.
 try:baseline=json.loads((core.APP/'Data/voice_reference_dependencies.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):baseline={}
 import attack_context
 for context in attack_context.catalog().get('characters',{}).get(actor,[]):
  if context['cue_name'] not in byid.get(context['cue_id'],set()):continue
  deps=sorted(set(dependency_list(context)+['SS/MasterDataAsset/CharacterData/CharacterData_'+live.get('cue_actor',actor)+'.uasset']))
  root=relative(context.get('root'))
  if root and root not in live['sources']:continue
  if not deps or any(dep not in baseline.get('assets',{}) for dep in deps):continue
  try:
   if all(asset_hash(cfg,dep)==baseline['assets'][dep] for dep in deps):add(dict(context,reference_validation='unchanged_source_assets'))
  except (OSError,ValueError):continue
 import cue_name_functions
 for context in cue_name_functions.contexts(bank_name,byid):add(context)
 if token(cfg)!=live['token']:raise ValueError('Game changed during cue validation')
 return out,live

def contexts(cfg,bank_name,acb):
 if game_installation._operation_state(cfg) is None:return _validated_contexts(cfg,bank_name,acb)
 key=('validated_contexts',bank_name,hashlib.sha256(acb).digest(),schema_data()[1])
 result=game_installation.operation_value(cfg,key,lambda:_validated_contexts(cfg,bank_name,acb))
 return copy.deepcopy(result)

def annotations(cfg,bank_name,acb,rows):
 contexts_now,data=contexts(cfg,bank_name,acb);byname={name:set(ids) for name,ids in data.get('current_cues',{}).items()}
 import voice_context
 try:baseline=json.loads((core.APP/'Data/voice_reference_dependencies.json').read_text(encoding='utf-8')).get('assets',{})
 except (OSError,ValueError):baseline={}
 for row in rows:
  row.update(interactions=[],emotes=[],usage_contexts=[])
  if bank_name not in data['banks']:continue
  for name in row['cue_names']:
   if not byname.get(name,set()).intersection(row['cue_ids']):continue
   row['interactions'].extend(data['interactions'].get(name,[]))
   for entry in voice_context.catalog().get(name,{}).get('emotes',[]):
    source=entry.get('source','').replace('\\','/');rel=relative(source.split('/Content/',1)[-1])
    if not rel or rel not in baseline:continue
    try:
     if asset_hash(cfg,rel)==baseline[rel] and entry not in row['emotes']:row['emotes'].append(entry)
    except (OSError,ValueError):pass
  if any(c['cue_id'] in row['cue_ids'] and c['cue_name'] in row['cue_names'] and c['cue_id']==10758 and c['action']=='actGRCRA' for c in contexts_now):row['usage_contexts']=['GuardBreak']
 return data
