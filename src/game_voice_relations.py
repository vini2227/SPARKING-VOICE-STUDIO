"""Exact reverse voice requests and configured form routes, validated against the game."""
import json,re,functools,struct
import core,live_voice_references as live,function_refinements as fr,fusion_voice_relations as fusion,game_references

@functools.lru_cache(maxsize=1)
def candidates():
 return json.loads((core.APP/'Data/voice_participant_candidates.json').read_text(encoding='utf-8'))

def installed_pairs(bank,cfg):
 raw=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+bank[-2:]+'/'+bank+'.uasset').read_bytes();at=raw.index(b'@UTF')
 return live.cue_index(raw[at:at+core.UTF(raw,at).size])[0]

def reverse_requests(rule,contexts):
 found={}
 for c in contexts:
  if c.get('reference_validation') not in ('live_assets','unchanged_source_assets'):continue
  for p in c.get('action_participants',[]):
   if p.get('actor')!=rule['cue'][:7] or p.get('cue_name')!=rule['cue'] or p.get('sequence_asset') not in rule['sequences']:continue
   # Stage comes from the actual sequence, never an action-group propagation.
   m=re.search(r'_(act[A-Za-z0-9_]+)\.uasset$',p['sequence_asset'])
   action=m[1] if m else c['action']
   key=(action,p['sequence_asset'])
   found[key]=dict(action=action,sequence=p['sequence_asset'],root=c.get('root'),cue_name=rule['cue'])
 return list(found.values())

def attach(bank,acb,rows,cfg):
 for r in rows:r.update(participant_relations=[],form_change_relations=[])
 if cfg is None or live.token(cfg) is None:return
 names={n for r in rows for n in r['cue_names']};rules=[r for r in candidates() if r['cue'] in names]
 pending=any(c.get('action','').startswith(('actFRMC','actFRMD')) for r in rows for c in r.get('attack_contexts',[]))
 if not rules and not pending:return
 token=live.token(cfg);cfg_json=json.dumps(cfg,sort_keys=True)
 try:
  opened=live.cue_index(acb)[0];installed=installed_pairs(bank,cfg)
  def valid(row,name,id):return name in row['cue_names'] and id in row['cue_ids'] and name in opened.get(id,set()) and name in installed.get(id,set())
  owner_contexts={};out=[]
  for rule in rules:
   for owner in rule['owners']:
    if owner not in owner_contexts:owner_contexts[owner]=fr.source_contexts(token,live.schema_data()[1],owner,bank[-2:],cfg_json)
    refs=reverse_requests(rule,owner_contexts[owner])
    for row in rows:
     for id in rule['ids'].get(bank[-2:],[]):
      if valid(row,rule['cue'],id):
       out.extend((row,'participant_relations',dict(ref,owner=owner,cue_id=id)) for ref in refs)
  if pending:
   routes=[r for r in fusion.all_catalog(token,live.schema_data()[1],cfg_json) if r['kind']=='FormChange' and r['owner']==bank[6:13]]
   for row in rows:
    for c in row.get('attack_contexts',[]):
     if c.get('reference_validation') not in ('live_assets','unchanged_source_assets') or not valid(row,c.get('cue_name'),c.get('cue_id')):continue
     for route in routes:
      if c['action'] in route['actions']:out.append((row,'form_change_relations',dict(route,action=c['action'],cue_name=c['cue_name'],cue_id=c['cue_id'])))
  if token!=live.token(cfg):return
  for row,field,ref in out:
   if ref not in row[field]:row[field].append(ref)
 except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):return

def labels(row,language,compact=True):
 import game_characters,compact_functions
 result=[]
 groups={}
 for r in row.get('participant_relations',[]):groups.setdefault((r['owner'],r['action']),[]).append(r)
 for owner,action in groups:
  heading=HEADINGS.get(language,HEADINGS['en'])[0]
  result.append(heading+game_characters.name(owner,language)+' — '+compact_functions.action(action,language))
 groups={}
 for r in row.get('form_change_relations',[]):groups.setdefault(r['action'],[]).append(r)
 for action,routes in groups.items():
  # Keep full form names: base names alone would hide different destinations.
  outputs=', '.join(dict.fromkeys(game_characters.name(r['result'],language) for r in routes))
  supports=sorted({p for r in routes for p in r['partners']})
  label=compact_functions.action(action,language)+' → '+outputs
  if supports:label+=HEADINGS.get(language,HEADINGS['en'])[1]+', '.join(game_characters.name(p,language) for p in supports)
  result.append(label)
 return list(dict.fromkeys(result))

def details(row,language):
 values=labels(row,language,False)
 for r in row.get('participant_relations',[]):values.append(r['sequence']+' | '+r['cue_name']+' | '+str(r['cue_id']))
 for r in row.get('form_change_relations',[]):values.append(r['root']+' | '+r['property_path']+' | '+r['cue_name']+' | '+str(r['cue_id'])+' | '+json.dumps(r['conditions'],ensure_ascii=False))
 if row.get('form_change_relations'):values.append('Auxiliar configurado não confirma uma fala desse personagem.' if language=='pt' else 'Configured support does not confirm a voice request from that character.')
 return '\n'.join(dict.fromkeys(values))

HEADINGS={'pt': ['Participação na ação de ', ' | Auxiliar configurado: '], 'en': ['Participation in action of ', ' | Configured support: '], 'es': ['Participación en la acción de ', ' | Apoyo configurado: '], 'es-419': ['Participación en la acción de ', ' | Apoyo configurado: '], 'fr': ['Participation à l’action de ', ' | Soutien configuré : '], 'it': ['Partecipazione all’azione di ', ' | Supporto configurato: '], 'de': ['Beteiligung an der Aktion von ', ' | Konfigurierte Unterstützung: '], 'ja': ['アクションへの参加: ', ' | 設定されたサポート: '], 'ru': ['Участие в действии персонажа ', ' | Настроенная поддержка: '], 'pl': ['Udział w akcji postaci ', ' | Skonfigurowane wsparcie: '], 'ar': ['المشاركة في حركة ', ' | الدعم المحدد: '], 'zh-Hans': ['参与动作：', ' | 配置的支援：'], 'zh-Hant': ['參與動作：', ' | 設定的支援：'], 'ko': ['동작 참여: ', ' | 설정된 지원: '], 'th': ['การมีส่วนร่วมในท่าของ ', ' | ตัวช่วยที่กำหนด: '], 'id': ['Partisipasi dalam aksi ', ' | Pendukung yang dikonfigurasi: ']}
