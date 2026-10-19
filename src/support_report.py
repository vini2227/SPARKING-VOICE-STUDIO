"""Explicitly saved, bounded support archives; never include audio, keys or settings."""
import json,zipfile,re,platform,sys,datetime
from pathlib import Path
import core

def redact(text,cfg=None):
    text=str(text)
    for key,value in sorted((cfg or {}).items(),key=lambda x:len(str(x[1])),reverse=True):
        if key in ('game','project','unreal_editor','pak_key_file') and value:
            text=re.sub(re.escape(str(value)),f'<{key}>',text,flags=re.I)
    text=re.sub(r'[A-Za-z]:[\\/][^\r\n"<>]*', '<local path>', text)
    text=re.sub(r'\\\\[^\r\n"<>]+','<network path>',text)
    text=re.sub(r'(?i)(keycode|encryption_key|aes[_ ]?key|pak[_ ]?key)\s*[:=]\s*\S+',r'\1=<redacted>',text)
    text=re.sub(r'(?i)(--keycode[\s\x27\x22,]+)\d+',r'\1<redacted>',text)
    return text

def contents(owner,message):
    cfg=getattr(owner,'cfg',{});root=core.APP
    manifest={'created_at':datetime.datetime.now().astimezone().isoformat(),'python':sys.version.split()[0],
              'windows':platform.version(),'language':owner.translator.language,
              'bank':getattr(getattr(owner,'bank',None),'name',None),'error':redact(message,cfg)}
    versions=root/'Data/dependency_versions.json'
    try:
        if versions.is_file():manifest['dependencies']=json.loads(versions.read_text())
    except (OSError,ValueError):pass
    result={'support.json':json.dumps(manifest,ensure_ascii=False,indent=2),'error.txt':redact(message,cfg)}
    for name in ('error.log','Reports/Diagnostics/interface_errors.log','Reports/Diagnostics/events.log'):
        path=root/name
        try:
            if path.is_file():
                with path.open('rb') as stream:
                    stream.seek(max(0,path.stat().st_size-128*1024));data=stream.read(128*1024)
                result['logs/'+path.name]=redact(data.decode('utf-8','replace'),cfg)
        except OSError:pass
    # Include only the import log explicitly mentioned by this failure, within our cache.
    for token in re.findall(r'[A-Za-z]:[^\r\n]*?import\.log',str(message),flags=re.I):
        path=Path(token);base=root/'Cache/NativeAssets'
        try:
            if path.resolve().is_relative_to(base.resolve()) and path.is_file() and not path.is_symlink():
                with path.open('rb') as stream:stream.seek(max(0,path.stat().st_size-256*1024));data=stream.read(256*1024)
                result['logs/import.log']=redact(data.decode('utf-8','replace'),cfg)
        except OSError:pass
    return result

def save(owner,message,destination):
    import os,tempfile
    destination=Path(destination)
    data=contents(owner,message)
    fd,name=tempfile.mkstemp(prefix='support_',suffix='.zip',dir=destination.parent);os.close(fd)
    try:
        with zipfile.ZipFile(name,'w',zipfile.ZIP_DEFLATED) as archive:
            for member,text in data.items():archive.writestr(member,text)
        os.replace(name,destination)
    finally:Path(name).unlink(missing_ok=True)
    return destination

def show(owner,message,*,parent=None,title=None):
    import tkinter as tk
    from tkinter import ttk,filedialog
    from modern_theme import BG,CARD,FG
    existing=getattr(owner,'support_error_window',None)
    if existing is not None and existing.winfo_exists():existing.destroy()
    previous=owner.grab_current();parent=parent or previous or owner
    win=tk.Toplevel(parent);owner.support_error_window=win;win.title(title or 'Sparking Zero Voice Studio');win.configure(bg=BG);win.transient(parent)
    win.geometry(f'{min(760,owner.winfo_screenwidth()-60)}x390');win.minsize(380,300)
    frame=ttk.Frame(win,padding=18);frame.pack(fill='both',expand=True)
    area=tk.Text(frame,height=8,wrap='word',bg=CARD,fg=FG,relief='flat');area.insert('1.0',owner.tr(message));area.configure(state='disabled');area.pack(fill='both',expand=True)
    status=tk.StringVar();ttk.Label(frame,textvariable=status,wraplength=680).pack(fill='x',pady=8)
    owner.label(frame,'O relatório inclui versões e logs, sem áudios, projetos ou chaves.',wraplength=680,style='Muted.TLabel').pack(fill='x')
    bar=ttk.Frame(frame);bar.pack(fill='x',pady=(12,0))
    def close():
        win.destroy()
        if previous is not None and previous.winfo_exists():previous.grab_set()
    def copy():
        data=contents(owner,message);text=data['support.json']+'\n\n'+data.get('logs/import.log',data.get('logs/error.log',''))
        owner.clipboard_clear();owner.clipboard_append(text);status.set(owner.tr('Detalhes copiados.'))
    def generate():
        destination=filedialog.asksaveasfilename(parent=win,title=owner.tr('Gerar relatório de suporte'),defaultextension='.zip',initialfile='VoiceStudio_support_'+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+'.zip',filetypes=[('ZIP','*.zip')])
        if not destination:return
        try:save(owner,message,destination);status.set(owner.tr('Relatório salvo: ')+destination)
        except (OSError,ValueError) as error:status.set(owner.tr(str(error)))
    bar.columnconfigure(0,weight=1);bar.columnconfigure(1,weight=1)
    owner.button(bar,'Gerar relatório de suporte',generate).grid(row=0,column=0,columnspan=2,sticky='ew',pady=(0,8))
    owner.button(bar,'Copiar detalhes',copy).grid(row=1,column=0,sticky='w')
    owner.button(bar,'Fechar',close).grid(row=1,column=1,sticky='e')
    frame.bind('<Configure>',lambda e:[w.configure(wraplength=max(200,e.width-36)) for w in frame.winfo_children() if isinstance(w,ttk.Label)],add='+')
    win.protocol('WM_DELETE_WINDOW',close);win.bind('<Escape>',lambda e:close());win.grab_set()
