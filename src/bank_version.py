"""Keep edits tied to complete cue identities when official banks change."""
import copy,hashlib,json

class BankReferenceConflict(ValueError):
    pass

def row_identity(row):
    return {'cue_ids':sorted(set(row.get('cue_ids',[]))),'cue_names':sorted(set(row.get('cue_names',[])))}

def snapshot(bank):
    return {'schema':1,'bank':bank.name,'acb_sha256':hashlib.sha256(bank.acb).hexdigest(),
        'awb_sha256':hashlib.sha256(bank.stream_bytes).hexdigest(),
        'game_identity':getattr(bank,'game_identity',None),
        'rows':{row['key']:row_identity(row) for row in bank.rows}}

def identity_token(identity):return json.dumps(identity,sort_keys=True,separators=(',',':'))

def reconcile(project,bank):
    """Never remap by waveform ID alone. Reject conflicts before changing the manifest."""
    old=project.get('bank_reference')
    if not old:return project,{'legacy':True,'changed':False,'remapped':0}
    if old.get('schema')!=1 or old.get('bank')!=bank.name or not isinstance(old.get('rows'),dict):
        raise ValueError('Referência de versão do banco inválida no projeto.')
    current=snapshot(bank)
    changed=(old.get('acb_sha256')!=current['acb_sha256'] or old.get('awb_sha256')!=current['awb_sha256'])
    tracked=set(project.get('replacements',{}))|set(project.get('manual_identifications',{}))
    targets={}
    for row in bank.rows:
        identity=row_identity(row)
        if identity['cue_names'] and identity['cue_ids']:targets.setdefault(identity_token(identity),[]).append(row['key'])
    remap={};conflicts=[]
    for key in tracked:
        identity=old['rows'].get(key)
        if old.get('acb_sha256')==current['acb_sha256'] and key in current['rows'] and identity==current['rows'][key]:
            remap[key]=key;continue
        if not identity or not identity.get('cue_ids') or not identity.get('cue_names'):
            conflicts.append(key);continue
        matches=targets.get(identity_token(identity),[])
        if len(matches)!=1:conflicts.append(key)
        else:remap[key]=matches[0]
    if conflicts or len(set(remap.values()))!=len(remap):
        raise BankReferenceConflict('O banco mudou e há edições sem correspondência exata de Cue ID e nome ('+', '.join(conflicts[:10])+'). O projeto original foi preservado. Use a migração para revisar a correspondência antes de exportar.')
    result=copy.deepcopy(project)
    for field in ('replacements','gains','variations','trim_originals','processing_originals','effects_originals','speed_originals','duplicate_originals','manual_identifications'):
        result[field]={remap.get(key,key):value for key,value in result.get(field,{}).items()}
    result['bank_reference']=current
    return result,{'legacy':False,'changed':changed,'remapped':sum(key!=value for key,value in remap.items())}

def ensure_current(bank):
    if not bank.external and getattr(bank,'game_identity',None):
        import game_installation
        if bank.game_identity!=game_installation.identity(bank.cfg):
            raise ValueError('O jogo foi atualizado depois que este banco foi aberto. Salve o projeto e reabra o banco para verificar as referências antes de exportar.')


EDIT_FIELDS=('replacements','gains','variations','trim_originals','processing_originals','effects_originals','speed_originals','duplicate_originals','manual_identifications')

def resume(project,bank):
    """Project continuation only: migrate stable logical cues, preserve unresolved edits."""
    try:
        return reconcile(project,bank)
    except BankReferenceConflict:
        pass
    old=project['bank_reference'];current=snapshot(bank)
    tracked=set().union(*(project.get(field,{}) for field in EDIT_FIELDS))
    remap={};methods={};unresolved={}
    def main_names(identity):
        return {name for name in identity.get('cue_names',[]) if not name.startswith('PTN_')}
    for key in sorted(tracked):
        identity=old['rows'].get(key,{})
        exact=[r['key'] for r in bank.rows if identity.get('cue_ids') and identity.get('cue_names') and row_identity(r)==identity]
        if len(exact)==1:
            remap[key]=exact[0];methods[key]='complete_identity';continue
        names=main_names(identity)
        # Pattern aliases can move after resolver/game updates. All actual logical
        # voice names must agree; physical waveform numbers never provide evidence.
        matches=[r['key'] for r in bank.rows if names and main_names(row_identity(r))==names and set(r['cue_ids'])&set(identity.get('cue_ids',[]))]
        old_matches=[k for k,i in old['rows'].items() if names and main_names(i)==names]
        if len(matches)==1 and len(old_matches)==1:
            remap[key]=matches[0];methods[key]='logical_voice_names_and_cue_ids'
        else:unresolved[key]='missing_or_ambiguous_logical_voice'
    from collections import Counter
    collisions={key for key,count in Counter(remap.values()).items() if count>1}
    for key,target in list(remap.items()):
        if target in collisions:
            remap.pop(key);methods.pop(key);unresolved[key]='multiple_edits_for_one_voice'
    result=copy.deepcopy(project)
    for field in EDIT_FIELDS:
        result[field]={remap[key]:value for key,value in result.get(field,{}).items() if key in remap}
    for key,item in result['manual_identifications'].items():
        item['identity']={'cue_ids':sorted(bank.wave_rows[key]['cue_ids']),'cue_names':sorted(bank.wave_rows[key]['cue_names'])}
    result['bank_reference']=current
    report={'schema':1,'kind':'automatic_project_resume','source_reference':old,'target_reference':current,
            'matches':[{'source_key':key,'target_key':target,'method':methods[key]} for key,target in remap.items()],
            'pending':{key:{'reason':reason,'identity':old['rows'].get(key),'edits':{field:copy.deepcopy(project[field][key]) for field in EDIT_FIELDS if key in project.get(field,{})}} for key,reason in unresolved.items()}}
    # Preserve the exact manifest and the pending edits before presenting a session.
    # The live project is only replaced by the normal Save operation.
    from pathlib import Path
    import core
    path=Path(project['project_file'])
    raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    folder=path.parent/'MigrationBackups'/digest[:24];folder.mkdir(parents=True,exist_ok=True)
    original=folder/'project.original.json'
    if original.exists():
        if original.read_bytes()!=raw:raise ValueError('Backup de migração inconsistente.')
    else:
        with original.open('xb') as stream:stream.write(raw)
    report['backup']=str(original)
    session_digest=hashlib.sha256(json.dumps(project,sort_keys=True).encode()).hexdigest()[:16]
    session_backup=folder/('session_'+session_digest+'.json')
    core.write_json(session_backup,project)
    report['session_backup']=str(session_backup)
    target_digest=hashlib.sha256(json.dumps(current,sort_keys=True).encode()).hexdigest()[:16]
    report_path=folder/('migration_'+session_digest+'_'+target_digest+'.json')
    core.write_json(report_path,report)
    migration=result.get('migration') or {}
    migration.setdefault('resume_history',[]).append({'report':str(report_path),'backup':str(original),'matched':len(remap),'pending':len(unresolved)})
    result['migration']=migration
    return result,{'legacy':False,'changed':True,'automatic_migration':True,'remapped':sum(k!=v for k,v in remap.items()),'matched':len(remap),'pending':len(unresolved),'report':str(report_path),'backup':str(original)}
