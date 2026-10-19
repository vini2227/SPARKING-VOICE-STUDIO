"""Bounded property evidence: voice requests, selectors and configured alternatives."""
import re
NAME=re.compile(r'\d{4}_\d{2}(?:_[01])?_\d{4}')

def voice_name(text):
 if not isinstance(text,dict):return None
 name=(text.get('key') or '').removeprefix('ST_')
 if not NAME.fullmatch(name):return None
 if text.get('namespace')=='ST_VOICE_TEXT' or text.get('table')=='/Game/SS/StringTables/Voice/Voice_'+name[:7]+'.Voice_'+name[:7]:return name

def walk(value,path=''):
 if isinstance(value,dict):
  yield path,value
  for k,v in value.items():yield from walk(v,path+'.'+str(k))
 elif isinstance(value,(list,tuple)):
  for i,v in enumerate(value):yield from walk(v,path+'['+str(i)+']')

def selection_context(obj,path):
 value=obj;keys=[];result={}
 for field,index in re.findall(r'\.([^\.\[\]]+)|\[(\d+)\]',path):
  if field:
   if not isinstance(value,dict) or field not in value:break
   value=value[field]
  else:
   i=int(index)
   if not isinstance(value,(list,tuple)) or i>=len(value):break
   value=value[i]
  if isinstance(value,(list,tuple)) and len(value)==2 and isinstance(value[1],dict):
   key=value[0]
   if isinstance(key,str):keys.append(key)
   elif isinstance(key,dict) and key.get('Key'):keys.append(key['Key'])
 if keys:result['selector_keys']=list(dict.fromkeys(keys))
 # Keep frame numbers exactly as serialized; no unverified conversion to seconds.
 for p,parent in walk(obj):
  if 'Times' not in parent or 'KeyValues' not in parent:continue
  prefix=p+'.KeyValues['
  if path.startswith(prefix):
   m=re.match(r'(\d+)\]',path[len(prefix):]);times=parent.get('Times') or [];values=parent.get('KeyValues') or []
   if m and len(times)==len(values) and int(m[1])<len(times):result['time_frame']=times[int(m[1])]
 return result

def requests(obj,cls,patterns):
 """A text reference alone is configuration, never proof of a voice request."""
 hits=[]
 def add(path,kind,name=None,id=None,conditions=None):
  if not name and not isinstance(id,int):return
  if name and not NAME.fullmatch(name):return
  if id is not None and (not isinstance(id,int) or id<=0):return
  hits.append(dict(cue_name=name,cue_id=id,kind=kind,property_path=path,conditions=dict(selection_context(obj,path),**(conditions or {}))))
 def sound(value,path,kind='voice_player'):
  if value.get('SheetType')!=1 or value.get('SoundGroupType')!=3:return
  conditions={k:value[k] for k in ('PatternName','SetPlayVoiceName','PlayVoiceIndex','IsResetRandomDataIndex','FormIdArray','ChargeLvArray','CtrlType','bStopSoundEndPlay','Volume','bDeleteOnFormChange') if value.get(k) is not None}
  name=value.get('SoundCueName');id=value.get('SoundCueID')
  if name or isinstance(id,int) and id>0:add(path+'.SoundCue',kind,name,id if id and id>0 else None,conditions)
  for branch,v in value.get('SoundBranches') or []:
   if v.get('SheetType')==1:add(path+'.SoundBranches', 'voice_branch',v.get('CueName'),v.get('CueId') if isinstance(v.get('CueId'),int) and v['CueId']>0 else None,dict(conditions,branch=branch))
  key=(value.get('PatternName') or {}).get('Key');pattern=patterns.get(key)
  if pattern and pattern.get('DefaultCueID',0)>0:add(path+'.PatternName','pattern_request',id=pattern['DefaultCueID'],conditions=dict(conditions,pattern=key))
 for path,value in walk(obj):
  if 'SheetType' in value and 'SoundGroupType' in value:sound(value,path)
  cv=value.get('BattleConversation')
  if isinstance(cv,dict) and value.get('IsBattleVoice')==1:
   name=voice_name(cv.get('Text'));cond={k:cv[k] for k in ('CharacterID','BattleConversationMode','ConversationCharacter','Interval','SoundNameSuffix','HiddenSubtitles','bStopSoundEndPlay') if cv.get(k) is not None}
   cond['TargetType']=value.get('TargetType') or 0
   if not cv.get('SoundNameSuffix') and not cv.get('ConversationVoiceMap'):add(path+'.BattleConversation.Text','voice_dialogue',name,conditions=cond)
   for team,explicit in cv.get('ConversationVoiceMap') or []:
    if NAME.fullmatch(explicit or ''):add(path+'.BattleConversation.ConversationVoiceMap','voice_map',explicit,conditions=dict(cond,team_index=team))
  if isinstance(value.get('Text'),dict) and value.get('IsBattleVoice')==1 and not value.get('SoundNameSuffix') and not value.get('ConversationVoiceMap'):
   add(path+'.Text','voice_dialogue',voice_name(value['Text']),conditions={k:v for k,v in value.items() if k not in ('Text','FillInBlankWord','FillInBlankWord2','UpdateNameText') and not isinstance(v,(list,dict))})
  for i,text in enumerate(value.get('VoiceTexts') or []):
   add(path+'.VoiceTexts['+str(i)+']','configured_fate',voice_name(text),conditions={k:v for k,v in value.items() if k!='VoiceTexts'})
  for i,name in enumerate(value.get('SubtilesIDArray') or []):add(path+'.SubtilesIDArray['+str(i)+']','configured_subtitle',name.removeprefix('ST_'))
  if 'PlayCueSetList' in value:
   for i,name in enumerate(value.get('PlayCueSetList') or []):
    add(path+'.PlayCueSetList['+str(i)+']','configured_set',name,conditions={'Weight':value.get('Weight')})
  # UI/story tables explicitly named voice lines are still configuration.
  for i,text in enumerate(value.get('LineTextArray') or []):add(path+'.LineTextArray['+str(i)+']','configured_voice_line',voice_name(text))
 return hits
