"""Cooperative cancellation at export boundaries, never halfway through delivery."""
import threading,time,re,shutil
from pathlib import Path

class Cancelled(Exception):pass

class Operation:
    def __init__(self,emit):
        self.emit=emit;self.requested=threading.Event();self.lock=threading.Lock()
        self.cancellable=True;self.started=time.monotonic();self.work_dir=None
    def cancel(self):
        with self.lock:
            if not self.cancellable:return False
            self.requested.set();return True
    def checkpoint(self):
        if self.requested.is_set():raise Cancelled('Exportação cancelada. Nenhum arquivo foi publicado.')
    def report(self,text):
        self.checkpoint();self.emit(str(text),self.cancellable)
    def begin_publish(self):
        with self.lock:
            self.checkpoint();self.cancellable=False
        self.emit('Salvando arquivos verificados...',False)
    def cleanup(self,root):
        if self.work_dir is None:return
        path=Path(self.work_dir);base=Path(root)/'Cache/ExportBuilds'
        if path.resolve().parent==base.resolve() and not path.is_symlink() and path.is_dir():shutil.rmtree(path)

class ProgressWindow:
    def __init__(self,owner,operation):
        import tkinter as tk
        from tkinter import ttk
        from modern_theme import BG
        self.owner=owner;self.operation=operation;self.timer=None;self.closed=False
        self.win=tk.Toplevel(owner);self.win.title(owner.tr('Preparando exportação...'));self.win.configure(bg=BG);self.win.transient(owner)
        self.win.geometry(f'{min(600,owner.winfo_screenwidth()-60)}x260');self.win.minsize(360,230)
        body=ttk.Frame(self.win,padding=18);body.pack(fill='both',expand=True)
        self.stage=tk.StringVar(value=owner.tr('Preparando exportação...'));self.elapsed=tk.StringVar()
        ttk.Label(body,textvariable=self.stage,wraplength=530,font=('Segoe UI',11,'bold')).pack(anchor='w',fill='x')
        self.bar=ttk.Progressbar(body,mode='indeterminate');self.bar.pack(fill='x',pady=14);self.bar.start(30)
        ttk.Label(body,textvariable=self.elapsed).pack(anchor='w')
        owner.label(body,'O cancelamento aguarda a etapa atual terminar.',wraplength=530,style='Muted.TLabel').pack(anchor='w',fill='x',pady=8)
        self.cancel_btn=owner.button(body,'Cancelar exportação',self.cancel);self.cancel_btn.pack(anchor='e')
        body.bind('<Configure>',lambda e:[w.configure(wraplength=max(200,e.width-36)) for w in body.winfo_children() if isinstance(w,ttk.Label)],add='+')
        self.win.protocol('WM_DELETE_WINDOW',self.cancel);self.tick()
    def tick(self):
        if self.closed:return
        seconds=int(time.monotonic()-self.operation.started)
        self.elapsed.set(self.owner.tr('Tempo decorrido')+f': {seconds//60:02d}:{seconds%60:02d}')
        self.timer=self.win.after(500,self.tick)
    def update(self,text,cancellable=True):
        if self.closed:return
        self.stage.set(self.owner.tr(text))
        match=re.match(r'Convertendo (\d+)/(\d+):',text)
        self.bar.stop()
        if match:self.bar.configure(mode='determinate',maximum=int(match[2]),value=int(match[1]))
        else:self.bar.configure(mode='indeterminate');self.bar.start(30)
        self.cancel_btn.configure(state='normal' if cancellable and not self.operation.requested.is_set() else 'disabled')
    def cancel(self):
        if self.operation.cancel():
            self.stage.set(self.owner.tr('Cancelamento solicitado. Aguardando a etapa atual...'));self.cancel_btn.configure(state='disabled')
    def finish(self):
        if self.closed:return
        self.closed=True
        if self.timer is not None:self.win.after_cancel(self.timer)
        self.bar.stop();self.win.destroy()
