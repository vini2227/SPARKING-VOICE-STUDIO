"""Enrich user classifications using exact source cues; keep inferences separate."""
import re,json,functools
import core,live_voice_references as live,game_references,user_voice_functions as uf

def family(action):
 match=re.fullmatch(r'act(EXA[12]|SPM[12]|ULT)[A-Za-z0-9_]*',action or '')
 return match[1] if match else None

def bucket(number):
 for lo,hi,group in ((600,609,'EXA1'),(610,619,'EXA2'),(620,649,'SPM1'),(650,679,'SPM2'),(680,699,'ULT')):
  if lo<=number<=hi:return group

def infer_group(name,contexts):
 match=re.fullmatch(r'(\d{4}_\d{2})_(\d{4})',name)
 if not match:return None
 actor,number=match[1],int(match[2]);expected=bucket(number)
 if not expected:return None
 anchors=[];families=set()
 for c in contexts:
  m=re.fullmatch(re.escape(actor)+r'_(\d{4})',c.get('cue_name',''))
  if not m or bucket(int(m[1]))!=expected:continue
  f=family(c.get('action'))
  if f:families.add(f);anchors.append(c)
 if families!={expected}:return None
 return dict(family=expected,anchors=anchors)

@functools.lru_cache(maxsize=128)
def source_contexts(token,schema_hash,actor,language,cfg_json):
 cfg=json.loads(cfg_json);data=live.build_actor(cfg,actor);bank='BTLCV_'+actor+'_'+language
 if bank not in data['banks']:return ()
 p=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+language+'/'+bank+'.uasset');blob=p.read_bytes();at=blob.index(b'@UTF');acb=blob[at:at+core.UTF(blob,at).size]
 contexts,validated=live.contexts(cfg,bank,acb)
 result=[c for c in contexts if c.get('source_kind')!='cue_name_pattern']
 _,names=live.cue_index(acb)
 charrel='SS/MasterDataAsset/CharacterData/CharacterData_'+actor+'.uasset'
 for name,entries in validated.get('interactions',{}).items():
  for id in names.get(name,set()):
   for entry in entries:result.append(dict(entry,cue_id=id,cue_name=name,action='Interaction: '+entry['event'],source_kind='origin_interaction',root=charrel,child=charrel,chain=[]))
 # The current pattern table can provide a more specific original function.
 patterns=core.pattern_functions(cfg)
 # A numbered cue may inherit the original PTN category through an alias that
 # resolves to the same waveform(s), even if its own ID is not a pattern key.
 parsed=object.__new__(core.Bank);parsed.acb=acb;parsed.root=core.UTF(acb)
 parsed.tables={k:parsed.root.child(k) for k in ('CueTable','CueNameTable','WaveformTable','SynthTable','SequenceTable','TrackTable','TrackEventTable','CommandTable')}
 cues=parsed.tables['CueTable'].rows;resolved={};aliases=[]
 for entry in parsed.tables['CueNameTable'].rows:
  cue=cues[entry['CueIndex']];waves=parsed.resolve(cue['ReferenceType'],cue['ReferenceIndex'],set())
  resolved.setdefault(entry['CueName'],set()).update(waves)
  pattern=patterns.get(cue['CueId']);english=core.description(pattern) if pattern else 'Unclassified'
  if entry['CueName'].startswith('PTN_') and english!='Unclassified':aliases.append((entry['CueName'],waves,pattern,english))
 for name,ids in names.items():
  matches=[];pattern=next((patterns[id] for id in ids if id in patterns and core.description(patterns[id])!='Unclassified'),None)
  if pattern:matches.append((None,pattern,core.description(pattern)))
  target=resolved.get(name,set())
  for alias,waves,pattern,english in aliases:
   if target and target<=waves and english not in [m[2] for m in matches]:matches.append((alias,pattern,english))
  for id in ids:
   for alias,pattern,english in matches:
    result.append(dict(cue_id=id,cue_name=name,action='Pattern: '+english,english_function=english,source_kind='origin_function',root='SS/Sounds/Battle_VOICE/'+language+'/'+bank+'.uasset',child='SS/Blueprints/PatternVoiceData.uasset',chain=[],pattern=pattern,source_alias=alias))
 return tuple(result)

def attach(bank_name,acb,rows,cfg):
 for row in rows:row['function_refinements']=[]
 if cfg is None or live.token(cfg) is None:return
 current_ids,current_names=live.cue_index(acb)
 # Gate edited/external cue pairs against the installed bank.
 p=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+bank_name[-2:]+'/'+bank_name+'.uasset');blob=p.read_bytes();at=blob.index(b'@UTF')
 installed_ids,_=live.cue_index(blob[at:at+core.UTF(blob,at).size])
 cfg_json=json.dumps(cfg,sort_keys=True);token=live.token(cfg);schema_hash=live.schema_data()[1]
 for row in rows:
  rules=uf.functions(row)
  foreign=any(re.fullmatch(r'\d{4}_\d{2}_\d{4}',name) and name[:7]!=bank_name[6:-3] for name in row.get('cue_names',[]))
  if not rules and not row.get('_manual') and not foreign:continue
  for name in row.get('cue_names',[]):
   match=re.fullmatch(r'(\d{4}_\d{2})_(\d{4})',name)
   if not match:continue
   origin=match[1]
   # Same-character and foreign-character references are both eligible.
   ids=[id for id in row['cue_ids'] if name in current_ids.get(id,set()) and name in installed_ids.get(id,set())]
   if not ids:continue
   try:contexts=source_contexts(token,schema_hash,origin,bank_name[-2:],cfg_json)
   except (OSError,ValueError,KeyError,IndexError,TypeError):continue
   exact=[c for c in contexts if c.get('cue_name')==name]
   for c in exact:
    row['function_refinements'].append(dict(c,source_cue_id=c['cue_id'],cue_id=ids[0],origin_actor=origin,refinement_kind='exact_source_cue'))
   if not exact and (rules or row.get('_manual')):
    group=infer_group(name,contexts)
    if group:row['function_refinements'].append(dict(cue_name=name,cue_id=ids[0],origin_actor=origin,refinement_kind='inferred_group',**group))
 if live.token(cfg)!=token:raise ValueError('Game changed during function refinement')

def label(context,language):
 from i18n import Translator
 tr=Translator(language)
 names={'EXA1':'Habilidade 1','EXA2':'Habilidade 2','SPM1':'Blast 1','SPM2':'Blast 2','ULT':'Ultimate'}
 if context.get('source_kind')=='origin_interaction':
  import voice_context
  return voice_context.event_label(context['event'],language)+((' — '+voice_context._character(context['target_id'],language)) if context.get('target_id') else '')
 if context.get('source_kind')=='origin_function':
  import compact_functions
  return compact_functions.function(context['english_function'],language)
 f=context.get('family') or family(context.get('action'))
 return tr.logical(names.get(f,'Referência de ação'))+((' ['+context['action']+']') if context.get('action') else '')

def has_exact_function(row):
 """Only an exact, asset-backed cue relation establishes a source function."""
 return any(c.get('refinement_kind')=='exact_source_cue'
            and c.get('cue_name') in row.get('cue_names',[])
            and c.get('cue_id') in row.get('cue_ids',[])
            and c.get('root') and c.get('child')
            for c in row.get('function_refinements',[]))
