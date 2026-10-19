"""User project names and safe relocation inside the app's Projects folder."""
import json,os,re,threading
from datetime import datetime,timedelta,timezone
from pathlib import Path
import core

def validate(name):
    name=str(name).strip()
    if not name or len(name)>80 or name.endswith(('.', ' ')) or re.search(r'[<>:"/\\|?*\x00-\x1f]',name):
        raise ValueError('Use um nome de 1 a 80 caracteres, sem caracteres inválidos para pastas.')
    if name.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        raise ValueError('Este nome é reservado pelo Windows. Escolha outro.')
    return name

LOCAL_ZONE=timezone(timedelta(hours=-3))

def readable_stamp(language='pt',moment=None):
    moment=moment or datetime.now(LOCAL_ZONE)
    if moment.tzinfo is None:moment=moment.replace(tzinfo=LOCAL_ZONE)
    moment=moment.astimezone(LOCAL_ZONE)
    pattern='%m-%d-%Y' if language=='en' else '%Y-%m-%d' if language in ('ja','zh-Hans','zh-Hant','ko') else '%d.%m.%Y' if language in ('de','ru') else '%d-%m-%Y'
    return moment.strftime(pattern+'_%Hh%Mm%Ss')

def folder_language(language=None):
    return language or core.config().get('ui_language') or 'pt'

def saved_moment(data,project):
    try:return datetime.fromisoformat(data['saved_at'])
    except (KeyError,TypeError,ValueError):return datetime.fromtimestamp((Path(project)/'project.json').stat().st_mtime,LOCAL_ZONE)

def readable_target(project,name,language=None):
    project=Path(project);parts=project_parts(project)
    if not parts:return None
    data=json.loads((project/'project.json').read_text(encoding='utf-8'))
    return project.parent/(parts['number']+'_'+validate(name)+'__'+readable_stamp(folder_language(language),saved_moment(data,project)))

def export_project_name(folder):
    value=Path(folder).name
    match=re.fullmatch(r'\d{6,}_(.+)__[0-9.-]+_\d{2}h\d{2}m\d{2}s',value)
    if match:return match.group(1)
    match=re.fullmatch(r'\d{6,}_(.+)_\d{8}_\d{6}_[a-f0-9]{8}',value)
    return match.group(1) if match else value


def relocate(project,name,language=None):
    name=validate(name);old=core.owned(project);root=core.owned(core.APP/'Projects')
    if old==root or not old.is_relative_to(root) or not (old/'project.json').is_file():
        raise ValueError('O projeto deve estar dentro da pasta Projects do app para ser renomeado.')
    data=json.loads((old/'project.json').read_text(encoding='utf-8'))
    identity=data.get('project_id') or os.urandom(5).hex()
    if not re.fullmatch('[a-f0-9]{10}',identity):identity=os.urandom(5).hex()
    parts=project_parts(old)
    if parts:
        identity=parts['id']
        target=core.owned(readable_target(old,name,language))
    else:
        # An identity already in use must never merge two independent projects.
        if root.is_dir() and any(child!=old and child.is_dir() and project_identity(child)==identity for child in root.iterdir()):
            raise FileExistsError('Já existe um projeto com esta identificação.')
        target=project_folder(name,identity,language=language)
    if target.parent!=root:raise ValueError('Pasta de projeto inválida.')
    if target!=old and target.exists():raise FileExistsError('Já existe um projeto nesta pasta. Escolha outro nome.')
    def update(value):
        if isinstance(value,dict):return {key:update(item) for key,item in value.items()}
        if isinstance(value,list):return [update(item) for item in value]
        if isinstance(value,str) and Path(value).is_absolute():
            path=Path(value).resolve()
            if path.is_relative_to(old):return str(target/path.relative_to(old))
        return value
    data=update(data);data['project_name']=name;data['project_id']=identity;data['schema']=5
    data.setdefault('saved_at',saved_moment(data,old).isoformat())
    moved=target!=old
    if moved:old.rename(target)
    try:core.write_json(target/'project.json',data)
    except Exception:
        if moved:target.rename(old)
        raise
    return target,data

_project_sequence_lock=threading.Lock()

def project_identity(folder):
    try:return json.loads((Path(folder)/'project.json').read_text(encoding='utf-8')).get('project_id')
    except (OSError,ValueError,TypeError,AttributeError):return None

def project_parts(folder):
    folder=Path(folder)
    match=re.fullmatch(r'(?P<number>\d{6,})_.+_(?P<stamp>\d{8}_\d{6})_(?P<id>[a-f0-9]{10})',folder.name)
    if match:return match.groupdict()
    match=re.fullmatch(r'(?P<number>\d{6,})_.+__(?P<stamp>[0-9.-]+_\d{2}h\d{2}m\d{2}s)',folder.name)
    if not match:return None
    parts=match.groupdict();parts['id']=project_identity(folder) or f"{int(parts['number']):010x}"
    return parts

def project_folder(name,identity=None,language=None):
    """Reserve a persistent sequence number for a newly created project."""
    name=validate(name);root=core.owned(core.APP/'Projects')
    identity=identity or os.urandom(5).hex()
    if not re.fullmatch('[a-f0-9]{10}',identity):raise ValueError('Identificação de projeto inválida.')
    stamp=readable_stamp(folder_language(language))
    with _project_sequence_lock:
        counter=core.owned(core.APP/'project_sequence.json');last=0
        if counter.exists():
            try:
                last=int(json.loads(counter.read_text(encoding='utf-8'))['last_number'])
                if last<0:raise ValueError()
            except (ValueError,KeyError,TypeError):
                raise ValueError('O contador de projetos está inválido. Verifique project_sequence.json.')
        if root.is_dir():
            for child in root.iterdir():
                parts=project_parts(child)
                if child.is_dir() and parts:last=max(last,int(parts['number']))
        number=last+1
        folder=core.owned(root/(f'{number:06d}_'+name+'__'+stamp))
        core.write_json(counter,{'last_number':number})
        return folder

_export_sequence_lock=threading.Lock()

def project_export_root(base,name,project=None):
    """Use the saved project number, without reserving a project or export."""
    base=Path(base).resolve()
    parts=project_parts(project) if project else None
    if not parts:return base
    folder=base/(parts['number']+'_'+validate(name))
    if folder.is_symlink() or folder.resolve().parent!=base:
        raise ValueError('O destino deve ser uma pasta.')
    if folder.exists() and not folder.is_dir():raise ValueError('O destino deve ser uma pasta.')
    return folder

def export_folder(base,name,project=None,language=None):
    """Keep numbered export versions inside the saved project's own folder."""
    base=project_export_root(base,name,project);name=validate(name)
    stamp=readable_stamp(folder_language(language))
    with _export_sequence_lock:
        counter=core.APP/'export_sequence.json'
        last=0
        if counter.exists():
            try:
                last=int(json.loads(counter.read_text(encoding='utf-8'))['last_number'])
                if last<0:raise ValueError()
            except (ValueError,KeyError,TypeError):
                raise ValueError('O contador de exportações está inválido. Verifique export_sequence.json.')
        if base.is_dir():
            for child in base.iterdir():
                match=re.match(r'^(\d{6,})_',child.name)
                if child.is_dir() and match:last=max(last,int(match.group(1)))
        number=last+1
        folder=base/(f'{number:06d}_'+name+'__'+stamp)
        counter.parent.mkdir(parents=True,exist_ok=True)
        pending=counter.with_name(counter.name+'.'+os.urandom(4).hex()+'.tmp')
        try:
            pending.write_text(json.dumps({'last_number':number})+'\n',encoding='utf-8')
            os.replace(pending,counter)
        finally:
            if pending.exists():pending.unlink()
        return folder
