"""Portable archives replace application files only; user data never ships."""
from pathlib import PurePosixPath

APP_FOLDERS={'src','Data','Tools','Runtime','Readme'}
APP_FILES={'Sparking Zero Voice Studio.exe','runtime.path','settings.example.json','README.md',
           'LICENSE','UPDATE.md','distribution_manifest.json','icon_verification.json','Preparar ferramentas.bat','preparar_ferramentas.py'}
PRIVATE_FOLDERS={'Projects','Exports','Imports','Cache','Backups','Reports','tests','.git','.venv','DependencyUpdates'}

def validate_paths(names):
    seen=set()
    for raw in names:
        name=str(raw).replace('\\','/');path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or ':' in name or not path.parts:
            raise ValueError('Invalid release path: '+name)
        lowered=name.casefold()
        if lowered in seen:raise ValueError('Duplicate release path: '+name)
        seen.add(lowered)
        if any(part.casefold() in {p.casefold() for p in PRIVATE_FOLDERS} for part in path.parts[:1]):
            raise ValueError('Personal folder entered release: '+name)
        if len(path.parts)==1:
            if name not in APP_FILES:raise ValueError('Unexpected root file: '+name)
        elif path.parts[0] not in APP_FOLDERS:raise ValueError('Unexpected release folder: '+name)
        if any(part.casefold()=='__pycache__' for part in path.parts) or path.suffix.lower() in {'.wav','.mp3','.hca','.awb','.acb','.pak','.ucas','.utoc','.uasset','.uexp'}:
            raise ValueError('Private audio/game/cache file entered release: '+name)
