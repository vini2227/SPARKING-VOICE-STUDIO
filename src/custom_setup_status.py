"""Read-only validation of the dependencies used by native Custom voice export."""
import json
from tkinter import font as tkfont, ttk
from pathlib import Path
import editor_asset
from modern_theme import SUCCESS, ERROR

def check(cfg):
    project=str(cfg.get('project') or '').strip()
    if not project:return False,'CustomProject não configurado'
    project=Path(project)
    if not project.is_dir():return False,'CustomProject não encontrado'
    if not any(project.glob('*.uproject')):return False,'Pasta do CustomProject inválida'
    folder=editor_asset.configured_folder(cfg)
    if not folder:return False,'Custom Engine não configurada'
    try:engine=editor_asset.engine_from_folder(folder)
    except (ValueError,OSError):return False,'Custom Engine não encontrada'
    plugin=project/'Plugins/Runtime/CriWare/CriWare'
    required=['CriWare.uplugin','Binaries/Win64/UnrealEditor.modules',
        'Binaries/Win64/UnrealEditor-CriWareRuntime.dll','Binaries/Win64/UnrealEditor-CriWareEditor.dll',
        'Source/ThirdParty/CriWare/cri/pc/libs/x64/cri_ware_pcx64_le.dll']
    if not all((plugin/name).is_file() for name in required):return False,'CriWare ausente ou incompleto'
    try:
        descriptor=json.loads((plugin/'CriWare.uplugin').read_text(encoding='utf-8-sig'))
        modules=json.loads((plugin/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
        if not isinstance(descriptor,dict) or not isinstance(modules,dict):raise ValueError()
        if not {'CriWareEditor','CriWareRuntime'} <= set(modules.get('Modules',{})):raise ValueError()
        engine_modules=engine.with_name('UnrealEditor.modules')
        if engine_modules.is_file():
            expected=json.loads(engine_modules.read_text(encoding='utf-8-sig')).get('BuildId')
            if expected and modules.get('BuildId')!=expected:return False,'CriWare incompatível com a engine'
    except (OSError,ValueError,TypeError):return False,'Configuração do CriWare inválida'
    return True,'Custom configurado e verificado'

def update(owner):
    if not hasattr(owner,'custom_setup_status'):return
    try:valid,label=check(owner.cfg)
    except OSError:valid,label=False,'Não foi possível verificar as pastas'
    labels={'Custom configurado e verificado':'Pasta Custom configurada e verificada',
            'CustomProject não configurado':'Pasta Custom não selecionada',
            'Custom Engine não configurada':'Pasta da Custom Engine não selecionada'}
    owner.custom_setup_status.configure(text=('✓ ' if valid else '● ')+owner.tr('Custom: ').rstrip()+' '+owner.tr(labels.get(label,label)),foreground=SUCCESS if valid else ERROR)
    owner.custom_setup_valid=valid

def layout(owner):
    """Use each translated label's natural width; wrap only when needed."""
    row=owner.custom_engine_notice_row
    width=row.winfo_width()
    if width<=1:return
    notice=owner.custom_engine_notice
    status=owner.custom_setup_status
    def natural_width(label):
        font=label.cget('font') or ttk.Style(label).lookup(label.cget('style'),'font') or 'TkDefaultFont'
        return tkfont.Font(root=label,font=font).measure(label.cget('text'))+4
    notice_width=natural_width(notice)
    status_width=natural_width(status)
    budget=max(2,width-14)
    if notice_width+status_width<=budget:
        notice_wrap,status_wrap=notice_width,status_width
    else:
        status_wrap=max(1,int(budget*status_width/max(1,notice_width+status_width)))
        notice_wrap=max(1,budget-status_wrap)
    for label,wrap in ((notice,notice_wrap),(status,status_wrap)):
        if int(float(label.cget('wraplength')))!=wrap:
            label.configure(wraplength=wrap)
