"""Stable bank identity width, measured from the localized catalog."""
import tkinter as tk
from tkinter import font
import core
from modern_theme import PANEL,FG,MUTED

def reserved_width(studio):
    signature=(tuple(studio.character_names.items()),tuple(getattr(studio,'banks',[])),
               studio.bank_character.get(),studio.bank_code.get(),studio.translator.language,
               float(studio.tk.call('tk','scaling')))
    cached=getattr(studio,'_bank_reserved_width',None)
    if cached is not None and cached[0]==signature:return cached[1]
    names=[studio.translator.display(str(value)) for value in studio.character_names.values()]
    names.extend([studio.bank_character.get(),studio.tr('Nenhum banco aberto')])
    name_font=font.Font(root=studio,family='Segoe UI',size=11,weight='bold')
    code_font=font.Font(root=studio,family='Consolas',size=8)
    codes=list(getattr(studio,'banks',[]))+[studio.bank_code.get(),'BTLCV_0000_00_US']
    name_width=max(map(name_font.measure,names),default=0)
    code_width=max((code_font.measure(str(code)+' • '+studio.tr('Importada')) for code in codes),default=0)
    title_font=font.Font(root=studio,family='Segoe UI',size=9,weight='bold')
    result=max(300,title_font.measure(studio.tr('BANCO ATUAL'))+name_width+name_font.measure('MMMMM')+code_width+48)
    studio._bank_reserved_width=(signature,result)
    return result

def build(studio,box):
    studio.bank_character=studio.localized_var('Nenhum banco aberto')
    studio.bank_code=tk.StringVar(value='—');display=tk.StringVar()
    box.columnconfigure(1,weight=1);box.rowconfigure(0,weight=1)
    title=studio.localize_widget(tk.Label(box,bg=PANEL,fg=MUTED,font=('Segoe UI',9,'bold')),'BANCO ATUAL')
    name=tk.Label(box,textvariable=display,bg=PANEL,fg=FG,font=('Segoe UI',11,'bold'),anchor='w',width=1)
    code=tk.Label(box,textvariable=studio.bank_code,bg=PANEL,fg=MUTED,font=('Consolas',8),anchor='e')
    title.grid(row=0,column=0,sticky='w',padx=(0,12))
    name.grid(row=0,column=1,sticky='ew',padx=(0,12));code.grid(row=0,column=2,sticky='e')
    studio.bank_identity_panel=box;studio.bank_character_label=name;studio.bank_code_label=code
    pending=[None]
    def fit():
        pending[0]=None
        if not box.winfo_exists():return
        measure=font.Font(root=studio,font=name.cget('font')).measure
        room=max(1,box.winfo_width()-48-title.winfo_reqwidth()-code.winfo_reqwidth())
        value=studio.bank_character.get()
        if measure(value)>room:
            while value and measure(value+'…')>room:value=value[:-1]
            value=value.rstrip()+'…'
        if display.get()!=value:display.set(value)
    def schedule(*args):
        if pending[0] is not None:box.after_cancel(pending[0])
        pending[0]=box.after_idle(fit)
    box.bind('<Configure>',lambda event:schedule() if event.widget is box else None,add='+')
    studio.bank_character.trace_add('write',schedule);studio.bank_code.trace_add('write',schedule);schedule()

def update(studio,bank):
    info=(bank.source or {}).get('package_origin',{}).get('bank_info',{}) if bank.external else {}
    studio.bank_character.set(info.get('label') or studio.character_names.get(core.character_id(bank.name)) or core.character_id(bank.name) or bank.name)
    studio.bank_code.set(bank.name+(' • '+studio.tr('Importada') if bank.external else ''))
    if hasattr(studio,'summary_flow'):studio.summary_flow.schedule()
