"""Localized portable installation guides; generated once per distribution."""
import json
from pathlib import Path

def write_guides(root):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    catalog=json.loads(Path(__file__).with_name('readme_languages.json').read_text(encoding='utf8'))
    folder=root/'Readme';folder.mkdir(exist_ok=True)
    links=[]
    for code,item in catalog.items():
        filename='README_'+code+'.md'
        (folder/filename).write_text(item['text'],encoding='utf8')
        links.append('- ['+item['name']+'](Readme/'+filename+')')
    index='# Sparking Zero Voice Studio\n\nInstallation • Requirements • Features • Export • Backup • Troubleshooting\n\nChoose your language / Escolha seu idioma / Elige tu idioma / Choisissez votre langue:\n\n'+'\n'.join(links)+'\n\nNew installations start in English. Custom Engine and CustomProject are not included.\n\nExtract the entire application ZIP before opening Sparking Zero Voice Studio.exe.\n'
    index+='\nUpdates: close the app, merge this ZIP into the existing installation and replace application files. Projects and personal settings are not included in the ZIP. See [UPDATE.md](UPDATE.md).\n'
    (root/'README.md').write_text(index,encoding='utf8')
    (root/'UPDATE.md').write_text(Path(__file__).with_name('UPDATE.md').read_text(encoding='utf8'),encoding='utf8')
    return list(catalog)
