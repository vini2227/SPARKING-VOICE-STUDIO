"""Read-only annotations from FateData and confirmed AppealVoice item effects."""
import struct
import functools,json,re
from pathlib import Path

EVENT_PT={'Introduction':'Introdução','Victory':'Vitória','Change':'Troca','IntroductionFriend':'Introdução: amigo','IntroductionEnemy':'Introdução: inimigo','IntroductionUnknown':'Introdução: desconhecido','IntroductionRival':'Introdução: rival','IntroductionGreatApe':'Introdução: Great Ape','IntroductionMirror':'Introdução: mesmo personagem','VictoryFriend':'Vitória: amigo','VictoryEnemy':'Vitória: inimigo','VictoryNormal':'Vitória: normal'}

@functools.lru_cache(maxsize=1)
def catalog():
    path=Path(__file__).resolve().parents[1]/'Data/voice_contexts.json'
    try:return json.loads(path.read_text(encoding='utf-8'))['cues']
    except FileNotFoundError:return {}

def attach(rows,bank_name=None,acb=None,cfg=None):
    import game_installation
    if cfg is not None and bank_name is not None and acb is not None and game_installation.identity(cfg):
        import live_voice_references
        try:live_voice_references.annotations(cfg,bank_name,acb,rows)
        except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):
            for row in rows:row.update(interactions=[],emotes=[],usage_contexts=[])
        return
    if bank_name is not None:
        import hashlib,attack_context
        if attack_context.catalog().get('bank_acb_sha256',{}).get(bank_name)!=hashlib.sha256(acb or b'').hexdigest():
            for row in rows:row.update(interactions=[],emotes=[],usage_contexts=[])
            return
    index=catalog()
    for row in rows:
        contexts=[];emotes=[]
        for cue in row['cue_names']:
            data=index.get(cue,{})
            for target,source in ((contexts,data.get('interactions',[])),(emotes,data.get('emotes',[]))):
                for entry in source:
                    if entry not in target:target.append(entry)
        row['interactions']=contexts;row['emotes']=emotes
        # Exact regular BTLCV cue identity; never infer a function from a suffix alone.
        row['usage_contexts']=['GuardBreak'] if 10758 in row['cue_ids'] and any(
            re.fullmatch(r'\d{4}_\d{2}_0758',cue) for cue in row['cue_names']) else []

EVENT_LANGUAGES=json.loads((Path(__file__).resolve().parents[1]/'Data/context_languages.json').read_text(encoding='utf-8'))
EVENT_LANGUAGES['pt']=EVENT_PT

USAGE_LABELS={
    'pt':{'GuardBreak':'Reação à quebra de defesa'},
    'en':{'GuardBreak':'Guard break reaction'},
    'es':{'GuardBreak':'Reacción a la ruptura de guardia'},
    'fr':{'GuardBreak':'Réaction à la rupture de garde'},
    'it':{'GuardBreak':'Reazione alla rottura della guardia'},
}
USAGE_NOTES={
    'pt':'Uso confirmado; este áudio também pode aparecer em outros contextos.',
    'en':'Confirmed use; this audio can also appear in other contexts.',
    'es':'Uso confirmado; este audio también puede aparecer en otros contextos.',
    'fr':"Utilisation confirmée ; cet audio peut aussi apparaître dans d'autres contextes.",
    'it':'Uso confermato; questo audio può comparire anche in altri contesti.',
}
def usage_label(usage,language):return USAGE_LABELS.get(language,USAGE_LABELS['en']).get(usage,usage)

def event_label(event,language):return EVENT_LANGUAGES.get(language,{}).get(event,event)

def matches_scope(row,scope):
    import function_refinements
    interactions=bool(row.get('interactions'))
    common=function_refinements.has_exact_function(row) or bool(row.get('_manual')) or bool(row.get('functions')) or any(x!='Unclassified' for x in row.get('english',[])) or bool(row.get('emotes')) or bool(row.get('usage_contexts')) or bool(row.get('attack_contexts'))
    return scope=='all' or scope=='interactions' and interactions or scope=='emotes' and bool(row.get('emotes')) or scope=='functions' and (common or not interactions)

def identified(row,scope):
    import function_refinements
    if scope in ('all','functions') and function_refinements.has_exact_function(row):return True
    if scope in ('all','functions') and row.get('_manual'):return True
    return (scope!='interactions' and (any(x and x!='Unclassified' for x in row.get('english',[])) or bool(row.get('emotes')) or bool(row.get('usage_contexts')) or bool(row.get('attack_contexts')))) or (scope in ('all','interactions') and bool(row.get('interactions')))

def matches_filter(row,value,scope):
    if not matches_scope(row,scope):return False
    if value=='*':return True
    if value=='+':return identified(row,scope)
    if value=='~':return not identified(row,scope)
    if value.startswith('manual:'):return scope in ('all','functions') and value[7:] in row.get('_manual',{}).get('tags',[])
    if value.startswith('action:'):return scope in ('all','functions') and any(c['action']==value[7:] for c in row.get('attack_contexts',[]))
    if value.startswith('usage:'):return scope in ('all','functions') and value[6:] in row.get('usage_contexts',[])
    if value.startswith('event:'):return any(x['event']==value[6:] for x in row.get('interactions',[]))
    if value.startswith('target:'):return any(x.get('target_id')==value[7:] for x in row.get('interactions',[]))
    if value=='emote:AppealVoice':return bool(row.get('emotes'))
    return value in row['functions']

def options(rows,scope,language):
    result=[]
    if scope in ('all','functions'):
        result.extend(('manual:'+tag,'Manual: '+tag) for tag in sorted({tag for row in rows for tag in row.get('_manual',{}).get('tags',[])}))
    if scope in ('all','interactions'):
        contexts=[x for row in rows for x in row.get('interactions',[])]
        result.extend(('event:'+event,event_label(event,language)) for event in sorted({x['event'] for x in contexts}))
        targets={x['target_id']:_character(x['target_id'],language) for x in contexts if x.get('target_id')}
        result.extend(('target:'+key,name+' ['+key+']') for key,name in sorted(targets.items(),key=lambda kv:kv[1].casefold()))
    if scope!='interactions' and any(row.get('emotes') for row in rows):result.append(('emote:AppealVoice','Emote — AppealVoice'))
    if scope in ('all','functions'):
        result.extend(('action:'+action,('' if action=='MenuSelection' else action_label(language)+': ')+context_action_text(action,language)) for action in sorted({c['action'] for row in rows for c in row.get('attack_contexts',[])}))
        result.extend(('usage:'+usage,usage_label(usage,language)) for usage in sorted({u for row in rows for u in row.get('usage_contexts',[])}))
    return result

def descriptions(row,language,scope='all',compact=True):
    result=[]
    if scope in ('all','functions') and row.get('_manual'):result.append('Manual: '+row['_manual']['label'])
    if scope in ('all','interactions'):
        groups={}
        for context in row.get('interactions',[]):
            group=groups.setdefault(context['event'],[])
            name=_character(context.get('target_id'),language) if context.get('target_id') else None
            if name and name not in group:group.append(name)
        for event,names in groups.items():
            label=event_label(event,language)
            if names:
                label+=' — '+', '.join(names[:3] if compact else names)
                if compact and len(names)>3:label+=f' (+{len(names)-3})'
            result.append(label)
    if scope!='interactions' and row.get('emotes'):result.append('Emote — AppealVoice')
    if scope in ('all','functions'):result.extend(usage_label(u,language) for u in row.get('usage_contexts',[]))
    if scope in ('all','functions') and row.get('attack_contexts'):
        actions=sorted({c['action'] for c in row['attack_contexts']})
        result.append(('' if actions==['MenuSelection'] else action_label(language)+': ')+', '.join(context_action_text(a,language) for a in (actions[:3] if compact else actions))+(f' (+{len(actions)-3})' if compact and len(actions)>3 else ''))
    return result


SUBTITLE_PT = {'変身IN':'Transformação — entrada','変身OT':'Transformação — saída','変身LP':'Transformação — ciclo','変身解除IN':'Reversão da transformação — entrada','変身解除OT':'Reversão da transformação — saída','インパクト勝利':'Vitória no impacto','ソニックスウェイ煽り':'Provocação de Sonic Sway','バトル導入演出（汎用）':'Introdução de batalha (genérica)','バトル勝利演出（汎用）':'Vitória de batalha (genérica)','合体完了':'Fusão concluída','合体前セリフ1':'Fala antes da fusão 1','合体前セリフ2':'Fala antes da fusão 2','通常投げ':'Arremesso normal','大型キャラ汎用投げ':'Arremesso de personagem gigante','アクション_吸収':'Absorção','SPC MAX Sparking状態開始':'Início do estado Sparking máximo','因縁投げ（ボディチェンジ対策用）':'Arremesso de rivalidade (Body Change)','フュージョン（フュ―……ジョン！)':'Fusão — chamada','フュージョン（はっ！)':'Fusão — conclusão'}
SKILL_PT={'ワイルドセンス':'Wild Sense','爆発波':'Onda explosiva','残像拳':'Afterimage','フルパワー':'Poder máximo','サイヤ人魂':'Espírito Saiyajin','フィニッシュサイン':'Finish Sign','瞬間移動':'Transmissão instantânea','ハイテンション':'High Tension','サイコキネシス':'Psicocinese','バリアー':'Barreira','フルパワーチャージ':'Carga de poder máximo','ギリギリ限界パワー':'Poder no limite','カカロットォ！':'Kakarotto!','乙女の怒り':'Fúria da donzela','雄たけび':'Rugido','不死身の体':'Corpo imortal','怪光線':'Raio estranho','ミスティックブレス':'Mystic Breath','パンプアップ':'Pump Up'}
def context_action_text(action,language):
    if action=='MenuSelection':
        import cue_name_functions
        return cue_name_functions.label(language)
    if not action.startswith('Subtitles: '):return action
    key=action[len('Subtitles: '):]
    if language!='pt':return 'Subtitle mapping: '+key
    label=SUBTITLE_PT.get(key)
    if not label:
        match=re.fullmatch(r'スキル\((.*)\)',key)
        if match:label='Habilidade: '+SKILL_PT.get(match[1],match[1])
        match=re.fullmatch(r'固有変身(\d+)\(形態別流用対応\)',key)
        if match:label='Transformação específica '+match[1]+' (reutilização por forma)'
    return 'Legenda configurada: '+(label or key)

def action_label(language):
    return {'pt':'Referência de ação','en':'Action reference','es':'Referencia de acción','fr':"Référence d'action",'it':"Riferimento azione"}.get(language,'Action reference')

def search_text(row):
    return ' '.join(c['action']+' '+context_action_text(c['action'],'pt')+' '+c['cue_name']+' '+str(c['cue_id']) for c in row.get('attack_contexts',[]))+' '+' '.join(usage_label(u,lang) for u in row.get('usage_contexts',[]) for lang in USAGE_LABELS)+' '+' '.join(str(value) for x in row.get('interactions',[])+row.get('emotes',[]) for value in x.values() if value is not None)

def details(row,language):
    result=[]
    manual=row.get('_manual')
    if manual:
        result.extend(['Manual: '+manual['label'],'Tags pessoais: '+', '.join(manual['tags']),manual['notes'], 'Anotação do usuário; uso no jogo não verificado.'])
    for x in row.get('interactions',[]):
        line=event_label(x['event'],language)
        if x.get('target_id'):line+=' — '+_character(x['target_id'],language)+' ['+x['target_id']+']'
        line+=' | '+x['cue_name']+' | '+_character(x['actor_id'],language)
        if x.get('order'):line+=' | '+{1:'First',2:'Second'}.get(x['order'],str(x['order']))
        result.append(line)
    for x in row.get('emotes',[]):result.append('Emote — AppealVoice | '+x['cue_name']+' | '+x['item'])
    for usage in row.get('usage_contexts',[]):
        result.append(usage_label(usage,language)+' | Cue ID 10758 | '+USAGE_NOTES.get(language,USAGE_NOTES['en']))
        result.append('GuardBreakReaction: actGRCRA → MS_9998_actGRCRA → LSSND_COMMON_REACTION_GRCRA (Chara / Voice)')
    for c in row.get('attack_contexts',[]):
        if c.get('source_kind')=='cue_name_pattern':
            import cue_name_functions
            result.append(cue_name_functions.details(c,language))
            continue
        result.append(action_label(language)+': '+context_action_text(c['action'],language)+' | Cue '+str(c['cue_id'])+' | '+c['cue_name'])
        if c.get('reference_validation'):result.append('Reference validation: '+c['reference_validation'])
        if c.get('character_data'):
            result.append('Character Data: '+c['character_data'])
            result.append('SoundDataAsset: '+c['sound_data'])
        if c.get('action_metadata'):
            meta=c['action_metadata']
            result.append('Action Data: '+meta['asset']+' | GroupId: '+str(meta.get('group') or '—'))
        if c.get('shared_participant'):
            result.append(('Participação de outro personagem: ' if language=='pt' else 'Other character participant: ')+_character(c['speaker_actor'],language)+' ['+c['speaker_actor']+']')
        if c.get('source_kind') in ('battle_dialogue','battle_dialogue_pattern'):
            label={'pt':'Trilha de diálogo de batalha','en':'Battle dialogue track','es':'Pista de diálogo de batalla','fr':'Piste de dialogue de combat','it':'Traccia dialogo di battaglia'}.get(language,'Battle dialogue track')
            result.append(label+' | '+c['text_key']+' | TargetType: Myself | IsBattleVoice: true')
            if c.get('subtitle_asset'):result.append('PatternName: '+c['subtitle_pattern']+' → '+c['subtitle_asset'])
        if c.get('source_kind') in ('animation_notify','event_sound','event_dialogue','sound_branch','sound_pattern','chain_sound'):
            result.append('Source: '+c['source_kind']+' | Property: '+str(c.get('property_path',''))+' | Notify: '+str(c.get('notify_name',''))+' | Pattern: '+str(c.get('sound_pattern',''))+' | Branch: '+str(c.get('sound_branch',''))+' | Chain: '+str(c.get('chain_sound_key','')))
        if c.get('source_kind')=='runtime_request':
            result.append(('Componente observado em reprodução; saída audível não confirmada.' if language=='pt' else 'Component observed playing; audible output not confirmed.') if c.get('observation_phase')=='playing_observed' else ('Solicitação observada; reprodução audível não confirmada.' if language=='pt' else 'Observed request; audible playback not confirmed.'))
            result.append('Action: '+c.get('runtime_action','')+' | User marker: '+c.get('marker','')+' | Observations: '+str(c.get('observations',0)))
            result.append('Observation phase: '+c.get('observation_phase','request_observed'))
            result.append('Trace SHA256: '+c.get('source_file_sha256',''))
        if c.get('source_kind')=='character_subtitles':
            result.append(('Correlação de legenda configurada; execução da fala não confirmada.' if language=='pt' else 'Configured subtitle correlation; voice playback not confirmed.'))
            result.append('PatternName: '+c['subtitle_pattern']+' | SubtitlesData: '+c['subtitle_asset'])
        if c.get('source_kind')=='conditional_voice':
            condition=c['condition']
            kind='RemainingTime' if condition.get('ConditionalTyoe')==1 else 'RemainingHP'
            result.append('ConditionalTyoe: '+kind+' | SettingValue: '+str(condition['SettingValue'])+' | IsWinnerVoice: '+str(bool(condition.get('IsWinnerVoice'))).lower()+' | Priority: '+str(condition['Priority'])+' | PlayAcceptTime: '+str(condition['PlayAcceptTime']))
            result.append('RecordName: '+c['condition_record'])
            if kind=='RemainingHP':result.append('Nome do registro e SettingValue divergem; limiar em execução não confirmado.' if language=='pt' else 'Record name and SettingValue differ; runtime threshold not confirmed.')
            result.append('ActionCategoryArray: '+', '.join(x.split('::')[-1] for x in c['action_categories']))
            result.append('USMAP SHA256: '+c['usmap_sha256'])
        if c.get('source_kind')=='inherited_mls':
            result.append(('Referência pela cadeia DefaultCharacterData; disponibilidade da ação não confirmada.' if language=='pt' else 'Reference through DefaultCharacterData; action availability not confirmed.'))
            result.append('DefaultCharacterData: '+' → '.join(c.get('inheritance',[])))
        result.append(' → '.join([c['root'],c['child']]+c['chain']))
    if row.get('attack_contexts'):
        result.append({'pt':'Referência nos assets analisados; não confirma uso exclusivo nem o ator da fala em tempo de execução.','en':'Reference in the analyzed assets; does not establish exclusive use or runtime speaker.','es':'Referencia en los assets analizados; no confirma uso exclusivo ni el hablante en ejecución.','fr':"Référence dans les assets analysés ; ne confirme ni usage exclusif ni locuteur à l'exécution.",'it':"Riferimento negli asset analizzati; non conferma uso esclusivo né interlocutore durante l'esecuzione."}.get(language,'Reference in analyzed assets.'))
    return '\n'.join(result)

_base_search_text=search_text
def search_text(row):
    m=row.get("_manual",{})
    return _base_search_text(row)+" "+" ".join([m.get("label",""),m.get("notes",""),*m.get("tags",[])])


# Human labels from the same offline language catalog used by the UI.
_EXTRA=json.loads((Path(__file__).resolve().parents[1]/'Data/extra_languages.json').read_text(encoding='utf-8'))
for _language,_groups in _EXTRA.items():
    if 'usage_labels' in _groups:USAGE_LABELS[_language]=_groups['usage_labels']
    if 'usage_notes' in _groups:USAGE_NOTES[_language]=_groups['usage_notes']['GuardBreak']
_original_context_action_text=context_action_text
def _human(text,language):
    from i18n import Translator
    return Translator(language).logical(text)
def context_action_text(action,language):
    if language!='pt':
        for prefix in ('Diagnóstico: ','Contexto marcado: ','Evento/diálogo: ','Animação: '):
            if action.startswith(prefix):return _human(prefix,language)+action[len(prefix):]
    if language=='pt' or not action.startswith('Subtitles: '):return _original_context_action_text(action,language)
    key=action[len('Subtitles: '):]
    label=_EXTRA.get(language,{}).get('subtitles',{}).get(key)
    return _human('Mapeamento de legenda: ',language)+(label or key)
def action_label(language):return _human('Referência de ação',language)
_original_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    values=_original_descriptions(row,language,scope,compact)
    return [value.replace('Manual: ',_human('Manual: ',language),1) if value.startswith('Manual: ') else value.replace('Emote — AppealVoice',_human('Emote — AppealVoice',language)) for value in values]
_original_details=details
def details(row,language):
    value=_original_details(row,language)
    replacements={
        'Manual: ':'Manual: ','Tags pessoais: ':'Tags pessoais: ',
        'Anotação do usuário; uso no jogo não verificado.':'Anotação do usuário; uso no jogo não verificado.',
        'Emote — AppealVoice':'Emote — AppealVoice',
        'Battle dialogue track':'Trilha de diálogo de batalha',
        'Configured subtitle correlation; voice playback not confirmed.':'Correlação de legenda configurada; execução da fala não confirmada.',
        'Reference through DefaultCharacterData; action availability not confirmed.':'Referência pela cadeia DefaultCharacterData; disponibilidade da ação não confirmada.',
        'Reference in analyzed assets.':'Referência nos assets analisados; não confirma uso exclusivo nem o ator da fala em tempo de execução.'}
    for original,source in replacements.items():value=value.replace(original,_human(source,language))
    return value

def _character(actor,language):
    import game_characters
    return game_characters.name(actor,language)


# User-supplied classifications remain separate from verified asset references.
import user_voice_functions as _user_functions
_before_user_identified=identified
def identified(row,scope):
    return _before_user_identified(row,scope) or bool(_user_functions.functions(row)) and (scope in ('all','functions') or scope=='emotes' and _user_functions.emote(row) or scope=='interactions' and _user_functions.interaction(row))
_before_user_scope=matches_scope
def matches_scope(row,scope):
    return _before_user_scope(row,scope) or scope=='emotes' and _user_functions.emote(row) or scope=='interactions' and _user_functions.interaction(row)
_before_user_filter=matches_filter
def matches_filter(row,value,scope):
    if value.startswith('user:'):
        return scope in ('all','functions','emotes','interactions') and any(r['key']==value[5:] for r in _user_functions.functions(row)) and matches_scope(row,scope)
    return _before_user_filter(row,value,scope)
_before_user_options=options
def options(rows,scope,language):
    values=_before_user_options(rows,scope,language)
    if scope in ('all','functions','emotes','interactions'):
        keys={r['key']:r for row in rows for r in _user_functions.functions(row) if (scope!='emotes' or r['key']=='unknown_emote') and (scope!='interactions' or r['key']=='unknown_interactions_100')}
        values.extend(('user:'+key,_human(rule['label'],language)) for key,rule in sorted(keys.items()))
    return values
_before_user_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    values=_before_user_descriptions(row,language,scope,compact)
    if scope in ('all','functions') or scope=='emotes' and _user_functions.emote(row) or scope=='interactions' and _user_functions.interaction(row):
        values.extend(_human('Manual: ',language)+label for label in _user_functions.labels(row,language))
    return values
_before_user_details=details
def details(row,language):
    value=_before_user_details(row,language)
    for rule,label in zip(_user_functions.functions(row),_user_functions.labels(row,language)):
        value+='\n'+_human('Manual: ',language)+label+' | Cue: '+', '.join(map(str,rule['matched']))
        if rule.get('description'):value+='\n'+_human(rule['description'],language)
        value+='\n'+_human('Classificação por correlação com o grupo de Cue IDs do modo história.' if rule.get('source')=='cue_family_correlation' else 'Classificação manual confirmada pelo usuário.',language)
    return value.strip()
_before_user_search=search_text
def search_text(row):
    return _before_user_search(row)+' '+' '.join(_user_functions.labels(row,'pt')+_user_functions.labels(row,'en'))

_before_refined_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    values=_before_refined_descriptions(row,language,scope,compact)
    if scope in ('all','functions'):
        import function_refinements as refinements
        extra=[]
        for c in row.get('function_refinements',[]):
            if c['refinement_kind']=='exact_source_cue':
                value=_human('Vínculo no personagem de origem: ',language)+refinements.label(c,language)
                if value not in extra:extra.append(value)
        values.extend(extra[:3] if compact else extra)
    return values
_before_refined_details=details
def details(row,language):
    value=_before_refined_details(row,language)
    import function_refinements as refinements
    for c in row.get('function_refinements',[]):
        if c['refinement_kind']=='exact_source_cue':
            value+='\n'+_human('Vínculo no personagem de origem: ',language)+refinements.label(c,language)+' | '+_character(c['origin_actor'],language)+' ['+c['origin_actor']+'] | '+c['cue_name']
            value+='\n'+' → '.join([c['root'],c['child']]+c.get('chain',[]))
            if c.get('source_alias'):value+='\n'+c['source_alias']+' → '+c['cue_name']
            value+='\n'+_human('O mesmo nome de cue possui esta referência nos arquivos do personagem de origem; a cena específica do modo história não é determinada por esse vínculo.',language)
        else:
            value+='\n'+_human('Grupo provável: ',language)+refinements.label(c,language)+' | '+c['cue_name']
            value+='\n'+_human('Inferência pela faixa de cues e pelas referências vizinhas da mesma forma; não é um vínculo direto desta fala.',language)
            value+='\n'+', '.join(sorted({a['cue_name']+' ['+a['action']+']' for a in c['anchors']}))
    return value
_before_refined_search=search_text
def search_text(row):
    return _before_refined_search(row)+' '+' '.join(c.get('action',c.get('family',''))+' '+c['cue_name']+' '+c['origin_actor'] for c in row.get('function_refinements',[]))

_before_compact_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    values=_before_compact_descriptions(row,language,scope,compact)
    if not compact:return values
    import compact_functions
    return compact_functions.context_values(row,values,language)
_before_compact_options=options
def options(rows,scope,language):
    import compact_functions
    result=[]
    for key,value in _before_compact_options(rows,scope,language):
        if key.startswith('user:'):
            rule=next(r for r in _user_functions.rules() if r['key']==key[5:])
            value=compact_functions.manual_label(rule['label'],language)
        elif key.startswith('action:'):
            code=key[7:];human=compact_functions.action(code,language)
            if human!=code:value=human
        result.append((key,value))
    return result
_before_compact_details=details
def details(row,language):
    import compact_functions
    full=[(compact_functions.FULL.get(language,{}).get(v) or v) for v in dict.fromkeys(row.get('english',[])) if v and v!='Unclassified']
    value=_before_compact_details(row,language)
    if full:value=_human('Funções completas: ',language)+' / '.join(full)+'\n'+value
    return value

_before_origin_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    values=_before_origin_descriptions(row,language,scope,compact)
    if scope not in ('all','functions','emotes','interactions') or row.get('_manual'):return values
    import compact_functions
    for rule in _user_functions.functions(row):
        origin=_user_functions.display_origin(row,rule)
        if origin=='manual':continue
        full_label=_human(rule['label'],language)
        short_label=compact_functions.manual_label(rule['label'],language)
        candidates={_human('Manual: ',language)+full_label,_human('Manual: ',language)+short_label}
        if origin=='game_reference':
            # The visible automatic function is supplied by the exact-reference entries.
            values=[value for value in values if value not in candidates]
        else:
            values=[(_human('Grupo provável: ',language)+(short_label if compact else full_label)) if value in candidates else value for value in values]
    return values

_before_participant_details=details
def details(row,language):
    value=_before_participant_details(row,language)
    shown=set()
    for c in row.get('attack_contexts',[]):
        for participant in c.get('action_participants',[]):
            marker=(c['action'],participant['actor'],participant['cue_name'],participant['sequence_asset'])
            if marker in shown:continue
            shown.add(marker)
            value+='\n'+_character(participant['actor'],language)+' ['+participant['actor']+'] | '+c['action']+' | '+participant['cue_name']
            value+='\n'+participant['sequence_asset']+' → '+participant['bank_asset']
    return value

# Family correlations identify a broad category, while retaining their provenance.
def correlation_label(rule,language):
    import compact_functions
    label=compact_functions.action('act'+rule['family'],language) if rule.get('family') else compact_functions.function(rule['english'],language)
    companions=[_character(a,language) for a in rule.get('participants',[]) if a[:4]!=rule.get('owner_actor','')[:4]]
    return _human('Grupo provável: ',language)+label+(' — '+', '.join(dict.fromkeys(companions)) if companions else '')

_before_correlations_identified=identified
def identified(row,scope):
    return _before_correlations_identified(row,scope) or scope in ('all','functions') and bool(row.get('function_correlations'))

_before_correlations_scope=matches_scope
def matches_scope(row,scope):
    return _before_correlations_scope(row,scope) or scope in ('all','functions') and bool(row.get('function_correlations'))

_before_correlations_filter=matches_filter
def matches_filter(row,value,scope):
    if value.startswith('category:'):
        import json
        try:keys=json.loads(value[9:])
        except (ValueError,TypeError):return False
        return isinstance(keys,list) and len(keys)<=1000 and any(isinstance(key,str) and not key.startswith('category:') and matches_filter(row,key,scope) for key in keys)
    if value.startswith('usergroup:'):
        return matches_scope(row,scope) and any(r['key'] in value[10:].split(';') for r in _user_functions.functions(row))
    if value.startswith('correlation:'):
        return scope in ('all','functions') and any(r['tag']==value[12:] for r in row.get('function_correlations',[]))
    return _before_correlations_filter(row,value,scope)

_before_correlations_options=options
def options(rows,scope,language):
    values=_before_correlations_options(rows,scope,language)
    # Equal category labels must select the whole category, not an invisible
    # numeric subset. Tk comboboxes cannot distinguish equal displayed strings.
    groups={}
    for key,label in values:
        if key.startswith('user:'):groups.setdefault(label,[]).append(key[5:])
    merged=[];shown=set()
    for key,label in values:
        if key.startswith('user:') and len(groups[label])>1:
            if label in shown:continue
            shown.add(label);key='usergroup:'+';'.join(sorted(groups[label]))
        merged.append((key,label))
    if scope in ('all','functions'):
        rules={r['tag']:r for row in rows for r in row.get('function_correlations',[])}
        merged.extend(('correlation:'+tag,correlation_label(rule,language)) for tag,rule in sorted(rules.items()))
    import json
    categories={}
    for key,label in merged:categories.setdefault(label,[]).append(key)
    result=[];seen=set()
    for key,label in merged:
        if label in seen:continue
        seen.add(label)
        if len(categories[label])>1:key='category:'+json.dumps(categories[label],ensure_ascii=False,separators=(',',':'))
        result.append((key,label))
    return result

_before_correlations_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    values=_before_correlations_descriptions(row,language,scope,compact)
    if scope in ('all','functions'):
        values.extend(correlation_label(rule,language) for rule in row.get('function_correlations',[]))
    return list(dict.fromkeys(values))

_before_correlations_details=details
def details(row,language):
    value=_before_correlations_details(row,language)
    from i18n import Translator
    for rule in row.get('function_correlations',[]):
        value+='\n'+correlation_label(rule,language)+((' | '+str(rule['support'])) if rule.get('relation') else ' | '+rule['tag']+' | '+str(rule['support'])+'/'+str(rule['compared']))
        value+='\n'+Translator(language).logical('Categoria por correlação entre bancos; não confirma a execução desta fala nem altera sua tag original.')
        if rule.get('relation'):
            value+='\n'+Translator(language).logical('Correlação entre formas do mesmo personagem; categoria confirmada no cue equivalente da forma de origem.' if rule['relation']=='same_character_form' else 'Correlação pela faixa de cues e pelos participantes explícitos da ação; o vínculo direto desta fala não foi encontrado.')
            value+='\n'+_character(rule['speaker_actor'],language)+' ['+rule['speaker_actor']+']'
            value+='\n'+', '.join(_character(a,language)+' ['+a+']' for a in rule.get('participants',[]))
        for anchor in rule['anchors']:
            value+='\n'+anchor['bank']+' | '+anchor['cue_name']+' | '+str(anchor['cue_id'])
            if anchor.get('tag'):value+=' | '+anchor['tag']
            if anchor.get('action'):value+=' | '+anchor['action']
            if anchor.get('root'):value+='\n'+anchor['root']+' → '+anchor['child']
    return value

_before_correlations_search=search_text
def search_text(row):
    return _before_correlations_search(row)+' '+' '.join(correlation_label(r,'pt')+' '+correlation_label(r,'en')+' '+r['tag'] for r in row.get('function_correlations',[]))

_before_fusion_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    import fusion_voice_relations as fusion
    if scope not in ('all','functions') or not row.get('fusion_relations'):
        return _before_fusion_descriptions(row,language,scope,compact)
    enriched={r['action'] for r in row['fusion_relations']}
    display=dict(row,attack_contexts=[c for c in row.get('attack_contexts',[]) if c['action'] not in enriched])
    return list(dict.fromkeys(_before_fusion_descriptions(display,language,scope,compact)+fusion.labels(row,language,compact)))

_before_fusion_details=details
def details(row,language):
    import fusion_voice_relations as fusion
    extra=fusion.details(row,language)
    return _before_fusion_details(row,language)+('\n'+extra if extra else '')

_before_fusion_search=search_text
def search_text(row):
    import fusion_voice_relations as fusion
    return _before_fusion_search(row)+' '+' '.join(fusion.labels(row,'pt',False)+fusion.labels(row,'en',False))+' '+' '.join(' '.join(r['partners']+[r['result']]) for r in row.get('fusion_relations',[]))

_before_audio_identified=identified
def identified(row,scope):
    return _before_audio_identified(row,scope) or scope in ('all','functions') and bool(row.get('audio_equivalences'))

_before_audio_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    import audio_function_equivalences as audio
    values=_before_audio_descriptions(row,language,scope,compact)
    if scope in ('all','functions'):values.extend(audio.label(e,language) for e in row.get('audio_equivalences',[]))
    return list(dict.fromkeys(values))

_before_audio_details=details
def details(row,language):
    import audio_function_equivalences as audio
    extra=audio.details(row,language)
    return _before_audio_details(row,language)+('\n'+extra if extra else '')

_before_audio_filter=matches_filter
def matches_filter(row,value,scope):
    if value.startswith('audio:'):return scope in ('all','functions') and any(e['action']==value[6:] for e in row.get('audio_equivalences',[]))
    return _before_audio_filter(row,value,scope)

_before_audio_options=options
def options(rows,scope,language):
    import audio_function_equivalences as audio
    values=_before_audio_options(rows,scope,language)
    if scope in ('all','functions'):
        actions={e['action']:e for r in rows for e in r.get('audio_equivalences',[])}
        values.extend(('audio:'+key,audio.label(e,language)) for key,e in sorted(actions.items()))
    return values

_before_audio_search=search_text
def search_text(row):
    import audio_function_equivalences as audio
    return _before_audio_search(row)+' '+' '.join(audio.label(e,'pt')+' '+audio.label(e,'en')+' '+e['anchor_cue_name'] for e in row.get('audio_equivalences',[]))

_before_game_relations_identified=identified
def identified(row,scope):
    return _before_game_relations_identified(row,scope) or scope in ('all','functions') and bool(row.get('participant_relations'))

_before_game_relations_scope=matches_scope
def matches_scope(row,scope):
    return _before_game_relations_scope(row,scope) or scope=='functions' and bool(row.get('participant_relations'))

_before_game_relations_descriptions=descriptions
def descriptions(row,language,scope='all',compact=True):
    import game_voice_relations as relations
    values=_before_game_relations_descriptions(row,language,scope,compact)
    if scope in ('all','functions'):values.extend(relations.labels(row,language,compact))
    return list(dict.fromkeys(values))

_before_game_relations_details=details
def details(row,language):
    import game_voice_relations as relations
    extra=relations.details(row,language)
    return _before_game_relations_details(row,language)+('\n'+extra if extra else '')

_before_game_relations_search=search_text
def search_text(row):
    import game_voice_relations as relations
    return _before_game_relations_search(row)+' '+relations.details(row,'pt')+' '+relations.details(row,'en')

_before_origin_details=details
def details(row,language):
    import voice_origin_details
    extra=voice_origin_details.detail(row,language)
    return _before_origin_details(row,language)+('\n\n'+extra if extra else '')

_before_origin_search=search_text
def search_text(row):
    import voice_origin_details
    return _before_origin_search(row)+' '+voice_origin_details.search_text(row)
