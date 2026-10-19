"""Read selected mod containers into app-owned snapshots; never borrow game voice metadata."""
import base64,hashlib,json,re,uuid
from pathlib import Path,PurePosixPath
import core,native

def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

VOICE=re.compile(r'^BTLCV_\d{4}_\d{2}_(US|JP)\.(uasset|uexp|acb|awb)$',re.I)

def safe_entry(name):
    path=PurePosixPath(name.replace('\\','/'))
    if path.is_absolute() or any(part in ('..','') or ':' in part for part in path.parts):
        raise ValueError('Caminho inválido dentro do pacote.')

def extract(cfg,selected):
    selected=Path(selected).resolve()
    if selected.suffix.lower() not in ('.pak','.utoc','.ucas'):raise ValueError('Selecione um pacote .pak, .utoc ou .ucas.')
    files={ext:selected.with_suffix(ext) for ext in ('.pak','.utoc','.ucas') if selected.with_suffix(ext).is_file()}
    if selected.suffix.lower() in ('.utoc','.ucas') and not all(ext in files for ext in ('.utoc','.ucas')):
        raise ValueError('O .utoc e o .ucas precisam estar juntos, com o mesmo nome base.')
    if '.utoc' in files and '.ucas' not in files:raise ValueError('O pacote está incompleto: falta o .ucas correspondente.')
    folder=core.owned(core.APP/'Imports/Packages'/uuid.uuid4().hex);folder.mkdir(parents=True)
    originals={ext:str(path) for ext,path in files.items()}
    digests={ext:file_hash(path) for ext,path in files.items()}
    copied={}
    for ext,path in files.items():
        dest=folder/('container'+ext)
        with path.open('rb') as source,dest.open('wb') as target:
            import shutil
            shutil.copyfileobj(source,target)
        if file_hash(dest)!=digests[ext]:raise ValueError('O pacote foi alterado durante a cópia. Tente novamente.')
        copied[ext]=dest
    pak=core.Pak(cfg);collected={};asset_paths={};asset_chunk_ids={};legacy_plain=False;iostore_version=None
    def add(path,data):
        name=PurePosixPath(path.replace('\\','/')).name
        if not VOICE.fullmatch(name):return
        key=name.lower()
        if name.lower().endswith('.uasset') and path.startswith('../../../'):
            relative=path[9:];safe_entry(relative)
            if not relative.startswith('SparkingZERO/'):raise ValueError('Caminho de voz fora do projeto SparkingZERO.')
            if key in asset_paths and asset_paths[key]!=relative:raise ValueError('O mesmo banco aparece em caminhos diferentes.')
            asset_paths[key]=relative
        if key in collected and collected[key].read_bytes()!=data:raise ValueError('Há versões diferentes do mesmo arquivo de voz no pacote: '+name)
        dest=folder/'Voices'/name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(data);collected[key]=dest
    try:
        if '.pak' in copied:
            crypto=folder/'crypto.json'
            core.write_json(crypto,{'EncryptionKey':{'Name':'Default','Guid':'00000000000000000000000000000000','Key':base64.b64encode(pak.key).decode()},'SecondaryEncryptionKeys':[],'SigningKey':None,'bEnablePakSigning':False,'bEnablePakIndexEncryption':False,'bEnablePakIniEncryption':False,'bEnablePakUAssetEncryption':False,'bEnablePakFullAssetEncryption':False})
            args=[core.APP/'Tools/UnrealPak/UnrealPak.exe',copied['.pak']]
            try:
                listed=core.run(args+['-List','-cryptokeys='+str(crypto),'-NoLog','-Unattended','-stdout'],folder).stdout.decode('utf-8','replace')
                names=re.findall(r'"([^"\r\n]+)" offset:',listed)
                if not names:raise ValueError('Não foi possível ler o índice do .pak ou o pacote está vazio.')
                for name in names:safe_entry(name)
                work=folder/'PakFiles';work.mkdir()
                core.run(args+['-Extract',work,'-cryptokeys='+str(crypto),'-NoLog','-Unattended','-stdout'],folder)
                for path in work.rglob('*'):
                    if path.is_file() and VOICE.fullmatch(path.name):add(path.name,path.read_bytes())
            finally:crypto.unlink(missing_ok=True)
        if '.utoc' in copied:
            store=native.IoStore(copied['.utoc'],pak)
            legacy_plain=store.directory_plaintext;iostore_version=store.b[16]
            for path,index in store.files.items():
                if VOICE.fullmatch(PurePosixPath(path.replace('\\','/')).name):
                    add(path,store.read_chunk(index))
                    asset_chunk_ids[PurePosixPath(path).name.lower()]=store.b[store.ids_pos+index*12:store.ids_pos+(index+1)*12].hex()
        # The user may start with the audio-only .pak rather than the character .utoc.
        # Resolve only the exact named voice bank in sibling complete IoStore pairs.
        missing_assets={p.stem.lower() for p in collected.values() if p.suffix.lower()=='.awb' and (p.stem+'.uasset').lower() not in collected and (p.stem+'.acb').lower() not in collected}
        if missing_assets and '.utoc' not in copied:
            for candidate in sorted(selected.parent.glob('*.utoc')):
                companion=candidate.with_suffix('.ucas')
                if not companion.is_file():continue
                sibling=native.IoStore(candidate,pak)
                matching=[(path,index) for path,index in sibling.files.items()
                    if PurePosixPath(path).suffix.lower()=='.uasset' and PurePosixPath(path).stem.lower() in missing_assets]
                if not matching:continue
                if '.utoc' in copied:raise ValueError('Mais de um pacote contém o banco de voz solicitado. Selecione o .utoc correspondente.')
                for ext in ('.utoc','.ucas'):
                    original=candidate.with_suffix(ext);stamp=file_hash(original);dest=folder/('container'+ext)
                    import shutil
                    shutil.copyfile(original,dest)
                    if file_hash(dest)!=stamp or file_hash(original)!=stamp:raise ValueError('O pacote complementar mudou durante a leitura.')
                    copied[ext]=dest;originals[ext]=str(original);digests[ext]=stamp
                companion_pak=candidate.with_suffix('.pak')
                if companion_pak.is_file() and companion_pak!=selected:
                    stamp=file_hash(companion_pak);dest=folder/'character_container.pak';shutil.copyfile(companion_pak,dest)
                    if file_hash(dest)!=stamp:raise ValueError('O pacote complementar mudou durante a leitura.')
                    originals['character_pak']=str(companion_pak);digests['character_pak']=stamp
                sibling=native.IoStore(copied['.utoc'],pak)
                legacy_plain=sibling.directory_plaintext;iostore_version=sibling.b[16]
                for path,index in matching:
                    add(path,sibling.read_chunk(index))
                    asset_chunk_ids[PurePosixPath(path).name.lower()]=sibling.b[sibling.ids_pos+index*12:sibling.ids_pos+(index+1)*12].hex()
        # Custom character mods commonly keep AWBs in a separate sibling .pak.
        missing={p.stem.lower() for p in collected.values() if p.suffix.lower()=='.uasset' and (p.stem+'.awb').lower() not in collected}
        if missing:
            crypto=folder/'companion_crypto.json'
            core.write_json(crypto,{'EncryptionKey':{'Name':'Default','Guid':'00000000000000000000000000000000','Key':base64.b64encode(pak.key).decode()},'SecondaryEncryptionKeys':[],'SigningKey':None})
            try:
                for sibling in sorted(selected.parent.glob('*.pak')):
                    if sibling.resolve() in [p.resolve() for p in files.values()]:continue
                    args=[core.APP/'Tools/UnrealPak/UnrealPak.exe',sibling]
                    listed=core.run(args+['-List','-cryptokeys='+str(crypto),'-NoLog','-Unattended','-stdout'],folder).stdout.decode('utf-8','replace')
                    names=re.findall(r'"([^"\r\n]+)" offset:',listed)
                    wanted=[n for n in names if PurePosixPath(n).suffix.lower()=='.awb' and PurePosixPath(n).stem.lower() in missing]
                    if not wanted:continue
                    for n in names:safe_entry(n)
                    stamp=file_hash(sibling);work=folder/('Companion_'+stamp[:16]);work.mkdir(exist_ok=True)
                    core.run(args+['-Extract',work,'-cryptokeys='+str(crypto),'-NoLog','-Unattended','-stdout'],folder)
                    if file_hash(sibling)!=stamp:raise ValueError('O pacote complementar mudou durante a leitura.')
                    originals['companion:'+sibling.name]=str(sibling);digests['companion:'+sibling.name]=stamp
                    for path in work.rglob('*.awb'):
                        if path.stem.lower() in missing:add(path.name,path.read_bytes())
            finally:crypto.unlink(missing_ok=True)
    finally:pak.f.close()
    banks=[]
    for name in sorted({p.stem for p in collected.values()}):
        paths={p.suffix.lower():p for p in collected.values() if p.stem==name}
        if '.awb' not in paths:continue
        banks.append({'bank_name':name,'asset':str(paths['.uasset']) if '.uasset' in paths else None,
                      'acb':str(paths['.acb']) if '.acb' in paths else None,'uexp':str(paths['.uexp']) if '.uexp' in paths else None,'awb':str(paths['.awb']),
                      'package_origin':{'original_paths':originals,'sha256':digests,'legacy_iostore_plaintext':legacy_plain,'iostore_version':iostore_version,'voice_asset_path':asset_paths.get((name+'.uasset').lower()),'voice_chunk_id':asset_chunk_ids.get((name+'.uasset').lower()),'container_snapshot':{ext:str(p) for ext,p in copied.items()}}})
    core.write_json(folder/'package_import.json',{'original_paths':originals,'sha256':digests,'banks':banks})
    if not banks:raise ValueError('O pacote não contém bancos BTLCV com AWB. Selecione o conjunto de arquivos do mod de voz.')
    return banks


def loose_pair_origin(cfg,asset,awb):
    """Recover a loose bank's package provenance only by exact asset and AWB bytes."""
    asset=Path(asset);awb=Path(awb);name=asset.name
    candidates=[];pak=None
    try:
        for candidate in sorted(asset.parent.glob('*.utoc')):
            if not candidate.with_suffix('.ucas').is_file():continue
            if pak is None:pak=core.Pak(cfg)
            store=native.IoStore(candidate,pak)
            for path,index in store.files.items():
                if PurePosixPath(path).name==name and path.startswith('../../../SparkingZERO/Mods/'):
                    if store.read_chunk(index)==asset.read_bytes():candidates.append(candidate)
    finally:
        if pak is not None:pak.f.close()
    if not candidates:return None
    if len(set(candidates))!=1:raise ValueError('Mais de um pacote corresponde ao UASSET. Importe o .utoc desejado diretamente.')
    banks=extract(cfg,candidates[0])
    matching=[bank for bank in banks if bank['bank_name']==asset.stem and Path(bank['awb']).read_bytes()==awb.read_bytes()]
    if len(matching)!=1:raise ValueError('O AWB selecionado difere do AWB do pacote original desse personagem customizado.')
    return matching[0]['package_origin']
