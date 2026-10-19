"""Verified references from extracted MLS/Combination assets, without changing cue tags."""
import struct
import functools,hashlib,json
from pathlib import Path

@functools.lru_cache(maxsize=1)
def catalog():
    path=Path(__file__).resolve().parents[1]/'Data/attack_contexts.json'
    try:return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:return {'characters':{},'bank_acb_sha256':{}}

def attach(bank_name,acb,rows,cfg=None):
    for row in rows:row['attack_contexts']=[]
    import game_installation
    if cfg is not None and game_installation.identity(cfg):
        import live_voice_references
        try:
            contexts,diagnostics=live_voice_references.contexts(cfg,bank_name,acb)
        except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):return
        import cue_name_functions
        for row in rows:
            for context in contexts:
                if context.get('source_kind')!='cue_name_pattern' and context['cue_id'] in row['cue_ids'] and context['cue_name'] in row['cue_names']:
                    row['attack_contexts'].append(context)
            if cue_name_functions.eligible(row):
                row['attack_contexts'].extend(c for c in contexts if c.get('source_kind')=='cue_name_pattern' and c['cue_id'] in row['cue_ids'] and c['cue_name'] in row['cue_names'])
        return
    data=catalog()
    # Version check plus complete logical cue identity; waveform IDs are not identities.
    digest=hashlib.sha256(acb).hexdigest()
    actor=bank_name[6:-3]
    contexts=list(data['characters'].get(actor,[])) if data.get('bank_acb_sha256',{}).get(bank_name)==digest else []
    conditional=conditional_catalog()
    if conditional.get('bank_acb_sha256',{}).get(bank_name)==digest:
        contexts.extend(conditional.get('banks',{}).get(bank_name,[]))
    for context in contexts:
        for row in rows:
            if context['cue_id'] in row['cue_ids'] and context['cue_name'] in row['cue_names']:
                row['attack_contexts'].append(context)

@functools.lru_cache(maxsize=1)
def conditional_catalog():
    path=Path(__file__).resolve().parents[1]/'Data/conditional_voice_contexts.json'
    try:return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:return {}

_base_attach=attach
def attach(bank_name,acb,rows,cfg=None):
    _base_attach(bank_name,acb,rows,cfg)
    import function_refinements
    try:function_refinements.attach(bank_name,acb,rows,cfg)
    except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):
        for row in rows:row['function_refinements']=[]

_before_correlations_attach=attach
def attach(bank_name,acb,rows,cfg=None):
    _before_correlations_attach(bank_name,acb,rows,cfg)
    import voice_function_correlations
    voice_function_correlations.attach(bank_name,acb,rows,cfg)

_before_fusion_attach=attach
def attach(bank_name,acb,rows,cfg=None):
    _before_fusion_attach(bank_name,acb,rows,cfg)
    import fusion_voice_relations
    fusion_voice_relations.attach(bank_name,acb,rows,cfg)

_before_game_relations_attach=attach
def attach(bank_name,acb,rows,cfg=None):
    _before_game_relations_attach(bank_name,acb,rows,cfg)
    import game_voice_relations
    game_voice_relations.attach(bank_name,acb,rows,cfg)
