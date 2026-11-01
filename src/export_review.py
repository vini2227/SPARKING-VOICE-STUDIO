"""Review the actual target character and delivery folders before exporting."""
import copy
from tkinter import messagebox
import core,project_exchange,project_names,replacer_folder,export_delivery

def lines(owner):
    bank=owner.bank;package=owner.export_mode.get()=='package';custom=owner.export_mode.get()=='audio_pak'
    counts=project_exchange.export_summary(bank,owner.project_document())
    info=(bank.source or {}).get('package_origin',{}).get('bank_info',{}) if bank.external else {}
    character=info.get('label') or owner.character_names.get(core.character_id(bank.name),core.character_id(bank.name))
    name=bank.name if package else core.validate_export_name(owner.export_name.get() or bank.name,bank.language)
    base=core.export_destination(owner.destination.get(),owner.cfg)
    root=project_names.project_export_root(base,owner.project_name or bank.name,owner.project if not owner.project_temporary else None)
    target=copy.copy(bank);target.name=name;target.cfg=dict(bank.cfg)
    if package:target.cfg['replacer_folder_name']=replacer_folder.selected_name(owner)
    destinations=export_delivery.destinations(target,package,custom)
    folders=sorted({str(path.parent) for path in destinations.values() if path.suffix not in ('.json','.acb','.awb')})
    tr=owner.tr
    result=[owner.project_name or bank.name,tr('Personagem / pasta' if info.get('custom_mount') else 'Personagem base')+': '+character,bank.name,
            tr('Replacer (.pak / .utoc / .ucas)' if package else 'Custom (.uasset + AWB .pak)' if custom else 'Asset para jogo + ACB + AWB'),
            tr('Nome do banco')+': '+name,'',tr('Vozes do banco: ')+str(len(bank.rows)),
            tr('Substituições WAV: ')+str(counts['custom']),tr('Importadas diferentes mantidas: ')+str(counts['imported']),
            tr('Originais / semelhantes mantidas: ')+str(counts['original']),tr('Importadas incertas preservadas: ')+str(counts['uncertain']),
            tr('Vozes em silêncio: ')+str(counts['silence']),'',tr('Destino: ')+str(root),tr('Pastas de entrega')+': '+', '.join(folders)]
    if package and info.get('custom_mount'):result+=['',tr('A exportação altera apenas o banco escolhido. Mantenha o mod original instalado.')]
    if custom:result.insert(4,tr('O personagem Custom depende das referências configuradas na Unreal.'))
    if owner.project_temporary:result+=['',tr('Sessão temporária: exportar não cria um projeto salvo.')]
    return result

def confirm(owner):
    try:text='\n'.join(lines(owner))
    except (ValueError,OSError) as error:owner.fail(str(error));return False
    return messagebox.askokcancel(owner.tr('Resumo da exportação'),text,parent=owner)
