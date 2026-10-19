"""Speed slider with reviewed previews and a reversible project edit."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import shutil,uuid
import trim_history
import core,voice_speed,voice_ai_ui,voice_effects_ui,voice_effects,playback_controls
from modern_theme import BG,CARD,FG,MUTED,EDGE

class Dialog(voice_ai_ui.Dialog):
 def __init__(self,o):
  self.owner=o;self.mode='speed';self.bank=o.bank;self.row=o.selected.copy();self.key=self.row['key'];self.source=o.replacements.get(self.key)
  self.gain=o.gains.get(self.key,0);self.variation=o.variations.get(self.key,1);self.result=None;self.pending=False;self.closed=False;self.setting=False
  self.folder=core.APP/'Cache/VoiceSpeed/Previews'/uuid.uuid4().hex;self.folder.mkdir(parents=True)
  self.win=tk.Toplevel(o);self.win.title(o.tr('Velocidade da voz'));self.win.configure(bg=BG);self.win.transient(o)
  self.win.geometry(f'{min(680,self.win.winfo_screenwidth()-60)}x{min(420,self.win.winfo_screenheight()-80)}');self.win.minsize(400,320);self.win.grab_set()
  bottom=ttk.Frame(self.win,padding=(18,10));bottom.pack(side='bottom',fill='x')
  self.close_btn=o.button(bottom,'Fechar',self.close);self.close_btn.pack(side='right')
  self.apply_btn=o.button(bottom,'Aplicar resultado',self.apply,True);self.apply_btn.pack(side='right',padx=8)
  restore_row=ttk.Frame(bottom);restore_row.pack(side='bottom',fill='x',pady=(8,0))
  self.restore_btn=o.button(restore_row,'Restaurar antes da velocidade',self.restore);self.restore_btn.pack(anchor='w')
  viewport=ttk.Frame(self.win);viewport.pack(fill='both',expand=True)
  canvas=tk.Canvas(viewport,bg=BG,highlightthickness=0);canvas.pack(side='left',fill='both',expand=True)
  scroll=ttk.Scrollbar(viewport,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y');canvas.configure(yscrollcommand=scroll.set)
  body=ttk.Frame(canvas,padding=(18,10));window=canvas.create_window(0,0,window=body,anchor='nw')
  canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
  body.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
  self.win.bind('<MouseWheel>',lambda e:canvas.yview_scroll(-int(e.delta/120),'units') if e.widget is not self.entry else None)
  o.label(body,'Velocidade da voz',font=('Segoe UI',16,'bold')).pack(anchor='w')
  self.hint=o.label(body,'Ajuste a velocidade, compare a prévia e aplique. Ctrl+Z desfaz.',style='Muted.TLabel',wraplength=620);self.hint.pack(fill='x',pady=(6,14))
  line=ttk.Frame(body);line.pack(fill='x');o.label(line,'Velocidade').pack(side='left')
  self.factor=tk.StringVar(value='1.00');self.slider=tk.DoubleVar(value=1);self.keep_pitch=tk.BooleanVar(value=True)
  self.entry=tk.Spinbox(line,from_=.25,to=3,increment=.05,textvariable=self.factor,width=7,format='%.2f',font=('Segoe UI',10),bg=CARD,fg=FG,insertbackground=FG,buttonbackground=CARD,disabledbackground=CARD,disabledforeground=MUTED,readonlybackground=CARD,selectbackground='#365678',selectforeground=FG,relief='flat',highlightthickness=1,highlightbackground=EDGE,highlightcolor=FG);self.entry.pack(side='left',padx=(12,4))
  ttk.Label(line,text='x').pack(side='left')
  self.reset_btn=o.button(line,'1.00x',self.reset);self.reset_btn.pack(side='right')
  slider=ttk.Scale(body,from_=.25,to=3,variable=self.slider,command=self.slide);slider.pack(fill='x',pady=10)
  self.pitch_box=ttk.Checkbutton(body,text=o.tr('Preservar o tom da voz'),variable=self.keep_pitch);self.pitch_box.pack(anchor='w')
  self.info=tk.StringVar(value=o.tr('A prévia não altera o projeto.'))
  self.info_label=ttk.Label(body,textvariable=self.info,wraplength=620,style='Muted.TLabel');self.info_label.pack(fill='x',pady=12)
  self.generate_btn=o.button(body,'Gerar prévia',self.generate,True);self.generate_btn.pack(anchor='w')
  preview=ttk.Frame(body);preview.pack(fill='x',pady=12)
  self.before_btn=o.button(preview,'Ouvir antes',lambda:self.listen(False));self.before_btn.pack(side='left',padx=(0,10))
  self.after_btn=o.button(preview,'Ouvir depois',lambda:self.listen(True));self.after_btn.pack(side='left')
  import preview_compare
  preview_compare.setup(self,preview)
  self.scale=voice_effects_ui.Controls([slider,self.entry,self.reset_btn,self.pitch_box])
  self.factor.trace_add('write',self.changed);self.keep_pitch.trace_add('write',self.changed);self.changed()
  body.bind('<Configure>',lambda e:[w.configure(wraplength=max(150,e.width-36)) for w in (self.hint,self.info_label)],add='+')
  self.win.protocol('WM_DELETE_WINDOW',self.close);self.win.bind('<Destroy>',lambda e:self.cleanup() if e.widget is self.win else None,add='+')
 def restore_records(self):return self.owner.speed_originals
 def slide(self,value):self.factor.set(f'{float(value):.2f}')
 def reset(self):self.factor.set('1.00')
 def changed(self,*_):
  if self.pending:return
  self.restore_btn.configure(state='normal' if self.key in trim_history.active(self.restore_records(),self.owner.replacements) else 'disabled')
  self.result=None;self.owner.stop();self.after_btn.configure(state='disabled');self.apply_btn.configure(state='disabled');self.compare_btn.configure(state='disabled')
  try:
   factor=voice_speed.valid(self.factor.get().replace(',','.'));self.slider.set(factor);self.generate_btn.configure(state='normal');self.info.set(self.owner.tr('A prévia não altera o projeto.'))
  except ValueError as error:
   self.generate_btn.configure(state='disabled');self.info.set(self.owner.tr(str(error)))
 def generate(self):
  if self.pending or not self.current():return
  try:factor=voice_speed.valid(self.factor.get().replace(',','.'))
  except ValueError as error:self.info.set(self.owner.tr(str(error)));return
  preserve=self.keep_pitch.get();output=self.folder/(uuid.uuid4().hex+'.wav');self.owner.stop();self.result=None
  def work():return voice_speed.render(self.source or self.bank.original(self.row),output,factor,preserve)
  def done(stats):
   self.result=str(output);self.info.set(self.owner.tr('Prévia pronta. Ouça antes de aplicar.')+f" {stats['before']:.3f}s → {stats['after']:.3f}s • {factor:.2f}x")
  self.job(work,done,'Processando velocidade da voz...')
 def listen(self,after):
  import preview_compare
  return preview_compare.listen(self,after)
 def apply(self):
  if self.pending or not self.result or not self.current():return
  o=self.owner;dest=o.project/'Replacements'/(self.key+'_speed_'+uuid.uuid4().hex+'.wav');result=self.result
  prior=trim_history.active(o.speed_originals,o.replacements).get(self.key)
  def work():
   gain=voice_effects.safe_gain(result,self.row,self.gain,self.variation)
   original=Path(prior['original']) if prior else o.project/'SpeedOriginals'/(self.key+'_'+uuid.uuid4().hex+'.wav')
   if not prior:
    original.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(self.source or self.bank.original(self.row),original)
   try:
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(result,dest)
   except Exception:
    if not prior:original.unlink(missing_ok=True)
    dest.unlink(missing_ok=True);raise
   return str(dest),gain,{'original':str(original),'trimmed':str(dest)}
  def done(result):
   path,gain,history=result
   o.stop();o.hide_audio_trim();o.replacements[self.key]=path;o.speed_originals[self.key]=history
   if gain<self.gain:o.gains[self.key]=gain
   o.level_token+=1;o.level_signature=None;o.fill_rows();o.select()
   o.status.set(o.tr('Processamento aplicado. Clique em Salvar projeto para guardar.')+(' '+o.tr('Ganho ajustado automaticamente para evitar clipping: ')+f'{gain:.1f} dB' if gain<self.gain else ''));self.source=path;self.close(force=True)
  self.job(work,done,'Aplicando processamento de voz...',edit_label='Alterar velocidade da voz')
 def restore(self):
  o=self.owner
  if self.pending or o.busy or not self.current():return
  history=trim_history.active(o.speed_originals,o.replacements).get(self.key)
  if not history:return
  before=o.history.begin();o.stop();o.hide_audio_trim()
  o.replacements[self.key]=history['original'];o.speed_originals.pop(self.key,None)
  o.level_token+=1;o.level_signature=None;o.fill_rows();o.select()
  o.history.finish(before,'Restaurar antes da velocidade')
  o.status.set(o.tr('Áudio anterior restaurado. Os ajustes de ganho e variação foram mantidos.'));self.close(force=True)
 def cleanup(self):
  if self.closed:return
  self.closed=True;self.owner.stop()
  if self.folder.resolve().is_relative_to((core.APP/'Cache/VoiceSpeed/Previews').resolve()):shutil.rmtree(self.folder,ignore_errors=True)

def install(Studio):
 def show(self):
  if self.busy:return
  if not self.can_trim_audio():self.fail('Selecione uma voz substituída ou uma voz importada confirmada como diferente.');return
  self.voice_speed_window=Dialog(self)
 Studio.show_voice_speed=show
 import session_features
 session_features.HELP['Velocidade da voz']='Abra Efeitos de voz e escolha Velocidade da voz. Ajuste de 0.25x a 3.00x; 1.00x mantém a velocidade. Preservar o tom da voz altera somente o ritmo. Desmarque para mudar também o tom. Gere a prévia e compare antes/depois. Aplicar resultado salva a nova duração no áudio editado; depois salve o projeto. Ctrl+Z desfaz e Ctrl+Y refaz. O processamento é local.'
