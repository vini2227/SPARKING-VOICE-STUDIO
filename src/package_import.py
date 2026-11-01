"""Read selected mod containers into app-owned snapshots; never borrow game voice metadata."""
import base64,hashlib,json,re,uuid
from pathlib import Path,PurePosixPath
import core,native

def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

VOICE=re.compile(r'^BTLCV_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*_(US|JP)\.(uasset|uexp|acb|awb)$',re.I)

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
    for bank in banks:
        origin=bank['package_origin']
        origin['catalog_path']=str(folder/'package_import.json')
        origin['bank_info']=inspect_pair(bank,cfg)
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


def custom_asset_name(name,origin):
    """Custom identifiers are allowed only with an exact mod asset mount."""
    if not VOICE.fullmatch(name+'.uasset') or len(name)>120:return False
    relative=str((origin or {}).get('voice_asset_path') or '')
    try:safe_entry(relative)
    except ValueError:return False
    return relative.startswith('SparkingZERO/Mods/') and PurePosixPath(relative).name==name+'.uasset'

def validate_custom_origin(cfg,asset,awb,origin):
    if not custom_asset_name(asset.stem,origin):raise ValueError('O pacote original do personagem customizado é necessário para exportar a voz.')
    toc=(origin.get('container_snapshot') or {}).get('.utoc')
    if not toc:raise ValueError('O pacote original do personagem customizado é necessário para exportar a voz.')
    toc=core.owned(toc)
    if not toc.is_file() or not toc.with_suffix('.ucas').is_file():raise ValueError('O .utoc e o .ucas precisam estar juntos, com o mesmo nome base.')
    pak=core.Pak(cfg)
    try:
        store=native.IoStore(toc,pak);path='../../../'+origin['voice_asset_path']
        if path not in store.files:raise ValueError('O pacote original do personagem customizado é necessário para exportar a voz.')
        index=store.files[path]
        if store.read_chunk(index)!=asset.read_bytes():raise ValueError('O asset selecionado difere do pacote original do personagem.')
        chunk=store.b[store.ids_pos+index*12:store.ids_pos+(index+1)*12].hex()
        if chunk!=origin.get('voice_chunk_id'):raise ValueError('O asset selecionado difere do pacote original do personagem.')
        expected=origin.get('bank_info',{}).get('awb_sha256')
        if not expected or file_hash(awb)!=expected:raise ValueError('O AWB selecionado difere do AWB do pacote original desse personagem customizado.')
    finally:pak.f.close()

def inspect_pair(bank,cfg):
    """Read actual mod metadata, never substitute a current game's ACB."""
    name=bank['bank_name'];origin=bank['package_origin'];relative=origin.get('voice_asset_path') or ''
    parent=PurePosixPath(relative).parent
    custom=relative.startswith('SparkingZERO/Mods/')
    actor=core.character_id(name)
    import game_characters
    label=parent.name if custom else game_characters.bundled(cfg.get('ui_language','en')).get(actor) or actor or name
    if custom:
        label=re.sub(r'^\d+_','',label).replace('_',' ')
        label=re.sub(r'(?<=[a-z])(?=[A-Z])',' ',label)
    result={'label':label,'group_key':str(parent) if custom else actor or name,'language':name[-2:].upper(),'voice_count':None,'custom_mount':custom,'awb_sha256':file_hash(bank['awb'])}
    if not bank.get('asset') and not bank.get('acb'):return result
    try:
        data=Path(bank.get('uexp') or bank.get('acb') or bank['asset']).read_bytes()
        at=data.index(b'@UTF');root=core.UTF(data,at);acb=data[at:at+root.size];root=core.UTF(acb)
        waveform=root.child('WaveformTable')
        if waveform is None:raise ValueError('Banco antigo sem tabela de cues ou de áudio.')
        stream=core.Awb(Path(bank['awb']).read_bytes());blob=root.rows[0].get('AwbFile');memory=core.Awb(acb[blob[0]:blob[0]+blob[1]]) if blob and blob[1] else None
        expected={r['StreamAwbId'] for r in waveform.rows if r['Streaming']}
        if set(stream.ids)!=expected or len(stream.ids)!=len(expected):raise ValueError('Os IDs do AWB não correspondem às faixas do ACB antigo.')
        import bank_migration
        identities=set()
        for row in waveform.rows:
            streamed=bool(row['Streaming']);aid=row['StreamAwbId'] if streamed else row['MemoryAwbId'];archive=stream if streamed else memory
            if archive is None or aid not in archive.entries:raise ValueError('Faixa ausente no AWB antigo.')
            bank_migration.hca_format(archive.entries[aid]);identities.add((streamed,aid))
        result['voice_count']=len(identities);table=root.child('StreamAwbHash')
        if table:
            pos,size=table.rows[0]['Hash'];result['stale_hash']=acb[pos:pos+size]!=hashlib.md5(stream.b).digest()
        result['structure_verified']=True
    except (OSError,ValueError,KeyError,IndexError,TypeError,AttributeError) as error:result['error']=str(error)
    return result

def catalog(owner):
    bank=getattr(owner,'bank',None)
    origin=((bank.source or {}).get('package_origin') or {}) if bank and bank.external else {}
    path=origin.get('catalog_path')
    if path:
        try:
            data=json.loads(core.owned(path).read_text(encoding='utf-8'))
            if isinstance(data.get('banks'),list):return data['banks']
        except (OSError,ValueError,TypeError):pass
    return getattr(owner,'_package_banks',[])
