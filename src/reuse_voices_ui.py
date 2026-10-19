"""Pick a donor project/bank, select tags, review each target and copy safely."""
import json,winsound
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
import core,project_exchange,reuse_voices,voice_context,playback_controls
from modern_theme import BG

class ReuseVoicesMixin:
    def reuse_voices(self):
        if self.busy or not self.bank:return
        win=tk.Toplevel(self);win.title(self.tr('Copiar vozes por tags ou função'));win.configure(bg=BG);win.transient(self);win.geometry(f'{min(1120,self.winfo_screenwidth()-80)}x{min(760,self.winfo_screenheight()-100)}');win.minsize(min(850,self.winfo_screenwidth()-80),min(570,self.winfo_screenheight()-100));win.grab_set()
        self.reuse_window=win;target=self.bank
        body=ttk.Frame(win,padding=16);body.pack(fill='both',expand=True)
        self.label(body,'Copiar vozes por tags ou função',font=('Segoe UI',16,'bold')).pack(anchor='w')
        hint=tk.StringVar(value=self.tr('Escolha um projeto, pacote PAK ou banco UASSET/ACB de origem. O banco atual continua sendo o destino.'))
        ttk.Label(body,textvariable=hint,wraplength=1050,style='Muted.TLabel').pack(anchor='w',pady=(6,10))
        sourcebar=ttk.Frame(body);sourcebar.pack(fill='x')
        filebar=ttk.Frame(body);filebar.pack(fill='x',before=sourcebar,pady=(0,6))
        self.button(filebar,'Escolher projeto de origem',lambda:load_project()).pack(side='left',padx=(0,8))
        self.reuse_external_button=self.button(filebar,'Escolher PAK / UASSET',lambda:self.open_external(on_source=load_external,parent=win))
        self.reuse_external_button.pack(side='left')
        names=[name for name in self.banks if name.endswith('_'+target.language)]
        labels={self.character_names.get(core.character_id(name),name)+' • '+name:name for name in names}
        game=ttk.Combobox(sourcebar,values=list(labels),state='readonly');game.pack(side='left',fill='x',expand=True)
        self.button(sourcebar,'Usar banco do jogo',lambda:load_game()).pack(side='left',padx=8)
        modebar=ttk.Frame(body);modebar.pack(fill='x',pady=(8,0))
        self.label(modebar,'Copiar por:').pack(side='left',padx=(0,8))
        mode_labels={self.tr('Tags'):'tags',self.tr('Funções'):'functions'}
        mode_choice=ttk.Combobox(modebar,values=list(mode_labels),state='readonly',width=22);mode_choice.pack(side='left');mode_choice.current(0);self.reuse_mode_choice=mode_choice
        options=ttk.Frame(body);options.pack(fill='x',pady=10)
        include=tk.BooleanVar(value=False);overwrite=tk.BooleanVar(value=True)
        ttk.Checkbutton(options,text=self.tr('Incluir vozes originais da origem'),variable=include,command=lambda:fill_tags()).pack(side='left')
        ttk.Checkbutton(options,text=self.tr('Substituir vozes já customizadas no destino'),variable=overwrite,command=lambda:refresh()).pack(side='left',padx=16)
        bottom=ttk.Frame(body);bottom.pack(side='bottom',fill='x',pady=(10,0))
        self.button(bottom,'Cancelar',lambda:close()).pack(side='right')
        copy_button=self.button(bottom,'Copiar vozes escolhidas',lambda:apply(),True);copy_button.pack(side='right',padx=8);copy_button.configure(state='disabled');self.reuse_copy_button=copy_button
        counts=tk.StringVar();ttk.Label(bottom,textvariable=counts,style='Muted.TLabel').pack(side='left')
        panes=ttk.Panedwindow(body,orient='horizontal');panes.pack(fill='both',expand=True)
        left=ttk.Frame(panes);right=ttk.Frame(panes);panes.add(left,weight=1);panes.add(right,weight=3)
        selection_heading=tk.StringVar(value=self.tr('Tags de origem (seleção múltipla)'))
        ttk.Label(left,textvariable=selection_heading).pack(anchor='w',pady=(0,5))
        search=tk.StringVar();ttk.Entry(left,textvariable=search).pack(fill='x',pady=(0,5))
        tagsframe=ttk.Frame(left);tagsframe.pack(fill='both',expand=True)
        tagtable=ttk.Treeview(tagsframe,columns=('label','count'),show='headings',selectmode='extended');tagtable.heading('label',text=self.tr('Tag / função'));tagtable.heading('count',text=self.tr('Vozes'));tagtable.column('label',width=270);tagtable.column('count',width=45,stretch=False);tagtable.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(tagsframe,command=tagtable.yview);scroll.pack(side='right',fill='y');tagtable.configure(yscrollcommand=scroll.set);self.reuse_tag_table=tagtable
        selection_hint=tk.StringVar(value=self.tr('Use Ctrl ou Shift para selecionar várias tags. Uma voz compartilhada só entra quando todas as suas tags estão selecionadas.'))
        ttk.Label(left,textvariable=selection_hint,wraplength=280,style='Muted.TLabel').pack(anchor='w',pady=8)
        self.label(right,'Revisar origem → destino').pack(anchor='w',pady=(0,5))
        tableframe=ttk.Frame(right);tableframe.pack(fill='both',expand=True)
        table=ttk.Treeview(tableframe,columns=('target','function','source','status'),show='headings',selectmode='browse');self.reuse_review_table=table
        for key,title,width in [('target','Voz de destino',155),('function','Função',235),('source','Voz de origem',155),('status','Situação',170)]:table.heading(key,text=self.tr(title));table.column(key,width=width,minwidth=55)
        table.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(tableframe,command=table.yview);scroll.pack(side='right',fill='y');table.configure(yscrollcommand=scroll.set)
        chooser=ttk.Frame(right);chooser.pack(fill='x',pady=(8,0))
        choice=ttk.Combobox(chooser,state='readonly');choice.pack(side='left',fill='x',expand=True);self.reuse_source_choice=choice
        listen_button=self.button(chooser,'Ouvir origem',lambda:listen());listen_button.pack(side='left',padx=6)
        state={'mode':'tags','bank':None,'data':None,'rows':[],'choices':{},'tags':{},'tag_ids':{},'selection':set(),'updating':False,'choice_labels':{}}
        self.reuse_state=state
        statuses={'matched':'Correspondência encontrada','choose':'Escolha uma voz','protected':'Customizada protegida','shared_unselected':'Selecione todas as tags','unmatched':'Sem correspondência'}
        def close():
            if self.busy:
                self.status.set("Aguarde a operação terminar antes de fechar.");return
            self.stop();win.destroy()
        win.protocol('WM_DELETE_WINDOW',close)
        def loaded(result):
            if not win.winfo_exists():return
            bank,data=result
            import session_features
            manual=session_features.clean_manual(data.get('manual_identifications',{}),bank)
            for row in bank.rows:
                row.pop('_manual',None)
                if row['key'] in manual:row['_manual']=manual[row['key']]
            state.update(bank=bank,data=data,choices={},selection=set())
            hint.set((data.get('project_name') or bank.name)+' → '+target.name)
            fill_tags()
        def load_project():
            if self.busy:return
            path=filedialog.askopenfilename(parent=win,title=self.tr('Escolher projeto de origem'),initialdir=core.APP/'Projects',filetypes=[(self.tr('Projeto do Voice Studio'),'project.json *.szvs')])
            if not path:return
            def work():
                manifest=project_exchange.unpack(path) if Path(path).suffix.lower()=='.szvs' else None
                if manifest:data=manifest['project']
                else:data=json.loads(core.owned(path).read_text(encoding='utf-8'))
                bank=core.Bank(self.cfg,core.Pak(self.cfg) if not data.get('source') else None,data['bank'],data.get('source'))
                if manifest and project_exchange.layout(bank)!=manifest['layout']:
                    raise ValueError('O banco local tem Cue IDs/tags diferentes. Atualize ou migre as referências antes de abrir este projeto.')
                if bank.external:
                    reference=None
                    try:
                        import bank_migration
                        name=bank_migration.infer_reference(bank)
                        if name:reference=core.Bank(self.cfg,core.Pak(self.cfg),name)
                    except (OSError,ValueError,KeyError):pass
                    core.classify_imported_audio(bank,reference)
                import bank_version
                data,_=bank_version.reconcile(data,bank)
                return bank,data
            include.set(False);self.job(work,loaded,'Lendo banco de origem...')
        def load_external(external):
            if self.busy:return
            include.set(False)
            def work():
                bank=core.import_external_bank(self.cfg,**external)
                reference=None
                try:
                    import bank_migration
                    name=bank_migration.infer_reference(bank)
                    if name:reference=core.Bank(self.cfg,core.Pak(self.cfg),name)
                except (OSError,ValueError,KeyError):pass
                try:core.classify_imported_audio(bank,reference)
                except (ValueError,KeyError,IndexError):core.classify_imported_audio(bank,None)
                return bank,{'bank':bank.name,'source':bank.source,'replacements':{},'gains':{},'variations':{}}
            self.job(work,loaded,'Lendo banco de origem...')

        def load_game():
            if self.busy or game.get() not in labels:return
            name=labels[game.get()];include.set(True)
            self.job(lambda:(core.Bank(self.cfg,core.Pak(self.cfg),name),{'bank':name,'replacements':{},'gains':{},'variations':{}}),loaded,'Lendo banco de origem...')
        def change_mode(event=None):
            state.update(mode=mode_labels[mode_choice.get()],choices={},selection=set())
            is_function=state['mode']=='functions'
            selection_heading.set(self.tr('Funções de origem (seleção múltipla)' if is_function else 'Tags de origem (seleção múltipla)'))
            selection_hint.set(self.tr('Use Ctrl ou Shift para selecionar várias funções. Uma voz compartilhada só entra quando todas as suas funções estão selecionadas.' if is_function else 'Use Ctrl ou Shift para selecionar várias tags. Uma voz compartilhada só entra quando todas as suas tags estão selecionadas.'))
            tagtable.heading('label',text=self.tr('Função' if is_function else 'Tag / função'))
            fill_tags()
        def tag_label(token,bank):
            language=self.function_language.get()
            if token.startswith('description:'):
                import compact_functions
                text=token.split(':',1)[1];return self.translator.display(compact_functions.function(text,language))
            if token.startswith('manual-label:'):
                row=next(row for row in bank.rows if token in reuse_voices.functions(row))
                return self.tr('Manual: ')+row['_manual']['label']
            if token.startswith('user:'):
                import user_voice_functions
                rule=next(rule for rule in user_voice_functions.rules() if rule['key']==token[5:])
                import compact_functions
                return compact_functions.manual_label(rule['label'],language) if state['mode']=='functions' else (self.tr('Manual: ') if rule.get('source')!='cue_family_correlation' else self.tr('Grupo provável: '))+self.tr(rule['label'])
            if token.startswith('action:'):
                import compact_functions
                return compact_functions.action(token[7:],language) if state['mode']=='functions' else voice_context.context_action_text(token[7:],language)
            if token.startswith('function:'):
                tag=token.split(':',1)[1]
                # Existing catalog is keyed by English descriptions, so prefer a
                # row's verified localized description plus the original PTN tag.
                row=next(row for row in bank.rows if token in reuse_voices.tags(row))
                return self.function_text(row)+' • '+tag
            if token.startswith('interaction:'):
                _,event,other,order=token.split(':',3)
                label=voice_context.event_label(event,self.function_language.get())
                return label+' • '+(self.character_names.get(other,other) or '—')+(f' • {order}' if order!='0' else '')
            if token.startswith('usage:'):return voice_context.usage_label(token[6:],self.function_language.get())
            return 'Emote — AppealVoice'
        def fill_tags(*args):
            bank=state['bank']
            if bank is None:return
            state['updating']=True
            counts_by_tag={}
            for row in bank.rows:
                if reuse_voices.eligible(bank,state['data'],row,include.get()):
                    for token in reuse_voices.semantics(row,state['mode']):counts_by_tag[token]=counts_by_tag.get(token,0)+1
            tagtable.delete(*tagtable.get_children());state['tag_ids']={};query=search.get().casefold()
            for i,(token,count) in enumerate(sorted(counts_by_tag.items())):
                label=tag_label(token,bank)
                if query not in (label+' '+token).casefold():continue
                key=str(i);state['tag_ids'][key]=token;tagtable.insert('','end',iid=key,values=(label,count))
                if token in state['selection']:tagtable.selection_add(key)
            state['updating']=False;refresh()
        def tag_selected(event=None):
            if state['updating']:return
            visible=set(state['tag_ids'].values());selected={state['tag_ids'][key] for key in tagtable.selection()}
            state['selection']=(state['selection']-visible)|selected;refresh()
        def refresh():
            if state['bank'] is None:return
            previous=table.selection();table.delete(*table.get_children())
            state['rows']=reuse_voices.plan(state['bank'],state['data'],target,self.project_document(),state['selection'],include.get(),overwrite.get(),mode=state['mode'])
            for item in state['rows']:
                key=item['target_key'];source_key=state['choices'].get(key,item['source_key'])
                if source_key not in item['candidates']:source_key=None
                row=target.wave_rows[key]
                table.insert('','end',iid=key,values=(row['filename'],self.function_text(row),state['bank'].wave_rows[source_key]['filename'] if source_key else '—',self.tr('Voz escolhida' if key in state['choices'] and source_key else ('Selecione todas as funções' if state['mode']=='functions' and item['status']=='shared_unselected' else 'Revisão necessária' if item['status']=='interaction_review' else statuses[item['status']]))))
            if previous and table.exists(previous[0]):table.selection_set(previous[0])
            elif table.get_children():table.selection_set(table.get_children()[0])
            update_counts();review_selection()
        def resolved():
            mapping={}
            for item in state['rows']:
                value=state['choices'].get(item['target_key'],item['source_key'])
                if value in item['candidates']:mapping[item['target_key']]=value
            return mapping
        def update_counts():
            mapping=resolved();counts.set(self.tr('Vozes escolhidas: ')+str(len(mapping))+' / '+str(len(state['rows'])))
            copy_button.configure(state='normal' if mapping and not self.busy else 'disabled')
        def review_selection(event=None):
            keys=table.selection();state['choice_labels']={}
            if not keys:return
            item=next(item for item in state['rows'] if item['target_key']==keys[0])
            for n,key in enumerate(item['candidates']):
                row=state['bank'].wave_rows[key];gain=state['data'].get('gains',{}).get(key,0);variation=state['data'].get('variations',{}).get(key,1)
                label=f"{n+1}. {row['filename']} • Cue "+', '.join(map(str,row['cue_ids']))+f' • {gain:+.1f} dB • v{variation}'
                if item['status']=='interaction_review':label+=' • '+' / '.join(tag_label(token,state['bank']) for token in sorted(reuse_voices.tags(row)) if token.startswith('interaction:'))
                state['choice_labels'][label]=key
            state['choice_labels'][self.tr('Não copiar esta voz')]=None;choice.configure(values=list(state['choice_labels']))
            current=state['choices'].get(keys[0],item['source_key']);choice.set(next((label for label,value in state['choice_labels'].items() if value==current),''))
        def choose(event=None):
            keys=table.selection()
            if keys and choice.get() in state['choice_labels']:
                state['choices'][keys[0]]=state['choice_labels'][choice.get()];refresh()
        def listen():
            source_key=state['choice_labels'].get(choice.get())
            if source_key is None or self.busy:return
            bank=state['bank'];row=bank.wave_rows[source_key]
            def done(path):
                if win.winfo_exists():playback_controls.start(self,path,listen_button)
            def work():
                source=state['data'].get('replacements',{}).get(source_key) or bank.original(row)
                import uuid
                path=core.APP/'Cache/ReusePreview'/(uuid.uuid4().hex+'.wav')
                core.normalize_wav(source,path,row['rate'],row['channels'],row['samples'],state['data'].get('gains',{}).get(source_key,0),state['data'].get('variations',{}).get(source_key,1))
                return path
            self.job(work,done,'Preparando áudio de origem...')
        def apply():
            if self.busy:return
            mapping=resolved()
            if not mapping:return
            copy_button.configure(state='disabled')
            def work():
                with self.level_lock:return reuse_voices.copy(state['bank'],state['data'],target,self.project,mapping,lambda text:self.jobs.put(('status',text)),mode=state['mode'])
            def done(result):
                for key,path in result['replacements'].items():
                    self.replacements[key]=path;self.gains.pop(key,None);self.variations.pop(key,None)
                self.gains.update(result['gains']);self.variations.update(result['variations'])
                self.level_signature=None;self.fill_rows();self.select();close()
                self.status.set(self.tr('Vozes reaproveitadas: ')+str(len(result['replacements']))+'. '+self.tr('Clique em Salvar projeto para guardar os ajustes.'))
            self.job(work,done,'Copiando vozes para o banco atual...',edit_label='Copiar vozes por função' if state['mode']=='functions' else 'Copiar vozes por tag')
        mode_choice.bind('<<ComboboxSelected>>',change_mode);self.reuse_change_mode=change_mode
        tagtable.bind('<<TreeviewSelect>>',tag_selected);table.bind('<<TreeviewSelect>>',review_selection);choice.bind('<<ComboboxSelected>>',choose);search.trace_add('write',fill_tags)
        # Expose normal callbacks for automated regression checks.
        self.reuse_load=loaded;self.reuse_refresh=refresh;self.reuse_load_external=load_external
