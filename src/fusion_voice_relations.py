"""Fusion partners/results from current CharacterData, separate from cue playback."""
import re,functools,json,copy
import core,live_voice_references as live

def valid_actor(value):return isinstance(value,str) and bool(re.fullmatch(r'\d{4}_\d{2}',value))

def record_routes(actor,record,root):
 if record.get('AlNumId')!=actor:return []
 result=[]
 for field,kind,partners_field in [('Fusion','Metamoru','FusionCharacters'),('Potara','Potara','PotaraCharacters')]:
  for i,entry in enumerate((record.get('BattleAssets') or {}).get(field) or []):
   output=(entry.get('ChangeCharacter') or {}).get('Key')
   partners=sorted({p.get('Key') for p in entry.get(partners_field) or [] if valid_actor(p.get('Key'))})
   actions=sorted({v.get('Key') for v in (entry.get('ChangeCharacterActinData') or {}).values() if isinstance(v,dict) and v.get('Key')})
   if not valid_actor(output) or not partners:continue
   result.append(dict(owner=actor,kind=kind,result=output,partners=partners,actions=actions,root=root,property_path='CharacterDataAssetRecord.BattleAssets.'+field+'['+str(i)+']'))
 return result

@functools.lru_cache(maxsize=2)
def all_catalog(token,schema_hash,cfg_json):
 cfg=json.loads(cfg_json);g,_=live.game(cfg);result=[]
 for root in sorted(g.entries):
  m=re.fullmatch(r'SS/MasterDataAsset/CharacterData/CharacterData_(\d{4}_\d{2})\.uasset',root)
  if not m:continue
  try:
   _,cls,obj=g.decoded(root)
   if cls=='SSCharacterDataAsset':result.extend(record_routes(m[1],obj.get('CharacterDataAssetRecord') or {},root));result.extend(form_routes(m[1],obj.get('CharacterDataAssetRecord') or {},root))
  finally:
   # Only small route metadata remains in memory. No new persistent cache.
   if hasattr(g,'cache'):g.cache.clear()
 if live.token(cfg)!=token:raise ValueError('Game changed while reading fusion routes')
 return tuple(result)

def fusion_kind(context):
 action=context.get('action','')
 if action.startswith('actFSN'):return 'Metamoru'
 if action.startswith('actPTR'):return 'Potara'
 if context.get('source_kind')=='character_subtitles':
  pattern=context.get('subtitle_pattern','')
  if pattern.startswith('フュージョン'):return 'Metamoru'
  if pattern in ('合体前セリフ1','合体前セリフ2','合体完了'):return 'any'

def relations(actor,context,routes):
 kind=fusion_kind(context)
 if not kind:return []
 own=[r for r in routes if r['owner']==actor and kind in ('any',r['kind'])]
 # Completed fusion voices in the resulting character can identify its
 # ingredients. A pre-fusion line cannot borrow an incoming relationship.
 if not own and context.get('subtitle_pattern')=='合体完了':
  own=[r for r in routes if r['result']==actor and kind in ('any',r['kind'])]
 result=[]
 for r in own:
  if context['action'].startswith('act') and context['action'] not in r['actions']:continue
  result.append(dict(r,cue_name=context['cue_name'],cue_id=context['cue_id'],action=context['action'],cue_source=context.get('child'),source_kind=context.get('source_kind'),direction='incoming' if r['result']==actor and r['owner']!=actor else 'outgoing'))
 return result

def attach(bank_name,acb,rows,cfg):
 for row in rows:row['fusion_relations']=[]
 if cfg is None or live.token(cfg) is None:return
 pending=[r for r in rows if any(fusion_kind(c) for c in r.get('attack_contexts',[]))]
 if not pending:return
 token=live.token(cfg)
 try:
  # These contexts have already passed installed/opened cue-pair checks.
  opened,_=live.cue_index(acb)
  import game_references
  raw=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+bank_name[-2:]+'/'+bank_name+'.uasset').read_bytes();at=raw.index(b'@UTF')
  installed,_=live.cue_index(raw[at:at+core.UTF(raw,at).size])
  routes=catalog(token,live.schema_data()[1],json.dumps(cfg,sort_keys=True));out=[]
  for row in pending:
   found=[]
   for c in row.get('attack_contexts',[]):
    if c.get('reference_validation') not in ('live_assets','unchanged_source_assets'):continue
    if c.get('cue_name') not in row['cue_names'] or c.get('cue_id') not in row['cue_ids']:continue
    if c['cue_name'] not in opened.get(c['cue_id'],set()) or c['cue_name'] not in installed.get(c['cue_id'],set()):continue
    found.extend(relations(bank_name[6:13],c,routes))
   out.append((row,[dict(v) for v in {json.dumps(v,sort_keys=True):v for v in found}.values()]))
  if token!=live.token(cfg):return
  for row,found in out:row['fusion_relations']=found
 except (OSError,ValueError,KeyError,IndexError,TypeError):return

def group_names(actors,language,compact):
 import game_characters
 names=[game_characters.name(a,language) for a in sorted(set(actors))]
 if not compact:return ', '.join(dict.fromkeys(names))
 groups={}
 for actor,name in zip(sorted(set(actors)),names):groups.setdefault(name.split(',')[0],[]).append(name)
 short=list(groups)
 return ', '.join(dict.fromkeys(short[:3]))+(' (+'+str(len(short)-3)+')' if len(short)>3 else '')

def labels(row,language,compact=True):
 from i18n import Translator
 import voice_context as vc
 groups={}
 for r in row.get('fusion_relations',[]):groups.setdefault((r['kind'],None if compact else r['action'],r['direction']),[]).append(r)
 result=[]
 for (kind,action,direction),routes in groups.items():
  heading=Translator(language).logical('Fusão Metamoru' if kind=='Metamoru' else 'Fusão Potara')
  partners={p for r in routes for p in r['partners']}
  owners={r['owner'] for r in routes}
  if direction=='incoming':
   pairs=sorted({' + '.join(sorted([group_names([r['owner']],language,compact),group_names(r['partners'],language,compact)])) for r in routes})
   participants=' / '.join(pairs[:2] if compact else pairs)+(' (+'+str(len(pairs)-2)+')' if compact and len(pairs)>2 else '')
  else:participants=group_names(partners,language,compact)
  outputs=group_names({r['result'] for r in routes},language,compact)
  if compact:
   import game_characters
   hidden=len({r['result'] for r in routes})-len({game_characters.name(r['result'],language).split(',')[0] for r in routes})
   if hidden>0:outputs+=' (+'+str(hidden)+')'
  actions=sorted({r['action'] for r in routes})
  stages=[a.removeprefix('act') if a.startswith('act') else vc.context_action_text(a,language).split(': ',1)[-1] for a in actions]
  stage=', '.join(stages[:2] if compact else stages)+(' (+'+str(len(stages)-2)+')' if compact and len(stages)>2 else '')
  result.append(heading+' — '+participants+' → '+outputs+' | '+stage)
 return list(dict.fromkeys(result))

def details(row,language):
 from i18n import Translator
 import game_characters
 result=labels(row,language,False)
 if not result:return ''
 result.append(Translator(language).logical('Parceiros e resultados configurados no jogo; o mapeamento de legenda não confirma a execução desta fala.'))
 for r in row['fusion_relations']:
  result.append(r['root']+' | '+r['property_path']+' | '+r['cue_name']+' | '+str(r['cue_id']))
  if r.get('cue_source'):result.append(r['cue_source'])
 return '\n'.join(dict.fromkeys(result))

def form_routes(actor,record,root):
 if record.get('AlNumId')!=actor:return []
 result=[]
 for i,entry in enumerate((record.get('BattleAssets') or {}).get('FormChange') or []):
  output=(entry.get('ChangeCharacter') or {}).get('Key')
  if not valid_actor(output):continue
  supports=[p for p in entry.get('UnionSupportCharacters') or [] if valid_actor((p.get('SubCharacter') or {}).get('Key'))]
  actions=sorted({v.get('Key') for v in (entry.get('ChangeCharacterActinData') or {}).values() if isinstance(v,dict) and v.get('Key')})
  result.append(dict(owner=actor,kind='FormChange',result=output,partners=sorted({p['SubCharacter']['Key'] for p in supports}),conditions=supports,actions=actions,root=root,property_path='CharacterDataAssetRecord.BattleAssets.FormChange['+str(i)+']'))
 return result

def catalog(token,schema_hash,cfg_json):
 return tuple(r for r in all_catalog(token,schema_hash,cfg_json) if r['kind']!='FormChange')
