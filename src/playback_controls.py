"""One playback owner, with stable-width play/stop buttons across all dialogs."""
import math,wave,winsound
import tkinter as tk
from tkinter import font as tkfont
import button_identity

def register(owner,button,text,callback):
    if not hasattr(owner,'_playback_buttons'):owner._playback_buttons=[]
    owner._playback_buttons.append((button,text))
    def clicked():
        if getattr(owner,'_active_play_button',None) is button:
            owner.stop()
        else:callback()
    button.configure(command=clicked)
    def destroyed(event):
        if event.widget is button and getattr(owner,'_active_play_button',None) is button:owner.stop()
    button.bind('<Destroy>',destroyed,add='+')
    refresh(owner)
    return button

def refresh(owner):
    alive=[]
    for button,text in getattr(owner,'_playback_buttons',[]):
        if not button.winfo_exists():continue
        alive.append((button,text))
        play_label=owner.tr(text).lstrip('▶■ ').strip()
        stop_label=owner.tr('■ Parar').lstrip('▶■ ').strip()
        font=tkfont.nametofont('TkDefaultFont',root=owner)
        width=math.ceil(max(font.measure(play_label),font.measure(stop_label))/max(1,font.measure('0')))+2
        active=getattr(owner,'_active_play_button',None) is button
        button.configure(text=stop_label if active else play_label,width=width,compound='left',
                         image=button_identity.icon(owner,'stop' if active else 'play','#ffb23f'))
    owner._playback_buttons=alive

def reset(owner):
    timer=getattr(owner,'_playback_finish_after',None)
    owner._playback_finish_after=None
    if timer:
        try:owner.after_cancel(timer)
        except tk.TclError:pass
    owner._active_play_button=None
    cleanup=getattr(owner,'_playback_cleanup',None);owner._playback_cleanup=None
    refresh(owner)
    if cleanup:cleanup()

def start(owner,path,button=None,*,stop_first=True,finish=True,cleanup=None):
    if stop_first:owner.stop()
    # All previews are PCM WAVs produced by the existing import/render paths.
    with wave.open(str(path),'rb') as stream:duration=stream.getnframes()/stream.getframerate()
    winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC)
    owner.playing=path;owner._active_play_button=button;owner._playback_cleanup=cleanup
    refresh(owner)
    if finish:owner._playback_finish_after=owner.after(max(1,math.ceil(duration*1000)),owner.stop)
    return duration
