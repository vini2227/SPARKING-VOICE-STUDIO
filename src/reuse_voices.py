"""Cross-bank reuse by confirmed semantic tags, never by physical waveform ID."""
import re,uuid
from pathlib import Path
import core,audio_levels,audio_variations

def tags(row):
    result={'function:'+value for value in row.get('functions',[])}
    for context in row.get('interactions',[]):
        result.add('interaction:'+str(context['event'])+':'+str(context.get('target_id') or '')+':'+str(context.get('order') or 0))
    if row.get('emotes'):result.add('emote:AppealVoice')
    result.update('usage:'+value for value in row.get('usage_contexts',[]))
    return result

def functions(row):
    """Language-independent function identities, including project annotations.

    Manual labels override the displayed function; personal notes are never
    used for matching. Unknown rows deliberately have no matching identity.
    Interaction targets and order stay part of the identity for safe reuse.
    """
    manual=row.get('_manual',{}).get('label','').strip()
    if manual:return {'manual-label:'+ ' '.join(manual.casefold().split())}
    import user_voice_functions
    result={'description:'+value for value in row.get('english',[]) if value and value!='Unclassified'}
    if not result:
        result.update('function:'+value for value in row.get('functions',[]) if value and value!='Unclassified')
    result.update(token for token in tags(row) if not token.startswith('function:'))
    result.update('action:'+context['action'] for context in row.get('attack_contexts',[]) if context.get('action'))
    result.update('user:'+rule['key'] for rule in user_voice_functions.functions(row))
    return result

def semantics(row,mode='tags'):
    if mode=='tags':return tags(row)
    if mode=='functions':return functions(row)
    raise ValueError('Unknown voice reuse mode: '+str(mode))

def interaction_pairs(tokens):
    """Known participant and event, keeping forms and event types distinct."""
    pairs=set()
    for token in tokens:
        if token.startswith('interaction:'):
            _,event,target,order=token.split(':',3)
            if target:pairs.add((event,target))
    return pairs

def interaction_equivalent(a,b,mode='tags'):
    left=semantics(a,mode);right=semantics(b,mode)
    # Other functions on a shared voice must still agree. Unknown participants
    # and generic introductions never establish a participant equivalence.
    if {t for t in left if not t.startswith('interaction:')} != {t for t in right if not t.startswith('interaction:')}:
        return False
    return bool(interaction_pairs(left) & interaction_pairs(right))

def compatible(a,b,mode='tags'):
    semantic=semantics(a,mode)
    return bool(semantic) and (semantic==semantics(b,mode) or interaction_equivalent(a,b,mode))

def slots(row):
    # Regular logical cue names carry character + form + slot. A slot is only
    # used to disambiguate candidates after their complete semantic tags match.
    return {match.group(1) for name in row.get('cue_names',[]) if (match:=re.fullmatch(r'\d{4}_\d{2}_(\d{4})',name))}

def eligible(bank,data,row,include_original=False):
    if include_original or row['key'] in data.get('replacements',{}):return True
    return bool(bank.external and (bank.source or {}).get('audio_similarity',{}).get(row['key'],{}).get('status')=='different')

def protected(bank,data,row):
    if row['key'] in data.get('replacements',{}):return True
    return bool(bank.external and (bank.source or {}).get('audio_similarity',{}).get(row['key'],{}).get('status','uncertain') in ('different','uncertain'))

def plan(source,document,target,target_document,selected_tags,include_original=False,overwrite=False,mode="tags"):
    selected_tags=set(selected_tags);result=[]
    selected_pairs=interaction_pairs(selected_tags)
    for row in target.rows:
        semantic=semantics(row,mode)
        shared_pairs=interaction_pairs(semantic) & selected_pairs
        if not semantic.intersection(selected_tags) and not shared_pairs:continue
        item={'target_key':row['key'],'candidates':[],'source_key':None,'status':'unmatched','tags':sorted(semantic)}
        if protected(target,target_document,row) and not overwrite:item['status']='protected'
        else:
            exact=[other for other in source.rows if semantics(other,mode)==semantic and eligible(source,document,other,include_original)]
            if not semantic.issubset(selected_tags) and exact:
                item['status']='shared_unselected'
            elif exact:
                item['candidates']=[other['key'] for other in exact]
                same_slot=[other for other in exact if slots(row) and slots(row)==slots(other)]
                if len(same_slot)==1:item['source_key']=same_slot[0]['key'];item['status']='matched'
                elif len(exact)==1:item['source_key']=exact[0]['key'];item['status']='matched'
                else:item['status']='choose'
            else:
                candidates=[other for other in source.rows if eligible(source,document,other,include_original)
                            and interaction_equivalent(row,other,mode)
                            and shared_pairs.intersection(interaction_pairs(semantics(other,mode)))]
                if candidates:
                    # Order and shared participants may differ: explicit choice,
                    # even for a unique candidate or the same regular cue slot.
                    item['candidates']=[other['key'] for other in candidates]
                    item['status']='interaction_review'
                elif not semantic.issubset(selected_tags):item['status']='shared_unselected'
        result.append(item)
    return result

def copy(source,document,target,folder,mapping,progress=lambda value:None,mode="tags"):
    replacements={};gains={};variations={}
    for index,(target_key,source_key) in enumerate(mapping.items()):
        row=target.wave_rows[target_key];original=source.wave_rows[source_key]
        if not compatible(row,original,mode):raise ValueError('As tags da origem e do destino não correspondem.')
        progress(f'{index+1}/{len(mapping)} • '+row['filename'])
        path=document.get('replacements',{}).get(source_key) or str(source.original(original))
        gain=audio_levels.valid_gain(document.get('gains',{}).get(source_key,0))
        variation=audio_variations.valid(document.get('variations',{}).get(source_key,1))
        dest=core.owned(Path(folder)/'Replacements'/(target_key+'_'+uuid.uuid4().hex+'.wav'))
        core.normalize_wav(path,dest,row['rate'],row['channels'],row['samples'])
        # Each target gets its own WAV; later edits cannot modify the source project.
        replacements[target_key]=str(dest)
        if gain:gains[target_key]=gain
        if variation!=1:variations[target_key]=variation
    return {'replacements':replacements,'gains':gains,'variations':variations}
