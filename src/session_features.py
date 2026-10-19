import support_report
"""Project-local manual annotations, crash recovery and offline help."""
import copy, hashlib, json, os, shutil, threading, time, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import core
from modern_theme import BG, PANEL, FG, MUTED

def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def identity(row):
    return {'cue_ids':sorted(row.get('cue_ids',[])), 'cue_names':sorted(row.get('cue_names',[]))}

def clean_manual(data, bank):
    result={}
    if not isinstance(data,dict):return result
    for key,item in data.items():
        row=bank.wave_rows.get(key)
        if not row or not isinstance(item,dict) or item.get('identity')!=identity(row):continue
        label=item.get('label','');notes=item.get('notes','');tags=item.get('tags',[])
        if not isinstance(label,str) or not isinstance(notes,str) or not isinstance(tags,list):continue
        tags=[t.strip()[:80] for t in tags[:20] if isinstance(t,str) and t.strip()]
        if label.strip():result[key]={'identity':identity(row),'label':label.strip()[:200],'notes':notes[:4000],'tags':list(dict.fromkeys(tags))}
    return result

def attach(owner):
    if not owner.bank:return
    for row in owner.bank.rows:
        row.pop('_manual',None)
        if row['key'] in owner.manual_identifications:row['_manual']=owner.manual_identifications[row['key']]
    # Add references without changing the person's label, tags or notes.
    annotated=[row for row in owner.bank.rows if row.get('_manual')]
    if annotated and hasattr(owner.bank,'acb') and hasattr(owner,'cfg'):
        import function_refinements
        try:function_refinements.attach(owner.bank.name,owner.bank.acb,annotated,owner.cfg)
        except (OSError,ValueError,KeyError,IndexError,TypeError):
            for row in annotated:row['function_refinements']=[]


def set_manual(owner,key,label,tags='',notes=''):
    if owner.busy or not owner.bank or key not in owner.bank.wave_rows:return
    if len(label)>200 or len(notes)>4000 or len(tags)>1600:raise ValueError('Identificação muito longa (nome: 200; notas: 4000; tags: 1600 caracteres).')
    before=owner.history.begin()
    if label.strip():
        owner.manual_identifications[key]={'identity':identity(owner.bank.wave_rows[key]),'label':label.strip(),
            'tags':list(dict.fromkeys(t.strip() for t in tags.split(',') if t.strip()))[:20],'notes':notes.strip()}
    else:owner.manual_identifications.pop(key,None)
    attach(owner);owner.refresh_function_choices();owner.fill_rows();owner.select()
    owner.history.finish(before,'Identificar voz manualmente')
    owner.status.set(owner.tr('Identificação manual atualizada. Salve o projeto para manter a alteração.'))

def manual_dialog(owner):
    if owner.busy or not owner.selected:return
    key=owner.selected['key'];item=owner.manual_identifications.get(key,{})
    win=tk.Toplevel(owner);win.title(owner.tr('Identificar voz'));win.configure(bg=BG);win.transient(owner)
    win.geometry('640x440');win.minsize(500,380)
    frame=ttk.Frame(win,padding=20);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text=owner.selected['filename']+' • Cue '+', '.join(map(str,owner.selected['cue_ids'])),wraplength=580).pack(anchor='w')
    ttk.Label(frame,text=owner.tr('Anotação do usuário; não altera a tag original nem confirma uso no jogo.'),wraplength=580).pack(anchor='w',pady=(6,16))
    fields=[]
    for title,value in [('Função ou interação',item.get('label','')),('Tags pessoais (separadas por vírgula)',', '.join(item.get('tags',[])))]:
        ttk.Label(frame,text=owner.tr(title)).pack(anchor='w');var=tk.StringVar(value=value)
        entry=ttk.Entry(frame,textvariable=var);entry.pack(fill='x',pady=(3,10));fields.append(var)
    ttk.Label(frame,text=owner.tr('Notas / como você identificou')).pack(anchor='w')
    notes=tk.Text(frame,height=5,bg=PANEL,fg=FG,insertbackground=FG,wrap='word');notes.pack(fill='both',expand=True,pady=(3,12));notes.insert('1.0',item.get('notes',''))
    buttons=ttk.Frame(frame);buttons.pack(fill='x')
    def save(remove=False):
        try:set_manual(owner,key,'' if remove else fields[0].get(),fields[1].get(),notes.get('1.0','end-1c'))
        except Exception as error:support_report.show(owner,str(error),parent=win,title=owner.tr('Identificar voz'));return
        win.destroy()
    owner.button(buttons,'Remover identificação',lambda:save(True)).pack(side='left')
    owner.button(buttons,'Cancelar',win.destroy).pack(side='right')
    owner.button(buttons,'Salvar identificação',save,True).pack(side='right',padx=8)
    win.grab_set()

class Recovery:
    """Only immutable recovery resources are written by the worker, never a saved project."""
    def __init__(self,owner):
        self.owner=owner;self.root=core.APP/'Cache/Recovery';self.folder=self.root/uuid.uuid4().hex
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='VoiceRecovery')
        self.lock=threading.Lock();self.generation=0;self.signature=None;self.future=None;self.closed=False;self.error=None
        self.files={};self.timers={};self.pid=os.getpid();self.marker=self.folder/'active';self.consumed=None
    def schedule(self,name,delay,callback):
        self.timers[name]=self.owner.after(delay,callback)
    def cancel_timers(self,event=None):
        if event is not None and event.widget is not self.owner:return
        for timer in self.timers.values():
            try:self.owner.after_cancel(timer)
            except tk.TclError:pass
        self.timers.clear()
        if event is not None:self.executor.shutdown(wait=False)
    def clear(self):
        with self.lock:
            self.generation+=1;self.signature=None
            for folder in (self.folder,self.consumed):
                if folder:
                    manifest=folder/'recovery.json'
                    if manifest.is_file():manifest.unlink()
            self.consumed=None
    def checkpoint(self):
        o=self.owner
        if self.closed or o.busy or not o.bank or not o.project:return
        if not o.has_unsaved_changes():
            if self.signature is not None:self.clear()
            return
        signature=o.project_edit_snapshot()
        if signature==self.signature or self.future and not self.future.done():return
        document=copy.deepcopy(o.project_document());generation=self.generation
        payload={'schema':1,'timestamp':time.time(),'pid':self.pid,'project':document,'origin':str(o.project),
            'original_project':None if o.project_temporary else str(o.project/'project.json')}
        self.signature=signature
        self.future=self.executor.submit(self.write,payload,generation)
    def write(self,payload,generation):
        try:
            self.folder.mkdir(parents=True,exist_ok=True);self.marker.write_text(str(self.pid))
            document=payload['project'];copied={}
            def preserve(value):
                if value in copied:return copied[value]
                path=Path(value);stat=path.stat();signature=(stat.st_size,stat.st_mtime_ns)
                cached=self.files.get(value)
                if cached and cached[0]==signature and Path(cached[1]).is_file():
                    copied[value]=cached[1];return cached[1]
                digest=file_hash(path)
                target=self.folder/'Files'/(digest+path.suffix.lower())
                if not target.is_file():
                    target.parent.mkdir(exist_ok=True);temporary=target.with_suffix(target.suffix+'.tmp')
                    shutil.copy2(path,temporary);os.replace(temporary,target)
                self.files[value]=(signature,str(target));copied[value]=str(target);return str(target)
            document['replacements']={key:preserve(value) for key,value in document['replacements'].items()}
            for key,item in list(document.get('trim_originals',{}).items())+list(document.get('processing_originals',{}).items())+list(document.get('effects_originals',{}).items())+list(document.get('speed_originals',{}).items())+list(document.get('duplicate_originals',{}).items()):
                item['original']=preserve(item['original']);item['trimmed']=document['replacements'][key]
            if document.get('source'):
                for field in ('asset','uexp','acb','awb'):
                    if document['source'].get(field):document['source'][field]=preserve(document['source'][field])
            with self.lock:
                if self.closed or generation!=self.generation:return
                temporary=self.folder/'recovery.tmp';temporary.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
                os.replace(temporary,self.folder/'recovery.json')
        except Exception as error:
            self.signature=None;self.error=str(error)
    def tick(self):
        if self.closed or self.owner._destroyed:return
        self.checkpoint()
        if self.error:
            self.owner.status.set(self.owner.tr('Falha na recuperação automática: ')+self.error);self.error=None
        self.schedule('tick',5000,self.tick)
    def shutdown(self):
        self.clear();self.closed=True;self.cancel_timers();self.executor.shutdown(wait=False)
        if self.marker.is_file():self.marker.unlink()
    def candidates(self):
        result=[]
        for path in self.root.glob('*/recovery.json'):
            if path.parent==self.folder:continue
            try:
                data=json.loads(path.read_text(encoding='utf-8'))
                if data.get('schema')!=1 or not isinstance(data.get('project'),dict):continue
                if not isinstance(data.get('timestamp'),(int,float)) or not isinstance(data['project'].get('bank'),str):continue
                if not isinstance(data['project'].get('project_name',''),str):continue
                # A second running instance owns its own recovery; never consume it.
                marker=path.parent/'active'
                if marker.is_file() and process_alive(int(marker.read_text())):continue
                result.append((path,data))
            except (OSError,ValueError,TypeError):continue
        return sorted(result,key=lambda pair:pair[1]['timestamp'],reverse=True)
    def materialize(self,path,payload):
        folder=path.parent.resolve();session=core.APP/'Cache/Sessions'/uuid.uuid4().hex
        document=copy.deepcopy(payload['project']);session.mkdir(parents=True)
        copied={}
        def restore(value):
            if value in copied:return copied[value]
            source=Path(value).resolve()
            if not source.is_relative_to(folder/'Files') or not source.is_file():raise ValueError('Arquivo de recuperação inválido ou indisponível: '+str(source))
            if file_hash(source)!=source.stem:raise ValueError('Áudio de recuperação corrompido: '+source.name)
            target=session/'RecoveredFiles'/source.name;target.parent.mkdir(exist_ok=True);shutil.copy2(source,target)
            copied[value]=str(target);return str(target)
        document['replacements']={k:restore(v) for k,v in document.get('replacements',{}).items()}
        for key,item in list(document.get('trim_originals',{}).items())+list(document.get('processing_originals',{}).items())+list(document.get('effects_originals',{}).items())+list(document.get('speed_originals',{}).items())+list(document.get('duplicate_originals',{}).items()):item['original']=restore(item['original']);item['trimmed']=document['replacements'][key]
        if document.get('source'):
            for field in ('asset','uexp','acb','awb'):
                if document['source'].get(field):document['source'][field]=restore(document['source'][field])
        document['project_file']=str(session/'project.json');document['temporary_session']=True
        document['project_name']=document.get('project_name',document['bank'])+' (recuperado)'
        document['project_id']=None
        document['_recovery_path']=str(folder)
        return document
    def offer(self):
        if self.closed or self.owner._destroyed:return
        if self.owner.grab_current() is not None:self.schedule('offer',1000,self.offer);return
        candidates=self.candidates()
        if not candidates:return
        o=self.owner;win=tk.Toplevel(o);win.title(o.tr('Recuperar sessão'));win.configure(bg=BG);win.transient(o);win.geometry('650x360')
        frame=ttk.Frame(win,padding=20);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text=o.tr('Há alterações recuperáveis de uma sessão interrompida.'),wraplength=600).pack(anchor='w')
        ttk.Label(frame,text=o.tr('Recuperar abre uma cópia. Salvar cria um novo projeto; a última versão salva fica preservada.'),wraplength=600).pack(anchor='w',pady=(6,12))
        listing=tk.Listbox(frame,bg=PANEL,fg=FG,selectbackground='#334155',height=7);listing.pack(fill='both',expand=True)
        for path,data in candidates:listing.insert('end',data['project'].get('project_name',data['project'].get('bank',''))+' • '+time.strftime('%d/%m/%Y %H:%M',time.localtime(data['timestamp'])))
        listing.selection_set(0);buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=(12,0))
        def recover():
            selected=listing.curselection()
            if not selected or o.busy:return
            path,payload=candidates[selected[0]]
            try:document=self.materialize(path,payload)
            except Exception as error:support_report.show(o,str(error),parent=win,title=o.tr('Recuperar sessão'));return
            win.destroy();o.load_bank(document['bank'],document)
        def discard():
            selected=listing.curselection()
            if not selected:return
            index=selected[0];path,_=candidates[index]
            path.unlink();candidates.pop(index);listing.delete(index)
            if not candidates:win.destroy()
            else:listing.selection_set(min(index,len(candidates)-1))
        o.button(buttons,'Descartar recuperação',discard).pack(side='left')
        o.button(buttons,'Mais tarde',win.destroy).pack(side='right')
        o.button(buttons,'Recuperar',recover,True).pack(side='right',padx=8);win.grab_set()

def process_alive(pid):
    if os.name=='nt':
        import ctypes
        handle=ctypes.windll.kernel32.OpenProcess(0x1000,False,pid)
        if handle:ctypes.windll.kernel32.CloseHandle(handle);return True
        return ctypes.windll.kernel32.GetLastError()==5
    try:os.kill(pid,0);return True
    except OSError:return False

HELP_TRANSLATIONS=json.loads((core.APP/"Data/extra_languages.json").read_text(encoding="utf-8"))
HELP={
 'Ouvir original e voz editada':'Ouvir original reproduz a voz original do jogo para comparação. Ouvir voz editada dá prioridade ao áudio que você colocou como substituição, incluindo cortes, processamento, ganho e variação. Quando não há substituição, reproduz a voz que veio no banco externo aberto, desde que ela não tenha sido confirmada como igual ao original do jogo. Vozes externas com igualdade confirmada aparecem como Original e não habilitam Ouvir voz editada. Uma comparação incerta não significa que a voz é igual ao original. Sem nenhuma dessas opções, o botão fica desativado. Durante a reprodução, o mesmo botão muda para Parar. Só uma prévia toca por vez.',
 'Gravar pelo microfone':'Escolha a voz do banco e clique em Gravar voz ao lado de Importar áudio. Selecione seu microfone, clique em Gravar e depois em Parar gravação. O medidor mostra o nível recebido e avisa se o sinal atingir o limite. Não há escuta ao vivo do microfone. Ouvir gravação permite revisar a tomada; Gravar faz uma nova tomada. Usar gravação aplica a voz à entrada selecionada, convertendo para o formato WAV do banco. A partir daí, use os cortes, restauração sem corte, ganho, clipping, maximização de volume, desfazer/refazer e salvar que já existem no app. A gravação só entra no projeto e na recuperação automática depois de Usar gravação. Para evitar retorno do áudio, pare a prévia antes de gravar. Se o microfone não abrir, confira a conexão, o dispositivo escolhido e as permissões de microfone para aplicativos de área de trabalho nas configurações de privacidade do Windows.',
 'Começar e salvar':'Escolha o banco de voz e clique em Abrir banco. Abrir um banco não cria um projeto salvo. Importe ou edite áudios e clique em Salvar projeto quando quiser criar o projeto. Ao sair com alterações, escolha Salvar, Não salvar ou Cancelar.',
 'Recuperação automática':'A cada 5 segundos, quando o aplicativo está livre, as alterações pendentes são copiadas para Cache/Recovery. Áudios, cortes, ganhos, variações e identificações manuais são preservados. Não substitui Salvar projeto. Após uma interrupção, escolha Recuperar na próxima abertura. A sessão recuperada é uma cópia; Salvar cria um novo projeto. Mais tarde mantém a recuperação. Descartar remove aquela recuperação. Sair normalmente com Não salvar descarta as alterações, inclusive a recuperação. A operação em andamento e os últimos segundos podem não estar no último ponto recuperado.',
 'Identificar vozes':'Selecione uma voz, abra Mostrar detalhes → Detalhes e tags e clique em Identificar voz. Também é possível clicar com o botão direito na lista. Informe função/interação, tags pessoais e notas sobre a identificação. Ela aparece como Manual e pode ser encontrada pela busca ou filtro de tags pessoais. Não altera tags PTN nem referências verificadas nos arquivos do jogo. A anotação vale para aquela faixa e seus Cue IDs no banco do projeto; não é transferida automaticamente para outro banco ou versão. Salve para persistir; compartilhar o projeto inclui as anotações. Remover identificação mantém as referências originais.',
 'Cores e referências':'Verde: áudio customizado ou diferente da referência. Amarelo: comparação incerta. Cor padrão: áudio semelhante ou sem substituição. A identificação automática mostra referências encontradas nos assets; os detalhes informam limites da evidência. Uma anotação Manual é fornecida pelo usuário. A cor não altera a política de silenciar/manter vozes não substituídas.',
 'Áudio, cortes e volume':'Importar áudio aceita áudio e vídeo; vídeo fornece somente sua faixa de áudio. O resultado é convertido para WAV. Corte usa linhas arrastáveis no começo/fim, com prévia antes de aplicar, sem fades. Restaurar sem corte recupera o áudio importado completo. Ganho, Corrigir clipping e Maximizar volume atuam na seleção ou no banco atual conforme o escopo escolhido.\n\nNo escopo Banco: customizadas, Maximizar volume e Corrigir clipping ajustam somente as substituições adicionadas ao projeto e as vozes de bancos externos identificadas como diferentes do original. Vozes originais, semelhantes ao original ou com comparação incerta ficam fora do ajuste em lote. A opção Voz selecionada permite ajustar individualmente a voz escolhida.',
 'Desfazer e refazer':'Por que Desfazer (Undo) e Refazer (Redo) estão apagados ao abrir um banco ou projeto? Ainda não há edições no histórico dessa sessão. Desfazer fica disponível após importar, cortar ou ajustar um áudio, ou alterar uma identificação manual. Refazer fica disponível depois de desfazer uma alteração. Salvar ou exportar não cria uma edição para desfazer. Abrir novamente o banco ou projeto inicia um novo histórico. Ctrl+Z desfaz. Ctrl+Y ou Ctrl+Shift+Z refaz. O histórico mantém até 80 operações por banco durante a sessão, incluindo áudio e identificação manual. Uma nova edição descarta o caminho de refazer. O histórico não é restaurado ao reiniciar. Em campos de texto, os atalhos pertencem à edição daquele campo.',
 'Importar e migrar':'Abrir voz externa aceita bancos e pacotes .pak/.utoc/.ucas com os arquivos correspondentes. Para um UASSET, use o AWB que pertence ao mesmo banco. Migrar banco antigo compara referências para trazer substituições ao banco atualizado. Verifique os casos incertos antes de exportar; nome ou Cue ID sozinho não prova equivalência entre versões.',
 'Replacer e Custom':'O indicador ao lado do aviso amarelo mostra verde quando o CustomProject, o editor da Custom Engine e os arquivos do CriWare passam na verificação local. Vermelho informa o que falta ou está inválido. O indicador se refere somente ao modo Custom e atualiza ao abrir o app, mudar o idioma ou salvar Configurações. A verificação dos arquivos não substitui o teste de exportação/cook e do mod dentro do jogo. Replacer substitui a voz de um banco existente. Para adicionar uma voz Custom, configure o CustomProject e a pasta da Custom Engine compatível com Sparking Zero. A Custom Engine é necessária para criar/cookar os assets Custom. Para dublar um personagem custom existente, o replacer deve usar os assets de voz daquele personagem; o mod do personagem também precisa estar instalado no jogo.',
 'Compartilhar e mesclar':'Ferramentas permite compartilhar projetos e mesclar substituições de modders que trabalharam no mesmo banco. Na mescla, revise conflitos em que a mesma faixa recebeu áudios diferentes. Identificações manuais acompanham o projeto compartilhado; a mescla de áudio não combina automaticamente anotações pessoais de projetos distintos.',
 'Nome dos arquivos e nome do projeto':'O que é File name (Asset mode), ou Nome dos arquivos (modo Asset)? É o nome-base dos assets de voz exportados: UASSET, UEXP, ACB e AWB usam esse mesmo nome-base, por exemplo BTLCV_0000_00_US. Na opção Custom (.uasset + AWB .pak), o campo pode ser editado; a referência a modo Asset é o rótulo desse campo. No modo Replacer (.pak / .utoc / .ucas), ele fica desativado porque a exportação deve manter o nome do banco que será substituído. Por que não consigo clicar nesse campo? Confira se o modo selecionado é Replacer. Para dar um nome ao seu trabalho, use Nome do projeto. Esse nome organiza o projeto salvo e não renomeia o banco original. Exemplo: o projeto pode se chamar Superman, enquanto o banco substituído continua BTLCV_0000_00_US.',
 'Pastas de saída':'Exportar banco cria o pacote para o jogo. Abrir pasta dos exports mostra esses pacotes. Abrir áudios editados mostra os áudios preparados do projeto. Salvar projeto guarda seu trabalho de edição; exportar e compartilhar têm finalidades diferentes.'
}

HELP_GUIDES=json.loads((core.APP/'Data/help_guides.json').read_text(encoding='utf-8'))

def help_dialog(owner):
    HELP.update({key:guide['pt'] for key,guide in HELP_GUIDES.items()})
    def localization():
        language=owner.translator.language
        result=copy.deepcopy(HELP_TRANSLATIONS.get(language,{}))
        result.setdefault('help',{}).update({key:guide.get(language,guide.get('en',guide['pt'])) for key,guide in HELP_GUIDES.items()})
        return result
    existing=getattr(owner,'help_window',None)
    if existing and existing.winfo_exists():
        if getattr(owner,'_help_language',None)==owner.translator.language:
            import window_toggle
            window_toggle.existing(owner,'help_window');return
        existing.destroy()
    win=tk.Toplevel(owner);owner.help_window=win;owner._help_language=owner.translator.language;win.title(owner.tr('Ajuda'));win.configure(bg=BG);win.geometry('1040x700');win.minsize(600,380)
    frame=ttk.Frame(win,padding=20);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text=owner.tr('Ajuda • Sparking Zero Voice Studio'),font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(0,12))
    ttk.Label(frame,text=owner.tr('Pesquisar na ajuda')).pack(anchor='w',pady=(0,4))
    query=tk.StringVar();entry=ttk.Entry(frame,textvariable=query);entry.pack(fill='x',pady=(0,12))
    body=ttk.Frame(frame);body.pack(fill='both',expand=True)
    topic_frame=ttk.Frame(body);topic_frame.pack(side='left',fill='y',padx=(0,16))
    topics=tk.Listbox(topic_frame,width=27,bg=PANEL,fg=FG,selectbackground='#334155',exportselection=False)
    topic_scroll=ttk.Scrollbar(topic_frame,orient='vertical',command=topics.yview)
    topic_scroll.pack(side='right',fill='y');topics.configure(yscrollcommand=topic_scroll.set);topics.pack(side='left',fill='both',expand=True)
    text=tk.Text(body,bg=PANEL,fg=FG,wrap='word',padx=16,pady=16,relief='flat',font=('Segoe UI',11),spacing1=3,spacing2=3,spacing3=7);scroll=ttk.Scrollbar(body,command=text.yview);scroll.pack(side='right',fill='y');text.configure(yscrollcommand=scroll.set);text.pack(fill='both',expand=True)
    text.tag_configure('title',font=('Segoe UI',16,'bold'),spacing3=14)
    text.tag_configure('section',font=('Segoe UI',11,'bold'),spacing1=10,spacing3=6)
    keys=[];shown=[None]
    def show(event=None):
        sel=topics.curselection();position=text.yview()[0];text.configure(state='normal');text.delete('1.0','end')
        if sel:
            key=keys[sel[0]];localized=localization()
            value=localized.get('help_titles',{}).get(key,owner.translator.logical(key))+'\n\n'+localized.get('help',{}).get(key,HELP[key])
            from tkinter import font
            measure=font.Font(font=text.cget('font')).measure
            text.configure(wrap='none' if owner.translator.language=='ar' else 'word')
            displayed=owner.translator.display(value,measure,max(250,text.winfo_width()-40))
            text.insert('1.0',displayed)
            text.tag_add('title','1.0','1.end')
            lines=displayed.splitlines()
            for index,line in enumerate(lines[2:],3):
                if line.strip() and len(line)<80 and not line.strip()[0].isdigit() and not line.rstrip().endswith(('.',':','؛','。')) and not lines[index-2].strip():
                    text.tag_add('section',f'{index}.0',f'{index}.end')
            text.yview_moveto(position if shown[0]==key else 0)
            shown[0]=key
        else:text.insert('1.0',owner.tr('Nenhum tópico encontrado.'))
        text.configure(state='disabled')
    def search(*args):
        localized=localization()
        keys[:]=[k for k,v in HELP.items() if query.get().casefold() in (k+' '+v+' '+localized.get('help_titles',{}).get(k,'')+' '+localized.get('help',{}).get(k,'')).casefold()];topics.delete(0,'end')
        for key in keys:topics.insert('end',owner.translator.display(localized.get('help_titles',{}).get(key,owner.translator.logical(key))))
        if keys:topics.selection_set(0)
        show()
    query.trace_add('write',search);topics.bind('<<ListboxSelect>>',show);text.bind('<Configure>',show,add='+');search();entry.focus_set()

HELP['Replacer e Custom']+=' Em Custom, o Nome do banco (Custom) deve corresponder exatamente ao SoundAtomCueSheet/banco de voz referenciado pelo personagem na Unreal, incluindo o sufixo US/JP. O caminho do asset também precisa corresponder à referência do personagem. Use, por exemplo, BTLCV_1111_11_US se essa for a referência configurada. Renomear somente a exportação não atualiza o CharacterData ou as referências do personagem. Nome do projeto serve apenas para organizar o trabalho e não precisa ter esse nome.'
HELP['Nome dos arquivos e nome do projeto']+=' Em Custom, o Nome do banco (Custom) deve corresponder exatamente ao SoundAtomCueSheet/banco de voz referenciado pelo personagem na Unreal, incluindo o sufixo US/JP. O caminho do asset também precisa corresponder à referência do personagem. Use, por exemplo, BTLCV_1111_11_US se essa for a referência configurada. Renomear somente a exportação não atualiza o CharacterData ou as referências do personagem. Nome do projeto serve apenas para organizar o trabalho e não precisa ter esse nome.'

HELP['Personagens e atualizações do jogo']='Os nomes dos personagens vêm do Data.locres do jogo instalado, usando as tabelas oficiais de nomes completos e as referências FText do CharacterData. Eles acompanham o idioma da interface, incluindo as formas de cada personagem. O idioma do texto original da fala continua separado. Se não houver um nome oficial legível para um ID, o app mostra o código e não inventa um nome. Esses nomes aparecem na lista de bancos, no banco atual, nos projetos recentes e nas descrições de interações.\n\nQuando o jogo está instalado e configurado, seus bancos e PatternVoiceData têm prioridade sobre as cópias do CustomProject. O CustomProject continua necessário para a exportação Custom, junto da Custom Engine compatível. Mods de personagem são abertos pela importação externa; a lista oficial não lê a pasta de mods.\n\nO app usa um cache por versão dos contêineres oficiais. Verifica alterações durante o uso e renova a lista, os nomes e o texto original; também lê a versão atual ao abrir o app e cada banco. Se o jogo mudar depois da abertura de um banco, salve suas edições e reabra o projeto antes de exportar. A sessão aberta não é substituída automaticamente. Aguarde a atualização do jogo terminar.\n\nProjetos salvos nesta versão registram os hashes do ACB e AWB e os nomes e IDs completos dos cues. Ao reabrir, o app só remapeia uma edição quando há correspondência exata e única da identidade completa. IDs físicos reutilizados, cues removidos e correspondências ambíguas bloqueiam a abertura para revisão/migração, preservando o projeto salvo. Projetos antigos não possuem essa prova de versão: confira as vozes e salve para registrar a identidade atual.\n\nNomes, novos bancos e tags presentes no PatternVoiceData são lidos novamente do jogo. As interpretações de ataques e interações incluídas no aplicativo dependem da versão analisada. Se os contêineres divergem, essas interpretações ficam ocultas até uma nova análise; isso evita apresentar uma referência antiga como confirmação atual. Mudanças no formato dos arquivos podem exigir uma atualização do aplicativo.'

def install(Studio):
    old_init=Studio.__init__
    def init(self,*args,**kwargs):
        self.manual_identifications={};old_init(self,*args,**kwargs)
        self.recovery=Recovery(self);self.recovery.schedule('tick',5000,self.recovery.tick);self.recovery.schedule('offer',1200,self.recovery.offer)
        self.bind('<Destroy>',self.recovery.cancel_timers,add='+')
        self.bind('<F1>',lambda e:help_dialog(self),add='+')
        menu=tk.Menu(self,tearoff=False);menu.add_command(label=self.tr('Identificar voz'),command=lambda:manual_dialog(self))
        def context(event):
            key=self.tree.identify_row(event.y)
            if not key or self.busy:return
            self.tree.selection_set(key);self.select()
            try:menu.tk_popup(event.x_root,event.y_root)
            finally:menu.grab_release()
        self.tree.bind('<Button-3>',context,add='+')
    Studio.__init__=init
    Studio.identify_voice=lambda self:manual_dialog(self)
    Studio.show_help=lambda self:help_dialog(self)
    old_document=Studio.project_document
    def document(self):
        data=old_document(self);data['manual_identifications']=copy.deepcopy(self.manual_identifications);return data
    Studio.project_document=document
    old_snapshot=Studio.project_edit_snapshot
    def snapshot(self):
        data=json.loads(old_snapshot(self));data['replacer_folder_name']=self.replacer_folder_name;data['manual_identifications']=self.manual_identifications;return json.dumps(data,sort_keys=True)
    Studio.project_edit_snapshot=snapshot
    old_fill=Studio.fill_rows
    def fill(self):attach(self);return old_fill(self)
    Studio.fill_rows=fill
    old_confirm=Studio.confirm_leaving_project
    def confirm(self):
        result=old_confirm(self)
        if result and hasattr(self,'recovery'):self.recovery.clear()
        return result
    Studio.confirm_leaving_project=confirm
    old_save=Studio.save_project
    def save(self,*args,**kwargs):
        result=old_save(self,*args,**kwargs)
        if hasattr(self,'recovery') and not self.has_unsaved_changes():self.recovery.clear()
        return result
    Studio.save_project=save
