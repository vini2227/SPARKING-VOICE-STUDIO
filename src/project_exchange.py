"""Portable edited projects and conservative same-bank collaboration."""
import hashlib,json,os,uuid,wave,zipfile
from pathlib import Path,PurePosixPath
import core,audio_levels,audio_variations

FORMAT='sparking-zero-voice-project-v1'

def layout(bank):
    return {'bank':bank.name,'rows':[{'key':r['key'],'cue_ids':sorted(r['cue_ids']),
        'cue_names':sorted(r.get('cue_names',[])),'rate':r['rate'],'channels':r['channels']}
        for r in sorted(bank.rows,key=lambda r:r['key'])]}

def edits(bank,data):
    import bank_version
    data,_=bank_version.reconcile(data,bank)
    result={};source=bank.source or {}
    for row in bank.rows:
        key=row['key'];path=data.get('replacements',{}).get(key)
        if not path and bank.external and source.get('audio_similarity',{}).get(key,{}).get('status')=='different':
            path=str(bank.original(row))
        if path:
            result[key]={'path':str(path),'gain':audio_levels.valid_gain(data.get('gains',{}).get(key,0)),
                         'variation':audio_variations.valid(data.get('variations',{}).get(key,1))}
    return result

def pcm_identity(item):
    digest=hashlib.sha256()
    with wave.open(str(item['path']),'rb') as f:
        if f.getcomptype()!='NONE':raise ValueError('O projeto contém um WAV comprimido não suportado.')
        digest.update(str((f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())).encode())
        remaining=f.getnframes()*f.getnchannels()*f.getsampwidth();read=0
        while block:=f.readframes(65536):digest.update(block);read+=len(block)
        if read!=remaining:raise ValueError('WAV incompleto no projeto compartilhado.')
    return digest.hexdigest(),round(float(item['gain']),6),int(item['variation'])

def pack(bank,data,destination):
    destination=Path(destination);pending=destination.with_name(destination.name+'.'+uuid.uuid4().hex+'.tmp')
    document=json.loads(json.dumps(data));document.pop('project_file',None)
    document.pop('migration',None);document['project_id']=None;document['usage_count']=0
    files={};paths={}
    def include(value):
        path=Path(value).resolve()
        if not path.is_file():raise ValueError('Arquivo do projeto não encontrado: '+str(path))
        token=paths.get(str(path))
        if token is None:
            token='files/'+uuid.uuid4().hex+path.suffix.lower();paths[str(path)]=token
            files[token]=path
        return token
    document['replacements']={key:include(path) for key,path in data.get('replacements',{}).items()}
    document['trim_originals']={key:{field:include(path) for field,path in item.items()} for key,item in data.get('trim_originals',{}).items()}
    document['processing_originals']={key:{field:include(path) for field,path in item.items()} for key,item in data.get('processing_originals',{}).items()}
    document['effects_originals']={key:{field:include(path) for field,path in item.items()} for key,item in data.get('effects_originals',{}).items()}
    document['speed_originals']={key:{field:include(path) for field,path in item.items()} for key,item in data.get('speed_originals',{}).items()}
    document['duplicate_originals']={key:{field:include(path) for field,path in item.items()} for key,item in data.get('duplicate_originals',{}).items()}
    if document.get('source'):
        source=document['source']
        for key in ('asset','acb','awb','uexp'):
            if source.get(key):source[key]=include(source[key])
        source.pop('package_origin',None);source['original_paths']={}
    edited=edits(bank,data)
    for item in edited.values():item['path']=include(item['path'])
    manifest={'format':FORMAT,'layout':layout(bank),'project':document,'edits':edited,'files':{}}
    try:
        destination.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(pending,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
            for token,path in files.items():
                digest=hashlib.sha256()
                with path.open('rb') as source,z.open(token,'w',force_zip64=True) as target:
                    while block:=source.read(1024*1024):digest.update(block);target.write(block)
                manifest['files'][token]=digest.hexdigest()
            z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        os.replace(pending,destination)
    finally:pending.unlink(missing_ok=True)
    return destination

def unpack(path):
    folder=core.owned(core.APP/'Cache/SharedProjects'/uuid.uuid4().hex)
    with zipfile.ZipFile(path) as z:
        if z.getinfo('manifest.json').file_size>8*1024*1024:raise ValueError('Manifesto de projeto muito grande.')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('format')!=FORMAT:raise ValueError('Este arquivo não é um projeto compartilhado do Voice Studio.')
        files=manifest['files'];names=z.namelist()
        if len(names)!=len(set(names)) or set(names)!=set(files)|{'manifest.json'}:raise ValueError('Estrutura inválida no pacote de projeto.')
        def validate(token):
            parts=PurePosixPath(token).parts
            if '\\' in token or len(parts)!=2 or parts[0]!='files' or parts[1] in ('.','..') or ':' in token:
                raise ValueError('Caminho inválido no pacote de projeto.')
            return core.owned(folder/token)
        for token in files:validate(token)
        # Files are streamed and checked; archive paths are never blindly extracted.
        folder.mkdir(parents=True)
        for token,expected in files.items():
            dest=validate(token);dest.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256()
            with z.open(token) as source,dest.open('wb') as target:
                while block:=source.read(1024*1024):digest.update(block);target.write(block)
            if digest.hexdigest()!=expected:raise ValueError('Arquivo corrompido no projeto compartilhado: '+token)
    def file_path(token):
        if token not in files:raise ValueError('Arquivo não listado no manifesto do projeto.')
        return str(validate(token))
    data=manifest['project'];data['replacements']={key:file_path(value) for key,value in data.get('replacements',{}).items()}
    data['trim_originals']={key:{field:file_path(path) for field,path in item.items()} for key,item in data.get('trim_originals',{}).items()}
    data['processing_originals']={key:{field:file_path(path) for field,path in item.items()} for key,item in data.get('processing_originals',{}).items()}
    data['effects_originals']={key:{field:file_path(path) for field,path in item.items()} for key,item in data.get('effects_originals',{}).items()}
    data['speed_originals']={key:{field:file_path(path) for field,path in item.items()} for key,item in data.get('speed_originals',{}).items()}
    data['duplicate_originals']={key:{field:file_path(path) for field,path in item.items()} for key,item in data.get('duplicate_originals',{}).items()}
    for key,item in list(data['trim_originals'].items())+list(data['processing_originals'].items())+list(data.get('effects_originals',{}).items())+list(data.get('speed_originals',{}).items())+list(data.get('duplicate_originals',{}).items()):
        if set(item)!={'original','trimmed'} or item['trimmed']!=data['replacements'].get(key):raise ValueError('Referência de corte inválida no projeto compartilhado.')
        pcm_identity({'path':item['original'],'gain':0,'variation':1})
    if data.get('source'):
        for key in ('asset','acb','awb','uexp'):
            if data['source'].get(key):data['source'][key]=file_path(data['source'][key])
    for key,item in manifest['edits'].items():
        item['path']=file_path(item['path']);item['gain']=audio_levels.valid_gain(item['gain']);item['variation']=audio_variations.valid(item['variation'])
        pcm_identity(item)
    for key,value in data.get('replacements',{}).items():
        pcm_identity({'path':value,'gain':data.get('gains',{}).get(key,0),'variation':data.get('variations',{}).get(key,1)})
    if data['bank']!=manifest['layout']['bank']:raise ValueError('Banco divergente no manifesto.')
    keys={r['key'] for r in manifest['layout']['rows']}
    if not set(manifest['edits']).issubset(keys) or not set(data.get('replacements',{})).issubset(keys):raise ValueError('Voz inexistente no banco compartilhado.')
    data['project_file']=str(folder/'project.json');data['temporary_session']=True
    return manifest

def merge_plan(descriptor,projects):
    buckets={};duplicates=0
    for index,project in enumerate(projects):
        if project['layout']!=descriptor:
            raise ValueError('Os projetos precisam usar o mesmo banco e os mesmos Cue IDs/tags. Migre as referências diferentes antes de mesclar: '+project['name'])
        allowed={r['key'] for r in descriptor['rows']}
        if not set(project['edits']).issubset(allowed):raise ValueError('Voz inexistente no projeto.')
        for key,edit in project['edits'].items():
            signature=pcm_identity(edit);options=buckets.setdefault(key,[])
            if any(item['signature']==signature for item in options):duplicates+=1;continue
            options.append({**edit,'signature':signature,'origin':index,'name':project['name']})
    return {'automatic':{key:items[0] for key,items in buckets.items() if len(items)==1},
            'conflicts':{key:items for key,items in buckets.items() if len(items)>1},'duplicates':duplicates}

def export_summary(bank,data):
    counts={'custom':0,'imported':0,'original':0,'silence':0,'uncertain':0}
    for row in bank.rows:
        key=row['key']
        if key in data.get('replacements',{}):counts['custom']+=1
        elif core.preserve_unreplaced(bank,row,data.get('keep_imported',False)):
            state=(bank.source or {}).get('audio_similarity',{}).get(key,{}).get('status','uncertain') if bank.external else None
            counts['uncertain' if state=='uncertain' else 'imported' if bank.external and state=='different' else 'original']+=1
        else:counts['silence']+=1
    return counts
