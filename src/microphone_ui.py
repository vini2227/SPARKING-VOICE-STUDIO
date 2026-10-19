import support_report
"""Record, review and explicitly apply a take to the selected voice."""
import queue,threading,uuid,math,winsound
import tkinter as tk
from tkinter import ttk,messagebox
import playback_controls
import microphone_capture as mic
from modern_theme import BG,PANEL,FG,MUTED,SUCCESS,ERROR,WARNING

class RecorderDialog:
    def __init__(self,owner):
        self.owner=owner;self.bank=owner.bank;self.row=dict(owner.selected)
        self.recorder=None;self.take=None;self.devices=[];self.events=queue.Queue();self.closed=False
        self.starting=False;self.finishing=False;self.refreshing=False;self.timer=None
        win=tk.Toplevel(owner);self.win=win;owner.microphone_window=win
        win.title(owner.tr('Gravar voz'));win.configure(bg=BG);win.transient(owner);win.geometry('740x600');win.minsize(620,600)
        frame=ttk.Frame(win,padding=20);frame.pack(fill='both',expand=True)
        owner.label(frame,'Gravar voz pelo microfone',font=('Segoe UI',15,'bold')).pack(anchor='w')
        ttk.Label(frame,text=self.row['filename']+' • '+owner.function_text(self.row),wraplength=660).pack(anchor='w',pady=(6,12))
        owner.label(frame,'Microfone').pack(anchor='w')
        device_row=ttk.Frame(frame);device_row.pack(fill='x',pady=(4,12))
        self.device_choice=ttk.Combobox(device_row,state='disabled');self.device_choice.pack(side='left',fill='x',expand=True)
        self.refresh_btn=owner.button(device_row,'Atualizar microfones',self.refresh);self.refresh_btn.pack(side='right',padx=(8,0))
        self.elapsed=tk.StringVar(value='00:00.000');ttk.Label(frame,textvariable=self.elapsed,font=('Consolas',22,'bold')).pack(anchor='center')
        self.canvas=tk.Canvas(frame,height=60,bg=PANEL,highlightthickness=0);self.canvas.pack(fill='x',pady=(8,4))
        self.level_var=owner.localized_var('Aguardando gravação.');ttk.Label(frame,textvariable=self.level_var).pack(anchor='w')
        self.note=owner.localized_var('Selecione o microfone e clique em Gravar.');self.note_label=ttk.Label(frame,textvariable=self.note,wraplength=660);self.note_label.pack(fill='x',pady=(8,12))
        controls=ttk.Frame(frame);controls.pack(fill='x')
        self.record_btn=owner.button(controls,'● Gravar',self.start,True);self.record_btn.pack(side='left')
        self.stop_btn=owner.button(controls,'■ Parar gravação',self.stop);self.stop_btn.pack(side='left',padx=8)
        self.preview_btn=owner.button(controls,'Ouvir gravação',self.preview);self.preview_btn.pack(side='left')
        from responsive_layout import Flow
        self.flow=Flow(controls)
        owner.label(frame,'A gravação só entra no projeto ao clicar em Usar gravação. Depois, você pode cortar e ajustar o volume.',wraplength=660).pack(fill='x',pady=(16,12))
        bottom=ttk.Frame(frame);bottom.pack(fill='x',side='bottom',before=frame.winfo_children()[0])
        owner.button(bottom,'Fechar',self.close).pack(side='right')
        self.use_btn=owner.button(bottom,'Usar gravação',self.use,True);self.use_btn.pack(side='right',padx=(0,8))
        win.protocol('WM_DELETE_WINDOW',self.close);win.bind('<Destroy>',self.destroyed,add='+')
        win.grab_set();owner.stop();self.refresh();self.tick()
    def enabled(self):
        recording=bool(self.recorder and self.recorder.active);locked=self.starting or self.finishing or self.refreshing
        for widget,enabled in ((self.record_btn,bool(self.devices) and not recording and not locked),
            (self.stop_btn,recording and not locked),(self.preview_btn,bool(self.take) and not recording and not locked),
            (self.use_btn,bool(self.take) and not recording and not locked),(self.refresh_btn,not recording and not locked)):
            widget.configure(state='normal' if enabled else 'disabled')
        self.device_choice.configure(state='readonly' if self.devices and not recording and not locked else 'disabled')
    def refresh(self):
        if self.starting or self.finishing or self.refreshing or self.recorder and self.recorder.active:return
        self.refreshing=True;self.devices=[];self.note.set('Procurando microfones...');self.enabled()
        def worker():
            try:self.events.put(('devices',mic.input_devices()))
            except Exception as error:self.events.put(('error',str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def start(self):
        index=self.device_choice.current()
        if index<0 or self.starting or self.finishing or self.recorder and self.recorder.active:return
        self.owner.stop();device=self.devices[index];self.take=None;self.elapsed.set('00:00.000')
        self.recorder=mic.Capture(self.owner.project/'Recordings'/('microphone_'+uuid.uuid4().hex+'.wav'),device['index'],device['rate'])
        recorder=self.recorder;self.starting=True;self.note.set('Preparando o microfone...');self.enabled()
        def worker():
            try:
                recorder.start()
                if self.closed:recorder.stop(allow_empty=True);return
                self.events.put(('started',None))
            except Exception as error:self.events.put(('start_error',str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def stop(self):
        if not self.recorder or self.starting or self.finishing:return
        self.finishing=True;self.note.set('Finalizando a gravação...');self.enabled();recorder=self.recorder
        def worker():
            try:self.events.put(('stopped',recorder.stop()))
            except Exception as error:self.events.put(('stop_error',str(error)))
        threading.Thread(target=worker,daemon=True).start()
    def preview(self):
        if not self.take or self.starting or self.finishing or self.recorder.active:return
        try:playback_controls.start(self.owner,self.take,self.preview_btn)
        except RuntimeError as error:support_report.show(self.owner,str(error),parent=self.win,title=self.owner.tr('Gravar voz'))
    def use(self):
        if not self.take or self.starting or self.finishing or self.owner.busy:return
        if self.owner.bank is not self.bank:support_report.show(self.owner,'O banco mudou. Abra novamente a gravação.',parent=self.win,title=self.owner.tr('Gravar voz'));return
        take=self.take;self.owner.stop();self.win.destroy()
        self.owner._import_audio_file(take,self.row)
    def close(self):
        if self.starting or self.finishing:self.note.set('Aguarde a finalização da operação.');return
        if self.recorder and self.recorder.active:
            if not messagebox.askyesno(self.owner.tr('Gravar voz'),self.owner.tr('Parar a gravação e fechar sem usar?'),parent=self.win):return
        self.win.destroy()
    def destroyed(self,event):
        if event.widget is not self.win:return
        self.closed=True
        if self.flow.pending:
            try:self.win.after_cancel(self.flow.pending)
            except tk.TclError:pass
            self.flow.pending=None
        if self.timer:
            try:self.win.after_cancel(self.timer)
            except tk.TclError:pass
            self.timer=None
        self.owner.stop()
        if self.recorder and self.recorder.active and not self.starting:
            def stop():
                try:self.recorder.stop(allow_empty=True)
                except Exception:pass
            threading.Thread(target=stop,daemon=True).start()
    def tick(self):
        if self.closed:return
        while True:
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='devices':
                self.refreshing=False;self.devices=value
                self.device_choice.configure(values=[d['name']+' ['+d['host']+']' for d in value])
                if value:self.device_choice.current(next((i for i,d in enumerate(value) if d['default']),0));self.note.set('Selecione o microfone e clique em Gravar.')
                else:self.note.set('Nenhum microfone disponível. Confira a conexão e as permissões de microfone do Windows.')
            elif kind=='started':self.starting=False;self.note.set('Gravando... Clique em Parar gravação quando terminar.')
            elif kind=='stopped':
                self.finishing=False;self.take=value
                self.note.set(self.recorder.error or ('O sinal atingiu o limite. Confira a gravação ou reduza o nível do microfone e grave novamente.' if self.recorder.clipped else 'Gravação pronta. Ouça antes de usar; se quiser, clique em Gravar para fazer outra tomada.'))
            elif kind in ('error','start_error','stop_error'):
                self.starting=False;self.finishing=False;self.refreshing=False
                self.note.set('Não foi possível gravar. Confira o dispositivo e permita o acesso ao microfone nas configurações de privacidade do Windows.')
                support_report.show(self.owner,self.note.raw + '\n\n' + value,parent=self.win,title=self.owner.tr('Gravar voz'))
            self.enabled()
        recorder=self.recorder
        if recorder:
            seconds=recorder.frames/recorder.rate;minutes=int(seconds//60);self.elapsed.set(f'{minutes:02}:{seconds%60:06.3f}')
            peak=recorder.level;db=20*math.log10(peak) if peak>0 else None
            self.level_var.set(self.owner.tr('Nível do microfone: ')+(f'{db:.1f} dBFS' if db is not None else '—'))
            width=max(1,self.canvas.winfo_width());self.canvas.delete('all');values=list(recorder.levels)
            step=width/max(100,len(values))
            for i,level in enumerate(values):
                height=max(1,level*50);self.canvas.create_rectangle(i*step,30-height/2,(i+1)*step-1,30+height/2,fill=ERROR if level>.98 else SUCCESS,outline='')
            self.note_label.configure(foreground=ERROR if recorder.error or recorder.clipped else MUTED)
            if recorder.error and recorder.active and not self.finishing:self.stop()
        self.timer=self.win.after(80,self.tick)

def open_recorder(owner):
    if owner.busy:return
    if not owner.bank or not owner.selected:owner.status.set(owner.tr('Selecione uma voz do banco antes de gravar.'));return
    existing=getattr(owner,'microphone_window',None)
    if existing and existing.winfo_exists():existing.lift();return
    owner.recording_dialog=RecorderDialog(owner)

def install(Studio):
    Studio.record_voice=lambda self:open_recorder(self)
    original=Studio.close
    def close(self):
        window=getattr(self,'microphone_window',None)
        if window and window.winfo_exists():
            window.lift();self.status.set(self.tr('Feche a janela de gravação antes de sair do aplicativo.'));return
        return original(self)
    Studio.close=close
