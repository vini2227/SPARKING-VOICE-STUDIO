import localized_dialogs
import replacer_folder
"""Windows desktop UI for original/custom battle voices."""
import design_clarity
import ctypes, json, os, queue, threading, traceback, wave, winsound, time, uuid
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import numpy as np
import core
import support_report,export_operations
import video_audio
import audio_import
import audio_levels
import audio_variations
import project_names
import recent_projects
import folder_navigation
import editor_asset
import batch_clipping
import voice_gain
import voice_context
from audio_trim_ui import AudioTrimMixin
from reuse_voices_ui import ReuseVoicesMixin
from video_audio_ui import VideoAudioMixin
from project_exchange_ui import ProjectExchangeMixin
from unsaved_project import UnsavedProjectMixin
from recent_projects import RecentProjectsMixin
from studio_audio import AudioStudioMixin
from migration_ui import MigrationMixin
from voice_text import OriginalTextMixin
from responsive_layout import ResponsiveMixin
import bank_migration
import migrated_audio
import package_import
from shell_drop import FileDrop
from bank_table import BankTable
from voice_table import VoiceTable
from project_audio import ProjectAudioWriter
import project_audio
from duplicate_wavs import DuplicateWavs, sources as duplicate_wavs_sources
from i18n import Translator, LocalizedVar, LANGUAGES
from activity_indicator import ActivityIndicator
import trim_history
import edit_history
import session_features
import custom_setup_status
import microphone_ui
import current_bank_identity
import header_project
import button_identity
import playback_controls
import compact_export_layout
import modern_theme
import ui_reliability
from modern_theme import BG,PANEL,CARD,FG,MUTED,ACCENT,RoundedPanel



class Studio(AudioTrimMixin,ReuseVoicesMixin,VideoAudioMixin,ProjectExchangeMixin,UnsavedProjectMixin,RecentProjectsMixin,ResponsiveMixin,MigrationMixin,AudioStudioMixin,OriginalTextMixin,tk.Tk):
    def __init__(self):
        # Use the monitor's real work area and Windows DPI scaling on Full HD displays.
        try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError,OSError):pass
        try:ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LimitBreaker.SparkingZeroVoiceStudio")
        except (AttributeError,OSError):pass
        super().__init__()
        self.title("Sparking Zero Voice Studio")
        self.game_icon_path=core.APP/"Data/game_icon.ico"
        if self.game_icon_path.is_file():self.iconbitmap(default=str(self.game_icon_path))
        # Supply Windows with independent sizes from the original artwork.
        # iconbitmap alone can leave Tk's taskbar icon using an enlarged small icon.
        logo_path=core.APP/"Data/app_logo_round.png"
        if logo_path.is_file():
            from PIL import Image,ImageTk
            with Image.open(logo_path) as original:
                original=original.convert("RGBA")
                bounds=original.getchannel("A").getbbox()
                if bounds:original=original.crop(bounds)
                self.window_icon_images=[]
                for size in (16,20,24,32,40,48,64,96,128,256):
                    image=original.copy()
                    image.thumbnail((size,size),Image.Resampling.LANCZOS)
                    canvas=Image.new("RGBA",(size,size))
                    canvas.alpha_composite(image,((size-image.width)//2,(size-image.height)//2))
                    self.window_icon_images.append(ImageTk.PhotoImage(canvas,master=self))
            self.iconphoto(True,*self.window_icon_images)
        self.bind("<Map>",lambda event:self.after_idle(self.set_native_window_icon) if event.widget is self else None,add="+")
        self.after(250,self.set_native_window_icon)
        width=min(1600,self.winfo_screenwidth()-80);height=min(940,self.winfo_screenheight()-100)
        self.geometry(f"{width}x{height}")
        self.minsize(min(960,width),min(600,height))
        self.state("zoomed")
        self.configure(bg=BG)
        self.cfg=core.config();self.pak=None;self.bank=None;self.reference_bank=None;self.replacements={};self.project=None;self.project_temporary=False;self.trim_originals={};self.processing_originals={};self.effects_originals={};self.speed_originals={};self.duplicate_originals={}
        self.translator=Translator(self.cfg.get("ui_language","en"));self._texts=[];self._choices=[];self._localized_vars=[]
        import game_characters
        self.character_names=game_characters.bundled(self.translator.language)
        self.function_catalog=json.loads((core.APP/"Data/function_languages.json").read_text(encoding="utf-8"))
        self.function_language=tk.StringVar(value=self.translator.language)
        self.migration=None;self.project_name="";self.replacer_folder_name="";self.project_id=None;self.project_renaming=False;self.project_usage_count=0;self.project_last_opened=None
        self.variations={};self.variation=tk.IntVar(value=1)
        self.gains={};self.gain=tk.DoubleVar(value=0.0);self._setting_gain=False
        self.level_token=0;self.level_signature=None;self.level_data={};self.level_lock=threading.Lock()
        self.level_after=None;self.gain_save_after=None;self._saved_project_snapshot=None;self.volume_scope=tk.StringVar(value="selected")
        self.original_level=tk.StringVar(value="—");self.import_level=tk.StringVar(value="—");self.adjusted_level=tk.StringVar(value="—")
        self.gain_text=tk.StringVar(value="+0.0 dB");self.volume_warning=tk.StringVar(value="")
        self.bank_counts={};self.catalog_ready=False;self.catalog_generation=0
        self.bank_query=tk.StringVar()
        self.bank_sort=tk.StringVar(value="name_asc");self.audio_sort=tk.StringVar(value="cue_asc");self.function_filter=tk.StringVar(value="*")
        self.function_scope=tk.StringVar(value="all")
        self.inspector_expanded=tk.BooleanVar(value=False)
        self.view_filter=tk.StringVar(value="all")
        self.duplicate_wavs=DuplicateWavs();self.duplicate_info={};self.duplicate_focus=None
        self.bank_filter_hint=self.localized_var("Contando vozes...")
        self.busy=False;self.jobs=queue.Queue();self.selected=None;self.playing=None;self.wave_after=None;self.wave_bars=[];self.wave_duration=0;self.wave_data=None
        self.project_audio=ProjectAudioWriter(lambda error:self.jobs.put(("project_audio_error",error)))
        self.bind("<Destroy>",lambda event:self.project_audio.shutdown() if event.widget is self else None,add="+")
        self.search=tk.StringVar();self.lang=tk.StringVar(value="US");self.status=self.localized_var("Lendo os bancos de referência...")
        self.keep_imported=tk.BooleanVar(value=True)
        self.export_mode=tk.StringVar(value="package")
        self.export_name=tk.StringVar()
        self.destination=tk.StringVar(value=str(core.APP/"Exports"))
        prefs=core.APP/"export_preferences.json"
        if prefs.exists():
            try:
                data=json.loads(prefs.read_text(encoding="utf-8"))
                self.destination.set(data.get("destination",self.destination.get()))
                saved=data.get("mode","package")
                self.export_mode.set("audio_pak" if saved in ("audio_pak","asset","Asset (.uasset + ACB + AWB)") else "package")
            except (ValueError,OSError):pass
        self._destroyed=False
        self.bind("<Destroy>",lambda event:setattr(self,"_destroyed",True) if event.widget is self else None,add="+")
        self.history=edit_history.EditHistory(self)
        self.style()
        self.build()
        self.banks=[]
        self.fill_banks()
        # Let Tk paint the window before parsing the installed containers.
        self.after(150,self.initialize_bank_list)
        for var in (self.bank_query,):var.trace_add("write",lambda *_:self.fill_banks())
        self.search.trace_add("write",lambda *_:self.fill_rows())
        self._poll_after=self.after(100,self.poll)
        ui_reliability.start(self)
        self.protocol("WM_DELETE_WINDOW",self.close)
    def initialize_bank_list(self):
        if self._destroyed:return
        if self.busy:self.after(100,self.initialize_bank_list);return
        cfg=dict(self.cfg)
        def work():
            try:return core.available_banks(cfg),None
            except (OSError,ValueError) as error:return [],str(error)
        def done(result):
            banks,error=result
            if cfg!=self.cfg:self.after(0,self.initialize_bank_list);return
            self.banks=banks;self.fill_banks();self.start_bank_catalog()
            if error:self.status.set(error)
            elif self.banks:self.status.set("Escolha um banco de voz e clique em Abrir banco para começar.")
            else:self.after(200,self.settings)
        self.job(work,done,"Lendo os bancos de referência...")
    def tr(self,text):return self.translator.text(text)
    def localized_var(self,value=""):
        var=LocalizedVar(self,self.translator,value);self._localized_vars.append(var);return var
    def localize_widget(self,widget,text):
        self._texts.append((widget,text));widget.configure(text=self.tr(text));return widget
    def choice(self,parent,variable,options,width=20,onchange=None,translate=True):
        display=tk.StringVar();widget=ttk.Combobox(parent,textvariable=display,state="readonly",width=width)
        record={"widget":widget,"variable":variable,"options":options,"display":display,"translate":translate}
        self._choices.append(record)
        def sync(*_):
            if widget.winfo_exists():
                ids=[id for id,label in record["options"]]
                widget.configure(values=[self.tr(label) if record["translate"] else label for id,label in record["options"]])
                if variable.get() in ids:widget.current(ids.index(variable.get()))
        def changed(event):
            index=widget.current()
            if index>=0:variable.set(record["options"][index][0])
        widget.bind("<<ComboboxSelected>>",changed)
        variable.trace_add("write",sync)
        if onchange:variable.trace_add("write",lambda *_:onchange())
        record["sync"]=sync;sync();return widget
    def update_choice(self,widget,options):
        record=next(item for item in self._choices if item["widget"] is widget)
        record["options"]=options
        if record["variable"].get() not in [id for id,label in options]:record["variable"].set(options[0][0])
        record["sync"]()
    def apply_language(self,language):
        previous_language=self.translator.language
        self.translator.language=language if language in LANGUAGES else "en"
        self.function_language.set(self.translator.language)
        alive=[]
        for widget,text in self._texts:
            if widget.winfo_exists():widget.configure(text=self.tr(text));alive.append((widget,text))
        self._texts=alive
        for record in self._choices:
            if record["widget"].winfo_exists():record["sync"]()
        for var in self._localized_vars:var.refresh()
        import window_toggle
        window_toggle.refresh_titles(self,previous_language)
        for tab,title in getattr(self,"_detail_tab_titles",()):
            if tab.winfo_exists():self.detail_tabs.tab(tab,text=self.tr(title))
        for column,text in self.headings.items():self.tree.heading(column,text=self.tr(text))
        self.bank_list.set_headers((self.tr("Personagem"),self.tr("ID"),"BTLCV"))
        self.refresh_function_choices();self.fill_banks();self.fill_rows()
        self.update_levels()
        design_clarity.refresh(self)
        custom_setup_status.update(self)
        if self.tree.selection():self.select()
        playback_controls.refresh(self)
        if hasattr(self,"flows"):self.update_responsive()
        if getattr(self,"help_window",None) is not None and self.help_window.winfo_exists():self.show_help()
    def start_bank_catalog(self):
        self.catalog_generation+=1;generation=self.catalog_generation;cfg=self.cfg.copy()
        self.bank_counts={};self.catalog_ready=False;self.fill_banks()
        def work():
            try:self.jobs.put(("catalog",(generation,core.bank_voice_catalog(cfg))))
            except Exception:self.jobs.put(("catalog",(generation,{})))
        threading.Thread(target=work,daemon=True).start()
    def change_function_scope(self):
        self.function_filter.set("*")
        self.refresh_function_choices();self.fill_rows()
    def refresh_function_choices(self):
        scope=self.function_scope.get()
        rows=[row for row in self.bank.rows if voice_context.matches_scope(row,scope)] if self.bank else []
        functions=sorted({function for row in rows for function in row["functions"]}) if scope not in ("interactions","emotes") else []
        options=[("*",self.tr("Todas as funções")),("+",self.tr("Somente funções identificadas")),("~",self.tr("Sem função identificada"))]
        options += [(name,self.tag_label(name)) for name in functions]
        options += voice_context.options(rows,scope,self.function_language.get())
        self.update_choice(self.function_choice,options)
    def style(self):
        s=ttk.Style();s.theme_use("clam")
        s.configure(".",background=BG,foreground=FG,font=("Segoe UI",10))
        s.configure("TFrame",background=BG)
        s.configure("Card.TFrame",background=PANEL)
        s.configure("TLabel",background=BG,foreground=FG)
        s.configure("Muted.TLabel",foreground=MUTED)
        s.configure("Title.TLabel",font=("Segoe UI",16,"bold"))
        s.configure("Volume.TFrame",background=PANEL)
        s.configure("TScale",background=PANEL,troughcolor=CARD,sliderlength=24)
        s.configure("TNotebook",background=BG,borderwidth=0)
        s.configure("TNotebook.Tab",padding=(16,6),background=CARD,foreground=MUTED)
        s.map("TNotebook.Tab",background=[("selected",PANEL)],foreground=[("selected",FG)])
        s.configure("Subtitle.TLabel",foreground=ACCENT,font=("Segoe UI",10,"bold"))
        s.configure("TButton",background=CARD,foreground=FG,padding=(12,8),borderwidth=0)
        s.map("TButton",background=[("active","#344158"),("disabled",PANEL)],foreground=[("disabled","#596678")])
        s.configure("Primary.TButton",background=ACCENT,foreground="#102323")
        s.map("Primary.TButton",background=[("active","#8cdfd4"),("disabled",PANEL)])
        s.configure("Invalid.TEntry",fieldbackground="#502c35",foreground=FG)
        s.configure("TEntry",fieldbackground=CARD,foreground=FG,insertcolor=FG,padding=8)
        s.configure("TCombobox",fieldbackground=CARD,foreground=FG,background=CARD,padding=6)
        s.map("TCombobox",fieldbackground=[("readonly",CARD)],foreground=[("readonly",FG)])
        s.configure("Treeview",background=PANEL,fieldbackground=PANEL,foreground=FG,rowheight=32,borderwidth=0)
        s.configure("Treeview.Heading",background=CARD,foreground=MUTED,font=("Segoe UI",9,"bold"),padding=8)
        s.map("Treeview",background=[("selected","#284e55")],foreground=[("selected",FG)])
        s.configure("TCheckbutton",background=BG,foreground=MUTED)
        s.map("TCheckbutton",background=[("disabled",BG),("active",BG)],foreground=[("disabled","#65758b"),("active",FG)])
        s.configure("TProgressbar",background=ACCENT,troughcolor=CARD,borderwidth=0)
        for orientation in ("Vertical","Horizontal"):
            name=orientation+".TScrollbar"
            s.configure(name,background="#53657d",troughcolor=PANEL,arrowcolor=FG,
                bordercolor=BG,lightcolor="#53657d",darkcolor="#53657d",arrowsize=22)
            s.map(name,background=[("pressed",ACCENT),("active","#8096b2")])
        modern_theme.install(self)
        button_identity.install(self)
    def label(self,parent,text,**kw):
        return self.localize_widget(ttk.Label(parent,**kw),text)
    def button(self,parent,text,fn,primary=False):
        button=self.localize_widget(ttk.Button(parent,command=fn,**button_identity.options(self,text,primary)),text)
        return playback_controls.register(self,button,text,fn) if 'Ouvir' in text else button
    def set_native_window_icon(self):
        """Give the Windows taskbar a full-resolution icon on Tk's outer HWND."""
        if not self.game_icon_path.is_file():return
        from ctypes import wintypes
        user=ctypes.windll.user32
        user.LoadImageW.argtypes=[wintypes.HINSTANCE,wintypes.LPCWSTR,wintypes.UINT,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        user.LoadImageW.restype=wintypes.HANDLE
        user.SendMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
        user.SendMessageW.restype=ctypes.c_ssize_t
        hwnd=int(self.wm_frame(),0)
        if not getattr(self,"native_icon_handles",None):
            self.native_icon_handles=[user.LoadImageW(None,str(self.game_icon_path),1,size,size,0x10) for size in (256,32)]
        for kind,handle in zip((1,0),self.native_icon_handles):
            if handle:user.SendMessageW(hwnd,0x80,kind,handle)

    def build(self):
        top=ttk.Frame(self,padding=(22,12));top.pack(fill="x")
        header=ttk.Frame(top);header.pack(fill="x",pady=(6,0))
        brand=ttk.Frame(header);brand.pack(side="left")
        self.brand_logo_path=core.APP/"Data/app_logo_round.png"
        if self.brand_logo_path.is_file():
            from PIL import Image,ImageTk
            with Image.open(self.brand_logo_path) as image:
                image=image.convert("RGBA")
                bounds=image.getchannel("A").getbbox()
                if bounds:image=image.crop(bounds)
                scale=max(1,float(self.tk.call("tk","scaling"))/(96/72))
                size=round(48*scale)
                image.thumbnail((size,size),Image.Resampling.LANCZOS)
                self.brand_mark=ImageTk.PhotoImage(image,master=self)
            self.brand_logo_label=ttk.Label(brand,image=self.brand_mark)
            self.brand_logo_label.pack(side="left",padx=(0,12),anchor="center")
        brand_text=ttk.Frame(brand);brand_text.pack(side="left")
        brand_title=ttk.Frame(brand_text);brand_title.pack(anchor="w")
        ttk.Label(brand_title,text="Sparking Zero",font=("Segoe UI",17,"bold"),foreground=FG).pack(side="left")
        ttk.Label(brand_text,text="VOICE STUDIO",font=("Segoe UI",9,"bold"),foreground=MUTED).pack(anchor="w")
        # A reserved slot keeps the title/buttons stable as operations start and stop.
        self.activity_slot=tk.Frame(brand,bg=BG,width=208,height=38)
        self.activity_slot.pack(side="left",padx=(28,0),anchor="center")
        self.activity_slot.pack_propagate(False)
        self.progress=ActivityIndicator(self.activity_slot,self.localized_var('Processando'),self.status)
        self.button(header,"Configurações",self.settings).pack(side="right")
        self.help_btn=self.button(header,"? Ajuda",self.show_help);self.help_btn.pack(side="right",padx=(8,0))
        self.project_tools_btn=self.button(header,"Ferramentas de Projeto",self.project_tools);self.project_tools_btn.pack(side="right",padx=(8,0))
        self.button(header,"Continuar projeto",self.recent_projects).pack(side="right",padx=8)
        self.open_external_btn=self.button(header,"Abrir voz externa",self.open_external)
        self.open_external_btn.pack(side="right")
        self.migrate_btn=self.button(header,"Migrar banco antigo",lambda:self.open_external(migrate=True));self.migrate_btn.pack(side="right",padx=(0,8))
        counts=ttk.Frame(self,padding=(22,0));counts.pack(fill="x")
        self.project_identity_panel=RoundedPanel(counts,padx=12,pady=6)
        self.project_identity_panel.pack(side="left",expand=True,fill="x",padx=(0,10))
        header_project.build(self,self.project_identity_panel)
        self.bank_stat=self.localized_var("Nenhum banco aberto");self.voice_stat=tk.StringVar(value="—");self.replace_stat=tk.StringVar(value="0");self.silence_stat=tk.StringVar(value="—")
        for title,var in [("BANCO ATUAL",self.bank_stat),("VOZES DO BANCO",self.voice_stat),("NOVAS SUBSTITUIÇÕES",self.replace_stat),("SERÃO SILENCIADOS",self.silence_stat)]:
            box=RoundedPanel(counts,padx=12,pady=6);box.pack(side="left",expand=True,fill="x",padx=(0,10))
            if title=="BANCO ATUAL":
                current_bank_identity.build(self,box);continue
            self.localize_widget(tk.Label(box,bg=PANEL,fg=MUTED,font=("Segoe UI",9,"bold")),title).pack(side="left")
            value_label=tk.Label(box,textvariable=var,bg=PANEL,fg=FG,font=("Segoe UI",11,"bold"),width=3,anchor="e")
            value_label.pack(side="right",padx=(12,0))
            if title=="NOVAS SUBSTITUIÇÕES":
                def recolor_replacements(*_,label=value_label):label.configure(fg=modern_theme.SUCCESS if self.replace_stat.get().isdigit() and int(self.replace_stat.get())>0 else FG)
                self.replace_stat.trace_add("write",recolor_replacements)
            elif title=="SERÃO SILENCIADOS":
                def recolor_silence(*_,label=value_label):label.configure(fg=modern_theme.WARNING if self.silence_stat.get().isdigit() and int(self.silence_stat.get())>0 else FG)
                self.silence_stat.trace_add("write",recolor_silence)
        body=ttk.Frame(self,padding=(22,12))
        left=ttk.Frame(body,width=400);left.pack(side="left",fill="y",padx=(0,16));left.pack_propagate(False)
        self.label(left,"BANCOS DE VOZ",style="Subtitle.TLabel").pack(anchor="w",pady=(0,10))
        self.label(left,"Personagem ou código BTLCV",style="Muted.TLabel").pack(anchor="w",pady=(0,3))
        bank_search_row=ttk.Frame(left);bank_search_row.pack(fill="x")
        self.bank_search_entry=ttk.Entry(bank_search_row,textvariable=self.bank_query)
        self.bank_search_entry.pack(side="left",fill="x",expand=True,padx=(0,8))
        langs=ttk.Combobox(bank_search_row,textvariable=self.lang,values=["US","JP"],state="readonly",width=5)
        langs.pack(side="right");self.bank_language_choice=langs
        langs.bind("<<ComboboxSelected>>",lambda e:self.fill_banks())
        self.bank_sort_choice=self.choice(left,self.bank_sort,[("name_asc","BTLCV: menor número"),("name_desc","BTLCV: maior número"),
            ("character_asc","Personagem: A–Z"),("character_desc","Personagem: Z–A"),
            ("count_asc","Vozes: menor quantidade"),("count_desc","Vozes: maior quantidade")],width=28,onchange=self.fill_banks)
        self.bank_sort_choice.pack(fill="x",pady=(8,3))
        ttk.Label(left,textvariable=self.bank_filter_hint,style="Muted.TLabel",wraplength=310).pack(anchor="w")
        bankframe=ttk.Frame(left);bankframe.pack(fill="both",expand=True,pady=10)
        self.bank_list=BankTable(bankframe)
        self.bank_list.set_headers((self.tr("Personagem"),self.tr("ID"),"BTLCV"))
        self.bank_scroll=ttk.Scrollbar(bankframe,orient="vertical",command=self.bank_list.yview)
        self.bank_list.canvas.configure(yscrollcommand=self.bank_scroll.set)
        bankframe.rowconfigure(0,weight=1);bankframe.columnconfigure(0,weight=1)
        self.bank_list.grid(row=0,column=0,sticky="nsew")
        self.bank_scroll.grid(row=0,column=1,sticky="ns")
        self.bank_list.bind("<Double-1>",lambda e:self.load_selected_bank())
        self.bank_list.bind("<Return>",lambda e:self.load_selected_bank())
        self.button(left,"Abrir banco",self.load_selected_bank,True).pack(fill="x")
        self.label(left,"US e JP preservados.\nDuplo clique para abrir.",style="Muted.TLabel").pack(anchor="w",pady=10)
        right=ttk.Frame(body);right.pack(side="right",fill="both",expand=True)
        self.voice_toolbar=ttk.Frame(right);self.voice_toolbar.pack(fill="x",pady=(0,6))
        self.voice_counter_stack=ttk.Frame(self.voice_toolbar)
        self.voice_counter_stack.pack(side="right",anchor="n",padx=(12,0))
        filter_content=ttk.Frame(self.voice_toolbar);filter_content.pack(side="left",fill="x",expand=True)
        filterbar=ttk.Frame(filter_content);filterbar.pack(fill="x",pady=(0,6))
        search_field=design_clarity.field(self,filterbar,"Busca")
        self.voice_search_entry=ttk.Entry(search_field,textvariable=self.search,width=34)
        self.voice_search_entry.pack(side="left",fill="x",expand=True)
        design_clarity.search_hint(self,self.voice_search_entry)
        view_field=design_clarity.field(self,filterbar,"Estado da voz")
        self.view_choice=self.choice(view_field,self.view_filter,[("all","Todas as vozes"),("replaced","Substituídas"),("silence","Silêncio"),("duplicates","WAVs repetidos")],width=22,onchange=self.change_voice_view)
        self.view_choice.pack(side="left",fill="x",expand=True)
        self.filtered_count=tk.StringVar(value=self.tr("Vozes exibidas: {shown} de {total}").format(shown=0,total=0))
        self.filtered_count_label=modern_theme.CounterBadge(self.voice_counter_stack,self.filtered_count,compact=True)
        self.filtered_count_label.pack(fill="x",pady=(0,4))
        filters=ttk.Frame(filter_content);filters.pack(fill="x")
        sort_field=design_clarity.field(self,filters,"Ordenação")
        self.sort_choice=self.choice(sort_field,self.audio_sort,[("name_asc","Nome: A–Z"),("name_desc","Nome: Z–A"),
            ("function_asc","Função: A–Z"),("function_desc","Função: Z–A"),
            ("cue_asc","Cue ID: crescente"),("cue_desc","Cue ID: decrescente")],width=19,onchange=self.fill_rows)
        self.sort_choice.pack(side="left",fill="x",expand=True)
        scope_field=design_clarity.field(self,filters,"Tipo")
        self.scope_choice=self.choice(scope_field,self.function_scope,[("all","Todos os tipos"),("functions","Funções sem interações"),("interactions","Somente interações"),("emotes","Somente emotes")],width=22,onchange=self.change_function_scope)
        self.scope_choice.pack(side="left",fill="x",expand=True)
        function_field=design_clarity.field(self,filters,"Função")
        self.function_choice=self.choice(function_field,self.function_filter,[("*","Todas as funções"),("+","Somente funções identificadas"),("~","Sem função identificada")],width=38,onchange=self.fill_rows,translate=False)
        self.function_choice.pack(side="left",fill="x",expand=True)
        self.duplicate_count=tk.StringVar(value=self.tr("Repetidas: {voices} em {groups} grupos").format(voices=0,groups=0))
        self.duplicate_count_label=modern_theme.CounterBadge(self.voice_counter_stack,self.duplicate_count,duplicates=True,compact=True)
        self.duplicate_count_label.pack(fill="x")
        comparisons=ttk.Frame(filters);comparisons.pack(side="left",padx=(8,0))
        self.compare_duplicates_btn=self.button(comparisons,"Comparar repetidas da selecionada",self.compare_duplicates)
        self.compare_duplicates_btn.pack(side="left");self.compare_duplicates_btn.configure(state="disabled")
        self.all_duplicates_btn=self.button(comparisons,"Todas as repetidas",self.show_all_duplicates)
        self.all_duplicates_btn.pack(side="left",padx=(8,0))
        self.duplicate_context=tk.StringVar(value="")
        ttk.Label(comparisons,textvariable=self.duplicate_context,style="Muted.TLabel").pack(side="left",padx=(12,0))
        self.voice_legend=ttk.Frame(right)
        self.voice_legend.pack(fill="x",pady=(0,6))
        self.label(self.voice_legend,"Legenda das cores nas vozes",foreground=MUTED,font=("Segoe UI",9)).pack(side="left",padx=(0,16))
        self.legend_labels=[]
        for caption,color in [("● Customizada / diferente",modern_theme.SUCCESS),("● Repetida: mesmo áudio em outras vozes",modern_theme.WARNING),("● Comparação incerta",modern_theme.INFO),("● Semelhante / sem substituição",FG),("● Função manual",modern_theme.MANUAL)]:
            label=self.label(self.voice_legend,caption,foreground=color,font=("Segoe UI",9))
            label.pack(side="left",padx=(0,18));self.legend_labels.append(label)
        split=ttk.Panedwindow(right,orient="vertical");split.pack(fill="both",expand=True)
        self.split=split
        split.bind("<Configure>",self.queue_inspector_fit)
        gridframe=ttk.Frame(split);split.add(gridframe,weight=3)
        self.tree=VoiceTable(gridframe,columns=("file","function","duplicate","tags","cues","duration","state"),show="headings",selectmode="browse")
        self.headings={}
        for col,label,width in [("file","NOME ORIGINAL",180),("function","FUNÇÃO",280),("tags","TAG ORIGINAL",180),("cues","CUE IDs",160),("duration","BASE (s)",95),("state","EXPORTAÇÃO",120),("duplicate","REPETIDA COM",140)]:
            self.headings[col]=label;self.tree.heading(col,text=self.tr(label));self.tree.column(col,width=width,minwidth=65)
        gridframe.rowconfigure(0,weight=1);gridframe.columnconfigure(0,weight=1)
        self.voice_scroll=ttk.Scrollbar(gridframe,orient="vertical",command=self.tree.yview)
        self.voice_xscroll=ttk.Scrollbar(gridframe,orient="horizontal",command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.voice_scroll.set,xscrollcommand=self.voice_xscroll.set)
        self.tree.grid(row=0,column=0,sticky="nsew")
        self.empty_bank_prompt=tk.Frame(gridframe,bg=PANEL,padx=18,pady=14)
        self.localize_widget(tk.Label(self.empty_bank_prompt,bg=PANEL,fg=FG,font=("Segoe UI",14,"bold")),"Escolha um banco de voz para começar").pack()
        instruction=self.localize_widget(tk.Label(self.empty_bank_prompt,bg=PANEL,fg=MUTED,font=("Segoe UI",10),justify="center"),"Abra a lista de bancos, escolha um personagem e clique em Abrir banco.")
        instruction.pack(pady=(8,0))
        gridframe.bind("<Configure>",lambda event:instruction.configure(wraplength=max(180,min(650,event.width-60))),add="+")
        self.empty_bank_prompt.place(relx=.5,rely=.5,anchor="center")

        self.voice_scroll.grid(row=0,column=1,sticky="ns")
        # All voice columns fit the viewport; horizontal scrolling is unnecessary.
        self.tree.tag_configure("manual",column_foregrounds={"function":modern_theme.MANUAL})
        self.tree.tag_configure("replaced",foreground=modern_theme.SUCCESS)
        self.tree.tag_configure("uncertain",foreground=modern_theme.INFO)
        self.tree.tag_configure("alternate",background=modern_theme.ALTERNATE)
        self.tree.bind("<<TreeviewSelect>>",lambda e:self.select())
        self.tree.bind("<Double-1>",lambda e:self.play_original())
        detail=ttk.Frame(split,padding=(0,8,0,0));split.add(detail,weight=0)
        detail.bind("<Configure>",self.queue_inspector_fit)
        self.selection_title=self.localized_var("Escolha um banco de voz para começar")
        selection_header=ttk.Frame(detail);selection_header.pack(fill="x")
        ttk.Label(selection_header,textvariable=self.selection_title,font=("Segoe UI",10,"bold")).pack(side="left")
        self.english=tk.StringVar(value="")
        description=tk.Label(detail,textvariable=self.english,bg=BG,fg=MUTED,font=("Segoe UI",9),height=2,width=1,anchor="nw",justify="left")
        self.inspector_description=description
        description.pack(fill="x",pady=(2,6))
        description.bind("<Configure>",lambda e:description.configure(wraplength=max(300,e.width)))
        tabs=ttk.Notebook(detail);tabs.pack(fill="both",expand=True)
        studio=ttk.Frame(tabs);detailframe=ttk.Frame(tabs)
        tabs.add(studio,text=self.tr("Áudio e volume"));tabs.add(detailframe,text=self.tr("Detalhes e tags"))
        self.setup_original_text(tabs)
        self.detail_tabs=tabs
        self._detail_tab_titles=((studio,"Áudio e volume"),(detailframe,"Detalhes e tags"),(self.original_text_frame,"Texto original"))
        self.inspector_tabs=tabs
        self.canvas=tk.Canvas(studio,height=60,bg=PANEL,highlightthickness=0);self.canvas.pack(fill="both",expand=True,pady=(5,0))
        self.canvas.bind("<Configure>",lambda event:self.redraw_waves())
        actions=ttk.Frame(detail);self.audio_action_frame=actions;actions.pack(fill="x",pady=4,before=description)
        self.inspector_caption=self.localized_var("Mostrar detalhes")
        self.inspector_toggle=self.button(actions,"Mostrar detalhes",self.toggle_inspector)
        self.inspector_toggle.configure(textvariable=self.inspector_caption)
        self.inspector_toggle.pack(side="left",padx=(0,8))
        self.play_btn=self.button(actions,"▶ Ouvir original",self.play_original);self.play_btn.pack(side="left")
        self.custom_btn=self.button(actions,"▶ Ouvir voz editada",self.play_edited);self.custom_btn.pack(side="left",padx=6)
        self.custom_btn.configure(state="disabled")
        self.import_btn=self.button(actions,"Importar áudio",self.import_audio,True);self.import_btn.pack(side="right")
        self.microphone_btn=self.button(actions,"Gravar voz",self.record_voice);self.microphone_btn.pack(side="right",padx=(6,0));self.microphone_btn.configure(state="disabled")
        self.wav_drop=FileDrop(self.import_btn,self.drop_wav)
        self.remove_btn=self.button(actions,"Remover substituição",self.remove);self.remove_btn.pack(side="right",padx=6)
        self.audio_controls=ttk.Frame(detail)
        self.audio_controls.pack(fill="x",pady=(3,0))
        volume=ttk.Frame(self.audio_controls,style="Volume.TFrame",padding=(10,4));volume.pack(fill="x")
        self.compact_volume=volume
        meters=tk.Frame(volume,bg=PANEL);meters.pack(fill="x")
        self.meter_values={}
        for title,color in [("ORIGINAL",MUTED),("IMPORTADA",modern_theme.SUCCESS),("APÓS AJUSTE",FG)]:
            frame=tk.Frame(meters,bg=PANEL);frame.pack(side="left",padx=(0,22))
            self.localize_widget(tk.Label(frame,bg=PANEL,fg=color,font=("Segoe UI",8,"bold")),title).pack(anchor="w")
            readings=tk.Frame(frame,bg=PANEL);readings.pack(anchor="w",pady=(1,0))
            variables=[];labels=[]
            for caption in ("Pico","RMS ativo"):
                self.localize_widget(tk.Label(readings,bg=PANEL,fg=MUTED,font=("Segoe UI",9)),caption).pack(side="left",padx=(0,5))
                value=tk.StringVar(value="—");variables.append(value)
                label=tk.Label(readings,textvariable=value,bg=PANEL,fg=FG,font=("Segoe UI",9,"bold"),anchor="w",width=10)
                label.pack(side="left",padx=(0,10));labels.append(label)
            self.meter_values[title]=variables
            if title=="APÓS AJUSTE":self.adjusted_meter_labels=labels
        self.compact_wave=tk.Canvas(meters,width=180,height=38,bg=PANEL,highlightthickness=0)
        self.compact_wave.pack(side="left",expand=True,fill="both",padx=(0,4))
        self.compact_wave.bind("<Configure>",lambda event:self.redraw_waves())
        self.variation_hint=tk.StringVar(value="")
        tk.Label(meters,textvariable=self.variation_hint,bg=PANEL,fg=MUTED,font=("Segoe UI",9)).pack(side="right")
        controls=tk.Frame(volume,bg=PANEL);controls.pack(fill="x",pady=(2,0))
        controls.columnconfigure(2,weight=1,minsize=100)
        variationbar=tk.Frame(controls,bg=PANEL);variationbar.grid(row=0,column=0,sticky="w",padx=(0,12))
        self.localize_widget(tk.Label(variationbar,bg=PANEL,fg=MUTED,font=("Segoe UI",9)),"Variação da voz").pack(side="left",padx=(0,8))
        self.variation_buttons=[]
        for value,title in [(1,"1 — Original"),(2,"2 — Mais rápida"),(3,"3 — Mais lenta")]:
            button=ttk.Radiobutton(variationbar,text=self.tr(title),value=value,variable=self.variation,command=self.change_variation,style="Compact.TRadiobutton")
            self.localize_widget(button,title);button.pack(side="left",padx=(0,8));self.variation_buttons.append(button)
        self.localize_widget(tk.Label(controls,bg=PANEL,fg=MUTED,font=("Segoe UI",9)),"Ganho da voz importada").grid(row=0,column=1,sticky="w")
        self.volume_slider=ttk.Scale(controls,from_=-48,to=24,variable=self.gain,command=self.change_gain)
        self.volume_slider.grid(row=0,column=2,sticky="ew",padx=10)
        tk.Label(controls,textvariable=self.gain_text,bg=PANEL,fg=FG,width=9,font=("Consolas",10,"bold")).grid(row=0,column=3)
        self.match_btn=self.button(controls,"Igualar ao original",self.match_original);self.match_btn.grid(row=0,column=4,padx=6)
        self.reset_gain_btn=self.button(controls,"Zerar ganho",self.reset_gain);self.reset_gain_btn.grid(row=0,column=5)
        self.volume_note=tk.Label(self.audio_controls,textvariable=self.volume_warning,bg=BG,fg=MUTED,font=("Segoe UI",9),height=2,width=1,anchor="nw",justify="left")
        self.volume_note.pack(fill="x",pady=(2,0))
        self.volume_note.bind("<Configure>",lambda event:self.volume_note.configure(wraplength=max(200,event.width)))
        self.setup_audio_trim(detail)
        self.manual_btn=self.button(detailframe,"Identificar voz",self.identify_voice);self.manual_btn.pack(anchor="e",pady=(4,6),padx=8)
        self.details=tk.Text(detailframe,height=4,bg=PANEL,fg=MUTED,font=("Consolas",10),relief="flat",wrap="word",padx=12,pady=10)
        self.detail_scroll=ttk.Scrollbar(detailframe,orient="vertical",command=self.details.yview)
        self.details.configure(yscrollcommand=self.detail_scroll.set)
        self.detail_scroll.pack(side="right",fill="y")
        self.details.pack(side="left",fill="both",expand=True);self.details.configure(state="disabled")
        tabs.pack_forget();description.pack_forget()
        self.update_levels()
        export_canvas=compact_export_layout.create(self)
        footer=RoundedPanel(export_canvas,padx=12,pady=10)
        self.export_panel=footer
        compact_export_layout.install(self,footer)
        style=ttk.Style(self)
        style.configure("Export.TFrame",background=PANEL)
        style.configure("Export.TLabel",background=PANEL,foreground=FG)
        style.configure("ExportMuted.TLabel",background=PANEL,foreground=MUTED,font=("Segoe UI",9))
        style.configure("ExportTitle.TLabel",background=PANEL,foreground=FG,font=("Segoe UI",9,"bold"))
        bottom=ttk.Frame(footer,style="Export.TFrame");bottom.pack(fill="x")
        self.label(bottom,"EXPORTAÇÃO",style="ExportTitle.TLabel").pack(side="left",padx=(0,14))
        self.mode_choice=self.choice(bottom,self.export_mode,[("package","Replacer (.pak / .utoc / .ucas)"),("audio_pak","Custom (.uasset + AWB .pak)")],width=28)
        self.mode_choice.pack(side="left")
        self.destination_btn=self.button(bottom,"Escolher pasta",self.choose_destination)
        self.destination_btn.pack(side="left",padx=8)
        self.destination_label=ttk.Entry(bottom,textvariable=self.destination,width=32,state="readonly")
        self.destination_label.pack(side="left",fill="x",expand=True,padx=(0,12))
        # Primary export action at the far right; folders and project actions precede it.
        self.export_btn=self.button(bottom,"Exportar banco",self.export,True);self.export_btn.pack(side="right")
        self.folders_btn=self.button(bottom,"Abrir pasta ▾",self.show_folder_menu)
        self.folders_btn.pack(side="right",padx=(0,8))
        self.folder_menu=tk.Menu(self,tearoff=False,bg=modern_theme.CARD,fg=FG,
            activebackground="#222d3a",activeforeground=FG,relief="flat",borderwidth=1,
            font=("Segoe UI",10))
        self.save_project_btn=self.button(bottom,"Salvar projeto",self.save_project);self.save_project_btn.pack(side="right",padx=(0,8))
        self.project_name_btn=self.button(bottom,"Nome do projeto",self.rename_project);self.project_name_btn.pack(side="right",padx=(0,8))
        self.replacer_folder_btn=self.button(bottom,"Nome da pasta Replacer",lambda:replacer_folder.rename(self));self.replacer_folder_btn.pack(side="right",padx=(0,8))
        self.custom_engine_notice_row=ttk.Frame(footer,style="Export.TFrame")
        self.custom_engine_notice_row.columnconfigure(2,weight=1)
        self.custom_engine_notice=ttk.Label(self.custom_engine_notice_row,text=self.tr('Custom: escolha as pastas da Custom Engine e do CustomProject.'),style="ExportMuted.TLabel",foreground=modern_theme.WARNING,wraplength=1100)
        self._texts.append((self.custom_engine_notice,'Custom: escolha as pastas da Custom Engine e do CustomProject.'))
        self.custom_engine_notice_row.bind("<Configure>",lambda e:custom_setup_status.layout(self))
        self.custom_engine_notice.grid(row=0,column=0,sticky="ew",padx=(0,14))
        self.custom_setup_status=ttk.Label(self.custom_engine_notice_row,style="ExportMuted.TLabel",font=("Segoe UI",9,"bold"),wraplength=260)
        self.custom_setup_status.grid(row=0,column=1,sticky="w")
        self.custom_setup_status.bind("<Configure>",lambda e:custom_setup_status.layout(self))
        output_row=ttk.Frame(footer,style="Export.TFrame");output_row.pack(fill="x",pady=(8,0))
        # Both modes share this information row; switching only changes state.
        self.custom_engine_notice_row.pack(fill="x",pady=(8,0),before=output_row)
        custom_setup_status.update(self)
        self.label(output_row,"Nome do banco (Custom)",style="Export.TLabel").pack(side="left",padx=(0,10))
        self.export_name_entry=ttk.Entry(output_row,textvariable=self.export_name,width=28)
        self.export_name_entry.pack(side="left")
        self.maximize_btn=self.button(output_row,"Maximizar volume",self.maximize_volume);self.maximize_btn.pack(side="right",padx=(8,0))
        self.clipping_btn=self.button(output_row,"Corrigir clipping",self.correct_clipping);self.clipping_btn.pack(side="right",padx=(8,0))
        self.volume_scope_choice=self.choice(output_row,self.volume_scope,[("selected","Voz selecionada"),("bank","Banco: customizadas")],width=19)
        self.volume_scope_choice.pack(side="right",padx=(8,0))
        self.effects_btn=self.button(output_row,"Efeitos de voz ▾",self.show_voice_effects_menu);self.effects_btn.pack(side="right",padx=(8,0))
        self.audio_treatment_label=self.label(output_row,"Tratamento de áudio",style="ExportMuted.TLabel")
        self.audio_treatment_label.pack(side="right",padx=(12,0))
        self.history.setup(output_row)
        def update_export_name_state(*_):
            replacer_folder.sync_button(self)
            custom=self.export_mode.get()!="package"
            self.export_name_entry.configure(state="normal" if custom else "disabled",style="Required.TEntry" if custom else "TEntry")
            self.project_name_btn.configure(style="Required.TButton" if custom else "Navigate.TButton",
                image=(button_identity.icon(self,"edit",button_identity.PALETTE["Required" if custom else "Navigate"][0]),
                    "disabled",button_identity.icon(self,"edit","#596270")))
        self.export_mode.trace_add("write",update_export_name_state);update_export_name_state()
        self.label(output_row,"BTLCV + ID do personagem custom + US/JP.",style="ExportMuted.TLabel",foreground=modern_theme.WARNING).pack(side="left",padx=12)
        foot=ttk.Frame(footer,style="Export.TFrame");foot.pack(fill="x",pady=(6,0))
        # Keep the footer geometry unchanged during preparing/playback/status updates.
        self.status_label=tk.Label(foot,textvariable=self.status,bg=PANEL,fg=MUTED,borderwidth=0,padx=0,pady=0,font=("Segoe UI",9),height=1,width=1,anchor="w",justify="left")
        self.status_label.pack(side="left",fill="x",expand=True)
        # Reserve header and footer controls before giving the remaining space to the lists.
        body.pack(fill="both",expand=True)
        self.filter_frame=filterbar;self.advanced_frames=[filters,self.voice_legend]
        design_clarity.install(self,filter_content,selection_header)
        self.setup_responsive(body,left,right,[header,counts,filterbar,filters,comparisons,self.voice_legend,actions,self.trim_panel,meters,controls,bottom,output_row],
            {counts:counts.pack_slaves(),filters:[function_field],filterbar:[search_field],bottom:[self.destination_label],meters:[self.compact_wave],controls:[self.volume_slider]},header)
    def report_callback_exception(self,exc,value,tb):
        ui_reliability.callback_error(self,exc,value,tb)

    def poll(self):
        if self._destroyed:return
        pending=getattr(self,'_poll_after',None)
        if pending is not None:
            self.after_cancel(pending);self._poll_after=None
        ui_reliability.heartbeat(self)
        kind='poll'
        try:
            while True:
                try:kind,payload=self.jobs.get_nowait()
                except queue.Empty:break
                if kind=="catalog":
                    generation,counts=payload
                    if generation==self.catalog_generation:
                        self.bank_counts=counts;self.catalog_ready=True;self.fill_banks()
                elif kind=="levels":
                    token,result=payload
                    if token==self.level_token and self.selected:
                        self.level_data=result;self.update_levels()
                elif kind=="character_names":self.finish_character_catalog(payload)
                elif kind=="game_inventory":self.finish_game_inventory(payload)
                elif kind=="voice_text":self.finish_original_text(payload)
                elif kind=="project_audio_error":self.status.set("Falha ao atualizar os áudios do projeto: "+payload)
                elif kind=="status":self.status.set(payload)
                elif kind=="export_progress":
                    window=getattr(self,"_export_progress_window",None)
                    if window is not None:window.update(*payload)
                elif kind=="cancelled":
                    self.busy=False;self.progress.stop();self.export_btn.configure(state="normal")
                    self._diagnostic_operation=None;self.finish_export_progress();self.status.set(payload)
                elif kind=="ok":
                    ui_reliability.event('job_finished',operation=getattr(self,'_diagnostic_operation',None),seconds=round(time.monotonic()-getattr(self,'_diagnostic_job_start',time.monotonic()),3))
                    self._diagnostic_operation=None
                    fn,value=payload;self.busy=False;self.progress.stop();self.export_btn.configure(state="normal");self.finish_export_progress()
                    fn(value)
                    if self._destroyed:return
                elif kind=="error":
                    ui_reliability.event('job_failed',operation=getattr(self,'_diagnostic_operation',None),message=str(payload)[:400])
                    self._diagnostic_operation=None
                    self.project_renaming=False
                    self.busy=False;self.progress.stop();self.export_btn.configure(state="normal");self.finish_export_progress();self.fail(payload)
            self.history.update_buttons()
        except Exception:
            if kind in ('ok','error'):
                self.busy=False;self.project_renaming=False;self.progress.stop()
                self.export_btn.configure(state='normal')
            ui_reliability.callback_error(self,*__import__('sys').exc_info(),context='task queue: '+kind)
        finally:
            if not self._destroyed:
                ui_reliability.heartbeat(self)
                self._poll_after=self.after(100,self.poll)
    def job(self,fn,done,text,edit_label=None,operation=None):
        if self.busy:return
        try:before=self.history.begin() if edit_label else None
        except Exception as error:self.fail(str(error));return
        if edit_label:
            callback=done
            def done(value):
                callback(value)
                self.history.finish(before,edit_label)
        if operation is not None:
            try:self._export_progress_window=export_operations.ProgressWindow(self,operation)
            except Exception as error:self.fail(str(error));return
        self._diagnostic_operation=str(text)[:300];self._diagnostic_job_start=time.monotonic()
        ui_reliability.event('job_started',operation=self._diagnostic_operation)
        self.busy=True;self.history.update_buttons();self.status.set(text);self.progress.start(12);self.export_btn.configure(state="disabled")
        def worker():
            try:self.jobs.put(("ok",(done,fn())))
            except export_operations.Cancelled as e:
                self.jobs.put(("cancelled",str(e)))
            except Exception as e:
                ui_reliability.record_error(type(e),e,e.__traceback__,'worker: '+str(text)[:300])
                try:(core.APP/"error.log").write_text(traceback.format_exc(),encoding="utf-8")
                except OSError:pass
                self.jobs.put(("error",str(e)))
        threading.Thread(target=worker,daemon=True).start()
    def finish_export_progress(self):
        window=getattr(self,"_export_progress_window",None)
        if window is not None:window.finish();self._export_progress_window=None
    def fail(self,text):
        self.status.set(text);support_report.show(self,text)
    def fill_banks(self):
        if not hasattr(self,"bank_list"):return
        selected_name=None
        selection=self.bank_list.curselection()
        if selection and selection[0]<len(getattr(self,"visible_banks",[])):selected_name=self.visible_banks[selection[0]]
        query=self.bank_query.get().casefold().strip();names=[]
        for name in getattr(self,"banks",[]):
            if not name.endswith("_"+self.lang.get()) or query not in (name+" "+self.character_names.get(core.character_id(name),"")).casefold():continue
            count=self.bank_counts.get(name)
            names.append(name)
        order=self.bank_sort.get()
        if order.startswith("count"):
            names.sort(key=lambda name:(self.bank_counts.get(name) is None,
                (self.bank_counts.get(name) or 0)*(-1 if order=="count_desc" else 1),name))
        elif order.startswith("character"):
            # Unlisted IDs remain available and stay after named banks in both directions.
            known=[name for name in names if core.character_id(name) in self.character_names]
            unknown=[name for name in names if core.character_id(name) not in self.character_names]
            known.sort(key=lambda name:(self.character_names[core.character_id(name)].casefold(),name),reverse=order=="character_desc")
            names=known+sorted(unknown)
        else:names.sort(reverse=order=="name_desc")
        self.visible_banks=names
        self.bank_list.set_rows([(self.translator.display(self.character_names.get(core.character_id(name),core.character_id(name) or name)),core.character_id(name),name) for name in names])
        if selected_name in names:
            index=names.index(selected_name);self.bank_list.selection_set(index);self.bank_list.see(index)
        self.bank_filter_hint.set("Contando vozes..." if not self.catalog_ready else self.tr("{count} bancos").format(count=len(names)) if names else "Sem bancos para este filtro.")
    def load_selected_bank(self):
        sel=self.bank_list.curselection()
        if sel:self.load_bank(self.visible_banks[sel[0]])
    def open_external(self,migrate=False,on_source=None,parent=None):
        if migrate and on_source is None:
            import window_toggle
            if window_toggle.existing(self,'migration_window'):return
        if self.busy:return
        parent=parent or self
        selected=filedialog.askopenfilename(parent=parent,title=self.tr("Abra um banco de voz ou pacote de mod"),
            filetypes=[(self.tr("Voz Unreal ou CRI"),("*.uasset","*.acb","*.awb","*.pak","*.utoc","*.ucas")),(self.tr("Pacote de voz"),("*.pak","*.utoc","*.ucas")),(self.tr("Banco ACB"),"*.acb"),(self.tr("Asset Unreal"),"*.uasset")])
        if not selected:return
        path=Path(selected)
        if path.suffix.lower() in ('.pak','.utoc','.ucas'):
            self.job(lambda:package_import.extract(self.cfg,path),lambda banks:self.choose_package_voice(banks,migrate,on_source,parent),"Lendo pacote de vozes...")
            return
        acb=None;uexp=None;asset=None;name=None;selected_awb=None
        if path.suffix.lower()==".awb":
            selected_awb=path
            companion=next((path.with_suffix(ext) for ext in (".uasset",".acb") if path.with_suffix(ext).exists()),None)
            if companion is None:
                chosen=filedialog.askopenfilename(parent=parent,title=self.tr("Abra um ACB + AWB ou um asset de voz já editado"),initialdir=path.parent,
                    filetypes=[(self.tr("Voz Unreal ou CRI"),("*.uasset","*.acb"))])
                if not chosen:return
                companion=Path(chosen)
            path=companion
        if path.suffix.lower()==".acb":
            acb=path;companion=path.with_suffix(".uasset")
            if companion.exists():
                try:
                    raw=companion.read_bytes()
                    if core.embedded_asset_supported(raw) and raw[:4]==b"\xc1\x83\x2a\x9e" and core.le(raw,12,4):
                        asset=companion;name=companion.stem
                except (OSError,ValueError) as e:self.fail(str(e));return
        else:
            asset=path;name=path.stem;uexp=path.with_suffix(".uexp")
            try:
                raw=path.read_bytes();is_zen=core.embedded_asset_supported(raw)
            except (OSError,ValueError) as e:self.fail(str(e));return
            if not uexp.exists() and not is_zen:
                companion=filedialog.askopenfilename(parent=parent,title=self.tr("Selecione o ACB ou o .uexp associado à voz"),
                    initialdir=path.parent,filetypes=[(self.tr("ACB ou export Unreal"),("*.acb","*.uexp")),(self.tr("Banco ACB"),"*.acb"),(self.tr("Export Unreal"),"*.uexp")])
                if not companion:return
                if Path(companion).suffix.lower()==".acb":acb=Path(companion);asset=None;uexp=None
                else:uexp=Path(companion)
        import export_delivery
        awb=selected_awb or export_delivery.companion(acb or path,".awb")
        if not awb.exists():
            chosen=filedialog.askopenfilename(parent=parent,title=self.tr("Selecione o AWB correspondente à voz editada"),
                initialdir=(acb or path).parent,filetypes=[(self.tr("Banco de áudio CRI"),"*.awb")])
            if not chosen:return
            awb=Path(chosen)
        if asset is None and name is None:
            try:
                named=any(core.re.fullmatch(r"BTLCV_[0-9]{4}_[0-9]{2}_(JP|US)",p.stem) for p in (acb,awb))
                language=None
                if not named:
                    language=localized_dialogs.askstring(self,self.tr("Idioma do banco"),self.tr("Informe JP ou US para escolher o template original:"),initialvalue=self.lang.get(),parent=parent)
                    if not language:return
                    language=language.strip().upper()
                name=core.acb_bank_name(acb,awb,language)
            except (ValueError,OSError) as e:self.fail(str(e));return
        external={"asset":str(asset) if asset else None,"awb":str(awb),"acb":str(acb) if acb else None,
            "uexp":str(uexp) if uexp and uexp.exists() else None,"bank_name":name}
        if on_source:on_source(external)
        elif migrate:self.prepare_migration(external)
        else:self.load_bank(name or path.stem,external=external)
    def choose_package_voice(self,banks,migrate=False,on_source=None,parent=None):
        parent=parent or self
        def open_bank(external):
            external=dict(external)
            if not external['asset'] and not external['acb']:
                messagebox.showinfo(self.tr('Pacote de voz'),self.tr('O pacote contém apenas o AWB. Selecione o UASSET/ACB da mesma versão; o app não usará o banco atual como substituto.'),parent=parent)
                chosen=filedialog.askopenfilename(parent=parent,title=self.tr('Selecione o UASSET/ACB antigo correspondente'),filetypes=[(self.tr('Voz Unreal ou CRI'),('*.uasset','*.acb'))])
                if not chosen:return
                path=Path(chosen);external['asset' if path.suffix.lower()=='.uasset' else 'acb']=str(path)
                if path.suffix.lower()=='.uasset' and path.with_suffix('.uexp').exists():external['uexp']=str(path.with_suffix('.uexp'))
            if on_source:on_source(external)
            elif migrate:self.prepare_migration(external)
            else:self.load_bank(external['bank_name'],external=external)
        if len(banks)==1:open_bank(banks[0]);return
        win=tk.Toplevel(parent);win.title(self.tr('Escolha o banco do pacote'));win.configure(bg=BG);win.geometry('550x190')
        if on_source:win.transient(parent);win.grab_set()
        self.label(win,'Escolha o banco de voz que deseja abrir.').pack(anchor='w',padx=20,pady=(18,10))
        names=[bank['bank_name'] for bank in banks];selected=tk.StringVar(value=names[0])
        ttk.Combobox(win,textvariable=selected,values=names,state='readonly').pack(fill='x',padx=20)
        def confirm():
            bank=banks[names.index(selected.get())];win.destroy()
            if on_source and parent.winfo_exists():parent.grab_set()
            open_bank(bank)
        def cancel():
            win.destroy()
            if on_source and parent.winfo_exists():parent.grab_set()
        win.protocol('WM_DELETE_WINDOW',cancel)
        self.button(win,'Abrir banco',confirm,True).pack(anchor='e',padx=20,pady=18)
    def load_bank(self,name,project=None,external=None):
        if self.busy or not self.confirm_leaving_project():return
        self.stop()
        def work():
            if project:
                previous=Path(project["project_file"]).parent
                if previous.resolve().is_relative_to((core.APP/"Projects").resolve()) and not project_names.project_parts(previous):
                    self.project_audio.wait()
                    folder,updated=project_names.relocate(previous,project.get("project_name") or name)
                    project.clear();project.update(updated);project["project_file"]=str(folder/"project.json")
            source=project.get("source") if project else None
            if external:
                bank=core.import_external_bank(self.cfg,**external)
                if external.get('package_origin'):bank.source['package_origin']=external['package_origin']
            elif source:bank=core.Bank(self.cfg,None,name,source)
            else:
                if self.pak is None:self.pak=core.Pak(self.cfg)
                bank=core.Bank(self.cfg,self.pak,name)
            reference=bank
            if bank.external:
                reference=None
                try:
                    if self.pak is None:self.pak=core.Pak(self.cfg)
                    reference=core.Bank(self.cfg,self.pak,bank_migration.infer_reference(bank) or name)
                except (OSError,ValueError,KeyError):pass
                bank.pak=self.pak
                try:core.classify_imported_audio(bank,reference)
                except (ValueError,KeyError,IndexError):core.classify_imported_audio(bank,None)
            if project:
                import bank_version
                updated,version_status=bank_version.resume(project,bank)
                if updated is not project:project.clear();project.update(updated)
                project['_bank_version_status']=version_status
            return bank,reference,migrated_audio.classify(project,bank)
        def done(result):
            bank,reference,self.migrated_original_audio=result
            self.migration=project.get("migration") if project else None
            self.bank=bank;self.reference_bank=reference;self.selected=None;self.duplicate_focus=None
            self.manual_identifications=session_features.clean_manual(project.get("manual_identifications",{}) if project else {},bank)
            if project and project.get("_recovery_path"):
                self.recovery.consumed=Path(project["_recovery_path"])
            self.export_name.set(project.get("export_name",bank.name) if project else bank.name)
            self.replacements=dict(project.get("replacements",{})) if project else {}
            self.trim_originals=trim_history.active(project.get("trim_originals",{}),self.replacements) if project else {}
            self.processing_originals=trim_history.active(project.get("processing_originals",{}),self.replacements) if project else {}
            self.effects_originals=trim_history.active(project.get("effects_originals",{}),self.replacements) if project else {};self.speed_originals=trim_history.active(project.get("speed_originals",{}),self.replacements) if project else {};self.duplicate_originals=trim_history.active(project.get("duplicate_originals",{}),self.replacements) if project else {}
            self.gains={key:audio_levels.valid_gain(value) for key,value in (project.get("gains",{}) if project else {}).items() if key in self.replacements}
            self.variations={key:audio_variations.valid(value) for key,value in (project.get("variations",{}) if project else {}).items() if key in self.replacements}
            self.variation.set(1)
            self.level_token+=1;self.level_signature=None;self.level_data={}
            self.keep_imported.set(self.cfg["unreplaced_policy"]=="original" if "unreplaced_policy" in self.cfg else (project["unreplaced_policy"]=="original" if "unreplaced_policy" in project else bool(self.bank.external) and project.get("keep_imported",True)) if project else bool(self.bank.external))

            self.project_temporary=not bool(project) or bool(project.get("temporary_session"))
            self.project=Path(project["project_file"]).parent if project else core.owned(core.APP/"Cache/Sessions"/uuid.uuid4().hex)
            self.project_name=(project.get("project_name") or name) if project else name
            self.project_id=project.get("project_id") if project else None
            self.replacer_folder_name=str(project.get("replacer_folder_name") or "") if project else ""
            self.project_usage_count=recent_projects.usage_count(project or {})+1
            self.project_last_opened=time.time()
            self.title("Sparking Zero Voice Studio • "+self.project_name)
            header_project.update(self)
            self.bank_stat.set(name+(" • Importada" if bank.external else ""));self.lang.set(bank.language);self.fill_banks()
            current_bank_identity.update(self,bank)
            self.search.set("");self.refresh_function_choices();self.fill_rows()
            self.bank_version_status=project.get('_bank_version_status',{}) if project else {}
            if project and not self.project_temporary and not self.bank_version_status.get('changed') and not (self.bank_version_status.get('legacy') and self.replacements):self.save_project(False)
            else:self._saved_project_snapshot="" if project else self.project_edit_snapshot()
            if bank.external:
                self.status.set(("ACB + AWB abertos e atribuídos ao template BTLCV. " if bank.source.get("import_kind")=="acb_awb" else "Voz externa aberta. ")+"Áudios importados mantidos; fontes preservadas."+
                    (" Original do jogo disponível para comparação." if reference else " Referência original do jogo indisponível."))
            else:self.status.set("Banco verificado • arquivos originais somente para leitura." if bank.compatible else "INCOMPATÍVEL: o AWB diverge do ACB. Exportação bloqueada.")
            if self.bank_version_status.get('automatic_migration'):
                status=self.bank_version_status
                self.status.set(self.tr('Projeto migrado automaticamente.')+' '+str(status['matched'])+' '+self.tr('edições recuperadas.')+
                    (' '+str(status['pending'])+' '+self.tr('edições sem correspondência preservadas no relatório: ')+status['report'] if status['pending'] else '')+
                    ' '+self.tr('Salve o projeto para manter a migração.'))
            elif self.bank_version_status.get('changed'):
                self.status.set(self.tr('Banco atualizado: edições conferidas por Cue ID e nome. Revise e salve o projeto para confirmar.'))
            elif self.bank_version_status.get('legacy') and self.replacements:
                self.status.set(self.tr('Projeto antigo sem referência de versão. Confira as vozes antes de exportar; salve para registrar a identidade atual.'))
            self.history.reset()
            children=self.tree.get_children()
            if children:self.tree.selection_set(children[0]);self.select()
        self.job(work,done,"Abrindo "+name+"...")
    def toggle_inspector(self):
        opened=not self.inspector_expanded.get();self.inspector_expanded.set(opened)
        if opened:
            self.inspector_description.pack(fill="x",pady=(2,4))
            self.inspector_tabs.pack(fill="both",expand=True)
        else:
            self.inspector_tabs.pack_forget();self.inspector_description.pack_forget()
        self.inspector_caption.set("Ocultar detalhes" if opened else "Mostrar detalhes")
        self._inspector_geometry=None
        self.queue_inspector_fit()
    def change_import_policy(self):
        self.fill_rows()
        self.status.set("Vozes não substituídas serão mantidas como no banco aberto." if self.keep_imported.get()
            else "Vozes sem nova substituição serão exportadas como silêncio.")
    def change_voice_view(self):
        self.duplicate_focus=None
        self.fill_rows()
    def show_all_duplicates(self):
        self.duplicate_focus=None
        self.search.set("");self.function_filter.set("*");self.view_filter.set("duplicates")
        self.fill_rows()
    def compare_duplicates(self):
        if not self.selected or self.busy:return
        key=self.selected["key"]
        if key not in self.duplicate_info:return
        self.search.set("");self.function_filter.set("*");self.view_filter.set("duplicates")
        self.duplicate_focus=key
        self.fill_rows()
        if self.tree.exists(key):self.tree.selection_set(key);self.select()
    def duplicate_partners(self,key):
        info=self.duplicate_info.get(key)
        if not info:return "—"
        return " / ".join(self.bank.wave_rows[other]["filename"] for other in info[1] if other!=key)
    def fill_rows(self):
        design_clarity.refresh(self)
        if not self.bank:return
        self.empty_bank_prompt.place_forget()
        prior=self.selected["key"] if self.selected else None
        self.duplicate_info=self.duplicate_wavs.find(duplicate_wavs_sources(self),self.bank.wave_rows)
        self.duplicate_count.set(self.tr("Repetidas: {voices} em {groups} grupos").format(voices=len(self.duplicate_info),groups=len({group for group,members in self.duplicate_info.values()})))
        focused=self.duplicate_info.get(self.duplicate_focus) if self.duplicate_focus else None
        self.duplicate_context.set(self.tr("Grupo {group} • {count} vozes").format(group=focused[0],count=len(focused[1])) if focused else self.tr("Nenhuma repetição nesta comparação.") if self.duplicate_focus else "")
        table_rows=[]
        query=self.search.get().casefold()
        order=self.audio_sort.get()
        if order.startswith("function"):
            rows=sorted(self.bank.rows,key=lambda row:(not bool(row["functions"]),self.function_text(row).casefold(),row["filename"].casefold()),reverse=order=="function_desc")
        elif order.startswith("cue"):
            # Shared audio uses its lowest Cue ID; entries without cues stay last.
            known=[row for row in self.bank.rows if row["cue_ids"]]
            unknown=[row for row in self.bank.rows if not row["cue_ids"]]
            rows=sorted(known,key=lambda row:(tuple(sorted(int(v) for v in row["cue_ids"])),row["filename"].casefold()),reverse=order=="cue_desc")
            rows+=sorted(unknown,key=lambda row:row["filename"].casefold())
        else:rows=sorted(self.bank.rows,key=lambda row:row["filename"].casefold(),reverse=order=="name_desc")
        if self.view_filter.get()=="duplicates":
            # Stable sorting keeps the chosen name/function order within each group.
            rows=sorted(rows,key=lambda row:self.duplicate_info.get(row["key"],(float("inf"),()))[0])
        for position,row in enumerate(rows):
            function=self.function_filter.get()
            if not voice_context.matches_filter(row,function,self.function_scope.get()):continue
            replaced=migrated_audio.is_replaced(self,row["key"])
            migrated_original=migrated_audio.is_original(self,row["key"])
            similarity=(self.bank.source or {}).get("audio_similarity",{}).get(row["key"],{}).get("status","uncertain") if self.bank.external else None
            if core.imported_is_original(self.bank,row):similarity="similar"
            filt=self.view_filter.get()
            if filt=="duplicates" and row["key"] not in self.duplicate_info:continue
            if filt=="duplicates" and self.duplicate_focus and (not focused or row["key"] not in focused[1]):continue
            if filt=="replaced" and not replaced or filt=="silence" and (replaced or migrated_original or core.preserve_unreplaced(self.bank,row,self.keep_imported.get())):continue
            hay=" ".join([row["filename"],*row["cue_names"],*row["functions"],*row["english"],self.function_text(row),voice_context.search_text(row),*map(str,row["cue_ids"])]).casefold()
            if query and query not in hay:continue
            table_rows.append((row["key"],{"values":(row["filename"],
                self.function_text(row),self.duplicate_partners(row["key"])," / ".join(row["functions"]) or self.tr("Sem tag específica"),
                ", ".join(map(str,row["cue_ids"])),f'{row["duration"]:.3f}s',
                self.tr("Customizada") if replaced else self.tr("Original") if migrated_original else self.tr("Importada" if self.bank.external and not core.imported_is_original(self.bank,row) else "Original") if core.preserve_unreplaced(self.bank,row,self.keep_imported.get()) else self.tr("Silêncio")),"tags":(("alternate",) if position%2 else ())+(("replaced",) if replaced or similarity=="different" else ("uncertain",) if similarity=="uncertain" else ())+(("manual",) if voice_context._user_functions.display_manual(row) else ())}))
        selection_unchanged=self.tree.selection()==(prior,)
        table_changed=self.tree.replace_rows(table_rows)
        self.filtered_count.set(self.tr("Vozes exibidas: {shown} de {total}").format(shown=len(self.tree.get_children()),total=len(self.bank.rows)))
        self.voice_stat.set(str(len(self.bank.rows)));self.replace_stat.set(str(sum(migrated_audio.is_replaced(self,key) for key in self.replacements)))
        self.silence_stat.set(str(sum(row["key"] not in self.replacements and not core.preserve_unreplaced(self.bank,row,self.keep_imported.get()) for row in self.bank.rows)))
        if prior and self.tree.exists(prior):
            self.tree.selection_set(prior)
            if table_changed and selection_unchanged:self.tree.event_generate("<<TreeviewSelect>>",when="tail")
        elif self.tree.get_children():self.tree.selection_set(self.tree.get_children()[0])
        else:
            self.stop();self.compact_wave.delete("all")
            self.selected=None;self.compare_duplicates_btn.configure(state="disabled");self.selection_title.set("Nenhum áudio corresponde a estes filtros.")
            design_clarity.refresh(self)
            self.english.set("");self.canvas.delete("all")
            self.level_token+=1;self.level_signature=None;self.level_data={};self.update_levels();self.update_original_text()
            self.details.configure(state="normal");self.details.delete("1.0","end");self.details.configure(state="disabled")
            for widget in (self.play_btn,self.custom_btn,self.import_btn,self.remove_btn,self.microphone_btn):widget.configure(state="disabled")
    def select(self):
        sel=self.tree.selection()
        if not sel:return
        if self.selected and self.selected["key"]!=sel[0]:self.stop()
        self.selected=self.bank.wave_rows[sel[0]];r=self.selected
        self.import_btn.configure(state="normal");self.remove_btn.configure(state="normal");self.microphone_btn.configure(state="normal")
        self.selection_title.set(r["filename"])
        design_clarity.refresh(self)
        self.compare_duplicates_btn.configure(state="normal" if r["key"] in self.duplicate_info else "disabled")
        functions=" / ".join(r["functions"]) or self.tr("Sem tag específica")
        self.english.set(self.function_text(r))
        text="Nomes dos cues: "+", ".join(r["cue_names"])+"\nIDs dos cues: "+", ".join(map(str,r["cue_ids"]))
        text+="\nFunção / tag original: "+functions
        contexts=voice_context.details(r,self.function_language.get())
        if contexts:text+="\n\n"+self.tr("Contextos do banco original:")+"\n"+contexts
        if self.bank.external:
            text+="\nBase: banco externo importado (cópia interna; arquivos de origem preservados)."
            reference=core.reference_row(self.bank,self.reference_bank,r)
            if reference:
                text+=f"\nOriginal do jogo: {reference['duration']:.3f}s • Importado: {r['duration']:.3f}s"
                text+="\n"+self.tr("Referência por cue: ")+reference['filename']
            similarity=(self.bank.source or {}).get('audio_similarity',{}).get(r['key'],{}).get('status','uncertain')
            text+="\n"+self.tr({'similar':'Semelhança sonora: muito semelhante ao original.','different':'Semelhança sonora: claramente diferente do original.','uncertain':'Comparação indisponível — importado protegido.'}[similarity])
            comparison=(self.bank.source or {}).get('audio_comparison',{}).get(r['key'],'unmapped')
            text+="\n"+self.tr({'unchanged':'Áudio idêntico ao original confirmado.','different':'Áudio não idêntico; permanece protegido contra silêncio.','unmapped':'Sem correspondência segura — importado protegido.','unavailable':'Comparação indisponível — importado protegido.'}[comparison])
        text+="\n"+self.tr("{rate} Hz • {channels} canais • {samples} amostras").format(rate=r["rate"],channels=r["channels"],samples=r["samples"])
        if len(r["cue_names"])>1:text+="\nÁudio compartilhado: esta substituição se aplica a TODOS os cues listados."
        if r["key"] in self.replacements:
            text+="\nWAV customizado: "+self.replacements[r["key"]]
            duplicate=self.duplicate_info.get(r["key"])
            if duplicate:
                group,members=duplicate
                text+="\n"+self.tr("Grupo {group} • {count} vozes").format(group=group,count=len(members))
                text+="\n"+self.tr("Mesmo WAV de origem; volume e variação podem ser diferentes.")
                text+="\n"+self.tr("Esta voz está repetida com:")+"\n"+"\n".join(self.bank.wave_rows[key]["filename"]+" — "+", ".join(map(str,self.bank.wave_rows[key]["cue_ids"])) for key in members if key!=r["key"])
            with wave.open(self.replacements[r["key"]],"rb") as w:
                text+=f"\nBase: {r['duration']:.3f}s • Custom completo: {w.getnframes()/w.getframerate():.3f}s"
        self.details.configure(state="normal");self.details.delete("1.0","end");self.details.insert("end",self.tr(text));self.details.configure(state="disabled")
        self.play_btn.configure(state="normal" if core.reference_row(self.bank,self.reference_bank,r) is not None and (not self.bank.external or r["key"] in self.replacements or core.imported_can_preview(self.bank,r)) else "disabled")
        self.custom_btn.configure(state="normal" if r["key"] in self.replacements or core.imported_can_preview(self.bank,r) else "disabled")
        if not self.playing:
            self.wave_data=None;self.wave_bars=[]
            self.canvas.delete("all");self.canvas.create_text(18,24,text=self.tr("▶ Ouça o original para visualizar a forma de onda."),fill=MUTED,anchor="w",font=("Segoe UI",10))
            self.compact_wave.delete("all");self.compact_wave.create_text(max(90,self.compact_wave.winfo_width()/2),19,text=self.tr("▶ Ouvir original"),fill=MUTED,font=("Segoe UI",9))
        self.variation.set(self.variations.get(r["key"],1))
        self._setting_gain=True;self.gain.set(self.gains.get(r["key"],0.0));self._setting_gain=False
        self.request_levels();self.update_original_text()
    def draw_wave(self,path):
        with wave.open(str(path),"rb") as w:
            rate=w.getframerate()
            samples=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(float).reshape(-1,w.getnchannels())/32768
        # Use the loudest channel so opposite stereo phases never erase the waveform.
        data=np.max(np.abs(samples),axis=1) if len(samples) else np.array([])
        self.wave_duration=len(data)/rate
        count=min(4096,len(data));edges=np.linspace(0,len(data),count+1).astype(int)
        self.wave_data=np.array([np.max(data[edges[i]:edges[i+1]]) for i in range(count)])
        self.redraw_waves()
    def redraw_waves(self):
        if getattr(self,"wave_data",None) is None:return
        self.wave_bars=[]
        for canvas in (self.canvas,self.compact_wave):
            width=canvas.winfo_width();height=canvas.winfo_height()
            if width<10 or height<10:continue
            canvas.delete("all");bars=[];padding=8;usable=max(1,width-padding*2)
            canvas.create_line(padding,height/2,width-padding,height/2,fill=modern_theme.EDGE)
            data=self.wave_data
            if len(data):
                count=max(1,usable//3);edges=np.linspace(0,len(data),count+1).astype(int)
                for i in range(count):
                    chunk=data[edges[i]:min(len(data),max(edges[i]+1,edges[i+1]))]
                    amp=min(1,float(np.max(chunk)))*max(1,height/2-5)
                    x=padding+(i+.5)*usable/count
                    item=canvas.create_line(x,height/2-amp,x,height/2+amp,fill=ACCENT,width=2)
                    bars.append((item,x))
            self.wave_bars.append((canvas,bars,width,height))
        if self.playing and self.wave_duration>0:
            self.paint_wave_progress(min(1,max(0,(time.perf_counter()-self.wave_started)/self.wave_duration)))
    def paint_wave_progress(self,progress):
        for canvas,bars,width,height in self.wave_bars:
            if not canvas.winfo_exists():continue
            x=8+progress*max(1,width-16)
            for item,position in bars:canvas.itemconfigure(item,fill=ACCENT if position<=x else "#60303d")
            canvas.delete("playhead")
            canvas.create_line(x,2,x,height-2,fill=FG,width=1,tags="playhead")
            canvas.create_polygon(x-3,1,x+3,1,x,5,fill=FG,outline="",tags="playhead")
    def play_original(self):
        if not self.bank or not self.selected:return
        if self.bank.external and self.selected["key"] not in self.replacements and not core.imported_can_preview(self.bank,self.selected):return
        bank=self.reference_bank
        row=core.reference_row(self.bank,bank,self.selected)
        if row is None:return
        self.job(lambda:bank.original(row),lambda path:self.play(path,self.play_btn),"Preparando voz original do jogo...")
    def play_edited(self):
        if self.busy or not self.bank or not self.selected:return
        if self.selected["key"] in self.replacements:self.play_custom()
        elif core.imported_can_preview(self.bank,self.selected):self.play_imported()
    def play_imported(self):
        if self.busy or not self.bank or not self.bank.external or not self.selected or not core.imported_can_preview(self.bank,self.selected):return
        bank=self.bank;row=self.selected.copy()
        self.job(lambda:bank.original(row),lambda path:self.play(path,self.custom_btn),"Preparando voz importada...")
    def play_custom(self):
        if not self.selected or self.busy:return
        key=self.selected["key"];source=self.replacements.get(key)
        if not source:return
        row=self.selected.copy();gain=self.gains.get(key,0.0);variation=self.variations.get(key,1);dest=self.project/"Preview"/(key+".wav")
        self.stop()
        def work():
            import voice_effects
            corrected=voice_effects.safe_gain(source,row,gain,variation)
            core.normalize_wav(source,dest,row["rate"],row["channels"],row["samples"],corrected,variation)
            return dest,corrected
        def done(result):
            if result[1]<gain:
                self.gains[key]=result[1];self.level_token+=1;self.level_signature=None;self.select()
            self.play(result[0],self.custom_btn)
            if result[1]<gain:self.status.set(self.tr('Ganho ajustado automaticamente para evitar clipping: ')+f'{result[1]:.1f} dB')
        self.job(work,done,"Preparando prévia com volume ajustado...",edit_label="Corrigir clipping automaticamente")
    def play(self,path,button=None):
        self.stop();self.draw_wave(path);playback_controls.start(self,path,button,stop_first=False)
        self.playing=path;self.status.set("Reproduzindo "+Path(path).name)
        self.wave_started=time.perf_counter();self.animate_wave()
    def animate_wave(self):
        self.wave_after=None
        if not self.playing or self.wave_duration<=0:return
        progress=min(1,max(0,(time.perf_counter()-self.wave_started)/self.wave_duration))
        self.paint_wave_progress(progress)
        if progress<1:self.wave_after=self.after(16,self.animate_wave)
        else:self.stop()
    def stop(self):
        if self.wave_after is not None:
            self.after_cancel(self.wave_after);self.wave_after=None
        for canvas,bars,width,height in self.wave_bars:
            if canvas.winfo_exists():
                canvas.delete("playhead")
                for item,position in bars:canvas.itemconfigure(item,fill=ACCENT)
        winsound.PlaySound(None,0);self.playing=None
        playback_controls.reset(self)
    def drop_wav(self,paths):
        if self.busy:
            self.status.set("Aguarde a operação atual antes de importar um áudio.");return
        if not self.bank or not self.selected:
            self.status.set("Selecione uma voz antes de arrastar um áudio.");return
        if len(paths)!=1 or Path(paths[0]).suffix.casefold() not in audio_import.EXTENSIONS or not Path(paths[0]).is_file():
            messagebox.showwarning(self.tr("Importar áudio"),self.tr("Arraste um único arquivo de áudio ou vídeo para a voz selecionada."),parent=self);return
        self.import_audio(paths[0])
    def import_wav(self,source=None):
        return self.import_audio(source)
    def import_audio(self,source=None):
        if not self.bank or not self.selected or self.busy:return
        p=source or filedialog.askopenfilename(parent=self,title=self.tr("Escolha sua voz customizada"),filetypes=[(self.tr("Áudio ou vídeo"),tuple("*"+suffix for suffix in audio_import.EXTENSIONS)),("WAV","*.wav"),("MP3","*.mp3"),("FLAC","*.flac"),("OGG","*.ogg"),("AIFF",("*.aiff","*.aif")),(self.tr("Vídeos"),tuple("*"+suffix for suffix in video_audio.VIDEO_EXTENSIONS)),("M4A / AAC / Opus / WMA",tuple("*"+suffix for suffix in video_audio.EXTRA_AUDIO))])
        if not p:return
        row=self.selected.copy()
        if Path(p).suffix.casefold() in video_audio.MEDIA_EXTENSIONS:
            self.job(lambda:video_audio.tracks(p),lambda tracks:self.choose_video_audio(p,row,tracks),"Lendo faixas de áudio do arquivo...")
        else:self._import_audio_file(p,row)
    def _import_audio_file(self,p,row,stream_index=None):
        dest=self.project/"Replacements"/(row["key"]+"_"+uuid.uuid4().hex+".wav")
        def done(info):
            self.replacements[row["key"]]=str(dest);self.gains.pop(row["key"],None);self.variations.pop(row["key"],None);self.variation.set(1);self.level_signature=None;self.fill_rows();self.select()
            self.status.set(f'Voz adicionada: {info["export_duration"]:.3f}s completos. Original mantido como referência.')
        self.job(lambda:audio_import.convert(p,dest,row["rate"],row["channels"],row["samples"],stream_index),done,"Importando áudio e convertendo para WAV...",edit_label="Importar áudio")
    def remove(self):
        if self.selected and not self.busy:
            self.replacements.pop(self.selected["key"],None);self.gains.pop(self.selected["key"],None);self.variations.pop(self.selected["key"],None);self.variation.set(1);self.level_signature=None;self.fill_rows();self.select()
            self.status.set("Substituição removida. O áudio do banco aberto será mantido." if core.preserve_unreplaced(self.bank,self.selected,self.keep_imported.get()) else "Substituição removida. Esta entrada será exportada como silêncio.")
    def project_document(self):
        return {"replacer_folder_name":self.replacer_folder_name,"saved_at":project_names.datetime.now(project_names.LOCAL_ZONE).isoformat(),"schema":5,"usage_count":self.project_usage_count,"last_opened":self.project_last_opened,"unreplaced_policy":"original" if self.keep_imported.get() else "mute","migration":self.migration,"export_name":self.export_name.get().strip(),"project_name":self.project_name,"project_id":self.project_id,"bank":self.bank.name,"replacements":dict(self.replacements),"trim_originals":trim_history.active(self.trim_originals,self.replacements),"processing_originals":trim_history.active(self.processing_originals,self.replacements),"effects_originals":trim_history.active(self.effects_originals,self.replacements),"speed_originals":trim_history.active(self.speed_originals,self.replacements),"duplicate_originals":trim_history.active(self.duplicate_originals,self.replacements),"gains":dict(self.gains),"variations":dict(self.variations),"source":self.bank.source,"keep_imported":self.keep_imported.get()}
    def save_project(self,notify=True,force=False):
        if not self.bank or not self.project or self.project_renaming:return
        # Internal export/open operations must never turn a session into a project.
        if self.project_temporary and not (notify or force):return
        if self.project_temporary:
            import shutil
            previous=self.project
            target=project_names.project_folder(self.project_name or self.bank.name,language=self.translator.language)
            data=self.project_document()
            data["project_id"]=project_names.project_parts(target)["id"]
            replacements={};created=False
            try:
                with self.level_lock:
                    target.mkdir(parents=True,exist_ok=False);created=True
                    for key,value in self.replacements.items():
                        source=Path(value).resolve()
                        if source.is_relative_to(previous.resolve()):
                            dest=target/source.relative_to(previous.resolve())
                            dest.parent.mkdir(parents=True,exist_ok=True)
                            shutil.copy2(source,dest)
                            replacements[key]=str(dest)
                        else:replacements[key]=value
                    data["replacements"]=replacements
                    for key,item in list(data.get("trim_originals",{}).items())+list(data.get("processing_originals",{}).items())+list(data.get('effects_originals',{}).items())+list(data.get('speed_originals',{}).items())+list(data.get('duplicate_originals',{}).items()):
                        source=Path(item["original"]).resolve()
                        if source.is_relative_to(previous.resolve()):
                            dest=target/source.relative_to(previous.resolve())
                            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
                            item["original"]=str(dest)
                        item["trimmed"]=replacements[key]
                    if data.get("source"):
                        source=dict(data["source"])
                        for field in ("asset","uexp","acb","awb"):
                            if source.get(field):
                                path=Path(source[field]);dest=target/"Source"/(self.bank.name+path.suffix.lower())
                                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
                                source[field]=str(dest)
                        data["source"]=source
                    core.write_json(target/"project.json",data)
            except Exception:
                # The original session remains intact if committing fails.
                if created and target.is_dir() and target.resolve().parent==(core.APP/"Projects").resolve():
                    shutil.rmtree(target)
                raise
            self.history.relocate(previous,target)
            self.project=target;self.project_id=data["project_id"]
            self.replacements=replacements;self.trim_originals=data.get("trim_originals",{});self.processing_originals=data.get("processing_originals",{});self.effects_originals=data.get("effects_originals",{});self.speed_originals=data.get("speed_originals",{});self.duplicate_originals=data.get("duplicate_originals",{});self.project_temporary=False
            if data.get("source"):
                self.bank.source=data["source"];self.bank.asset=Path(data["source"]["asset"])
                if data["source"].get("uexp"):self.bank.uexp_path=Path(data["source"]["uexp"])
            self.level_signature=None;self.level_data={};self.request_levels()
        else:core.write_json(self.project/"project.json",self.project_document())
        header_project.update(self)
        self.project_audio.submit(self.bank,self.project,self.replacements,self.gains,self.variations,self.keep_imported.get(),self.level_lock)
        self._saved_project_snapshot=self.project_edit_snapshot()
        if notify:self.status.set("Projeto salvo: "+str(self.project/"project.json"))
        if notify and not self.busy:self.refresh_project_folder()
    def refresh_project_folder(self):
        if self.busy or self.project_temporary or self.project_renaming:return
        target=project_names.readable_target(self.project,self.project_name or self.bank.name,self.translator.language)
        if target is None or target==self.project:return
        self.stop();self.level_token+=1;self.level_signature=None
        if self.level_after:self.after_cancel(self.level_after);self.level_after=None
        if self.gain_save_after:self.after_cancel(self.gain_save_after);self.gain_save_after=None
        old=self.project;name=self.project_name or self.bank.name;language=self.translator.language
        self.project_renaming=True
        def work():
            self.project_audio.wait()
            with self.level_lock:return project_names.relocate(old,name,language=language)
        def done(result):
            folder,data=result;self.project_renaming=False
            self.history.relocate(old,folder);self.project=folder;self.project_id=data['project_id']
            self.replacements=data.get('replacements',{});self.trim_originals=data.get('trim_originals',{});self.processing_originals=data.get('processing_originals',{});self.effects_originals=data.get('effects_originals',{});self.speed_originals=data.get('speed_originals',{});self.duplicate_originals=data.get('duplicate_originals',{})
            self.bank.source=data.get('source',self.bank.source)
            for attribute in ('asset','uexp_path'):
                path=getattr(self.bank,attribute,None)
                if path and Path(path).resolve().is_relative_to(old):setattr(self.bank,attribute,folder/Path(path).resolve().relative_to(old))
            self.level_data={};header_project.update(self)
            self._saved_project_snapshot=self.project_edit_snapshot()
            self.fill_rows();self.select()
            self.status.set('Projeto salvo: '+str(folder/'project.json'))
        self.job(work,done,'Renomeando projeto...')

    def rename_project(self):
        if not self.bank or not self.project or self.busy:return
        from project_name_dialog import ProjectNameDialog
        name=ProjectNameDialog(self).result
        if name is None:return
        try:name=project_names.validate(name)
        except ValueError as error:
            support_report.show(self,str(error),parent=self,title=self.tr('Nome do projeto'));return
        if self.project_temporary:
            self.project_name=name;self.title("Sparking Zero Voice Studio • "+name)
            header_project.update(self)
            self.status.set("Nome definido. Clique em Salvar projeto para criar o projeto.")
            return
        self.stop();self.level_token+=1;self.level_signature=None
        if self.level_after:self.after_cancel(self.level_after);self.level_after=None
        if self.gain_save_after:self.after_cancel(self.gain_save_after);self.gain_save_after=None
        self.save_project(False);old=self.project;self.project_renaming=True
        def work():
            self.project_audio.wait()
            with self.level_lock:return project_names.relocate(old,name,language=self.translator.language)
        def done(result):
            self.project_renaming=False
            folder,data=result;self.history.relocate(old,folder);self.project=folder;self.project_name=data["project_name"];self.project_id=data["project_id"]
            self.replacements=data.get("replacements",{});self.trim_originals=data.get("trim_originals",{});self.processing_originals=data.get("processing_originals",{});self.effects_originals=data.get("effects_originals",{});self.speed_originals=data.get("speed_originals",{});self.duplicate_originals=data.get("duplicate_originals",{});self.bank.source=data.get("source",self.bank.source)
            for attribute in ("asset","uexp_path"):
                path=getattr(self.bank,attribute,None)
                if path and Path(path).resolve().is_relative_to(old):setattr(self.bank,attribute,folder/Path(path).resolve().relative_to(old))
            self.level_data={};self.title("Sparking Zero Voice Studio • "+self.project_name)
            header_project.update(self)
            self.fill_rows();self.select();self.save_project(False)
            self.status.set("Projeto renomeado: "+self.project_name)
        self.job(work,done,"Renomeando projeto...")

    def open_project(self):
        if self.busy:return
        p=filedialog.askopenfilename(parent=self,title=self.tr("Continuar projeto"),initialdir=core.APP/"Projects",filetypes=[(self.tr("Projeto"),"project.json")])
        if not p:return
        self.open_project_path(p)
    def open_project_path(self,p):
        if self.busy:return
        try:
            path=core.owned(p);data=json.loads(path.read_text(encoding="utf-8"))
            if not data.get("source") and data.get("bank") not in self.banks:raise ValueError("Banco do projeto não encontrado.")
            if data.get("source"):
                for key in ("asset","awb","acb","uexp"):
                    value=data["source"].get(key)
                    if value and not core.owned(value).is_file():raise ValueError("Cópia importada do projeto não encontrada: "+value)
            for key,value in data.get("replacements",{}).items():
                if not core.owned(value).is_file():raise ValueError("WAV do projeto não encontrado: "+value)
            for key,value in data.get("gains",{}).items():
                if key not in data.get("replacements",{}):raise ValueError("Há ajustes de volume sem voz importada correspondente.")
                audio_levels.valid_gain(value)
            for key,value in data.get("variations",{}).items():
                if key not in data.get("replacements",{}):raise ValueError("Há variações sem voz importada correspondente.")
                audio_variations.valid(value)
            data["project_file"]=str(path);self.load_bank(data["bank"],data)
        except Exception as e:self.fail(str(e))
    def save_export_preferences(self):
        core.write_json(core.APP/"export_preferences.json",{
            "destination":self.destination.get(),"mode":self.export_mode.get()})
    def choose_destination(self):
        if self.busy:return
        folder=filedialog.askdirectory(parent=self,title=self.tr("Escolha a pasta exata para os arquivos exportados"),
            initialdir=self.destination.get(),mustexist=False)
        if not folder:return
        try:
            path=core.export_destination(folder,self.cfg)
            self.destination.set(str(path));self.save_export_preferences()
            self.status.set("Destino: "+str(path))
        except (ValueError,OSError) as e:self.fail(str(e))
    def show_folder_menu(self):
        if self.busy:return
        menu=self.folder_menu
        menu.delete(0,"end")
        menu.add_command(label=self.tr("Abrir pasta dos exports"),command=self.open_destination)
        menu.add_command(label=self.tr("Abrir áudios editados"),command=self.open_edited_audio)
        menu.add_command(label=self.tr("Abrir pasta dos projetos"),command=self.open_projects_folder)
        button=self.folders_btn
        try:
            menu.tk_popup(button.winfo_rootx(),button.winfo_rooty()+button.winfo_height())
        finally:
            menu.grab_release()

    def open_edited_audio(self):
        if self.busy:return
        if not self.bank or not self.project:
            self.status.set("Escolha um banco de voz para abrir seus áudios editados.");return
        bank=self.bank;project=self.project
        replacements=dict(self.replacements);gains=dict(self.gains);variations=dict(self.variations)
        if not any(project_audio.is_edited(bank,row,replacements) for row in bank.rows):
            self.status.set("Não há áudios editados neste banco.");return
        def work():
            project_audio.materialize(bank,project,replacements,gains,variations,True,self.level_lock,edited_only=True)
            return project/"Audios editados"
        def done(path):
            try:
                folder_navigation.open_folder(path)
                self.status.set("Pasta de áudios editados: "+str(path))
            except OSError as error:self.fail(str(error))
        self.job(work,done,"Preparando áudios editados com os ajustes atuais...")

    def open_projects_folder(self):
        if self.busy:return
        path=core.APP/"Projects"
        try:
            path.mkdir(parents=True,exist_ok=True)
            folder_navigation.open_folder(path)
        except OSError as error:self.fail(str(error))

    def open_destination(self):
        if self.busy:return
        try:
            base=core.export_destination(self.destination.get(),self.cfg)
            project=self.project if self.bank and self.project and not self.project_temporary else None
            path=project_names.project_export_root(base,self.project_name or (self.bank.name if self.bank else ""),project)
            core.export_destination(path,self.cfg).mkdir(parents=True,exist_ok=True)
            folder_navigation.open_folder(path)
        except (ValueError,OSError) as error:self.fail(str(error))
    def export(self):
        if not self.bank or self.busy:return
        import bank_version
        try:bank_version.ensure_current(self.bank)
        except (ValueError,OSError) as error:self.fail(str(error));return
        if not self.confirm_export_summary():return
        try:
            base=core.export_destination(self.destination.get(),self.cfg)
            destination=project_names.export_folder(base,self.project_name or self.bank.name,self.project if not self.project_temporary else None,language=self.translator.language)
            export_name=core.validate_export_name(self.export_name.get() or self.bank.name,self.bank.language) if self.export_mode.get()!="package" else self.bank.name
        except (ValueError,OSError) as e:self.fail(str(e));return
        self.stop();self.save_project(False);self.save_export_preferences()
        bank=self.bank;repl=dict(self.replacements);gains=dict(self.gains);variations=dict(self.variations);keep=self.keep_imported.get();package=self.export_mode.get()=="package";audio_package=self.export_mode.get()=="audio_pak"
        folder_name=replacer_folder.selected_name(self) if package else None
        operation=export_operations.Operation(lambda text,allowed:self.jobs.put(("export_progress",(text,allowed))))
        def work():return core.export_bank(bank,repl,lambda s:self.jobs.put(("status",s)),package,destination,keep,gains=gains,variations=variations,export_name=export_name,audio_package=audio_package,replacer_folder_name=folder_name,operation=operation)
        def done(out):
            self.status.set("Exportação concluída: "+str(out))
            kind="Pacote .pak / .utoc / .ucas" if package else "Asset Zen .uasset completo com ACB, .acb e .awb" if bank.file_kind in ("zen","inline_cooked") else "Asset .uasset + .uexp com ACB atualizado, .acb e .awb"
            if audio_package:kind="Asset editável .uasset, salvo e reaberto na Unreal, com ACB incorporado.\nAWB finalizado em .pak separado, sem .utoc/.ucas."
            messagebox.showinfo(self.tr("Exportação concluída"),self.tr(kind)+"\n\n"+self.tr("Exportação salva em:")+"\n"+str(out)+"\n\n"+self.tr("Nomes, IDs e tags verificados. Originais preservados.")+"\n"+self.tr("O teste dentro do jogo ainda deve ser realizado."),parent=self)
        self.job(work,done,"Preparando exportação...",operation=operation)
    def correct_clipping(self):
        self.adjust_voice_volume("correct")
    def maximize_volume(self):
        self.adjust_voice_volume("maximize")
    def adjust_voice_volume(self,mode):
        if self.busy or not self.bank:return
        key=self.selected["key"] if self.volume_scope.get()=="selected" and self.selected else None
        if self.volume_scope.get()=="selected" and key is None:
            self.status.set("Selecione uma voz do banco para ajustar o volume.");return
        self.stop();self.level_token+=1
        if self.level_after:self.after_cancel(self.level_after);self.level_after=None
        bank=self.bank;replacements=dict(self.replacements);gains=dict(self.gains);variations=dict(self.variations);keep=self.keep_imported.get()
        def work():
            with self.level_lock:
                return voice_gain.adjust(bank,replacements,gains,variations,keep,mode,key,lambda value:self.jobs.put(("status",value)))
        def done(result):
            self.replacements=result["replacements"];self.gains=result["gains"]
            self.level_signature=None;self.level_data={};self.fill_rows()
            if self.tree.selection():self.select()
            text=self.tr("Volume maximizado: " if mode=="maximize" else "Clipping corrigido: ")+str(result["changed"])+self.tr(" vozes ajustadas. Limite: −1 dBFS.")
            if result["muted"]:text+=" "+self.tr("Silenciadas preservadas: ")+str(result["muted"])+"."
            if result["silent"]:text+=" "+self.tr("Áudios sem sinal: ")+str(result["silent"])+"."
            if result["limited"]:text+=" "+self.tr("No limite de ganho (+24 dB): ")+str(result["limited"])+"."
            if result["errors"]:
                text+=" "+self.tr("Vozes com erro: ")+str(len(result["errors"]))+" • "+result["errors"][0]["key"]+": "+result["errors"][0]["error"]
            if result["changed"]:text+=" "+self.tr("Clique em Salvar projeto para guardar os ajustes.")
            self.status.set(text)
        text=("Maximizando volume da voz selecionada..." if mode=="maximize" else "Corrigindo clipping da voz selecionada...") if key is not None else ("Maximizando vozes customizadas do banco atual..." if mode=="maximize" else "Corrigindo clipping das vozes customizadas do banco atual...")
        self.job(work,done,text,edit_label="Maximizar volume" if mode=="maximize" else "Corrigir clipping")
    def settings(self):
        import window_toggle
        if window_toggle.existing(self,'settings_window'):return
        if self.busy:return
        win=tk.Toplevel(self);win.title(self.tr("Configurações"));win.configure(bg=BG)
        win.geometry(f"{min(760,self.winfo_screenwidth()-60)}x{min(700,self.winfo_screenheight()-80)}")
        win.minsize(min(420,self.winfo_screenwidth()-60),min(260,self.winfo_screenheight()-80))
        footer=ttk.Frame(win);footer.pack(side="bottom",fill="x")
        viewport=ttk.Frame(win);viewport.pack(fill="both",expand=True)
        canvas=tk.Canvas(viewport,bg=BG,highlightthickness=0,width=1,height=1)
        scrollbar=ttk.Scrollbar(viewport,orient="vertical",command=canvas.yview)
        scrollbar.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        body=ttk.Frame(canvas);body_window=canvas.create_window(0,0,window=body,anchor="nw")
        self.settings_body=body;self.settings_canvas=canvas
        def fit_settings(event=None):
            width=max(1,canvas.winfo_width());canvas.itemconfigure(body_window,width=width)
            for widget in body.winfo_children():
                if isinstance(widget,ttk.Label):widget.configure(wraplength=max(100,width-40))
            canvas.configure(scrollregion=(0,0,width,body.winfo_reqheight()))
        canvas.bind('<Configure>',fit_settings,add='+');body.bind('<Configure>',fit_settings,add='+')
        def wheel_settings(event):
            if event.widget.winfo_class()=='TCombobox':return
            if body.winfo_reqheight()>canvas.winfo_height():
                canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
        win.bind('<MouseWheel>',wheel_settings,add='+')
        self.settings_window=win
        self.label(body,"Idioma do app").pack(anchor="w",padx=20,pady=(16,4))
        selected_language=tk.StringVar(value=LANGUAGES[self.translator.language])
        self.language_choice=ttk.Combobox(body,textvariable=selected_language,values=list(LANGUAGES.values()),state="readonly")
        self.language_choice.pack(fill="x",padx=20)
        self.label(body,"Nomes dos personagens seguem o idioma do app; Cue IDs e tags técnicas permanecem originais.",style="Muted.TLabel",wraplength=710).pack(anchor="w",padx=20,pady=(5,0))
        self.label(body,"Vozes não substituídas").pack(anchor="w",padx=20,pady=(16,4))
        policy=tk.StringVar(value="original" if self.keep_imported.get() else "mute")
        self.unreplaced_policy_choice=policy
        ttk.Radiobutton(body,text=self.tr("Silenciar (0,5 segundo)"),variable=policy,value="mute").pack(anchor="w",padx=20,pady=2)
        ttk.Radiobutton(body,text=self.tr("Manter o áudio original"),variable=policy,value="original").pack(anchor="w",padx=20,pady=2)
        self.label(body,"Áudios importados diferentes do original ou sem comparação segura são sempre preservados.",style="Muted.TLabel",wraplength=710).pack(anchor="w",padx=20,pady=(4,0))
        self.custom_project_setup_notice=self.label(body,'Replacer: basta configurar a instalação do jogo; as referências são lidas automaticamente. Custom: exige o CustomProject e a Custom Engine do Sparking Zero com CriWare.',style="Muted.TLabel",wraplength=710)
        self.custom_project_setup_notice.pack(anchor="w",fill="x",padx=20,pady=(12,0))
        values={}
        for title,key in [("CustomProject (opcional para Replacer)","project"),("Instalação do jogo","game"),("Pasta da Custom Engine (somente para Custom)","custom_engine")]:
            self.label(body,title).pack(anchor="w",padx=20,pady=(14,4))
            v=tk.StringVar(value=editor_asset.configured_folder(self.cfg) if key=="custom_engine" else self.cfg.get(key,""));values[key]=v
            if key=="custom_engine":self.custom_engine_folder_var=v
            row=ttk.Frame(body);row.pack(fill="x",padx=20)
            def choose_folder(variable=v,field=key,caption=title):
                folder=filedialog.askdirectory(parent=win,title=self.tr("Escolha a pasta da Custom Engine") if field=="custom_engine" else self.tr(caption),initialdir=variable.get() or None)
                if not folder:return
                if field=="custom_engine":
                    try:editor_asset.engine_from_folder(folder)
                    except ValueError as error:support_report.show(self,str(error),parent=win,title=self.tr('Configuração'));return
                variable.set(folder)
            button=self.button(row,"Escolher pasta",choose_folder)
            button.pack(side="right",padx=(8,0))
            entry=ttk.Entry(row,textvariable=v,width=1);entry.pack(side="left",fill="x",expand=True)
            setattr(self,key+'_folder_button',button)
            setattr(self,key+'_folder_entry',entry)
        def save():
            cfg=self.cfg.copy();cfg.update({k:v.get() for k,v in values.items()})
            # Preferences can be saved before setup, or with unavailable old paths.
            # Validate folders only when the user actually edits folder settings.
            previous={key:(editor_asset.configured_folder(self.cfg) if key=="custom_engine" else self.cfg.get(key,"")) for key in values}
            folders_changed=any(cfg[key].strip()!=str(previous[key]).strip() for key in values)
            if folders_changed:
                for key in values:cfg[key]=cfg[key].strip()
                if any(cfg[key] and not Path(cfg[key]).is_dir() for key in ("game","project")):
                    support_report.show(self,'Confira as pastas informadas.',parent=win,title=self.tr('Configuração'));return
                try:
                    cfg['unreal_editor']=str(editor_asset.engine_from_folder(cfg['custom_engine'])) if cfg['custom_engine'] else ''
                except ValueError as error:
                    support_report.show(self,str(error),parent=win,title=self.tr('Configuração'));return
                if cfg["game"]:
                    try:core.available_banks(cfg)
                    except (OSError,ValueError) as error:
                        support_report.show(self,str(error),parent=win,title=self.tr('Configuração'));return
            language=next(key for key,value in LANGUAGES.items() if value==selected_language.get())
            policy_changed=self.keep_imported.get()!=(policy.get()=="original")
            cfg["unreplaced_policy"]=policy.get()
            cfg["ui_language"]=language;cfg["function_language"]=language;changed=cfg["project"]!=self.cfg["project"]
            references_changed=any(cfg[key]!=self.cfg[key] for key in ("project","game"))
            core.write_json(core.APP/"settings.json",cfg);self.cfg=cfg
            custom_setup_status.update(self)
            self.function_language.set(cfg["function_language"]);self.apply_language(language);win.destroy()
            self.keep_imported.set(policy.get()=="original")
            if policy_changed and self.bank:self.change_import_policy()
            if references_changed:
                self.pak=None;self.original_text_data={};self.original_text_pending=set()
            elif self.bank:self.bank.cfg=cfg
            if references_changed:
                self.banks=core.available_banks(cfg) if cfg["game"].strip() else [];self.start_bank_catalog();self.fill_banks()
            self.status.set("Configuração salva. Abra novamente o banco desejado." if references_changed else "Configurações salvas.")
        self.settings_save_btn=self.button(footer,"Salvar configurações",save,True)
        self.settings_save_btn.pack(anchor="e",padx=20,pady=20)
    def close(self):
        ui_reliability.event('close_requested',busy=self.busy,operation=getattr(self,'_diagnostic_operation',None))
        if self.busy:
            messagebox.showinfo(self.tr("Operação em andamento"),self.tr("Aguarde a operação terminar antes de fechar."),parent=self);return
        if not self.confirm_leaving_project():return
        self.level_token+=1
        if self.level_after:self.after_cancel(self.level_after);self.level_after=None
        if self.gain_save_after:self.after_cancel(self.gain_save_after);self.gain_save_after=None
        self.stop()
        def finished(result):
            # A failed final write leaves the editor open and recovery active.
            self.recovery.shutdown()
            self.project_audio.shutdown()
            self.destroy()
        self.job(self.project_audio.wait,finished,"Finalizando os áudios do projeto...")

edit_history.install(Studio)
session_features.install(Studio)
microphone_ui.install(Studio)
import voice_ai_ui
voice_ai_ui.install(Studio)
import voice_effects_ui
voice_effects_ui.install(Studio)
import voice_speed_ui
voice_speed_ui.install(Studio)
import game_catalog_ui
game_catalog_ui.install(Studio)

if __name__=="__main__":
    app=Studio()
    if "--smoke-ui" in __import__("sys").argv:
        app.after(3000,lambda:(core.write_json(core.APP/"tests/ui_smoke.json",{
            "title":app.title(),"banks":len(app.banks),"loaded":app.bank.name if app.bank else None,
            "visible_rows":len(app.tree.get_children())}),app.destroy()))
    app.mainloop()




