import localized_dialogs
"""Project naming with the Custom plugin requirement beside the input."""
from tkinter import simpledialog,ttk
import modern_theme

class ProjectNameDialog(simpledialog.Dialog):
    def __init__(self,owner):
        self.owner=owner
        self.custom=owner.export_mode.get()!='package'
        super().__init__(owner,owner.tr('Nome do projeto'))

    def body(self,parent):
        self.configure(bg=modern_theme.PANEL)
        parent.configure(bg=modern_theme.PANEL)
        ttk.Label(parent,text=self.owner.tr('Digite o nome do seu projeto:'),background=modern_theme.PANEL,foreground=modern_theme.FG).pack(anchor='w',pady=(0,8))
        self.entry=ttk.Entry(parent,width=42,style='Required.TEntry' if self.custom else 'TEntry')
        self.entry.pack(fill='x')
        self.entry.insert(0,self.owner.project_name)
        self.entry.selection_range(0,'end')
        if self.custom:
            ttk.Label(parent,text=self.owner.tr('Use exatamente o nome da pasta do mod em Plugins na Unreal. Ele compõe o caminho do AWB.'),
                background=modern_theme.PANEL,foreground=modern_theme.WARNING,wraplength=390,justify='left').pack(anchor='w',pady=(8,0))
        return self.entry

    def buttonbox(self):
        localized_dialogs.buttonbox(self,self.owner)

    def apply(self):
        self.result=self.entry.get()
