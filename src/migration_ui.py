import support_report
"""Preview and apply old-bank migrations; original inputs stay read-only."""
import tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
import core,bank_migration,modern_theme

class MigrationMixin:
    def prepare_migration(self,external):
        name=external.get('bank_name') or ''
        language=name[-2:] if name.endswith(('_US','_JP')) else self.lang.get()
        self.job(lambda:bank_migration.read_old(self.cfg,external,language),self.migration_preview,'Lendo banco antigo para migração...')

    def migration_preview(self,old):
        win=tk.Toplevel(self);win.title(self.tr('Migrar banco antigo'));win.configure(bg=modern_theme.BG)
        width=min(1050,self.winfo_screenwidth()-80);height=min(720,self.winfo_screenheight()-120)
        win.geometry(f'{width}x{height}');win.minsize(min(720,width),min(480,height))
        win.transient(self)
        # Pack the fixed actions first so the growing table cannot push them offscreen.
        footer=ttk.Frame(win,padding=(18,12));footer.pack(side='bottom',fill='x')
        footer.columnconfigure(0,weight=1)
        project_name=tk.StringVar(value=old.name+' — Migrated')
        naming=ttk.Frame(footer);naming.grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,8))
        self.label(naming,'Nome do projeto').pack(side='left',padx=(0,12))
        ttk.Entry(naming,textvariable=project_name).pack(side='left',fill='x',expand=True)
        notice=tk.StringVar(value=self.tr('Após a análise, clique em Criar projeto atualizado.'))
        notice_label=ttk.Label(footer,textvariable=notice,style='Muted.TLabel',wraplength=420)
        notice_label.grid(row=1,column=0,sticky='w',padx=(0,12))
        notice_label.bind('<Configure>',lambda e:notice_label.configure(wraplength=max(180,e.width)))
        buttons=ttk.Frame(footer);buttons.grid(row=1,column=1,sticky='e')
        local_progress=ttk.Progressbar(footer,mode='indeterminate')
        local_progress.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(8,0))
        self.migration_project_name=project_name
        self.migration_window=win
        body=ttk.Frame(win,padding=18);body.pack(fill='both',expand=True)
        self.label(body,'Migrar para a referência atualizada',style='Title.TLabel').pack(anchor='w')
        ttk.Label(body,text=old.name,style='Muted.TLabel').pack(anchor='w',pady=(4,10))
        self.label(body,'Banco original atualizado',style='Muted.TLabel').pack(anchor='w')
        controls=ttk.Frame(body);controls.pack(fill='x',pady=(4,10))
        names=[name for name in self.banks if name.endswith('_'+old.language)]
        suggested=old.reference_name if old.reference_name in names else self.bank.name if self.bank and self.bank.name in names else names[0] if names else ''
        selected=tk.StringVar(value=suggested)
        choice=ttk.Combobox(controls,textvariable=selected,values=names,state='readonly',width=32)
        choice.pack(side='left',fill='x',expand=True)
        self.label(body,'Só correspondências seguras são transferidas. Entradas novas e ambíguas ficam em silêncio até você editá-las.',style='Muted.TLabel',wraplength=890).pack(anchor='w',pady=(0,10))
        summary=tk.StringVar(value='');ttk.Label(body,textvariable=summary,wraplength=890).pack(fill='x',pady=(0,8))
        frame=ttk.Frame(body);frame.pack(fill='both',expand=True)
        table=ttk.Treeview(frame,columns=('state','old','new','ids'),show='headings',selectmode='browse')
        for key,title,width in [('state','Situação',155),('old','Voz antiga',125),('new','Voz atualizada',125),('ids','CUE IDs',340)]:
            table.heading(key,text=self.tr(title));table.column(key,width=width,minwidth=60,stretch=True)
        scrollbar=ttk.Scrollbar(frame,orient='vertical',command=table.yview)
        table.configure(yscrollcommand=scrollbar.set);scrollbar.pack(side='right',fill='y');table.pack(fill='both',expand=True)
        table.tag_configure('matched',foreground=modern_theme.SUCCESS)
        table.tag_configure('new',foreground=modern_theme.MUTED)
        table.tag_configure('ambiguous',foreground=modern_theme.WARNING)
        self.label(body,'O relatório inclui os cue IDs, nomes e tags completos, além das vozes antigas sem correspondência.',style='Muted.TLabel',wraplength=890).pack(anchor='w',pady=(8,0))
        # Long descriptions wrap to the window width at every supported scale.
        def wrap_labels(event):
            if event.widget is body:
                for child in body.winfo_children():
                    if isinstance(child,ttk.Label):child.configure(wraplength=max(240,event.width-36))
        body.bind('<Configure>',wrap_labels,add='+')
        state={}
        def run(work,done,text):
            notice.set(self.tr(text));local_progress.start(12)
            def guarded():
                try:return work(),None
                except Exception as error:return None,str(error)
            def finished(result):
                if not win.winfo_exists():return
                local_progress.stop();value,error=result
                if error:
                    notice.set(self.tr('Não foi possível concluir a migração: ')+error)
                    apply_button.configure(state='normal' if state.get('report',{}).get('summary',{}).get('matched') else 'disabled')
                    support_report.show(self,error,parent=win,title=self.tr('Migrar banco antigo'))
                    return
                done(value)
            self.job(guarded,finished,text)
        def invalidate(*_):
            state.clear();apply_button.configure(state='disabled');summary.set('');table.delete(*table.get_children());notice.set(self.tr('Após a análise, clique em Criar projeto atualizado.'))
        selected.trace_add('write',invalidate)
        def analyze():
            if self.busy or not selected.get():return
            state.clear();apply_button.configure(state='disabled');target_name=selected.get()
            def work():
                target=core.Bank(self.cfg,core.Pak(self.cfg),target_name)
                return target,bank_migration.analyze(old,target)
            def done(result):
                if not win.winfo_exists() or selected.get()!=target_name:return
                target,report=result;state.update(target=target,report=report)
                table.delete(*table.get_children())
                for i,row in enumerate(report['rows']):
                    status=row['status'];source=row['source_key'] or '—'
                    table.insert('', 'end',iid=str(i),values=(self.tr({'matched':'Correspondência segura','new':'Nova entrada','ambiguous':'Revisão necessária'}[status]),source,row['target_key'],', '.join(map(str,row['cue_ids']))),tags=(status,))
                for row in report['unmatched_old']:
                    table.insert('','end',values=(self.tr('Antiga sem correspondência'),row['key'],'—',', '.join(map(str,row['cue_ids']))),tags=('ambiguous',))
                counts=report['summary']
                text=self.tr('Seguras: {matched} • Novas: {new} • Revisar: {ambiguous} • Antigas sem correspondência: {old}').format(**counts,old=len(report['unmatched_old']))
                if not old.hash_verified:text+='\n'+self.tr('Banco da ferramenta antiga: hash desatualizado; faixas HCA verificadas estruturalmente.')
                summary.set(text);apply_button.configure(state='normal' if counts['matched'] else 'disabled')
                notice.set(self.tr('Pronto para criar o projeto atualizado.' if counts['matched'] else 'Nenhuma correspondência segura. Revise o banco de referência.'))
            run(work,done,'Comparando cues com a referência atualizada...')
        def apply():
            if self.busy or not state:return
            name=project_name.get().strip()
            if not name:
                notice.set(self.tr('Informe um nome para o projeto.'));return
            target=state['target'];report=state['report'];apply_button.configure(state='disabled')
            def work():
                return bank_migration.create_project(old,target,report,lambda value:self.jobs.put(('status',self.tr('Migrando vozes: ')+value)),project_name=name)
            def done(project):
                if win.winfo_exists():win.destroy()
                self.load_bank(target.name,project=project)
                messagebox.showinfo(self.tr('Migração concluída'),self.tr('Um novo projeto foi criado com a referência atualizada. Os arquivos antigos foram preservados.')+'\n\n'+project['project_file']+'\n\n'+self.tr('Relatório: ')+project['migration']['report'],parent=self)
            run(work,done,'Migrando vozes para um novo projeto...')
        self.button(controls,'Analisar correspondências',analyze).pack(side='left',padx=(8,0))
        apply_button=self.button(buttons,'Criar projeto atualizado',apply,True);apply_button.pack(side='right');apply_button.configure(state='disabled')
        self.migration_create_btn=apply_button;self.migration_notice=notice
        self.button(buttons,'Fechar',win.destroy).pack(side='right',padx=8)
        if suggested:analyze()
        else:notice.set(self.tr('Referência atualizada não encontrada nas pastas configuradas.'))
