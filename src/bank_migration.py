import project_names
"""Read old cue identities without an old Unreal template; migrate conservatively."""
import hashlib,collections,re,time,uuid
from pathlib import Path
import core

def hca_format(data):
    if len(data)<24 or bytes(x&127 for x in data[:4])!=b'HCA\0':raise ValueError('Faixa HCA inválida no banco antigo.')
    end=core.be(data,6,2);header=bytes(x&127 for x in data[:end]);at=header.find(b'fmt\0')
    if not 24<=end<=len(data) or at<0 or at+16>end:raise ValueError('Cabeçalho HCA incompleto no banco antigo.')
    channels=data[at+4];rate=core.be(data,at+5,3)
    samples=core.be(data,at+8,4)*1024-core.be(data,at+12,2)-core.be(data,at+14,2)
    if not 1<=channels<=8 or not 8000<=rate<=192000 or samples<=0:raise ValueError('Formato HCA não suportado no banco antigo.')
    return rate,channels,samples

class OldBank(core.Bank):
    """Metadata reader only. This object is never used as an export template."""
    def __init__(self,cfg,acb,awb,language,source,legacy_editor=False):
        self.cfg=cfg;self.acb=acb;self.root=core.UTF(acb);self.stream_bytes=awb;self.stream=core.Awb(awb)
        self.language=language;self.external=True;self.source=source;self.pak=None
        self.name=str(self.root.rows[0].get('Name','OldBank'))
        self.tables={key:self.root.child(key) for key in ('CueTable','CueNameTable','WaveformTable','SynthTable','SequenceTable','TrackTable','TrackEventTable','CommandTable')}
        if any(not self.tables[k] for k in ('CueTable','CueNameTable','WaveformTable')):raise ValueError('Banco antigo sem tabela de cues ou de áudio.')
        table=self.root.child('StreamAwbHash');self.hash_verified=False
        if table:
            at,size=table.rows[0]['Hash'];self.hash_verified=acb[at:at+size]==hashlib.md5(awb).digest()
        if not self.hash_verified and not legacy_editor:raise ValueError('O AWB selecionado não corresponde ao ACB antigo.')
        memory=self.root.rows[0].get('AwbFile');self.memory=core.Awb(self.blob(memory)) if memory and memory[1] else None
        self.rows=[];self.wave_rows={};self.unresolved=[]
        try:self.functions=core.pattern_functions(cfg)
        except (OSError,ValueError):self.functions={}
        for i,entry in enumerate(self.tables['WaveformTable'].rows):
            streamed=bool(entry['Streaming']);aid=entry['StreamAwbId'] if streamed else entry['MemoryAwbId'];key=('S' if streamed else 'M')+str(aid)
            if key not in self.wave_rows:
                bank=self.stream if streamed else self.memory
                if not bank or aid not in bank.entries:raise ValueError('Faixa ausente no AWB antigo.')
                rate,channels,samples=hca_format(bank.entries[aid])
                row={'key':key,'id':aid,'streaming':streamed,'wave_indices':[],'cue_names':[],'cue_ids':[],'functions':[],
                     'pattern_names':[],'english':[],'rate':rate,'channels':channels,'samples':samples,'duration':samples/rate,
                     'available':True,'filename':f'{aid:05d}'+('_streaming' if streamed else '')+'.hca'}
                self.rows.append(row);self.wave_rows[key]=row
            self.wave_rows[key]['wave_indices'].append(i)
        expected={r['id'] for r in self.rows if r['streaming']}
        if set(self.stream.entries)!=expected:raise ValueError('As faixas do AWB antigo não correspondem ao ACB.')
        waveform=self.tables['WaveformTable'].rows
        for entry in self.tables['CueNameTable'].rows:
            cue=self.tables['CueTable'].rows[entry['CueIndex']]
            resolved=self.resolve(cue['ReferenceType'],cue['ReferenceIndex'],set())
            if not resolved and cue['Length']!=0:self.unresolved.append(entry['CueName'])
            for wi in resolved:
                w=waveform[wi];key=('S' if w['Streaming'] else 'M')+str(w['StreamAwbId'] if w['Streaming'] else w['MemoryAwbId'])
                row=self.wave_rows[key]
                row['cue_names'].append(entry['CueName']);row['cue_ids'].append(cue['CueId'])
                if entry['CueName'].startswith('PTN_'):row['functions'].append(entry['CueName'])
        for row in self.rows:
            for field in ('cue_names','cue_ids','functions'):row[field]=list(dict.fromkeys(row[field]))
        digest=hashlib.sha256(acb+awb).hexdigest()[:24]
        self.cache=core.owned(core.APP/'Cache/MigrationSources'/digest);self.cache.mkdir(parents=True,exist_ok=True)
        self.reference_name=infer_reference(self)

def infer_reference(bank):
    ids={m.group(1) for row in bank.rows for name in row['cue_names'] if (m:=re.match(r'^(\d{4}_\d{2})_',name))}
    if len(ids)==1:return 'BTLCV_'+next(iter(ids))+'_'+bank.language
    root=str(bank.root.rows[0].get('Name',''))
    if re.fullmatch(r'BTLCV_\d{4}_\d{2}(?:_(?:JP|US))?',root):return root if root.endswith(('_US','_JP')) else root+'_'+bank.language
    return None

def read_old(cfg,external,language):
    files={k:Path(external[k]).resolve() for k in ('asset','acb','awb','uexp') if external.get(k)}
    raw={key:path.read_bytes() for key,path in files.items()}
    legacy=bool(external.get('package_origin',{}).get('legacy_iostore_plaintext') and external.get('package_origin',{}).get('iostore_version')==3);embedded=None
    if 'asset' in raw:
        data=raw.get('uexp',raw['asset'])
        at=data.find(b'@UTF')
        if at>=0:embedded=data[at:at+core.UTF(data,at).size]
        asset=raw['asset'];legacy=legacy or asset[:4]==b'\xc1\x83\x2a\x9e' and len(asset)>=16 and bool(core.le(asset,12,4))
    acb=core.standalone_acb(raw['acb']) if 'acb' in raw else embedded
    if acb is None:raise ValueError('Selecione um ACB ou um asset com ACB incorporado.')
    if embedded is not None and acb!=embedded and not legacy:raise ValueError('O ACB selecionado difere do ACB atribuído ao asset.')
    digest=hashlib.sha256(acb+raw['awb']).hexdigest()[:24]
    folder=core.owned(core.APP/'Imports/Migration'/digest);folder.mkdir(parents=True,exist_ok=True)
    originals={key:str(path) for key,path in files.items()}
    for key,data in raw.items():
        dest=folder/('original_'+key+files[key].suffix)
        if dest.exists() and dest.read_bytes()!=data:raise ValueError('Cópia de importação inconsistente.')
        dest.write_bytes(data)
    (folder/'source.acb').write_bytes(acb)
    (folder/'source.awb').write_bytes(raw['awb'])
    source={'original_paths':originals,'acb':str(folder/'source.acb'),'awb':str(folder/'source.awb'),'legacy_editor':legacy}
    return OldBank(cfg,acb,raw['awb'],language,source,legacy)

def identities(bank):
    result={row['key']:set() for row in bank.rows};waveform=bank.tables['WaveformTable'].rows
    for name in bank.tables['CueNameTable'].rows:
        cue=bank.tables['CueTable'].rows[name['CueIndex']]
        for wi in bank.resolve(cue['ReferenceType'],cue['ReferenceIndex'],set()):
            w=waveform[wi];key=('S' if w['Streaming'] else 'M')+str(w['StreamAwbId'] if w['Streaming'] else w['MemoryAwbId'])
            result[key].add((int(cue['CueId']),str(name['CueName'])))
    return result

def plan_rows(old_rows,new_rows,old_ids,new_ids):
    pairs=collections.defaultdict(set);names=collections.defaultdict(set);ids=collections.defaultdict(set)
    for key,tokens in old_ids.items():
        for cue_id,name in tokens:pairs[(cue_id,name)].add(key);names[name].add(key);ids[cue_id].add(key)
    result=[];used=set()
    for row in new_rows:
        candidates=set();constraints=[];missing=False;methods=set();id_only=False
        tokens=new_ids[row['key']]
        for token in tokens:
            matches=pairs.get(token,set());method='cue_id+name'
            if not matches:matches=names.get(token[1],set());method='name'
            if matches:candidates.update(matches);constraints.append(set(matches));methods.add(method)
            else:
                missing=True
                if ids.get(token[0]):id_only=True;candidates.update(ids[token[0]])
        consistent=set.intersection(*constraints) if constraints else set()
        status='matched' if tokens and len(consistent)==1 and not missing else 'ambiguous' if candidates else 'new'
        source=next(iter(consistent)) if status=='matched' else None
        if source:used.add(source)
        result.append({'target_key':row['key'],'source_key':source,'status':status,'candidates':sorted(candidates),
                       'cue_ids':row['cue_ids'],'cue_names':row['cue_names'],'tags':row['functions'],
                       'method':'+'.join(sorted(methods)), 'reason':'id_only' if id_only else 'shared_new_or_multiple' if status=='ambiguous' else ''})
    return {'rows':result,'unmatched_old':[{'key':r['key'],'cue_ids':r['cue_ids'],'cue_names':r['cue_names'],'tags':r['functions']} for r in old_rows if r['key'] not in used]}

def analyze(old,target):
    if target.external or not target.compatible:raise ValueError('Escolha um banco original atualizado compatível com os arquivos do jogo.')
    if old.language!=target.language:raise ValueError('Os bancos antigo e atualizado devem usar o mesmo idioma de áudio.')
    if old.reference_name and old.reference_name!=target.name:raise ValueError('O banco atualizado selecionado não corresponde à origem identificada do banco antigo.')
    if old.unresolved or target.unresolved:raise ValueError('Existem cues sem mapeamento; a migração não pode ser feita com segurança.')
    result=plan_rows(old.rows,target.rows,identities(old),identities(target))
    result.update({'schema':1,'source_bank':old.name,'identified_reference':old.reference_name,'target_bank':target.name,
                   'source_acb_sha256':hashlib.sha256(old.acb).hexdigest(),'target_acb_sha256':hashlib.sha256(target.acb).hexdigest(),
                   'source':old.source,'hash_verified':old.hash_verified,'new_audio_policy':'silence_0.5_seconds',
                   'ambiguous_audio_policy':'silence_until_manually_replaced','source_audio_policy':'preserve_all_safely_matched_old_audio',
                   'summary':{status:sum(row['status']==status for row in result['rows']) for status in ('matched','new','ambiguous')}})
    return result

def create_project(old,target,report,progress=lambda text:None,project_name=None):
    project_name=project_names.validate(project_name or target.name+' — Migrated')
    folder=project_names.project_folder(project_name)
    replacements={};work=folder/'Replacements';work.mkdir(parents=True,exist_ok=False)
    matched=[r for r in report['rows'] if r['status']=='matched']
    for i,item in enumerate(matched):
        progress(f'{i+1}/{len(matched)}')
        source=old.original(old.wave_rows[item['source_key']]);row=target.wave_rows[item['target_key']]
        destination=work/(row['key']+'.wav')
        core.normalize_wav(source,destination,row['rate'],row['channels'],row['samples'])
        replacements[row['key']]=str(destination)
    core.write_json(folder/'migration_report.json',report)
    import bank_version
    project={'schema':6,'bank_reference':bank_version.snapshot(target),'bank':target.name,'source':None,'project_name':project_name,'project_id':project_names.project_parts(folder)['id'],
             'export_name':target.name,'replacements':replacements,'gains':{},'variations':{},'keep_imported':False,
             'migration':{'report':str(folder/'migration_report.json'),'source_bank':old.name,'summary':report['summary']}}
    core.write_json(folder/'project.json',project);project['project_file']=str(folder/'project.json')
    return project
