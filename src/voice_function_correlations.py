"""Conservative categories from consistent cue families, with live game anchors."""
import json,re,functools,hashlib
import core,live_voice_references as live,game_references

def data():
 raw=(core.APP/'Data/voice_function_correlations.json').read_bytes()
 value=json.loads(raw)
 if value.get('schema')!=1:raise ValueError('Invalid function correlation schema')
 return value['rules'],hashlib.sha256(raw).hexdigest()

def metadata(acb):
 bank=object.__new__(core.Bank);bank.acb=acb;bank.root=core.UTF(acb)
 bank.tables={k:bank.root.child(k) for k in ('CueTable','CueNameTable','WaveformTable','SynthTable','SequenceTable','TrackTable','TrackEventTable','CommandTable')}
 return bank

def anchor_valid(bank,anchor,english,patterns):
 cues=bank.tables['CueTable'].rows;names=bank.tables['CueNameTable'].rows
 target=set();tagged=set()
 for entry in names:
  cue=cues[entry['CueIndex']]
  if entry['CueName']==anchor['cue_name'] and cue['CueId']==anchor['cue_id']:target.update(bank.resolve(cue['ReferenceType'],cue['ReferenceIndex'],set()))
  if entry['CueName']==anchor['tag'] and core.description(patterns.get(cue['CueId'],''))==english:tagged.update(bank.resolve(cue['ReferenceType'],cue['ReferenceIndex'],set()))
 return bool(target) and target<=tagged

@functools.lru_cache(maxsize=4)
def validated_rules(token,digest,cfg_json):
 cfg=json.loads(cfg_json);rules,current=data()
 if current!=digest:raise ValueError('Function correlations changed during validation')
 patterns=core.pattern_functions(cfg);banks={};result=[]
 for rule in rules:
  if rule['support']<100 or rule['support']/rule['compared']<.95 or len({a['bank'][6:10] for a in rule['anchors']})<3:continue
  valid=True
  for anchor in rule['anchors']:
   name=anchor['bank']
   if name not in banks:
    raw=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+name[-2:]+'/'+name+'.uasset').read_bytes();start=raw.index(b'@UTF')
    banks[name]=metadata(raw[start:start+core.UTF(raw,start).size])
   if not anchor_valid(banks[name],anchor,rule['english'],patterns):valid=False;break
  if valid:result.append(rule)
 if live.token(cfg)!=token:raise ValueError('Game changed during function correlation validation')
 return tuple(result)

def candidate(row,actor):
 result=set()
 for name in row.get('cue_names',[]):
  match=re.fullmatch(re.escape(actor)+r'_(?:([01])_)?(\d{4})',name)
  if not match:continue
  variant,number=match[1],int(match[2])
  expected=10000+number if variant is None else (int(variant)+1)*100000+number
  if expected in row.get('cue_ids',[]):result.add(number)
 return result

def attach(bank_name,acb,rows,cfg):
 import voice_context as vc
 for row in rows:row['function_correlations']=[]
 if cfg is None or live.token(cfg) is None:return
 actor=bank_name[6:-3];pending=[r for r in rows if not vc.identified(r,'all') and candidate(r,actor)]
 if not pending:return
 try:
  rules,digest=data();rules=validated_rules(live.token(cfg),digest,json.dumps(cfg,sort_keys=True))
  raw=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+bank_name[-2:]+'/'+bank_name+'.uasset').read_bytes();start=raw.index(b'@UTF')
  current,_=live.cue_index(raw[start:start+core.UTF(raw,start).size]);opened,_=live.cue_index(acb)
 except (OSError,ValueError,KeyError,IndexError,TypeError):return
 for row in pending:
  # Edited banks must retain the installed logical cue name/ID pair.
  safe=dict(row,cue_names=[n for n in row['cue_names'] if any(n in current.get(i,set()) and n in opened.get(i,set()) for i in row['cue_ids'])])
  suffixes=candidate(safe,actor)
  row['function_correlations']=[rule for rule in rules if rule['suffix'] in suffixes]

_before_local_attach=attach
def attach(bank_name,acb,rows,cfg):
 _before_local_attach(bank_name,acb,rows,cfg)
 import local_voice_correlations
 local_voice_correlations.attach(bank_name,acb,rows,cfg)
