"""Create editor CueSheets with UE's native CRI importer in isolated projects."""
import hashlib, json, os, re, shutil, subprocess, threading, uuid, ntpath
from pathlib import Path

_lock = threading.Lock()
ENGINE = Path(r'C:\Program Files\Epic Games\UE_5.1\SBSZEngine\DBSZEngine\Engine\Binaries\Win64\UnrealEditor-Cmd.exe')

def engine_from_folder(folder):
    root=Path(folder).expanduser()
    if not root.is_dir():raise ValueError('Pasta da Custom Engine não encontrada.')
    for relative in ('Engine/Binaries/Win64/UnrealEditor-Cmd.exe','DBSZEngine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe','SBSZEngine/DBSZEngine/Engine/Binaries/Win64/UnrealEditor-Cmd.exe','Binaries/Win64/UnrealEditor-Cmd.exe'):
        candidate=root/relative
        if candidate.is_file():return candidate.resolve()
    raise ValueError('O editor não foi encontrado nesta pasta. Selecione a pasta da Custom Engine do Sparking Zero que contém Engine, ou a pasta SBSZEngine/DBSZEngine.')

def configured_folder(cfg):
    if cfg.get('custom_engine'):return str(cfg['custom_engine'])
    if cfg.get('unreal_editor'):
        executable=Path(cfg['unreal_editor'])
        if len(executable.parents)>3:return str(executable.parents[3])
    return ''

def clear_import_sources(raw, source_path, relative_roots=()):
    """Clear native import JSON/registry records without changing UE offsets."""
    def same_source(filename):
        if not isinstance(filename,str) or not filename:return False
        expected=ntpath.normcase(ntpath.normpath(str(source_path)))
        if ntpath.isabs(filename):return ntpath.normcase(ntpath.normpath(filename))==expected
        # A drive-relative path such as C:foo is ambiguous and is not accepted.
        if ntpath.splitdrive(filename)[0]:return False
        return any(ntpath.normcase(ntpath.normpath(ntpath.join(str(base),filename)))==expected for base in relative_roots)
    result = bytearray(raw)
    found = 0
    for match in re.finditer(rb'\[\s*\{\s*"RelativeFilename"', raw):
        start = match.start()
        length = int.from_bytes(raw[start-4:start], 'little', signed=True)
        if not 0 < length <= len(raw)-start or raw[start+length-1] != 0:
            continue
        try:
            records = json.loads(raw[start:start+length-1].decode('utf-8'))
        except (UnicodeError, ValueError):
            continue
        if not isinstance(records, list) or not records or any(not isinstance(x,dict) or not same_source(x.get('RelativeFilename')) for x in records):
            raise ValueError('Registro de origem diferente do ACB importado.')
        result[start:start+length-1] = b'[]'+b' '*(length-3)
        found += 1
    if not found:
        raise ValueError('Registro de importação não encontrado para limpeza segura.')
    return bytes(result)

def build(app, cfg, acb, destination, mount='VoiceMod', awb=None):
    app, acb, destination = Path(app), Path(acb), Path(destination)
    engine=engine_from_folder(cfg['custom_engine']) if cfg.get('custom_engine') else Path(cfg.get('unreal_editor') or ENGINE)
    plugin = Path(cfg['project'])/'Plugins/Runtime/CriWare/CriWare'
    if not engine.is_file() or not (plugin/'CriWare.uplugin').is_file():
        raise ValueError('A exportação para Unreal exige a Unreal 5.1 e o plugin CriWare do projeto configurado.')
    mount = re.sub(r'[^A-Za-z0-9_]', '_', mount) or 'VoiceMod'
    with _lock:
        root = app/'Cache/NativeAssets'/uuid.uuid4().hex
        inputs = root/'Input'
        inputs.mkdir(parents=True)
        source_acb = acb
        shutil.copy2(source_acb, inputs/source_acb.name)
        shutil.copy2(Path(awb) if awb is not None else source_acb.with_suffix('.awb'), inputs/(source_acb.stem+'.awb'))
        acb = inputs/source_acb.name
        cri = root/'Plugins/Runtime/CriWare/CriWare'
        cri.mkdir(parents=True)
        shutil.copy2(plugin/'CriWare.uplugin', cri/'CriWare.uplugin')
        # DLLs and module descriptor only; source/reference assets remain untouched.
        for source in (plugin/'Binaries/Win64').iterdir():
            if source.suffix in ('.dll', '.modules'):
                target = cri/'Binaries/Win64'/source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        dll_rel = Path('Source/ThirdParty/CriWare/cri/pc/libs/x64/cri_ware_pcx64_le.dll')
        (cri/dll_rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(plugin/dll_rel, cri/dll_rel)
        content = root/'Plugins'/mount/'Content'
        content.mkdir(parents=True)
        audio = root/'Content/CriWareData'
        audio.mkdir(parents=True)
        shutil.copy2(acb.with_suffix('.awb'), audio/(acb.stem+'.awb'))
        (content.parent/(mount+'.uplugin')).write_text(json.dumps({'FileVersion':3,'Version':1,'VersionName':'1','CanContainContent':True,'Modules':[]}), encoding='utf-8')
        project = root/'VoiceBuilder.uproject'
        project.write_text(json.dumps({'FileVersion':3,'Plugins':[{'Name':n,'Enabled':True} for n in ('CriWare','PythonScriptPlugin',mount)]}), encoding='utf-8')
        package = '/'+mount+'/'+acb.stem
        report = root/'verified.json'
        script = root/'import_voice.py'
        script.write_text('import unreal\n'
            'task = unreal.AssetImportTask()\n'
            f'task.filename = {str(acb)!r}\n'
            f'task.destination_path = {("/"+mount)!r}\n'
            f'task.destination_name = {acb.stem!r}\n'
            'task.automated = True\ntask.replace_existing = True\ntask.save = True\n'
            'task.factory = unreal.SoundAtomCueSheetFactory()\n'
            'options = unreal.SoundAtomCueSheetImportOptions()\n'
            'options.new_cue_preset = unreal.AtomNewCuePresets.DO_NOT_CREATE\n'
            'options.override_awb_directory = True\noptions.awb_directory = "CriWareData"\n'
            'options.force_copy_awb_files = False\ntask.options = options\n'
            'unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])\n'
            f'asset = unreal.load_asset({package!r})\n'
            'if not asset: raise RuntimeError("CueSheet import failed")\n'
            'asset.set_editor_property("awb_directory", unreal.DirectoryPath(path="CriWareData"))\n'
            'asset.set_editor_property("override_awb_directory", False)\n'
            'unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False)\n', encoding='utf-8')
        def execute(script_path, label):
            proc = subprocess.run([str(engine),str(project),'-run=pythonscript','-script='+script_path.resolve().as_posix(),'-unattended','-nullrhi','-nosplash','-stdout','-FullStdOutLogOutput'], capture_output=True, timeout=240, creationflags=0x08000000)
            log = proc.stdout.decode('utf-8','replace')+proc.stderr.decode('utf-8','replace')
            (root/(label+'.log')).write_text(log, encoding='utf-8')
            errors = [line for line in log.splitlines() if ': Error:' in line]
            # This plugin checks the unset default AWB root during FactoryCreateBinary,
            # before applying import options. A separate process must still reopen
            # the saved asset successfully with its final directory and exact cues.
            initial_root_check = label == 'import' and proc.returncode == 1 and errors and all('LogCriWareRuntime: Error: Failed to Open \\' in line for line in errors)
            if (proc.returncode and not initial_root_check) or 'LogPython: Error:' in log:
                from unreal_diagnostics import failure_details
                details=failure_details(log)
                raise RuntimeError('A Unreal não validou o asset. Consulte '+str(root/(label+'.log'))+('\n\n'+details if details else ''))
        execute(script, 'import')
        asset_path = content/(acb.stem+'.uasset')
        raw = asset_path.read_bytes()
        original = acb.read_bytes()
        # CRI's LoadAcbData mutates working table fields in-place. Restore the
        # finalized ACB without changing native package/BulkData byte counts.
        positions = [i for i in range(len(raw)) if raw.startswith(original[:32], i)]
        if len(positions) != 1 or positions[0]+len(original) > len(raw):
            raise ValueError('Não foi possível localizar o ACB nativo com segurança.')
        start = positions[0]
        raw = raw[:start]+original+raw[start+len(original):]
        asset_path.write_bytes(clear_import_sources(raw, acb, (asset_path.parent, root, engine.parent)))
        verify = root/'verify_voice.py'
        verify.write_text('import unreal, json\n'
            f'asset = unreal.load_asset({package!r})\n'
            'if not asset: raise RuntimeError("Saved CueSheet failed to load")\n'
            'directory = asset.get_editor_property("awb_directory").path\n'
            'override = asset.get_editor_property("override_awb_directory")\n'
            'source_files = asset.get_editor_property("asset_import_data").extract_filenames()\n'
            'if directory != "CriWareData" or override or source_files: raise RuntimeError("CueSheet fields were not preserved")\n'
            'infos = asset.get_editor_property("cue_infos")\n'
            'data = [{"id":int(x.get_editor_property("id")),"name":str(x.get_editor_property("name"))} for x in infos]\n'
            f'with open({str(report)!r}, "w", encoding="utf-8") as f: json.dump(data,f)\n', encoding='utf-8')
        execute(verify, 'reload')
        raw = asset_path.read_bytes()
        if acb.read_bytes() not in raw:
            raise ValueError('O asset nativo não preservou o ACB finalizado.')
        cues = json.loads(report.read_text(encoding='utf-8'))
        from core import UTF
        utf = UTF(original)
        table = utf.child('CueTable').rows
        expected = {(table[x['CueIndex']]['CueId'], x['CueName']) for x in utf.child('CueNameTable').rows}
        if {(x['id'],x['name']) for x in cues} != expected or len(cues) != len(expected):
            raise ValueError('A Unreal não preservou todos os nomes e IDs dos cues.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset_path, destination)
        return {'editor_asset':True,'unreal_reload_verified':True,'awb_directory':'CriWareData','override_awb_directory':False,'source_files':[],'editor_cues':cues,'editor_asset_sha256':hashlib.sha256(raw).hexdigest(),'native_build_log':str(root)}
