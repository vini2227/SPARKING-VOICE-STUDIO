"""Reviewed local audio processing with a preserved, reversible source."""
import tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
import shutil,uuid
import core,voice_ai,trim_history,playback_controls
from modern_theme import BG

HELP_TITLE='Aprimorar e isolar voz'
HELP_TEXT='Selecione uma voz substituída ou uma voz importada confirmada como diferente e use Aprimorar voz ou Isolar voz ao lado de Cortar áudio. Aprimorar voz reduz ruído de uma gravação; Isolar voz tenta separar a fala de música e outros sons. O processamento é local, sem envio dos áudios à internet. Escolha a intensidade e clique em Gerar prévia. Ouvir antes e Ouvir depois usam os mesmos ajustes de ganho e variação. A prévia não altera o projeto. Aplicar resultado grava a edição; depois use Desfazer/Refazer ou Restaurar antes da IA na mesma ferramenta. O áudio anterior também é preservado ao salvar, recuperar ou compartilhar o projeto. Intensidades altas podem alterar o timbre e remover partes de gritos ou efeitos: compare antes de aplicar. Não há garantia de resultado igual ao CapCut.'

class Dialog:
 def __init__(self,o,mode):
  self.owner=o;self.mode=mode;self.bank=o.bank;self.row=o.selected.copy();self.key=self.row['key'];self.source=o.replacements.get(self.key)
  self.gain=o.gains.get(self.key,0);self.variation=o.variations.get(self.key,1);self.result=None;self.pending=False;self.closed=False
  self.folder=core.APP/'Cache/VoiceAI/Previews'/uuid.uuid4().hex;self.folder.mkdir(parents=True)
  self.win=tk.Toplevel(o);self.win.title(o.tr('Aprimorar voz' if mode=='enhance' else 'Isolar voz'));self.win.configure(bg=BG);self.win.transient(o);self.win.geometry('720x420');self.win.minsize(640,390);self.win.grab_set()
  body=ttk.Frame(self.win,padding=20);body.pack(fill='both',expand=True)
  o.label(body,'Aprimorar voz' if mode=='enhance' else 'Isolar voz',font=('Segoe UI',16,'bold')).pack(anchor='w')
  o.label(body,'Reduz ruído de uma gravação de voz.' if mode=='enhance' else 'Separa a voz de música e outros sons.',wraplength=630).pack(anchor='w',pady=(8,4))
  o.label(body,'Processamento local. Compare a prévia: intensidades altas podem alterar o timbre ou remover partes de gritos.',wraplength=630,style='Muted.TLabel').pack(anchor='w',pady=(0,12))
  self.strength=tk.DoubleVar(value=75 if mode=='enhance' else 100);self.percent=tk.StringVar();self.info=tk.StringVar(value=o.tr('A prévia não altera o projeto.'))
  line=ttk.Frame(body);line.pack(fill='x');o.label(line,'Intensidade').pack(side='left');ttk.Label(line,textvariable=self.percent,width=6,anchor='e').pack(side='right')
  self.scale=ttk.Scale(body,from_=0,to=100,variable=self.strength,command=self.changed);self.scale.pack(fill='x',pady=(4,14))
  self.generate_btn=o.button(body,'Gerar prévia',self.generate,True);self.generate_btn.pack(anchor='w')
  preview=ttk.Frame(body);preview.pack(fill='x',pady=14)
  self.before_btn=o.button(preview,'Ouvir antes',lambda:self.listen(False));self.before_btn.pack(side='left',padx=(0,10))
  self.after_btn=o.button(preview,'Ouvir depois',lambda:self.listen(True));self.after_btn.pack(side='left');self.after_btn.configure(state='disabled')
  import preview_compare
  preview_compare.setup(self,preview)
  ttk.Label(body,textvariable=self.info,wraplength=630,style='Muted.TLabel').pack(anchor='w',fill='x')
  bottom=ttk.Frame(body);bottom.pack(side='bottom',fill='x',pady=(14,0))
  self.restore_btn=o.button(bottom,'Restaurar antes da IA',self.restore);self.restore_btn.pack(side='left')
  self.close_btn=o.button(bottom,'Fechar',self.close);self.close_btn.pack(side='right')
  self.apply_btn=o.button(bottom,'Aplicar resultado',self.apply,True);self.apply_btn.pack(side='right',padx=8)
  self.changed();self.win.protocol('WM_DELETE_WINDOW',self.close)
  self.win.bind('<Destroy>',lambda e:self.cleanup() if e.widget is self.win else None,add='+')
 def current(self):return self.owner.bank is self.bank and self.owner.replacements.get(self.key)==self.source
 def restore_records(self):return self.owner.processing_originals
 def changed(self,*_):
  self.percent.set(f'{round(self.strength.get())}%');self.result=None
  if hasattr(self,'apply_btn'):
   self.apply_btn.configure(state='disabled');self.after_btn.configure(state='disabled');self.compare_btn.configure(state='disabled')
   history=trim_history.active(self.restore_records(),self.owner.replacements)
   self.restore_btn.configure(state='normal' if self.key in history else 'disabled')
   self.owner.stop()
 def job(self,work,done,text,edit_label=None):
  if self.owner.busy or self.pending:return
  self.pending=True;self.compare_btn.configure(state='disabled')
  for b in (self.generate_btn,self.before_btn,self.after_btn,self.apply_btn,self.restore_btn):b.configure(state='disabled')
  self.scale.configure(state='disabled');self.info.set(self.owner.tr(text))
  self.owner.job(work,done,self.owner.tr(text),edit_label=edit_label)
  def ready():
   if self.closed:return
   if self.owner.busy:self.info.set(self.owner.status.get());self.win.after(100,ready);return
   self.pending=False;self.scale.configure(state='normal');self.generate_btn.configure(state='normal');self.before_btn.configure(state='normal')
   if self.result:
    self.after_btn.configure(state='normal');self.apply_btn.configure(state='normal');self.compare_btn.configure(state='normal')
   else:self.info.set(self.owner.status.get())
   self.restore_btn.configure(state='normal' if self.key in trim_history.active(self.restore_records(),self.owner.replacements) else 'disabled')
  self.win.after(100,ready)
 def generate(self):
  if not self.current():self.info.set(self.owner.tr('A voz mudou. Feche e abra a ferramenta novamente.'));return
  self.owner.stop();self.result=None;strength=round(self.strength.get());output=self.folder/(uuid.uuid4().hex+'.wav')
  def work():
   source=self.source or str(self.bank.original(self.row));voice_ai.process(source,output,self.mode,strength,progress=lambda text:self.owner.jobs.put(('status',text)));return str(output)
  def done(path):
   self.result=path;self.info.set(self.owner.tr('Prévia pronta. Ouça antes de aplicar.'))
  self.job(work,done,'Processando voz localmente...')
 def listen(self,after):
  import preview_compare
  return preview_compare.listen(self,after)
 def apply(self):
  if not self.result or not self.current():return
  o=self.owner;result=self.result;dest=o.project/'Replacements'/(self.key+'_ai_'+uuid.uuid4().hex+'.wav');prior=trim_history.active(o.processing_originals,o.replacements).get(self.key)
  def work():
   source=self.source or self.bank.original(self.row)
   original=Path(prior['original']) if prior else o.project/'ProcessingOriginals'/(self.key+'_'+uuid.uuid4().hex+'.wav')
   if not prior:original.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,original)
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(result,dest)
   import voice_effects
   gain=voice_effects.safe_gain(dest,self.row,self.gain,self.variation)
   return {'original':str(original),'trimmed':str(dest)},gain
  def done(result):
   history,gain=result
   o.gains[self.key]=gain
   o.stop();o.hide_audio_trim();o.replacements[self.key]=str(dest);o.processing_originals[self.key]=history;o.level_token+=1;o.level_signature=None;o.fill_rows();o.select()
   o.status.set(o.tr('Processamento aplicado. Clique em Salvar projeto para guardar.')+(' '+o.tr('Ganho ajustado automaticamente para evitar clipping: ')+f'{gain:.1f} dB' if gain<self.gain else ''));self.source=str(dest);self.close(force=True)
  self.job(work,done,'Aplicando processamento de voz...',edit_label='Aprimorar voz' if self.mode=='enhance' else 'Isolar voz')
 def restore(self):
  o=self.owner
  if o.busy or not self.current():return
  history=trim_history.active(o.processing_originals,o.replacements).get(self.key)
  if not history:return
  before=o.history.begin();o.stop();o.hide_audio_trim();o.replacements[self.key]=history['original'];o.processing_originals.pop(self.key,None);o.level_token+=1;o.level_signature=None;o.fill_rows();o.select();o.history.finish(before,'Restaurar antes da IA');o.status.set(o.tr('Áudio anterior restaurado. Os ajustes de ganho e variação foram mantidos.'));self.close(force=True)
 def close(self,force=False):
  if self.pending and not force:
   messagebox.showinfo(self.owner.tr('Operação em andamento'),self.owner.tr('Aguarde a operação terminar antes de fechar.'),parent=self.win);return
  self.owner.stop();self.win.destroy()
 def cleanup(self):
  if self.closed:return
  self.closed=True;self.owner.stop()
  if self.folder.resolve().is_relative_to((core.APP/'Cache/VoiceAI/Previews').resolve()):shutil.rmtree(self.folder,ignore_errors=True)

def install(Studio):
 def show(self,mode):
  if self.busy:return
  if not self.can_trim_audio():self.fail('Selecione uma voz substituída ou uma voz importada confirmada como diferente.');return
  self.voice_ai_window=Dialog(self,mode)
 Studio.voice_ai_dialog=show
 import session_features
 session_features.HELP[HELP_TITLE]=HELP_TEXT
