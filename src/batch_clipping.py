"""Reversible batch peak headroom for saved custom voice projects."""
import math,os,json
from pathlib import Path
import core,audio_levels,project_audio

TARGET_DBFS=-1.0

def safe_gain(peak,current):
    current=audio_levels.valid_gain(current)
    if peak is None:return current
    allowed=math.floor((TARGET_DBFS-peak)*10+1e-8)/10
    return max(audio_levels.MIN_GAIN,min(current,allowed))

def correct_project(cfg,project,progress=lambda s:None,io_lock=None,cache=None):
    project=core.owned(project);path=project/'project.json'
    data=json.loads(path.read_text(encoding='utf-8'))
    bank=core.Bank(cfg,None if data.get('source') else core.Pak(cfg),data['bank'],data.get('source'))
    replacements=dict(data.get('replacements',{}));gains=dict(data.get('gains',{}));variations=data.get('variations',{})
    keep=data['unreplaced_policy']=='original' if 'unreplaced_policy' in data else bool(bank.external) and data.get('keep_imported',True)
    changes=[];cache=cache if cache is not None else {}
    work=core.owned(core.APP/'Cache/Clipping');work.mkdir(parents=True,exist_ok=True)
    for index,row in enumerate(bank.rows):
        key=row['key'];source=replacements.get(key)
        if not source and not core.preserve_unreplaced(bank,row,keep):continue
        progress(f"{data.get('project_name',bank.name)} • {index+1}/{len(bank.rows)}")
        if not source:source=str(bank.original(row))
        p=Path(source);stat=p.stat();variation=variations.get(key,1)
        signature=(str(p.resolve()),stat.st_mtime_ns,stat.st_size,row['rate'],row['channels'],variation)
        if signature not in cache:
            processed=work/(os.urandom(6).hex()+'.wav')
            try:
                core.normalize_wav(p,processed,row['rate'],row['channels'],row['samples'],variation=variation)
                peaks=[audio_levels.analyze(processed)['peak_dbfs'],audio_levels.analyze(p)['peak_dbfs']]
                cache[signature]=max((value for value in peaks if value is not None),default=None)
            finally:processed.unlink(missing_ok=True)
        peak=cache[signature];old=audio_levels.valid_gain(gains.get(key,0))
        new=safe_gain(peak,old)
        if new<old-1e-8:
            replacements[key]=str(p);gains[key]=new
            changes.append({'key':key,'cue_ids':row['cue_ids'],'old_gain_db':old,'new_gain_db':new,'peak_before_dbfs':peak+old,'peak_after_dbfs':peak+new})
    if changes:
        data['replacements']=replacements;data['gains']=gains
        core.write_json(path,data)
        project_audio.materialize(bank,project,replacements,gains,variations,keep,io_lock)
    return {'project':str(project),'name':data.get('project_name',bank.name),'changes':changes}

def correct_projects(cfg,projects,progress=lambda s:None,io_lock=None):
    result={'target_peak_dbfs':TARGET_DBFS,'projects':[],'errors':[]};cache={}
    for project in projects:
        try:result['projects'].append(correct_project(cfg,project,progress,io_lock,cache))
        except Exception as error:result['errors'].append({'project':str(project),'error':str(error)})
    result['corrected_voices']=sum(len(p['changes']) for p in result['projects'])
    report=core.owned(core.APP/'Reports'/('Clipping_'+os.urandom(6).hex()+'.json'))
    core.write_json(report,result);result['report']=str(report)
    return result
