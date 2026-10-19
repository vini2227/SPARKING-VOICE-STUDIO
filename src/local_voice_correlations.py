"""Local probable relations, derived from installed cues and explicit participants."""
import re,json
import core,live_voice_references as live,game_references,function_refinements as fr

def cue_parts(name):
 m=re.fullmatch(r'(\d{4}_\d{2})_(\d{4})',name)
 return (m[1],int(m[2])) if m else None

def joint_rule(name,owner,contexts,language):
 parts=cue_parts(name)
 if not parts:return
 speaker,number=parts
 # This is a local Ultimate block, including extra participant takes. The
 # number alone never establishes the action or its participants.
 if not 680<=number<=709:return
 anchors=[];participants=set();families=set()
 for c in contexts:
  p=cue_parts(c.get('cue_name',''))
  if not p or not 680<=p[1]<=709 or c.get('source_kind')!='battle_dialogue':continue
  if not c.get('root') or not c.get('child'):continue
  f=fr.family(c.get('action'))
  if f:families.add(f)
  if f!='ULT':continue
  explicit={p['actor'] for p in c.get('action_participants',[])}
  # A foreign voice must be a documented participant, never merely a
  # similarly numbered cue or an opponent's damage response.
  if speaker[:4]!=owner[:4] and not any(a[:4]==speaker[:4] for a in explicit):continue
  anchors.append(c);participants.update(explicit)
 if families!={'ULT'} or len({c['cue_name'] for c in anchors})<2:return
 if number>=700 and speaker[:4]==owner[:4]:return
 return dict(key='local_joint_ULT',tag='local:ULT:'+','.join(sorted(participants)),english='Ultimate',family='ULT',relation='joint_action',speaker_actor=speaker,owner_actor=owner,participants=sorted(participants),support=len({c['cue_name'] for c in anchors}),compared=len({c['cue_name'] for c in anchors}),anchors=[dict(bank='BTLCV_'+owner+'_'+language,cue_name=c['cue_name'],cue_id=c['cue_id'],action=c['action'],root=c['root'],child=c['child']) for c in { (c['cue_name'],c['action']):c for c in anchors}.values()])

def sibling_rule(name,owner,sources,language):
 parts=cue_parts(name)
 if not parts or parts[0]!=owner or parts[1]>=600:return
 number=parts[1];anchors=[];labels=set()
 for actor,contexts in sources:
  if actor==owner or actor[:4]!=owner[:4]:continue
  for c in contexts:
   if c.get('source_kind')!='origin_function' or not c.get('source_alias'):continue
   if cue_parts(c.get('cue_name',''))!=(actor,number):continue
   labels.add(c['english_function']);anchors.append(dict(bank='BTLCV_'+actor+'_'+language,cue_name=c['cue_name'],cue_id=c['cue_id'],tag=c['source_alias'],root=c['root'],child=c['child']))
 if len(labels)!=1:return
 label=next(iter(labels));tag=anchors[0]['tag']
 return dict(key='local_form_'+str(number),tag='local:form:'+tag,english=label,relation='same_character_form',speaker_actor=owner,owner_actor=owner,participants=[],support=len({a['bank'] for a in anchors}),compared=len({a['bank'] for a in anchors}),anchors=anchors)

def attach(bank_name,acb,rows,cfg):
 import voice_context as vc
 if cfg is None or live.token(cfg) is None:return
 pending=[r for r in rows if not vc.identified(r,'all') and not r.get('_manual')]
 if not pending:return
 owner=bank_name[6:-3];language=bank_name[-2:];token=live.token(cfg)
 try:
  raw=game_references.asset(cfg,'SS/Sounds/Battle_VOICE/'+language+'/'+bank_name+'.uasset').read_bytes();at=raw.index(b'@UTF')
  installed,_=live.cue_index(raw[at:at+core.UTF(raw,at).size]);opened,_=live.cue_index(acb)
  contexts=[c for r in rows for c in r.get('attack_contexts',[]) if c.get('reference_validation') in ('live_assets','unchanged_source_assets')]
  sources=None;results=[]
  for row in pending:
   rules=[]
   for name in row.get('cue_names',[]):
    if not any(name in installed.get(i,set()) and name in opened.get(i,set()) for i in row['cue_ids']):continue
    rule=joint_rule(name,owner,contexts,language)
    if not rule and cue_parts(name) and cue_parts(name)[0]==owner and cue_parts(name)[1]<600:
     if sources is None:
      _,entries=game_references.session(cfg);actors=set()
      for path in entries:
       m=re.fullmatch(r'SS/Sounds/Battle_VOICE/'+language+r'/BTLCV_('+owner[:4]+r'_\d{2})_'+language+r'\.uasset',path)
       if m and m[1]!=owner:actors.add(m[1])
      sources=[(a,fr.source_contexts(token,live.schema_data()[1],a,language,json.dumps(cfg,sort_keys=True))) for a in sorted(actors)]
     rule=sibling_rule(name,owner,sources,language)
    if rule:rules.append(rule)
   results.append((row,rules))
  if token!=live.token(cfg):return
  for row,rules in results:row.setdefault('function_correlations',[]).extend(rules)
 except (OSError,ValueError,KeyError,IndexError,TypeError):return
