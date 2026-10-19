"""User-supplied cue functions, used only when no prior identification exists."""
import json,re,functools
from pathlib import Path

@functools.lru_cache(maxsize=1)
def rules():
 return json.loads((Path(__file__).resolve().parents[1]/'Data/user_voice_functions.json').read_text(encoding='utf-8'))['rules']

def functions(row):
 # Keep asset-backed labels and project-local manual annotations authoritative.
 if row.get('_manual') or row.get('interactions') or row.get('emotes') or row.get('usage_contexts') or row.get('attack_contexts') or any(v and v!='Unclassified' for v in row.get('english',[])):return []
 ids={v for v in row.get('cue_ids',[]) if isinstance(v,int)};short=set()
 for name in row.get('cue_names',[]):
  match=re.fullmatch(r'\d{4}_\d{2}_(\d{4})',name)
  if match:
   value=int(match[1])
   if any(cue%10000==value for cue in ids):short.add(value)
  # Alternate speakers use an explicit variant prefix in both cue name and ID.
  alternate=re.fullmatch(r'\d{4}_\d{2}_([01])_(\d{4})',name)
  if alternate:
   variant,value=int(alternate[1]),int(alternate[2])
   if (variant+1)*100000+value in ids:short.add(value)
 result=[]
 for rule in rules():
  if result and rule.get("only_if_no_prior_rule"):continue
  domain=short if rule['domain']=='character_cue' else ids
  selected=domain&set(rule.get('ids',[])) if 'ids' in rule else {v for v in domain if rule['min']<=v<=rule['max']}
  selected-=set(rule.get('exclude',[]))
  if rule.get('required_name_pattern'):
   selected={cue for cue in selected if any(re.fullmatch(rule['required_name_pattern'],name) and cue%10000==int(name[-4:]) for name in row.get('cue_names',[]))}
  if rule.get('encoded_form'):
   selected={cue for cue in selected if any(re.fullmatch(rule['required_name_pattern'],name) and int(name[5:7])>0 and cue==int(name[5:7])*100000+10000+int(name[-4:]) for name in row.get('cue_names',[]))}
  if selected:result.append(dict(rule,matched=sorted(selected)))
 return result

def labels(row,language):
 from i18n import Translator
 tr=Translator(language)
 return [tr.logical(rule['label']) for rule in functions(row)]

def emote(row):return any(rule['key']=='unknown_emote' for rule in functions(row))

def interaction(row):return any(rule['key']=='unknown_interactions_100' for rule in functions(row))


def verified_rule(row,rule):
 """The displayed function can come from exact game references, independently of the original category."""
 refs=[c for c in row.get('function_refinements',[]) if c.get('refinement_kind')=='exact_source_cue' and c.get('cue_name') in row.get('cue_names',[]) and c.get('cue_id') in row.get('cue_ids',[]) and c.get('root') and c.get('child')]
 matched=set(rule.get('matched',[]))
 covered={c['cue_id']%10000 if rule['domain']=='character_cue' else c['cue_id'] for c in refs}
 return bool(matched) and matched<=covered

def display_manual(row):
 # Personal wording stays personal, even when additional game references exist.
 if row.get('_manual'):return True
 return any(rule.get('source')!='cue_family_correlation' and not verified_rule(row,rule) for rule in functions(row))

def display_origin(row,rule):
 if verified_rule(row,rule):return 'game_reference'
 if rule.get('source')=='cue_family_correlation':return 'correlation'
 return 'manual'
