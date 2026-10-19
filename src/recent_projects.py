"""Project browser using saved manifests; no separate stale recent-path registry."""
import json
from pathlib import Path
from project_directory_watch import ProjectDirectoryWatch
from datetime import datetime,timezone,timedelta
import tkinter as tk
from tkinter import ttk
import core,modern_theme
from project_names import project_parts

def usage_count(data):
    try:return max(0,int(data.get('usage_count',0)))
    except (ValueError,TypeError,OverflowError):return 0

def sorted_projects(projects,mode='recent'):
    def key(item):
        recent=(-item['modified'],item['name'].casefold(),item['path'])
        return (-item.get('uses',0),)+recent if mode=='used' else recent
    return sorted(projects,key=key)

def scan_projects():
    projects=[];skipped=0
    for file in (core.APP/'Projects').glob('*/project.json'):
        try:
            file=core.owned(file)
            data=json.loads(file.read_text(encoding='utf-8'))
            bank=data.get('bank')
            if not isinstance(bank,str) or not bank:raise ValueError('Missing bank')
            name=data.get('project_name') or file.parent.name
            if not isinstance(name,str):raise ValueError('Invalid name')
            parts=project_parts(file.parent)
            number=parts['number'] if parts else '—'
            modified=file.stat().st_mtime
            projects.append({'path':str(file),'number':number,'name':name,'bank':bank,'modified':modified,'uses':usage_count(data),
                             'date':datetime.fromtimestamp(modified,timezone(timedelta(hours=-3))).strftime('%d/%m/%Y %H:%M')})
        except (OSError,ValueError,TypeError,AttributeError):skipped+=1
    return sorted_projects(projects),skipped

class RecentProjectsMixin:
    def recent_projects(self):
        import window_toggle
        if window_toggle.existing(self,'recent_window'):return
        if self.busy:return
        win=tk.Toplevel(self);self.recent_window=win;win.title(self.tr('Projetos recentes'))
        win.configure(bg=modern_theme.BG)
        width=min(980,self.winfo_screenwidth()-80);height=min(590,self.winfo_screenheight()-100)
        win.geometry(f'{width}x{height}');win.minsize(min(700,width),min(400,height));win.transient(self)
        body=ttk.Frame(win,padding=20);body.pack(fill='both',expand=True)
        self.label(body,'Projetos recentes',font=('Segoe UI',16,'bold')).pack(anchor='w')
        self.label(body,'Continue de onde parou. Organize por última edição ou pelos projetos que você mais abre.',style='Muted.TLabel',wraplength=850).pack(anchor='w',pady=(4,14))
        search=tk.StringVar();self.recent_search=search
        self.label(body,'Buscar número, projeto, personagem ou banco',style='Muted.TLabel').pack(anchor='w')
        searchbar=ttk.Frame(body);searchbar.pack(fill='x',pady=(4,12))
        entry=ttk.Entry(searchbar,textvariable=search);entry.pack(side='left',fill='x',expand=True,padx=(0,12));entry.focus_set()
        preference=core.APP/'recent_projects_preferences.json'
        try:mode=json.loads(preference.read_text(encoding='utf-8')).get('sort','recent')
        except (OSError,ValueError,AttributeError):mode='recent'
        options={'recent':self.tr('Mais recentes'),'used':self.tr('Mais utilizados')}
        sort=tk.StringVar(value=options.get(mode,options['recent']));self.recent_sort=sort
        choice=ttk.Combobox(searchbar,textvariable=sort,values=list(options.values()),state='readonly',width=19)
        choice.pack(side='right');self.recent_sort_choice=choice
        tableframe=ttk.Frame(body);tableframe.pack(fill='both',expand=True)
        style=ttk.Style(self);style.layout('Recent.Treeview',[('Treeview.treearea',{'sticky':'nswe'})]);style.configure('Recent.Treeview',background=modern_theme.PANEL,fieldbackground=modern_theme.PANEL,rowheight=34,borderwidth=0)
        style.configure('Recent.Treeview.Heading',background=modern_theme.CARD,foreground=modern_theme.MUTED,font=('Segoe UI',9,'bold'),padding=(10,9),relief='flat');style.layout('Recent.Treeview.Heading',[('Treeheading.padding',{'sticky':'nswe','children':[('Treeheading.text',{'sticky':'we'})]})]);style.map('Recent.Treeview',background=[('selected',modern_theme.SELECTED)],foreground=[('selected',modern_theme.FG)])
        table=ttk.Treeview(tableframe,style='Recent.Treeview',height=6,columns=('number','name','character','bank','date','uses'),show='headings',selectmode='browse')
        self.recent_table=table
        for key,title,size in [('number','Nº',80),('name','Projeto',220),('character','Personagem base',185),('bank','Banco',185),('date','Última edição',140),('uses','Usos',55)]:
            table.heading(key,text=self.tr(title));table.column(key,width=size,minwidth=50 if key=='uses' else 70,stretch=key in ('name','character'))
        table.pack(side='left',fill='both',expand=True)
        scrollbar=ttk.Scrollbar(tableframe,orient='vertical',command=table.yview);scrollbar.pack(side='right',fill='y');table.configure(yscrollcommand=scrollbar.set)
        table.tag_configure('alternate',background=modern_theme.ALTERNATE)
        caption=tk.StringVar(value=self.tr('Carregando projetos...'))
        summary=ttk.Label(body,textvariable=caption,style='Muted.TLabel')
        buttons=ttk.Frame(body);buttons.pack(side='bottom',fill='x',before=tableframe)
        summary.pack(side='bottom',anchor='w',pady=(10,6),before=tableframe)
        state={'projects':[],'visible':{},'skipped':0}
        self.refresh_recent_projects=lambda:filter_projects() if win.winfo_exists() else None
        def selection_changed(event=None):
            selected=table.selection()
            continue_button.configure(state='normal' if selected and not self.busy else 'disabled')
        def filter_projects(*args):
            if not win.winfo_exists():return
            previous=table.selection();previous=previous[0] if previous else None
            scroll=table.yview()[0]
            table.delete(*table.get_children());state['visible']={}
            query=search.get().casefold().strip()
            mode=next((key for key,value in options.items() if value==sort.get()),'recent')
            for item in sorted_projects(state['projects'],mode):
                character=self.character_names.get(core.character_id(item['bank']),core.character_id(item['bank']) or '—')
                if query not in (' '.join((item.get('number','—'),item['name'],character,item['bank']))).casefold():continue
                key=item['path'];state['visible'][key]=item
                table.insert('', 'end',iid=key,values=(item.get('number','—'),item['name'],self.translator.display(character),item['bank'],item['date'],item.get('uses',0)),tags=('alternate',) if len(state['visible'])%2==0 else ())
            visible=table.get_children()
            if visible:table.selection_set(previous if previous in visible else visible[0])
            caption.set(self.tr('Nenhum projeto salvo ainda. Abra um banco para começar.') if not state['projects'] else self.tr('Nenhum projeto encontrado.') if not visible else self.tr('Projetos exibidos: ')+str(len(visible)))
            if state['skipped']:caption.set(caption.get()+' • '+self.tr('Projetos que não puderam ser lidos: ')+str(state['skipped']))
            table.yview_moveto(scroll)
            selection_changed()
        def continue_selected(event=None):
            selected=table.selection()
            if self.busy or not selected:return
            item=state['visible'].get(selected[0])
            if item and not Path(item['path']).is_file():
                watcher.refresh();return
            if item:win.destroy();self.open_project_path(item['path'])
        def browse():
            if self.busy:return
            win.destroy();self.open_project()
        self.button(buttons,'Procurar projeto...',browse).pack(side='left')
        self.button(buttons,'Abrir pasta dos projetos',self.open_projects_folder).pack(side='left',padx=(8,0))
        self.button(buttons,'Fechar',win.destroy).pack(side='right')
        continue_button=self.button(buttons,'Continuar projeto',continue_selected,True);continue_button.pack(side='right',padx=8);continue_button.configure(state='disabled')
        self.recent_continue_button=continue_button
        table.bind('<<TreeviewSelect>>',selection_changed);table.bind('<Double-1>',continue_selected);table.bind('<Return>',continue_selected)
        win.bind('<Escape>',lambda event:win.destroy());search.trace_add('write',filter_projects)
        def change_sort(event=None):
            filter_projects()
            mode=next((key for key,value in options.items() if value==sort.get()),'recent')
            core.write_json(preference,{'sort':mode})
        choice.bind('<<ComboboxSelected>>',change_sort)

        def refresh_language():
            current=next((key for key,value in options.items() if value==sort.get()),'recent')
            options.clear();options.update({'recent':self.tr('Mais recentes'),'used':self.tr('Mais utilizados')})
            choice.configure(values=list(options.values()));sort.set(options[current])
            for key,title in [('number','Nº'),('name','Projeto'),('character','Personagem base'),('bank','Banco'),('date','Última edição'),('uses','Usos')]:
                table.heading(key,text=self.tr(title))
            filter_projects()
        win._refresh_language=refresh_language

        def loaded(result):
            if not win.winfo_exists():return
            state['projects'],state['skipped']=result;filter_projects()
        watcher=ProjectDirectoryWatch(win,core.APP/'Projects',scan_projects,loaded)
        win.bind('<Destroy>',lambda event:watcher.close() if event.widget is win else None,add='+')
        win.bind('<FocusIn>',lambda event:watcher.refresh() if event.widget is win else None,add='+')
