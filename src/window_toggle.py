"""Reuse modeless tool windows while preserving unsaved fields and scroll state."""
import tkinter as tk


def existing(owner,attribute):
    window=getattr(owner,attribute,None)
    if window is None:return False
    try:
        if not window.winfo_exists():return False
        if window.state() in ('withdrawn','iconic'):
            window.deiconify();window.lift();window.focus_set()
        else:window.withdraw()
        return True
    except tk.TclError:
        return False


def refresh_titles(owner,previous_language):
    """Refresh owned tool titles without destroying fields or changing visibility."""
    from i18n import Translator
    previous=Translator(previous_language)
    keys=('Configurações','Ajuda','Projetos recentes','Ferramentas de Projeto',
          'Áudio e volume','Migrar banco antigo','Identificar voz','Recuperar sessão',
          'Revisar mescla','Copiar vozes por tags ou função','Velocidade da voz',
          'Aprimorar voz','Isolar voz','Efeitos de voz','Gravar voz','Escolher faixa de áudio')
    for child in owner.winfo_children():
        if not isinstance(child,tk.Toplevel):continue
        title=child.title()
        for key in keys:
            if title==previous.text(key):
                child.title(owner.tr(key));break
        refresh=getattr(child,'_refresh_language',None)
        if refresh is not None:refresh()
