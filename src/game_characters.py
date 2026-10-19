"""Official character names from Data.locres and explicit CharacterData FText keys."""
import json,re,struct,threading
from pathlib import Path
import core,voice_text,game_installation,game_references

SCHEMA=1
_lock=threading.RLock()
_catalogs={}
_active={}
TABLES=('ST_CHR_NAME_FULL','ST_CHR_NAME','ST_CHR_EVENT_NAME')

def game_language(language):return 'pt-BR' if language=='pt' else language

def bundled(language):
    """Portable official names; never depend on another user's game/cache paths."""
    language=game_language(language)
    try:
        data=json.loads((core.APP/'Data/official_character_names.json').read_text(encoding='utf-8'))
        if data.get('schema')!=1:return {}
        names=data['languages'].get(language,{}).get('names',{})
        return {actor:value for actor,value in names.items() if re.fullmatch(r'\d{4}_\d{2}',actor) and isinstance(value,str) and value.strip()}
    except (OSError,ValueError,KeyError,TypeError,AttributeError):return {}

def ftext_keys(path):
    """Accept exact StringTable FText serialization, never an arbitrary matching string."""
    data=Path(path).read_bytes();names=core.asset_names(path)
    payload=data if data[:4]==b'\0'*4 else Path(path).with_suffix('.uexp').read_bytes()
    result={}
    for table in TABLES:
        keys=set()
        pattern=rb'ST_CHR_'+table.removeprefix('ST_CHR_').encode()+rb'_\d{4}_\d{2}\x00'
        for match in re.finditer(pattern,payload):
            pos=match.start()
            if pos<17:continue
            flags,history,index,number,length=struct.unpack_from('<IbIIi',payload,pos-17)
            expected='/Game/SS/StringTables/Data/'+table+'.'+table
            if history==11 and number==0 and 0<=index<len(names) and names[index]==expected and length==len(match.group()):
                keys.add(match.group()[:-1].decode('ascii'))
        if len(keys)==1:result[table]=keys.pop()
    return result

def bindings(cfg,identity):
    cache=core.APP/'Cache/CharacterNames'/identity/'bindings.json'
    with _lock:
        if cache.is_file():
            try:
                data=json.loads(cache.read_text(encoding='utf-8'))
                if data.get('schema')==SCHEMA:return data['entries']
            except (ValueError,KeyError,OSError):pass
        _,entries=game_references.session(cfg);result={}
        for relative in sorted(entries):
            match=re.fullmatch(r'SS/MasterDataAsset/CharacterData/CharacterData_(\d{4}_\d{2})\.uasset',relative)
            if not match:continue
            try:result[match[1]]=ftext_keys(game_references.asset(cfg,relative))
            except (ValueError,UnicodeError,struct.error):result[match[1]]={}
        core.write_json(cache,{'schema':SCHEMA,'entries':result})
        return result

def load(cfg,language):
    language=game_language(language)
    if language not in voice_text.LANGUAGES:raise ValueError('Idioma de nomes desconhecido.')
    identity=game_installation.identity(cfg)
    if not identity:raise ValueError('Instalação do jogo não configurada para ler os nomes oficiais.')
    token=(identity,language)
    cache=core.APP/'Cache/CharacterNames'/identity/(language+'.json')
    with _lock:
        if token in _catalogs:return _catalogs[token]
        if cache.is_file():
            try:
                data=json.loads(cache.read_text(encoding='utf-8'))
                if data.get('schema')==SCHEMA and data.get('identity')==identity and data.get('language')==language:
                    _catalogs[token]=data;return data
            except (ValueError,OSError):pass
    texts={};sources=[]
    for path in game_installation.pak_paths(cfg):
        pak=core.Pak(cfg,path=path)
        try:
            for entry in pak.entries:
                if entry.endswith('/SparkingZERO/Content/Localization/Data/'+language+'/Data.locres'):
                    catalog=voice_text.parse_locres(pak.file(entry),namespace=None)
                    for (namespace,key),value in catalog.items():
                        if namespace in TABLES:texts[(namespace,key)]=value
                    sources.append(str(path))
        finally:pak.f.close()
    if not sources:raise ValueError('Data.locres não encontrado para este idioma: '+language)
    mapping=bindings(cfg,identity)
    ids=set(mapping)
    for namespace,key in texts:
        match=re.fullmatch(re.escape(namespace)+r'_(\d{4}_\d{2})',key)
        if match:ids.add(match[1])
    names={};evidence={}
    for actor in sorted(ids):
        for table in TABLES:
            explicit=mapping.get(actor,{}).get(table)
            key=explicit or table+'_'+actor
            value=texts.get((table,key),'')
            if value.strip() and not value.startswith(('TR_','ST_')):
                names[actor]=value.replace('\r\n',' ').replace('\n',' ').strip()
                evidence[actor]={'namespace':table,'key':key,'character_data_ftext':bool(explicit)}
                break
    if identity!=game_installation.identity(cfg):raise ValueError('Os arquivos do jogo mudaram durante a leitura dos nomes. Tente novamente após a atualização.')
    data={'schema':SCHEMA,'identity':identity,'language':language,'names':names,'references':evidence,'sources':sources}
    core.write_json(cache,data)
    with _lock:_catalogs[token]=data
    return data

def activate(data):
    with _lock:_active[game_language(data['language'])]=data['names']

def name(actor,language):
    with _lock:return _active.get(game_language(language),{}).get(actor) or actor or '—'
