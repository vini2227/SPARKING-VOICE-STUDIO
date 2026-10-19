"""Reviewed PCM equality; current game payloads and source action are revalidated."""
import json,hashlib
import core,game_references,live_voice_references as live,function_refinements as fr

def data():return json.loads((core.APP/'Data/audio_function_equivalences.json').read_text(encoding='utf-8'))

def attach(bank):
 for row in bank.rows:row['audio_equivalences']=[]
 if bank.external or not bank.compatible:return
 token=live.token(bank.cfg)
 try:
  value=data()
  if value.get('schema')!=1:return
  rules=[r for r in value['rules'] if r['bank']==bank.name and r.get('pcm_verified')]
  if not rules:return
  anchors={};pending=[]
  for rule in rules:
   row=bank.wave_rows.get(rule['key'])
   if not row or not row['streaming'] or not row.get('available') or row.get('_manual'):continue
   if rule['cue_name'] not in row['cue_names'] or rule['cue_id'] not in row['cue_ids']:continue
   if (row['rate'],row['channels'],row['samples'])!=(rule['rate'],rule['channels'],rule['samples']):continue
   if bank.stream.key!=rule['awb_key'] or hashlib.sha256(bank.stream.entries[row['id']]).hexdigest()!=rule['encoded_sha256']:continue
   name=rule['anchor_bank']
   if name not in anchors:
    raw=game_references.asset(bank.cfg,'SS/Sounds/Battle_VOICE/'+name[-2:]+'/'+name+'.uasset').read_bytes();at=raw.index(b'@UTF');acb=raw[at:at+core.UTF(raw,at).size]
    from voice_function_correlations import metadata
    parsed=metadata(acb);cues=parsed.tables['CueTable'].rows;waves=parsed.tables['WaveformTable'].rows;logical={}
    for entry in parsed.tables['CueNameTable'].rows:
     c=cues[entry['CueIndex']];indices=parsed.resolve(c['ReferenceType'],c['ReferenceIndex'],set())
     logical[(entry['CueName'],c['CueId'])]={('S' if waves[i]['Streaming'] else 'M')+str(waves[i]['StreamAwbId'] if waves[i]['Streaming'] else waves[i]['MemoryAwbId']) for i in indices}
    awb=bank.stream if name==bank.name else core.Awb(bank.pak.bank(name))
    contexts=fr.source_contexts(token,live.schema_data()[1],name[6:-3],name[-2:],json.dumps(bank.cfg,sort_keys=True))
    anchors[name]=(logical,awb,contexts)
   logical,awb,contexts=anchors[name]
   if rule['anchor_key'] not in logical.get((rule['anchor_cue_name'],rule['anchor_cue_id']),set()):continue
   id=int(rule['anchor_key'][1:])
   if awb.key!=rule['anchor_awb_key'] or id not in awb.entries or hashlib.sha256(awb.entries[id]).hexdigest()!=rule['anchor_encoded_sha256']:continue
   exact=[c for c in contexts if c.get('cue_name')==rule['anchor_cue_name'] and c.get('cue_id')==rule['anchor_cue_id'] and c.get('action')==rule['action'] and c.get('source_kind')=='battle_dialogue' and c.get('reference_validation')=='live_assets']
   if exact:pending.append((row,dict(rule,source_context=exact[0])))
  if token!=live.token(bank.cfg):return
  for row,evidence in pending:row['audio_equivalences'].append(evidence)
 except (OSError,ValueError,KeyError,IndexError,TypeError):return

def label(evidence,language):
 from i18n import Translator
 import compact_functions
 return Translator(language).logical('Áudio idêntico: ')+compact_functions.action(evidence['action'],language)

def details(row,language):
 from i18n import Translator
 lines=[]
 for e in row.get('audio_equivalences',[]):
  c=e['source_context'];lines+=[label(e,language)+' | '+e['cue_name']+' → '+e['anchor_cue_name'],e['anchor_bank']+' | '+str(e['anchor_cue_id'])+' | '+e['anchor_key'],c['root']+' → '+c['child']]+c.get('chain',[])
  lines.append(Translator(language).logical('Mesma gravação do cue de origem; não confirma que este Cue ID seja executado no mesmo contexto.'))
 return '\n'.join(dict.fromkeys(lines))
