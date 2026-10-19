"""Read-only Unreal LOCRES voice text, matched by exact cue names."""
import io,json,struct,hashlib,threading
from pathlib import Path
from tkinter import ttk
import tkinter as tk
import core,modern_theme,game_installation

LANGUAGES={'en':'English','pt-BR':'Português (Brasil)','es-419':'Español (Latinoamérica)','es':'Español (España)','fr':'Français','it':'Italiano','ja':'日本語','de':'Deutsch','ru':'Русский','pl':'Polski','ar':'العربية','zh-Hans':'简体中文','zh-Hant':'繁體中文','ko':'한국어','th':'ไทย','id':'Bahasa Indonesia'}
MAGIC=struct.pack('<IIII',0x7574140E,0xFC034A67,0x9D90154A,0x1B7F37C3)

def parse_locres(data,namespace='ST_VOICE_TEXT'):
    selected_namespace=namespace
    r=io.BytesIO(data)
    def exact(n):
        if n<0 or n>len(data)-r.tell():raise ValueError('LOCRES incompleto.')
        return r.read(n)
    def num(fmt):return struct.unpack('<'+fmt,exact(struct.calcsize(fmt)))[0]
    def count():
        n=num('I')
        if n>len(data)//4:raise ValueError('Tabela LOCRES inválida.')
        return n
    def string():
        n=num('i');raw=exact(abs(n)*(2 if n<0 else 1))
        if n and not raw.endswith(b'\0\0' if n<0 else b'\0'):raise ValueError('String LOCRES inválida.')
        return raw.decode('utf-16le' if n<0 else 'utf-8').rstrip('\0')
    version=num('B') if exact(16)==MAGIC else 0
    if version>3:raise ValueError('Versão LOCRES não suportada.')
    if not version:r.seek(0)
    strings=[]
    if version>=1:
        offset=num('q');position=r.tell()
        if offset!=-1:
            if not position<=offset<len(data):raise ValueError('Índice LOCRES inválido.')
            r.seek(offset)
            for _ in range(count()):
                strings.append(string())
                if version>=2:num('i')
            r.seek(position)
    if version>=2:count()
    def key():
        if version>=2:num('I')  # UE5 FTextKey stores a 32-bit hash in both optimized formats.
        return string()
    entries={}
    for _ in range(count()):
        namespace=key()
        for _ in range(count()):
            name=key();num('I')
            if version:
                index=num('i')
                if not 0<=index<len(strings):raise ValueError('Referência de texto LOCRES inválida.')
                text=strings[index]
            else:text=string()
            if selected_namespace is None:entries[(namespace,name)]=text
            elif namespace==selected_namespace:entries[name]=text
    return entries

def load_language(cfg,language):
    if language not in LANGUAGES:raise ValueError('Idioma de texto desconhecido.')
    folder=Path(cfg['game'])/'SparkingZERO/Content/Paks'
    sources=game_installation.pak_paths(cfg)
    digest=game_installation.identity(cfg)
    cache=core.APP/'Cache/VoiceText'/digest/(language+'.json')
    if cache.exists():return json.loads(cache.read_text(encoding='utf-8'))
    result={};paths=[]
    for path in sources:
        pak=core.Pak(cfg,path=path)
        try:
            for entry in pak.entries:
                if entry.endswith('/Localization/Voice/'+language+'/Voice.locres'):
                    result.update(parse_locres(pak.file(entry)));paths.append(str(path))
        finally:pak.f.close()
    if not paths:raise ValueError('LOCRES de voz não encontrado para este idioma.')
    data={'entries':result,'language':language,'sources':paths,'game_identity':digest}
    core.write_json(cache,data)
    return data

def entries_for_row(row,catalog):
    result=[]
    for cue in row.get('cue_names',[]):
        key='ST_'+cue;value=catalog.get(key)
        if value and value.strip() and not value.startswith(('TR_','ST_')):
            result.append((cue,key,value))
    return result

class OriginalTextMixin:
    def setup_original_text(self,tabs):
        self.original_text_data={};self.original_text_pending=set()
        default={'pt':'pt-BR','es':'es-419'}.get(self.translator.language,self.translator.language)
        language=self.cfg.get('voice_text_language',default)
        self.voice_text_language=tk.StringVar(value=language if language in LANGUAGES else 'en')
        frame=ttk.Frame(tabs);self.original_text_frame=frame
        tabs.add(frame,text=self.tr('Texto original'))
        controls=ttk.Frame(frame,padding=(10,6));controls.pack(fill='x')
        self.label(controls,'Idioma do texto').pack(side='left',padx=(0,12))
        combo=ttk.Combobox(controls,values=list(LANGUAGES.values()),state='readonly',width=25)
        combo.set(LANGUAGES[self.voice_text_language.get()]);combo.pack(side='left')
        self.original_text_choice=combo
        def changed(event=None):
            self.voice_text_language.set(next(k for k,v in LANGUAGES.items() if v==combo.get()))
            self.cfg['voice_text_language']=self.voice_text_language.get()
            core.write_json(core.APP/'settings.json',self.cfg)
            self.update_original_text(force=True)
        combo.bind('<<ComboboxSelected>>',changed)
        body=ttk.Frame(frame);body.pack(fill='both',expand=True)
        text=tk.Text(body,height=4,wrap='word',font=('Segoe UI',10),bg=modern_theme.PANEL,fg=modern_theme.FG,relief='flat',padx=12,pady=8)
        scroll=ttk.Scrollbar(body,command=text.yview);scroll.pack(side='right',fill='y')
        text.configure(yscrollcommand=scroll.set,state='disabled');text.pack(fill='both',expand=True)
        self.original_text_widget=text
        tabs.bind('<<NotebookTabChanged>>',lambda e:self.update_original_text(),add='+')
    def set_original_text(self,value):
        text=self.original_text_widget;text.configure(state='normal');text.delete('1.0','end');text.insert('end',value);text.configure(state='disabled')
    def update_original_text(self,force=False):
        if not hasattr(self,'original_text_widget'):return
        self.detail_tabs.tab(self.original_text_frame,text=self.tr('Texto original'))
        row=self.selected
        if not row:self.set_original_text(self.tr('Escolha uma entrada de voz'));return
        language=self.voice_text_language.get();data=self.original_text_data.get(language)
        if data is not None and data.get('game_identity')!=game_installation.identity(self.cfg):
            self.original_text_data.pop(language,None);data=None
        if data is None:
            if not force and (not self.detail_tabs.winfo_ismapped() or self.detail_tabs.select()!=str(self.original_text_frame)):
                self.set_original_text(self.tr('Abra esta aba para carregar o texto original.'));return
            self.set_original_text(self.tr('Carregando textos originais...'))
            if language in self.original_text_pending:return
            self.original_text_pending.add(language);cfg=dict(self.cfg)
            def worker():
                try:result,error=load_language(cfg,language),None
                except Exception as e:result,error=None,str(e)
                self.jobs.put(('voice_text',(language,result,error)))
            threading.Thread(target=worker,daemon=True).start();return
        reference=core.reference_row(self.bank,self.reference_bank,row)
        matches=entries_for_row(reference or row,data['entries'])
        if not matches:self.set_original_text(self.tr('Sem texto original disponível no LOCRES para esta voz.'));return
        self.set_original_text('\n\n'.join(cue+'\n'+text for cue,key,text in matches))
    def finish_original_text(self,payload):
        language,data,error=payload;self.original_text_pending.discard(language)
        if data and data.get('game_identity')!=game_installation.identity(self.cfg):return
        if data:self.original_text_data[language]=data
        if language!=self.voice_text_language.get():return
        if error:self.set_original_text(self.tr('Não foi possível carregar o texto original: ')+error)
        else:self.update_original_text(force=True)
