"""Choose a track only when the imported media contains several audio streams."""
import tkinter as tk
from tkinter import ttk
from modern_theme import BG

class VideoAudioMixin:
    def choose_video_audio(self,source,row,tracks):
        if len(tracks)==1:
            self._import_audio_file(source,row,tracks[0]['index']);return
        win=tk.Toplevel(self);win.title(self.tr('Escolher faixa de áudio'));win.configure(bg=BG);win.transient(self);win.resizable(False,False)
        self.video_track_window=win;body=ttk.Frame(win,padding=20);body.pack(fill='both',expand=True)
        self.label(body,'Este vídeo possui várias faixas de áudio. Escolha qual importar.',wraplength=560).pack(anchor='w',pady=(0,14))
        labels=[]
        for n,item in enumerate(tracks):
            parts=[self.tr('Faixa')+f" {n+1}",item['title'] or item['language'] or '—',item['codec'],str(item['channels'])+' '+self.tr('canais')]
            if item['default']:parts.append(self.tr('Padrão'))
            labels.append(' • '.join(parts))
        choice=ttk.Combobox(body,values=labels,state='readonly',width=68);choice.pack(fill='x')
        choice.current(next((i for i,item in enumerate(tracks) if item['default']),0));self.video_track_choice=choice
        self.label(body,'Somente o áudio será convertido para WAV. O vídeo original será preservado.',wraplength=560,style='Muted.TLabel').pack(anchor='w',pady=12)
        buttons=ttk.Frame(body);buttons.pack(fill='x')
        def cancel():win.destroy();self.status.set('Importação cancelada.')
        def confirm():
            item=tracks[choice.current()];win.destroy();self._import_audio_file(source,row,item['index'])
        self.button(buttons,'Cancelar',cancel).pack(side='right')
        self.video_track_import_button=self.button(buttons,'Importar faixa',confirm,True);self.video_track_import_button.pack(side='right',padx=8)
        win.protocol('WM_DELETE_WINDOW',cancel);win.bind('<Escape>',lambda event:cancel())
        win.grab_set();win.focus_set()
