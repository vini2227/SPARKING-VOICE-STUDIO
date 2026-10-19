"""App-owned string dialogs with localized confirm/cancel buttons."""
from tkinter import simpledialog,ttk
import modern_theme

def buttonbox(dialog,owner):
    box=ttk.Frame(dialog,padding=(12,8),style='Card.TFrame')
    ttk.Button(box,text=owner.tr('Confirmar'),command=dialog.ok,default='active').pack(side='left',padx=5)
    ttk.Button(box,text=owner.tr('Cancelar'),command=dialog.cancel).pack(side='left',padx=5)
    dialog.bind('<Return>',dialog.ok);dialog.bind('<Escape>',dialog.cancel)
    box.pack()

class StringDialog(simpledialog.Dialog):
    def __init__(self,owner,title,prompt,initialvalue='',parent=None):
        self.owner=owner;self.prompt=prompt;self.initialvalue=initialvalue
        super().__init__(parent or owner,title)
    def body(self,parent):
        self.configure(bg=modern_theme.PANEL)
        parent.configure(bg=modern_theme.PANEL)
        ttk.Label(parent,text=self.prompt,wraplength=460,justify='left',background=modern_theme.PANEL,foreground=modern_theme.FG).pack(anchor='w',pady=(0,8))
        self.entry=ttk.Entry(parent,width=45);self.entry.pack(fill='x')
        self.entry.insert(0,str(self.initialvalue or ''));self.entry.selection_range(0,'end')
        return self.entry
    def buttonbox(self):buttonbox(self,self.owner)
    def apply(self):self.result=self.entry.get()

def askstring(owner,title,prompt,initialvalue='',parent=None):
    return StringDialog(owner,title,prompt,initialvalue,parent).result
