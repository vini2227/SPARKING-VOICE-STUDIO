"""Character/folder groups from actual package mounts, with explicit US/JP selection."""
import tkinter as tk
from tkinter import ttk
import unicodedata
from modern_theme import BG,PANEL,CARD,FG,MUTED,ACCENT

def folded(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value).casefold()) if not unicodedata.combining(c))

def groups(banks,query=''):
    result={};query=folded(query.strip())
    for index,bank in enumerate(banks):
        info=bank.get('package_origin',{}).get('bank_info',{})
        label=info.get('label') or bank['bank_name'];key=info.get('group_key') or bank['bank_name']
        if query and query not in folded(' '.join((label,bank['bank_name'],info.get('language',''),key))):continue
        entry=result.setdefault(key,{'label':label,'banks':[]})
        entry['banks'].append((index,bank,info))
    return sorted(result.values(),key=lambda item:folded(item['label']))

def show(owner,banks,open_bank,parent=None):
    parent=parent or owner
    old=getattr(owner,'package_browser_window',None)
    if old is not None and old.winfo_exists():old.destroy()
    previous_grab=parent.grab_current()
    win=tk.Toplevel(parent);owner.package_browser_window=win
    win.title(owner.tr('Personagens do pacote'));win.configure(bg=BG);win.transient(parent)
    width=min(880,win.winfo_screenwidth()-60);height=min(620,win.winfo_screenheight()-100)
    win.geometry(f'{width}x{height}');win.minsize(min(460,width),min(320,height))
    body=ttk.Frame(win,padding=18);body.pack(fill='both',expand=True)
    owner.label(body,'Personagens do pacote',font=('Segoe UI',15,'bold')).pack(anchor='w')
    summary=owner.label(body,owner.tr('Este pacote contém {characters} personagens/pastas e {banks} bancos de voz.').format(characters=len(groups(banks)),banks=len(banks)))
    summary.pack(anchor='w',fill='x',pady=(7,4))
    hint=owner.label(body,'A exportação altera apenas o banco escolhido. Mantenha o mod original instalado.',style='Muted.TLabel')
    hint.pack(anchor='w',fill='x',pady=(0,12))
    owner.label(body,'Buscar personagem ou banco').pack(anchor='w',pady=(0,4))
    query=tk.StringVar();entry=ttk.Entry(body,textvariable=query);entry.pack(fill='x',pady=(0,12))
    footer=ttk.Frame(body);footer.pack(side='bottom',fill='x',pady=(12,0))
    detail=tk.StringVar();details=ttk.Label(body,textvariable=detail,foreground=MUTED)
    details.pack(side='bottom',fill='x',pady=(8,0))
    area=ttk.Frame(body);area.pack(fill='both',expand=True);area.rowconfigure(0,weight=1);area.columnconfigure(0,weight=1)
    style=ttk.Style(win)
    style.configure('Package.Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,rowheight=28)
    style.map('Package.Treeview',background=[('selected',ACCENT)],foreground=[('selected','#ffffff')])
    style.configure('Package.Treeview.Heading',background=CARD,foreground=FG)
    tree=ttk.Treeview(area,columns=('bank','voices'),show='tree headings',selectmode='browse',style='Package.Treeview')
    tree.heading('#0',text=owner.tr('Personagem / pasta'));tree.heading('bank',text=owner.tr('Banco'));tree.heading('voices',text=owner.tr('Vozes'))
    tree.column('#0',width=220,minwidth=160);tree.column('bank',width=280,minwidth=180);tree.column('voices',width=80,minwidth=65,stretch=False,anchor='center')
    tree.grid(row=0,column=0,sticky='nsew')
    vertical=ttk.Scrollbar(area,orient='vertical',command=tree.yview);vertical.grid(row=0,column=1,sticky='ns')
    horizontal=ttk.Scrollbar(area,orient='horizontal',command=tree.xview);horizontal.grid(row=1,column=0,sticky='ew')
    tree.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
    def close():
        win.destroy()
        if previous_grab is not None and previous_grab.winfo_exists():previous_grab.grab_set()
    def selected():
        selection=tree.selection()
        return int(selection[0][1:]) if selection and selection[0].startswith('b') else None
    def choose(event=None):
        index=selected()
        if index is None:return
        bank=banks[index]
        error=bank.get('package_origin',{}).get('bank_info',{}).get('error')
        if error:return
        close();open_bank(bank)
    owner.button(footer,'Fechar',close).pack(side='left')
    button=owner.button(footer,'Abrir banco',choose,True);button.pack(side='right');button.configure(state='disabled')
    def selection_changed(event=None):
        index=selected()
        if index is None:detail.set('');button.configure(state='disabled');return
        bank=banks[index];origin=bank.get('package_origin',{});info=origin.get('bank_info',{})
        error=info.get('error');detail.set(owner.tr(error) if error else origin.get('voice_asset_path') or bank['bank_name'])
        button.configure(state='disabled' if error else 'normal')
    def refresh(*args):
        selected_before=tree.selection();opened={tree.item(key,'text') for key in tree.get_children() if tree.item(key,'open')}
        tree.delete(*tree.get_children())
        for i,group in enumerate(groups(banks,query.get())):
            key='g'+str(i);tree.insert('','end',iid=key,text=group['label'],open=bool(query.get()) or group['label'] in opened or not opened)
            for index,bank,info in sorted(group['banks'],key=lambda item:item[1]['bank_name']):
                count=info.get('voice_count');count='—' if count is None else str(count)
                text=info.get('language') or bank['bank_name'][-2:]
                if info.get('error'):text+=' ⚠'
                tree.insert(key,'end',iid='b'+str(index),text=text,values=(bank['bank_name'],count))
        if selected_before and tree.exists(selected_before[0]):tree.selection_set(selected_before[0])
        selection_changed()
    query.trace_add('write',refresh);tree.bind('<<TreeviewSelect>>',selection_changed)
    tree.bind('<Double-1>',choose);tree.bind('<Return>',choose)
    win.bind('<Escape>',lambda event:close());win.protocol('WM_DELETE_WINDOW',close)
    def resized(event):
        if event.widget is body:
            for label in (summary,hint,details):label.configure(wraplength=max(180,event.width-36))
    body.bind('<Configure>',resized,add='+')
    win.bank_tree=tree;win.search_var=query;win.open_button=button
    refresh();win.grab_set();entry.focus_set()
    return win
