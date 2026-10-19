"""Delivery folders only; game asset names and package contents stay unchanged."""
from pathlib import Path
from i18n import Translator, LANGUAGES

UNREAL='Custom - Pasta do mod na Unreal'
GAME='Custom - Pasta do mod para o game'
REPLACER='Pasta do mod Replacer'
SUPPORT='Arquivos de apoio'

def folder(cfg,key):
    return Translator(cfg.get('ui_language') or 'pt').logical(key)

def replacer_name(cfg):
    import project_names
    value=str(cfg.get('replacer_folder_name') or '').strip()
    if not value:return folder(cfg,REPLACER)
    value=project_names.validate(value)
    if value.casefold()==folder(cfg,SUPPORT).casefold():raise ValueError('Use outro nome para a pasta de entrega Replacer.')
    return value

def destinations(bank,make_package,audio_package=False):
    name=bank.name;stem='Voice_'+name+'_P'
    if make_package:
        result={stem+ext:Path(replacer_name(bank.cfg))/(stem+ext) for ext in ('.pak','.utoc','.ucas')}
    elif audio_package:
        result={name+'.uasset':Path(folder(bank.cfg,UNREAL))/(name+'.uasset'),
                stem+'.pak':Path(folder(bank.cfg,GAME))/(stem+'.pak'),
                name+'.acb':Path(folder(bank.cfg,SUPPORT))/(name+'.acb'),
                name+'.awb':Path(folder(bank.cfg,SUPPORT))/(name+'.awb')}
    else:
        extensions=['.uasset','.acb','.awb']
        if bank.file_kind not in ('zen','inline_cooked'):extensions.append('.uexp')
        result={name+ext:Path(name+ext) for ext in extensions}
    report_folder=Path(folder(bank.cfg,SUPPORT)) if make_package or audio_package else Path('.')
    for report in ('manifest.json','validation.json'):
        filename=name+'_'+report;result[filename]=report_folder/filename
    return result

def validate_paths(bank,target,make_package,audio_package=False):
    paths=destinations(bank,make_package,audio_package)
    original=set()
    if getattr(bank,'external',False):
        source=bank.source or {}
        original={Path(p).resolve() for p in list(source.get('original_paths',{}).values())+list(source.get('package_origin',{}).get('original_paths',{}).values()) if p}
    for relative in paths.values():
        path=target/relative
        if not path.resolve().is_relative_to(target):raise ValueError('Destino redirecionado para fora da pasta selecionada.')
        if any(part.is_symlink() for part in [path,*path.parents] if part.is_relative_to(target)):
            raise ValueError('Destino redirecionado para fora da pasta selecionada.')
        if path.exists() and not path.is_file():raise ValueError('O destino do arquivo não é um arquivo regular: '+str(path))
        if path.resolve() in original:raise ValueError('Exporte em outra pasta para preservar os arquivos importados.')
    return paths

def companion(path,suffix):
    """Find matching auxiliary files in our delivery folders, without broad scans."""
    path=Path(path);direct=path.with_suffix(suffix)
    if direct.is_file():return direct
    names={Translator(lang).logical(key) for lang in LANGUAGES for key in (UNREAL,GAME,REPLACER,SUPPORT,'Pasta do mod na Unreal','Pasta do mod para o game')}
    if path.parent.name not in names:return direct
    candidates=[path.parent.parent/name/(path.stem+suffix) for name in names]
    found=[candidate for candidate in candidates if candidate.is_file()]
    return found[0] if len(found)==1 else direct
