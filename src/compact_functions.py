"""Short function display labels; original tags and semantic identities stay intact."""
import json,re
from pathlib import Path
from i18n import Translator
DATA=json.loads((Path(__file__).resolve().parents[1]/'Data/compact_function_languages.json').read_text(encoding='utf-8'))
FULL=json.loads((Path(__file__).resolve().parents[1]/'Data/function_languages.json').read_text(encoding='utf-8'))
def function(english,language):return DATA.get(language,DATA['en']).get(english) or FULL.get(language,{}).get(english) or english
def manual_label(source,language):return Translator(language).logical(DATA['manual'].get(source,source))
def action(code,language):
 import function_refinements as fr
 for pattern,label in ((r'actFRM[CD][A-Za-z0-9_]*','Mudança de forma'),(r'actAPL\d*[A-Za-z0-9_]*','Emote')):
  if re.fullmatch(pattern,code or ''):return Translator(language).logical(label)+' ['+code.removeprefix('act')+']'
 f=fr.family(code)
 if not f:return code
 names={'EXA1':'Habilidade 1','EXA2':'Habilidade 2','SPM1':'Blast 1','SPM2':'Blast 2','ULT':'Ultimate'}
 prefix='act'+f;suffix=code[len(prefix):]
 return Translator(language).logical(names[f])+(' ['+suffix+']' if suffix else '')
def context_values(row,values,language):
 from i18n import Translator
 tr=Translator(language);result=[]
 for value in values:
  # A person's own wording is never abbreviated automatically.
  if row.get('_manual') and value==tr.logical('Manual: ')+row['_manual']['label']:
   result.append(value);continue
  for source in DATA['manual']:
   original=tr.logical(source)
   if value==tr.logical('Manual: ')+original:value=tr.logical('Manual: ')+manual_label(source,language);break
  for c in row.get('function_refinements',[]):
   import function_refinements as fr
   if c.get('refinement_kind')=='exact_source_cue' and value==tr.logical('Vínculo no personagem de origem: ')+fr.label(c,language):
    if any(a.get('action')==c['action'] and a.get('cue_name')==c['cue_name'] for a in row.get('attack_contexts',[])):value='';break
    value=tr.logical('Origem: ')+(action(c['action'],language) if fr.family(c.get('action')) else fr.label(c,language));break
  if not value:continue
  value=value.replace(tr.logical('Vínculo no personagem de origem: '),tr.logical('Origem: '))
  value=value.replace(tr.logical('Referência de ação')+': ','')
  for c in row.get('attack_contexts',[])+row.get('function_refinements',[]):
   code=c.get('action','')
   if code and not code.startswith(('Subtitles: ','Evento/diálogo: ','Animação: ')):
    value=re.sub(r'(?<![\w])'+re.escape(code)+r'(?![\w])',lambda m:action(code,language),value)
  if row.get('attack_contexts') and not value.startswith(tr.logical('Origem: ')):
   import voice_context
   companions={}
   for c in row['attack_contexts']:
    actors={p['actor'] for p in c.get('action_participants',[]) if p['actor']!=c.get('owner_actor',c.get('character_data','').rsplit('CharacterData_',1)[-1].removesuffix('.uasset'))}
    if c.get('shared_participant') and c.get('speaker_actor'):actors.add(c['speaker_actor'])
    label=action(c['action'],language);names=companions.setdefault(label,[])
    for actor in sorted(actors):
     name=voice_context._character(actor,language)
     if name not in names:names.append(name)
   for label,names in companions.items():
    if names and label in value:value=value.replace(label,label+' — '+', '.join(names),1)
  if value not in result:result.append(value)
 return result
