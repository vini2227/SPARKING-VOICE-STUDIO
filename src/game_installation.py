"""Inventory official top-level containers, excluding installed mods."""
import hashlib,json,re,threading
from contextlib import contextmanager
from pathlib import Path

def container_order(path):
    name=Path(path).stem
    # Unreal patch containers take priority over their base containers.
    patch=bool(re.search(r'(?:^|_)P$',name,re.I))
    numbers=tuple(int(n) for n in re.findall(r'\d+',name))
    return patch,numbers,name.casefold()

def containers(cfg):
    if not str(cfg.get('game') or '').strip():return []
    folder=Path(cfg['game'])/'SparkingZERO/Content/Paks'
    return sorted((p for p in folder.iterdir() if p.is_file()
        and p.name.startswith('pakchunk') and '-Windows' in p.name
        and (p.suffix.lower() in ('.pak','.utoc','.ucas') or re.search(r'\.ucas\.\d+$',p.name))),
        key=lambda p:(container_order(p),p.name)) if folder.is_dir() else []

def signature(cfg):
    files=containers(cfg)
    records=[]
    for path in files:
        info=path.stat()
        records.append([str(path.resolve()),info.st_size,info.st_mtime_ns,info.st_ctime_ns])
    return records

_operation=threading.local()

def _inventory_identity(cfg):
    records=signature(cfg)
    if not records:return None
    return hashlib.sha256(json.dumps(records,separators=(',',':')).encode()).hexdigest()[:24]

def _operation_state(cfg):
    state=getattr(_operation,'state',None)
    return state if state and state['game']==str(cfg.get('game') or '').strip() else None

def identity(cfg):
    state=_operation_state(cfg)
    return state['identity'] if state is not None else _inventory_identity(cfg)

def operation_value(cfg,key,factory):
    state=_operation_state(cfg)
    if state is None:return factory()
    if key not in state['values']:state['values'][key]=factory()
    return state['values'][key]

@contextmanager
def checked_inventory(cfg):
    """Temporary, thread-local snapshot with fresh checks at both boundaries."""
    if _operation_state(cfg) is not None:
        yield
        return
    previous=getattr(_operation,'state',None)
    identity_before=_inventory_identity(cfg)
    _operation.state={'game':str(cfg.get('game') or '').strip(),'identity':identity_before,'values':{}}
    try:
        yield
        if identity_before!=_inventory_identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a leitura. Aguarde a atualização terminar e tente novamente.')
    finally:
        _operation.state=previous

def pak_paths(cfg):return [p for p in containers(cfg) if p.suffix.lower()=='.pak' and p.stat().st_size>=500]

def toc_paths(cfg):return [p for p in containers(cfg) if p.suffix.lower()=='.utoc']

_reference_versions={}
def reference_revision(cfg):
    token=identity(cfg)
    if token not in _reference_versions:
        result={}
        for path in toc_paths(cfg):
            result[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        if token!=identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a verificação das referências.')
        _reference_versions[token]=result
    return _reference_versions[token]

def semantic_references_current(cfg):
    import core
    path=core.APP/'Data/game_reference_version.json'
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
        expected=data.get('utoc_sha256')
        return bool(expected) and data.get('schema')==1 and expected==reference_revision(cfg)
    except (OSError,ValueError):return False
