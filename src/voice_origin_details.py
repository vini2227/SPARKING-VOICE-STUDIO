"""Explain manual functions without changing their labels, IDs or original tags."""
import json,hashlib,functools,struct,weakref,uuid,collections
import core,live_voice_references as live,user_voice_functions as uf,function_refinements as fr
_banks=weakref.WeakValueDictionary()
_foreign_anchors=collections.OrderedDict()

@functools.lru_cache(maxsize=1)
def catalog():
 try:
  value=json.loads((core.APP/'Data/manual_voice_origins.json').read_text(encoding='utf-8'))
  reader=(core.APP/'src/manual_origin_reader.py').read_text(encoding='utf-8').encode('utf-8')
  return value if value.get('schema')==1 and value.get('reader_sha256')==hashlib.sha256(reader).hexdigest() else {}
 except (OSError,ValueError):return {}

@functools.lru_cache(maxsize=512)
def source_hash(token,schema_hash,cfg_json,relative):
 cfg=json.loads(cfg_json);g,_=live.game(cfg)
 if relative not in g.entries:raise ValueError('Origin asset absent')
 store,index=g.entries[relative]
 # Read the game container directly. No extraction or persistent cache.
 return hashlib.sha256(store.read_chunk(index)).hexdigest()

def installed_acb(cfg,name):
 g,_=live.game(cfg);relative='SS/Sounds/Battle_VOICE/'+name[-2:]+'/'+name+'.uasset'
 store,index=g.entries[relative];raw=store.read_chunk(index);at=raw.index(b'@UTF')
 return raw[at:at+core.UTF(raw,at).size]

def eligible(row):
 return bool(row.get('_manual') or uf.functions(row) or row.get('function_correlations') or row.get('origin_evidence') or row.get('origin_audio'))

def anchor_matches(bank,anchor,token,cfg_json):
 name=anchor['bank'];acb=installed_acb(bank.cfg,name)
 from voice_function_correlations import metadata
 parsed=metadata(acb);waves=parsed.tables['WaveformTable'].rows;cues=parsed.tables['CueTable'].rows
 pairs={(n,i) for n in anchor['cue_names'] for i in anchor['cue_ids']};indices=set();valid_pairs=set()
 for entry in parsed.tables['CueNameTable'].rows:
  cue=cues[entry['CueIndex']]
  if (entry['CueName'],cue['CueId']) in pairs:
   resolved=parsed.resolve(cue['ReferenceType'],cue['ReferenceIndex'],set());indices.update(resolved)
   if any(('S' if waves[i]['Streaming'] else 'M')+str(waves[i]['StreamAwbId'] if waves[i]['Streaming'] else waves[i]['MemoryAwbId'])==anchor['key'] for i in resolved):valid_pairs.add((entry['CueName'],cue['CueId']))
 matching=[w for i in indices for w in [waves[i]] if ('S' if w['Streaming'] else 'M')+str(w['StreamAwbId'] if w['Streaming'] else w['MemoryAwbId'])==anchor['key']]
 if not matching:return None
 if not any((w['SamplingRate'],w['NumChannels'],w['NumSamples'])==(anchor['rate'],anchor['channels'],anchor['samples']) for w in matching):return None
 if name==bank.name:awb=bank.stream if anchor['streaming'] else bank.memory
 elif anchor['streaming']:awb=core.Awb(bank.pak.bank(name))
 else:
  blob=parsed.root.rows[0].get('AwbFile');awb=core.Awb(acb[blob[0]:blob[0]+blob[1]]) if blob and blob[1] else None
 id=int(anchor['key'][1:])
 if not awb or awb.key!=anchor['awb_key'] or id not in awb.entries or hashlib.sha256(awb.entries[id]).hexdigest()!=anchor['sha']:return None
 contexts=fr.source_contexts(token,live.schema_data()[1],name[6:-3],name[-2:],cfg_json)
 exact=[c for c in contexts if (c.get('cue_name'),c.get('cue_id')) in valid_pairs and (c.get('source_kind')=='origin_function' or c.get('reference_validation') in ('live_assets','unchanged_source_assets','extended_source_assets'))]
 if not exact:return None
 return dict(anchor,verified_contexts=[{k:c[k] for k in ('cue_name','cue_id','action','root','child','chain','source_kind','english_function','source_alias','condition','sound_branch','sound_pattern') if k in c} for c in exact])

def attach(bank,rows=None,resolve_audio=False):
 selected=bank.rows if rows is None else rows
 for row in selected:row.update(origin_evidence=[],origin_audio=[],_origin_audio_pending=False)
 if not resolve_audio:
  try:
   key=getattr(bank,'_origin_context_id',None) or uuid.uuid4().hex;bank._origin_context_id=key;_banks[key]=bank
   for row in selected:row['_origin_context_id']=key
  except TypeError:resolve_audio=True # Non-weakref test adapters can validate eagerly.
 data=catalog();pending=[r for r in selected if eligible(r)]
 if not pending or not data or data.get('schema_hash')!=live.schema_data()[1] or live.token(bank.cfg) is None:return
 token=live.token(bank.cfg);cfg_json=json.dumps(bank.cfg,sort_keys=True);out=[]
 anchor_cache=getattr(bank,'_origin_anchor_cache',{}) if type(bank) is core.Bank else {}
 if type(bank) is core.Bank:bank._origin_anchor_cache=anchor_cache
 try:
  opened=live.cue_index(bank.acb)[0];installed=live.cue_index(installed_acb(bank.cfg,bank.name))[0]
  for row in pending:
   key=bank.name+'|'+row['key'];evidence=[];audio=[]
   for ref in data.get('refs',{}).get(key,[]):
    name,cue_id=ref['cue_name'],ref['cue_id']
    if name not in row['cue_names'] or cue_id not in row['cue_ids'] or name not in opened.get(cue_id,set()) or name not in installed.get(cue_id,set()):continue
    expected=data.get('sources',{}).get(ref['asset'])
    if not expected:continue
    try:
     if source_hash(token,data['schema_hash'],cfg_json,ref['asset'])!=expected:continue
     if ref['kind']=='pattern_request' and source_hash(token,data['schema_hash'],cfg_json,'SS/Blueprints/PatternVoiceData.uasset')!=data['sources'].get('SS/Blueprints/PatternVoiceData.uasset'):continue
    except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):continue
    callers=[]
    for caller in ref.get('callers',[]):
     try:
      if caller.get('dependencies') and all(source_hash(token,data['schema_hash'],cfg_json,dep)==data['sources'].get(dep) for dep in caller['dependencies']):callers.append(caller)
     except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):continue
    evidence.append(dict(ref,callers=callers,owners=sorted({c['owner'] for c in callers})))
   target=data.get('audio_targets',{}).get(key)
   if target and not bank.external and bank.compatible:
    awb=bank.stream if row['streaming'] else bank.memory
    valid=any(n in row['cue_names'] and id in row['cue_ids'] and n in opened.get(id,set()) and n in installed.get(id,set()) for n,id in target['pairs'])
    if valid and awb and awb.key==target['awb_key'] and row['id'] in awb.entries and (row['rate'],row['channels'],row['samples'])==(target['rate'],target['channels'],target['samples']) and hashlib.sha256(awb.entries[row['id']]).hexdigest()==target['sha']:
     if not resolve_audio:row['_origin_audio_pending']=True
     for anchor in data['audio_groups'][target['group']] if resolve_audio else []:
      if anchor['bank']==bank.name and anchor['key']==row['key']:continue
      anchor_json=json.dumps(anchor,sort_keys=True)
      akey=(token,data['schema_hash'],id(fr.source_contexts),anchor_json)
      if akey not in anchor_cache:
       cachekey=(token,data['schema_hash'],cfg_json,id(fr.source_contexts),anchor_json)
       try:
        if anchor['bank']!=bank.name and cachekey in _foreign_anchors:
         anchor_cache[akey]=_foreign_anchors[cachekey];_foreign_anchors.move_to_end(cachekey)
        else:
         anchor_cache[akey]=anchor_matches(bank,anchor,token,cfg_json)
         if anchor['bank']!=bank.name:
          _foreign_anchors[cachekey]=anchor_cache[akey]
          while len(_foreign_anchors)>256:_foreign_anchors.popitem(last=False)
       except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):anchor_cache[akey]=None
      verified=anchor_cache[akey]
      if verified:audio.append(verified)
   out.append((row,evidence,audio))
  if token!=live.token(bank.cfg):return
  for row,evidence,audio in out:row.update(origin_evidence=evidence,origin_audio=audio,_origin_checked_token=token)
 except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):return

def ensure_audio(row):
 bank=_banks.get(row.get('_origin_context_id',''))
 if bank is not None and row.get('_origin_checked_token')!=live.token(bank.cfg):
  row.update(origin_evidence=[],origin_audio=[],_origin_audio_pending=False);return
 if row.get('_origin_audio_pending') and bank is not None:
  # Expensive cross-bank checks run only for a selected detail, not bank loading.
  try:
   with live.bank_read_scope(bank.cfg):attach(bank,rows=[row],resolve_audio=True)
  except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):row.update(origin_audio=[],_origin_audio_pending=False)

def status(row):
 refs=row.get('origin_evidence',[])
 if any(r['kind'] in ('voice_dialogue','voice_player','voice_branch','voice_map','pattern_request') for r in refs):return 'request_asset'
 if row.get('participant_relations') or fr.has_exact_function(row):return 'exact_reference'
 if refs:return 'configuration'
 if row.get('origin_audio') or row.get('audio_equivalences'):return 'recording'
 if row.get('function_correlations') or any(c.get('refinement_kind')=='inferred_group' for c in row.get('function_refinements',[])):return 'probable'
 return 'not_located'

@functools.lru_cache(maxsize=1)
def translations():return json.loads((core.APP/'Data/voice_origin_languages.json').read_text(encoding='utf-8'))

def detail(row,language):
 ensure_audio(row)
 if not eligible(row):return ''
 import compact_functions,game_characters
 tr=translations().get(language,translations()['en']);lines=[tr['heading'],tr[status(row)]]
 if row.get('_manual'):lines.append(tr['personal']+row['_manual']['label'])
 else:
  for rule in uf.functions(row):lines.append(tr['classification']+uf.labels(row,language)[uf.functions(row).index(rule)])
 raw_refs=row.get('origin_evidence',[])
 for ref in raw_refs:
  lines.extend(['',tr['configured']+ref['cue_name']+' | '+str(ref['cue_id']),ref['asset']+' | '+ref['export']+' #'+str(ref.get('export_index','?')),ref['property_path']])
  if ref.get('conditions'):lines.append(tr['conditions']+json.dumps(ref['conditions'],ensure_ascii=False,sort_keys=True))
  for caller in ref.get('callers',[]):
   lines.append(tr['dependency_owners']+game_characters.name(caller['owner'],language)+' ['+caller['owner']+'] | '+caller['action']+' | '+caller['role'])
   lines.append(' → '.join([caller['root'],caller['child']]+caller['chain']))
   if len(caller.get('inheritance',[]))>1:lines.append('DefaultCharacterData: '+' → '.join(caller['inheritance']))
   if caller.get('selector'):lines.append(tr['conditions']+json.dumps(caller['selector'],ensure_ascii=False))
   for route in caller.get('routes',[]):
    lines.append(route['kind']+': '+', '.join(game_characters.name(a,language) for a in route['partners'])+' → '+game_characters.name(route['result'],language))
 if raw_refs:lines.append(tr['configuration_note'])
 for item in row.get('origin_audio',[]):
  lines.extend(['',tr['recording_heading']+game_characters.name(item['bank'][6:-3],language)+' | '+item['bank']+' | '+item['key'],', '.join(item['cue_names'])])
  contexts=item['verified_contexts'];labels=[]
  for c in contexts:
   label=compact_functions.function(c['english_function'],language) if c.get('english_function') else compact_functions.action(c['action'],language)
   if label not in labels:labels.append(label)
  lines.append(tr['source_usage']+' / '.join(labels))
  for c in contexts:
   lines.append(' → '.join(dict.fromkeys([c['root'],c['child']]+c.get('chain',[]))))
 if row.get('origin_audio'):lines.append(tr['recording_note'])
 for c in row.get('function_refinements',[]):
  if c.get('refinement_kind')=='exact_source_cue' and c.get('time_frame') is not None:lines.append(tr['frame']+str(c['time_frame'])+' | '+c['action'])
 if status(row)=='not_located':lines.append(tr['absence_note'])
 if any(rule['key'].startswith('unused_') for rule in uf.functions(row)):lines.append(tr['unused_note'])
 return '\n'.join(lines)

def search_text(row):
 return ' '.join(json.dumps(r,ensure_ascii=False) for r in row.get('origin_evidence',[]))+ ' '+' '.join(a['bank']+' '+a['key']+' '+' '.join(a['cue_names']) for a in row.get('origin_audio',[]))
