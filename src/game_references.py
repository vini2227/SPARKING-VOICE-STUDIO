"""Read installed official references into a cache tied to the container inventory."""
import threading,re,json
from collections import OrderedDict
from pathlib import Path
import core,native,game_installation

_lock=threading.RLock()
_sessions=OrderedDict()
_paks={}
PREFIX='../../../SparkingZERO/Content/'

def session(cfg):
    identity=game_installation.identity(cfg)
    if not identity:raise ValueError('Selecione a instalação do jogo com os arquivos .pak, .utoc e .ucas.')
    with _lock:
        if identity not in _sessions:
            paths=game_installation.toc_paths(cfg)
            if not paths:raise ValueError('Selecione a instalação do jogo com os arquivos .pak, .utoc e .ucas.')
            paks=[core.Pak(cfg,path=p) for p in game_installation.pak_paths(cfg)]
            if not paks:raise ValueError('Pacotes oficiais do jogo não encontrados.')
            codec=paks[0];entries={}
            for path in paths:
                store=native.IoStore(path,codec)
                for name,index in store.files.items():
                    if name.startswith(PREFIX):entries[name[len(PREFIX):]]=(store,index)
            # Don't publish an inventory taken while an update is replacing files.
            if identity!=game_installation.identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a leitura. Aguarde a atualização terminar e tente novamente.')
            _sessions[identity]=(core.owned(core.APP/'Cache/GameReferences'/identity),entries)
            _paks[identity]=paks
            while len(_sessions)>3:
                old,_=_sessions.popitem(last=False);_paks.pop(old,None)
        _sessions.move_to_end(identity)
        return _sessions[identity]

def reference_root(cfg):
    identity=game_installation.identity(cfg)
    if identity:return core.owned(core.APP/'Cache/GameReferences'/identity)
    if str(cfg.get('project') or '').strip():return Path(cfg['project'])
    return session(cfg)[0]

def banks(cfg):
    identity=game_installation.identity(cfg)
    cache=core.owned(core.APP/'Cache/GameReferences'/str(identity)/'banks.json')
    try:
        data=json.loads(cache.read_text(encoding='utf-8'))
        names=data['banks']
        if data.get('schema')==1 and data.get('identity')==identity and isinstance(names,list) and len(names)<=5000 and all(isinstance(name,str) and re.fullmatch(r'BTLCV_\d{4}_\d{2}(?:_[A-Z])?_(US|JP)',name) for name in names):
            if identity==game_installation.identity(cfg):return sorted(set(names))
    except (OSError,ValueError,KeyError,TypeError):pass
    root,entries=session(cfg)
    names=sorted({Path(path).stem for path in entries if re.fullmatch(r'SS/Sounds/Battle_VOICE/(US|JP)/BTLCV_\d{4}_\d{2}(?:_[A-Z])?_(US|JP)\.uasset',path)})
    if root.name!=game_installation.identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a leitura. Aguarde a atualização terminar e tente novamente.')
    core.write_json(root/'banks.json',{'schema':1,'identity':root.name,'banks':names})
    return names

def _cached_asset(root,entries,relative):
    destination=core.owned(root/'Content'/relative)
    with _lock:
        if relative not in entries:raise ValueError('Referência não encontrada no jogo: '+relative)
        if not destination.is_file():
            store,index=entries[relative];data=store.read_chunk(index)
            if len(data)<44 or data[:4]!=b'\0'*4:raise ValueError('Referência Zen do jogo inválida.')
            destination.parent.mkdir(parents=True,exist_ok=True)
            temporary=destination.with_suffix('.tmp');temporary.write_bytes(data);temporary.replace(destination)
    return destination

def asset(cfg,relative):
    if not game_installation.identity(cfg) and str(cfg.get('project') or '').strip():return Path(cfg['project'])/'Content'/relative
    root,entries=session(cfg)
    return _cached_asset(root,entries,relative)

def assets(cfg,relatives):
    """One version-checked batch instead of repeating inventory for every bank."""
    identity=game_installation.identity(cfg)
    if not identity and str(cfg.get('project') or '').strip():
        return {relative:Path(cfg['project'])/'Content'/relative for relative in relatives}
    root,entries=session(cfg)
    if root.name!=identity:raise ValueError('Os arquivos do jogo mudaram durante a leitura. Aguarde a atualização terminar e tente novamente.')
    result={relative:_cached_asset(root,entries,relative) for relative in relatives}
    if identity!=game_installation.identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a leitura. Aguarde a atualização terminar e tente novamente.')
    return result

def bank_audio(cfg,name):
    with _lock:
        root,_=session(cfg)
        target=PREFIX+'CriWareData/'+name+'.awb'
        for pak in reversed(_paks[root.name]):
            if target in pak.entries:return pak.file(target)
    raise ValueError('AWB não encontrado nos pacotes oficiais: '+name)

def pattern(cfg):
    path=asset(cfg,'SS/Blueprints/PatternVoiceData.uasset')
    if path.with_suffix('.uexp').is_file():return path,path.with_suffix('.uexp').read_bytes()
    data=path.read_bytes();header=core.le(data,4,4);exportmap=core.le(data,32,4)
    if core.le(data,36,4)-exportmap!=72:raise ValueError('Tabela de funções Zen não suportada.')
    size=core.le(data,exportmap+8,8)
    if header+size!=len(data):raise ValueError('Tamanho da tabela de funções Zen inválido.')
    return path,data[header:]
