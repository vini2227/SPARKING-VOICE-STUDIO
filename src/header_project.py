"""A quiet, fixed-width project identity before the current bank."""
import tkinter as tk
from tkinter import ttk,font
import modern_theme

def build(owner,box):
    title=owner.localize_widget(tk.Label(box,bg=modern_theme.PANEL,fg=modern_theme.MUTED,font=('Segoe UI',9,'bold')),'PROJETO')
    title.pack(side='left');owner.project_identity_title=title
    owner.header_project_name=tk.StringVar(value='—')
    label=tk.Label(box,textvariable=owner.header_project_name,bg=modern_theme.PANEL,font=('Segoe UI',11,'bold'),width=1,anchor='w',fg=modern_theme.FG)
    label.pack(side='left',fill='x',expand=True,padx=(12,0));owner.header_project_label=label
    owner.header_project_font=font.Font(font=label.cget('font'))
    owner._header_project_tip=None;owner._header_project_hover=None
    def hide(event=None):
        if owner._header_project_hover is not None:
            owner.after_cancel(owner._header_project_hover);owner._header_project_hover=None
        tip=owner._header_project_tip
        if tip and tip.winfo_exists():tip.destroy()
        owner._header_project_tip=None
    def show():
        owner._header_project_hover=None
        if owner.header_project_name.get()==owner.header_project_full:return
        tip=tk.Toplevel(owner);tip.overrideredirect(True);owner._header_project_tip=tip
        tip.configure(bg=modern_theme.EDGE)
        tk.Label(tip,text=owner.header_project_full,bg=modern_theme.CARD,fg=modern_theme.FG,font=('Segoe UI',10),padx=10,pady=7,wraplength=440).pack(padx=1,pady=1)
        tip.geometry(f'+{label.winfo_rootx()}+{label.winfo_rooty()+label.winfo_height()+6}')
    def enter(event):
        hide();owner._header_project_hover=owner.after(450,show)
    label.bind('<Enter>',enter);label.bind('<Leave>',hide)
    owner.hide_header_project_tip=hide
    box.bind('<Configure>',lambda event:update(owner) if event.widget is box else None,add='+')
    update(owner)

def update(owner):
    if not hasattr(owner,'header_project_name'):return
    owner.hide_header_project_tip()
    saved=bool(owner.project and not owner.project_temporary and owner.project_name)
    name=owner.project_name if saved else '—'
    owner.header_project_full=name
    text=name;measure=owner.header_project_font.measure
    available=max(1,owner.project_identity_panel.winfo_width()-36-owner.project_identity_title.winfo_reqwidth())
    if measure(text)>available:
        while text and measure(text+'…')>available:text=text[:-1]
        text=text.rstrip()+'…'
    owner.header_project_name.set(text)
    owner.header_project_label.configure(fg=modern_theme.FG)
