import localized_dialogs
"""Project-specific delivery folder name, visible only in Replacer mode."""
import re
from tkinter import simpledialog
import core,project_names,export_delivery

def default_name(owner):
    actor=core.character_id(owner.bank.name)
    name=owner.character_names.get(actor) or actor or owner.bank.name
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','-',str(name)).strip().rstrip('. ')[:80]
    try:return project_names.validate(name)
    except ValueError:return owner.bank.name

def selected_name(owner):
    return owner.replacer_folder_name.strip() or default_name(owner)

def name_hint(owner):
    text=owner.tr('Deixe vazio para usar o nome oficial do personagem no idioma do app.')
    if owner.bank:text+='\n'+owner.tr('Personagem base')+': '+default_name(owner)
    return text

def rename(owner):
    if owner.busy or not owner.bank or owner.export_mode.get()!='package':return
    value=localized_dialogs.askstring(owner,owner.tr('Nome da pasta Replacer'),name_hint(owner),initialvalue=owner.replacer_folder_name,parent=owner)
    if value is None:return
    value=value.strip()
    try:
        if value:export_delivery.replacer_name(dict(owner.cfg,replacer_folder_name=value))
    except ValueError as error:owner.fail(str(error));return
    owner.replacer_folder_name=value
    owner.save_project(False)

def sync_button(owner):
    if not hasattr(owner,'replacer_folder_btn'):return
    button=owner.replacer_folder_btn;show=owner.export_mode.get()=='package'
    flow=getattr(owner,'export_flow',None)
    if flow is None:
        if show and not button.winfo_manager():button.pack(side='right',padx=(0,8))
        elif not show:button.pack_forget()
        return
    present=button in flow.widgets
    if show and not present:flow.widgets.insert(flow.widgets.index(owner.project_name_btn),button)
    elif not show and present:flow.widgets.remove(button);button.grid_forget()
    flow.trailing.add(button)
    flow.schedule()
