import migrated_audio
"""Small clarity improvements; no changes to audio, export rules or layout painting."""
import tkinter as tk
from tkinter import ttk
import core,voice_context
from modern_theme import BG,PANEL,FG,MUTED,SUCCESS,WARNING,INFO


class Tooltip:
    def __init__(self,widget,text):
        self.widget=widget;self.text=text;self.pending=None;self.window=None
        widget.bind('<Enter>',self.schedule,add='+');widget.bind('<Leave>',self.hide,add='+')
        widget.bind('<ButtonPress>',self.hide,add='+');widget.bind('<Destroy>',self.hide,add='+')
    def schedule(self,event=None):
        self.hide();self.pending=self.widget.after(500,self.show)
    def show(self):
        self.pending=None
        if not self.widget.winfo_exists() or not self.widget.winfo_ismapped():return
        value=self.text()
        if not value:return
        win=tk.Toplevel(self.widget);self.window=win;win.overrideredirect(True)
        tk.Label(win,text=value,bg=PANEL,fg=FG,font=('Segoe UI',9),padx=9,pady=6,wraplength=300,justify='left').pack()
        win.update_idletasks()
        x=min(self.widget.winfo_rootx(),self.widget.winfo_screenwidth()-win.winfo_reqwidth()-8)
        y=min(self.widget.winfo_rooty()+self.widget.winfo_height()+6,self.widget.winfo_screenheight()-win.winfo_reqheight()-8)
        win.geometry(f'+{max(0,x)}+{max(0,y)}')
    def hide(self,event=None):
        if event is not None and event.type==tk.EventType.Destroy and event.widget is not self.widget:return
        if self.pending is not None:
            self.widget.after_cancel(self.pending);self.pending=None
        if self.window is not None:self.window.destroy();self.window=None


def field(owner,parent,caption):
    frame=ttk.Frame(parent)
    frame.pack(side='left',fill='x',expand=False)
    owner.label(frame,caption,style='Muted.TLabel').pack(side='left',padx=(0,8))
    return frame


def search_hint(owner,entry):
    style=ttk.Style(entry)
    hint=owner.localize_widget(tk.Label(entry,bg=style.lookup('TEntry','fieldbackground') or PANEL,fg=MUTED,font=('Segoe UI',9),anchor='w',padx=0,pady=0),'Buscar nome, Cue ID ou função')
    def update(*_):
        if not owner.search.get() and entry.focus_get() is not entry:
            hint.place(x=9,rely=.5,anchor='w')
        else:hint.place_forget()
    hint.bind('<Button-1>',lambda event:entry.focus_set())
    entry.bind('<FocusIn>',update,add='+');entry.bind('<FocusOut>',update,add='+')
    owner.search.trace_add('write',update)
    update()


def remove_filter(owner,name):
    variables={'Busca':(owner.search,''),'Estado':(owner.view_filter,'all'),
               'Tipo':(owner.function_scope,'all'),'Função':(owner.function_filter,'*')}
    if name=='Grupo de repetidas':owner.duplicate_focus=None
    elif name in variables:
        variable,value=variables[name];variable.set(value)
    owner.fill_rows();refresh(owner)


def filter_values(owner):
    result=[]
    for name in filters(owner):
        if name=='Busca':value=owner.search.get()
        elif name=='Grupo de repetidas':value=owner.tr(name)
        else:
            variable={'Estado':owner.view_filter,'Tipo':owner.function_scope,'Função':owner.function_filter}[name]
            record=next((item for item in owner._choices if item['variable'] is variable),None)
            value=next((label for key,label in record['options'] if key==variable.get()),variable.get()) if record else variable.get()
            if record and record['translate']:value=owner.tr(value)
        result.append((name,value))
    return result


def open_filter_menu(owner):
    if not filters(owner):return
    button=owner.active_filter_button
    try:owner.active_filter_menu.tk_popup(button.winfo_rootx(),button.winfo_rooty()+button.winfo_height()+3)
    finally:owner.active_filter_menu.grab_release()


def refresh_filter_menu(owner):
    values=filter_values(owner)
    signature=tuple((name,owner.tr(name),value) for name,value in values)
    owner.active_filter_button.configure(state='normal' if values else 'disabled')
    owner.clear_filters_button.configure(state='normal' if values else 'disabled')
    if signature==owner.active_filter_signature:return
    owner.active_filter_signature=signature
    owner.active_filter_menu.delete(0,'end')
    for name,value in values:
        owner.active_filter_menu.add_command(label=owner.tr(name)+': '+value+'  ×',command=lambda name=name:remove_filter(owner,name))


def filters(owner):
    return [label for active,label in [(bool(owner.search.get()),'Busca'),(owner.view_filter.get()!='all','Estado'),(owner.function_scope.get()!='all','Tipo'),(owner.function_filter.get()!='*','Função'),(bool(owner.duplicate_focus),'Grupo de repetidas')] if active]


def clear(owner):
    owner.duplicate_focus=None
    for variable,value in [(owner.function_scope,'all'),(owner.function_filter,'*'),(owner.search,''),(owner.view_filter,'all')]:
        if variable.get()!=value:variable.set(value)
    owner.fill_rows();refresh(owner)


def selected_status(owner):
    row=owner.selected
    if not owner.bank or row is None:return [],MUTED
    key=row['key'];tags=[];color=MUTED
    if migrated_audio.is_replaced(owner,key):tags.append('Customizada');color=SUCCESS
    elif migrated_audio.is_original(owner,key):tags.append('Original')
    elif owner.bank.external:
        status=(owner.bank.source or {}).get('audio_similarity',{}).get(key,{}).get('status','uncertain')
        if core.imported_is_original(owner.bank,row):status='similar'
        tags.append({'similar':'Semelhante / sem substituição','different':'Customizada / diferente','uncertain':'Comparação incerta'}.get(status,'Comparação incerta'))
        color={'different':SUCCESS,'uncertain':INFO}.get(status,MUTED)
    else:tags.append('Original')
    if key in owner.duplicate_info:tags.append('Repetida')
    if voice_context._user_functions.display_manual(row):tags.append('Função manual')
    if key not in owner.replacements and not core.preserve_unreplaced(owner.bank,row,owner.keep_imported.get()):tags.append('Silêncio')
    return tags,color


def refresh(owner):
    if not hasattr(owner,'active_filter_row'):return
    names=filters(owner)
    owner.active_filter_caption.set(owner.tr('Filtros ativos: {count}').format(count=len(names))+' ▾')
    refresh_filter_menu(owner)
    tags,color=selected_status(owner)
    owner.selected_status_caption.set(' • '.join(owner.tr(tag) for tag in tags))
    owner.selected_status_label.configure(fg=color)


def install(owner,filter_content,title_row):
    # Reuse the height beside the two field rows; filtering never adds a row.
    owner.active_filter_row=ttk.Frame(owner.voice_counter_stack)
    owner.active_filter_row.pack(fill='x',pady=(4,0))
    owner.active_filter_caption=tk.StringVar(owner)
    owner.active_filter_button=ttk.Button(owner.active_filter_row,textvariable=owner.active_filter_caption,width=14,style='CompactFilter.TButton',padding=(6,3),command=lambda:open_filter_menu(owner))
    owner.active_filter_button.pack(side='left',fill='x',expand=True)
    owner.active_filter_menu=tk.Menu(owner.active_filter_button,tearoff=False,bg=PANEL,fg=FG,activebackground=BG,activeforeground=FG,font=('Segoe UI',9))
    owner.active_filter_signature=None
    owner.clear_filters_button=owner.button(owner.active_filter_row,'Limpar filtros',lambda:clear(owner))
    owner.clear_filters_button.configure(style='CompactFilter.TButton',padding=(6,3))
    owner.clear_filters_button.pack(side='right',padx=(6,0))
    owner.selected_status_caption=tk.StringVar(owner)
    owner.selected_status_label=tk.Label(title_row,textvariable=owner.selected_status_caption,bg=BG,fg=MUTED,font=('Segoe UI',9),anchor='w',height=1,width=1,padx=0,pady=0)
    owner.selected_status_label.pack(side='left',fill='x',expand=True,padx=(12,0))
    owner.bank_language_tooltip=Tooltip(owner.bank_language_choice,lambda:owner.tr('Idioma das vozes: US / JP. Não altera o idioma da interface.'))
    owner.selected_status_tooltip=Tooltip(owner.selected_status_label,lambda:owner.selected_status_caption.get())
    owner.project_name_tooltip=Tooltip(owner.project_name_btn,lambda:owner.tr('Custom: nome idêntico à pasta do seu plugin em Plugins na Unreal.') if owner.export_mode.get()=='audio_pak' else '')
    import replacer_folder
    owner.replacer_folder_tooltip=Tooltip(owner.replacer_folder_btn,lambda:replacer_folder.name_hint(owner) if owner.export_mode.get()=='package' else '')
    for variable in [owner.search,owner.view_filter,owner.function_scope,owner.function_filter]:variable.trace_add('write',lambda *_:refresh(owner))
    refresh(owner)
