"""Asynchronous official names and refresh after installed container changes."""
import struct
import threading
import live_voice_references
import core,game_characters,game_installation,current_bank_identity,bank_version

def install(Studio):
    def start_names(self):
        self.character_catalog_generation=getattr(self,'character_catalog_generation',0)+1
        generation=self.character_catalog_generation;cfg=dict(self.cfg);language=self.translator.language
        self.character_names=game_characters.bundled(language)
        game_characters.activate({'language':language,'names':self.character_names})
        self.fill_banks()
        if self.bank:current_bank_identity.update(self,self.bank)
        def worker():
            try:data,error=game_characters.load(cfg,language),None
            except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error) as exc:data,error=None,str(exc)
            self.jobs.put(('character_names',(generation,data,error)))
        threading.Thread(target=worker,daemon=True).start()
    Studio.start_character_catalog=start_names

    def finish_names(self,payload):
        generation,data,error=payload
        if generation!=getattr(self,'character_catalog_generation',0):return
        if data:
            if data.get('identity')!=game_installation.identity(self.cfg):return
            if data['identity']!=getattr(self,'installed_game_identity',None):self.refresh_installed_game()
            self.character_names=game_characters.bundled(self.translator.language)
            self.character_names.update(data['names'])
            game_characters.activate(dict(data,names=self.character_names))
        else:
            self.character_names=game_characters.bundled(self.translator.language)
            game_characters.activate({'language':self.translator.language,'names':self.character_names})
            if self.cfg.get('game'):self.status.set(self.tr('Não foi possível ler os nomes oficiais do jogo: ')+(error or '—'))
        self.fill_banks();self.refresh_function_choices();self.fill_rows()
        if hasattr(self,"summary_flow"):self.summary_flow.schedule()
        if self.bank:current_bank_identity.update(self,self.bank)
        if self.tree.selection():self.select()
        refresh=getattr(self,'refresh_recent_projects',None)
        if refresh:refresh()
    Studio.finish_character_catalog=finish_names

    old_init=Studio.__init__
    def init(self,*args,**kwargs):
        old_init(self,*args,**kwargs)
        self.installed_game_identity=game_installation.identity(self.cfg)
        self.installed_reference_token=live_voice_references.token(self.cfg)
        self.game_refresh_pending=False;self.game_watch_after=None
        self.after(300,self.start_character_catalog)
        def check():
            self.game_watch_after=None
            if self._destroyed:return
            if not self.busy:
                try:identity=game_installation.identity(self.cfg)
                except OSError:identity=self.installed_game_identity
                if identity!=self.installed_game_identity or live_voice_references.token(self.cfg)!=self.installed_reference_token:self.refresh_installed_game()
            if not self._destroyed:self.game_watch_after=self.after(60000,check)
        self.game_watch_after=self.after(15000,check)
        def destroy(event):
            if event.widget is self and self.game_watch_after:
                try:self.after_cancel(self.game_watch_after)
                except Exception:pass
                self.game_watch_after=None
        self.bind('<Destroy>',destroy,add='+')
    Studio.__init__=init

    def refresh_game(self):
        if self.game_refresh_pending:return
        cfg=dict(self.cfg);identity=game_installation.identity(cfg);self.game_refresh_pending=True
        open_banks=[bank for bank in (self.bank,self.reference_bank) if bank is not None]
        reference_token=live_voice_references.token(cfg)
        def worker():
            try:
                result,error=core.available_banks(cfg),None
                import live_voice_references
                for bank in open_banks:
                    try:live_voice_references.contexts(cfg,bank.name,bank.acb)
                    except (OSError,ValueError,KeyError,IndexError,TypeError,struct.error):pass
            except (OSError,ValueError) as exc:result,error=None,str(exc)
            self.jobs.put(('game_inventory',(identity,cfg.get('game'),result,error,reference_token)))
        threading.Thread(target=worker,daemon=True).start()
    Studio.refresh_installed_game=refresh_game

    def finish_game(self,payload):
        identity,game,banks,error,reference_token=payload;self.game_refresh_pending=False
        if game!=self.cfg.get('game') or identity!=game_installation.identity(self.cfg) or reference_token!=live_voice_references.token(self.cfg):return
        if error:self.status.set(str(error));return
        self.installed_game_identity=identity;self.installed_reference_token=reference_token;self.pak=None;self.banks=banks
        # Only annotations change here; never replace the open audio session or edits.
        import voice_context,attack_context
        seen=set()
        for bank in (self.bank,self.reference_bank):
            if bank is not None and id(bank) not in seen:
                seen.add(id(bank))
                voice_context.attach(bank.rows,bank.name,bank.acb,self.cfg)
                attack_context.attach(bank.name,bank.acb,bank.rows,self.cfg)
        self.original_text_data={};self.original_text_pending=set()
        self.start_bank_catalog();self.start_character_catalog();self.fill_banks()
        self.status.set(self.tr('Arquivos do jogo atualizados. Lista de bancos e nomes renovada; reabra o banco atual para conferir suas edições.'))
    Studio.finish_game_inventory=finish_game

    old_language=Studio.apply_language
    def language(self,value):
        old_language(self,value);self.start_character_catalog()
    Studio.apply_language=language

    old_document=Studio.project_document
    def document(self):
        data=old_document(self);data['schema']=6;data['bank_reference']=bank_version.snapshot(self.bank);return data
    Studio.project_document=document
