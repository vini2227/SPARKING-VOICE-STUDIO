import playback_controls
"""Sharing, review before export, and explicit conflict choices."""
import json,shutil,uuid,winsound
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import core,project_exchange
from modern_theme import BG

class ProjectExchangeMixin:
    def project_tools(self):
        import window_toggle
        if window_toggle.existing(self,'project_tools_window'):return
        if self.busy:return
        win=tk.Toplevel(self);self.project_tools_window=win;win.title(self.tr('Ferramentas de Projeto'));win.configure(bg=BG);win.transient(self)
        body=ttk.Frame(win,padding=20);body.pack(fill='both',expand=True)
        self.label(body,'Ferramentas de Projeto',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(0,12))
        self.label(body,'Envie o projeto editável para outros modders. Mescle substituições do mesmo banco e escolha as versões em conflito.',wraplength=490,style='Muted.TLabel').pack(anchor='w',pady=(0,16))
        def action(fn):win.destroy();fn()
        for text,fn,needs_bank in [('Compartilhar projeto',self.share_project,True),('Abrir projeto compartilhado',self.import_shared_project,False),('Mesclar projetos neste banco',self.merge_projects,True),('Copiar vozes por tags ou função',self.reuse_voices,True)]:
            button=self.button(body,text,lambda fn=fn:action(fn));button.pack(fill='x',pady=5)
            if needs_bank and not self.bank:button.configure(state='disabled')
        self.button(body,'Fechar',win.destroy).pack(anchor='e',pady=(16,0))

    def share_project(self,destination=None):
        if self.busy or not self.bank:return
        destination=destination or filedialog.asksaveasfilename(parent=self,title=self.tr('Compartilhar projeto'),initialdir=core.APP/'Exports',initialfile=self.project_name+'.szvs',defaultextension='.szvs',filetypes=[(self.tr('Projeto do Voice Studio'),'*.szvs')])
        if not destination:return
        data=self.project_document();bank=self.bank
        def done(path):
            self.status.set(self.tr('Projeto compartilhado: ')+str(path))
            messagebox.showinfo(self.tr('Compartilhar projeto'),self.tr('O pacote contém as substituições, ganhos e variações atuais. Quem receber pode abrir ou mesclar pelo menu Projetos. A sessão local continua aguardando Salvar projeto.')+'\n\n'+str(path),parent=self)
        self.job(lambda:project_exchange.pack(bank,data,destination),done,self.tr('Preparando projeto compartilhado...'))

    def import_shared_project(self,path=None):
        if self.busy:return
        path=path or filedialog.askopenfilename(parent=self,title=self.tr('Abrir projeto compartilhado'),filetypes=[(self.tr('Projeto do Voice Studio'),'*.szvs')])
        if not path:return
        def done(manifest):
            data=manifest['project']
            if not data.get('source') and data['bank'] not in self.banks:self.fail(self.tr('Banco do projeto não encontrado.'));return
            self.load_bank(data['bank'],data)
        def work():
            manifest=project_exchange.unpack(path);data=manifest['project']
            bank=core.Bank(self.cfg,core.Pak(self.cfg) if not data.get('source') else None,data['bank'],data.get('source'))
            if project_exchange.layout(bank)!=manifest['layout']:
                raise ValueError('O banco local tem Cue IDs/tags diferentes. Atualize ou migre as referências antes de abrir este projeto.')
            return manifest
        self.job(work,done,self.tr('Abrindo projeto compartilhado...'))

    def merge_projects(self,paths=None):
        if self.busy or not self.bank:return
        paths=paths or filedialog.askopenfilenames(parent=self,title=self.tr('Escolha os projetos para mesclar'),filetypes=[(self.tr('Projetos do Voice Studio'),'*.szvs project.json'),(self.tr('Projeto compartilhado'),'*.szvs'),(self.tr('Projeto salvo'),'project.json')])
        if not paths:return
        bank=self.bank;data=self.project_document();descriptor=project_exchange.layout(bank)
        def work():
            current={'name':self.project_name+' ('+self.tr('Atual')+')','layout':descriptor,'edits':project_exchange.edits(bank,data)}
            projects=[current]
            for path in paths:
                if Path(path).suffix.lower()=='.szvs':
                    manifest=project_exchange.unpack(path)
                    projects.append({'name':manifest['project'].get('project_name') or Path(path).stem,'layout':manifest['layout'],'edits':manifest['edits']})
                else:
                    path=core.owned(path);document=json.loads(path.read_text(encoding='utf-8'))
                    other=core.Bank(self.cfg,core.Pak(self.cfg) if not document.get('source') else None,document['bank'],document.get('source'))
                    projects.append({'name':document.get('project_name') or path.parent.name,'layout':project_exchange.layout(other),'edits':project_exchange.edits(other,document)})
            return project_exchange.merge_plan(descriptor,projects)
        self.job(work,self.review_merge,self.tr('Comparando projetos para mesclar...'))

    def review_merge(self,plan):
        win=tk.Toplevel(self);win.title(self.tr('Revisar mescla'));win.configure(bg=BG);win.transient(self);win.geometry('920x610');win.minsize(700,460)
        win.grab_set();self.merge_window=win;body=ttk.Frame(win,padding=20);body.pack(fill='both',expand=True)
        self.label(body,'Revisar mescla',font=('Segoe UI',16,'bold')).pack(anchor='w')
        text=f"{len(plan['automatic'])} "+self.tr('vozes sem conflito')+f" • {len(plan['conflicts'])} "+self.tr('conflitos')+f" • {plan['duplicates']} "+self.tr('substituições idênticas')
        self.label(body,text,style='Muted.TLabel').pack(anchor='w',pady=(8,12))
        self.label(body,'Vozes originais não apagam substituições. Ganhos e variações diferentes geram conflito. Importadas com comparação incerta não entram automaticamente na mescla; revise essas vozes antes de compartilhar.',wraplength=850,style='Muted.TLabel').pack(anchor='w')
        bottom=ttk.Frame(body);bottom.pack(side='bottom',fill='x',pady=(15,0))
        self.button(bottom,'Cancelar',win.destroy).pack(side='right')
        choices={};selected=tk.StringVar();index={};preview=tk.StringVar()
        def apply():
            if len(choices)!=len(plan['conflicts']):return
            resolved=dict(plan['automatic']);resolved.update({key:value for key,value in choices.items() if value is not None})
            try:
                before=self.history.begin()
                replacements=dict(self.replacements);gains=dict(self.gains);variations=dict(self.variations)
                for key,item in resolved.items():
                    if item['origin']==0:continue
                    dest=self.project/'Replacements'/(key+'_'+uuid.uuid4().hex+'.wav');dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(item['path'],dest);replacements[key]=str(dest)
                    if item['gain']:gains[key]=item['gain']
                    else:gains.pop(key,None)
                    if item['variation']!=1:variations[key]=item['variation']
                    else:variations.pop(key,None)
                self.stop();self.replacements=replacements;self.gains=gains;self.variations=variations
                self.level_signature=None;self.fill_rows();self.select();win.destroy()
                self.history.finish(before,'Mesclar projetos')
                self.status.set(self.tr('Mescla aplicada. Revise as vozes e clique em Salvar projeto.'))
            except Exception as error:self.fail(str(error))
        apply_button=self.button(bottom,'Aplicar mescla',apply,True);apply_button.pack(side='right',padx=8)
        if plan['conflicts']:apply_button.configure(state='disabled')
        self.merge_apply_button=apply_button
        tableframe=ttk.Frame(body);tableframe.pack(fill='both',expand=True,pady=(12,8))
        table=ttk.Treeview(tableframe,columns=('cue','function','choice'),show='headings',selectmode='browse');self.merge_table=table
        for key,title,width in [('cue','Voz / Cue IDs',185),('function','Função',280),('choice','Versão escolhida',290)]:table.heading(key,text=self.tr(title));table.column(key,width=width)
        table.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(tableframe,command=table.yview);scroll.pack(side='right',fill='y');table.configure(yscrollcommand=scroll.set)
        for key in plan['conflicts']:
            row=self.bank.wave_rows[key];table.insert('','end',iid=key,values=(key+' / '+', '.join(map(str,row['cue_ids'])),self.function_text(row),self.tr('Escolha uma versão')))
        bar=ttk.Frame(body);bar.pack(fill='x');combo=ttk.Combobox(bar,textvariable=selected,state='readonly');combo.pack(side='left',fill='x',expand=True)
        def selection(event=None):
            keys=table.selection()
            if not keys:return
            key=keys[0];index.clear()
            for n,item in enumerate(plan['conflicts'][key]):index[f"{n+1}. {item['name']} • {item['gain']:+.1f} dB • v{item['variation']}"]=item
            index[self.tr('Manter voz atual sem adicionar')]=None
            combo.configure(values=list(index));selected.set(next((label for label,value in index.items() if key in choices and value==choices[key]),''))
        def chosen(event=None):
            keys=table.selection()
            if not keys or selected.get() not in index:return
            choices[keys[0]]=index[selected.get()];table.set(keys[0],'choice',selected.get())
            if len(choices)==len(plan['conflicts']):apply_button.configure(state='normal')
        def listen():
            item=index.get(selected.get())
            if item:playback_controls.start(self,item['path'],listen_button)
        listen_button=self.button(bar,'Ouvir WAV',listen);listen_button.pack(side='left',padx=8)
        table.bind('<<TreeviewSelect>>',selection);combo.bind('<<ComboboxSelected>>',chosen)
        win.bind('<Destroy>',lambda event:self.stop() if event.widget is win else None,add='+')
        if plan['conflicts']:table.selection_set(next(iter(plan['conflicts'])));selection()
        else:table.insert('','end',values=('—',self.tr('Todas as substituições podem ser combinadas.'),'—'));combo.configure(state='disabled')

    def confirm_export_summary(self):
        import export_review
        return export_review.confirm(self)
