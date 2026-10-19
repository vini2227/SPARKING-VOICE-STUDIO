import support_report
import localized_dialogs
"""Selected-voice effect rack with previews, presets and reversible application."""
import tkinter as tk
from tkinter import ttk,simpledialog,messagebox
from pathlib import Path
import shutil,uuid
import voice_effect_presets
import core,voice_effects,voice_ai_ui,trim_history,playback_controls,batch_voice_effects
from modern_theme import BG

class Controls:
 def __init__(self,widgets):self.widgets=widgets
 def configure(self,state):
  for w in self.widgets:w.configure(state='readonly' if state=='normal' and isinstance(w,ttk.Combobox) else state)

class Dialog(voice_ai_ui.Dialog):
 def __init__(self,o):
  self.owner=o;self.mode='effects';self.bank=o.bank;self.row=o.selected.copy();self.key=self.row['key'];self.source=o.replacements.get(self.key)
  self.gain=o.gains.get(self.key,0);self.variation=o.variations.get(self.key,1);self.result=None;self.pending=False;self.closed=False;self.setting=False
  self.folder=core.APP/'Cache/VoiceEffects/Previews'/uuid.uuid4().hex;self.folder.mkdir(parents=True)
  self.win=tk.Toplevel(o);self.win.title(o.tr('Efeitos de voz'));self.win.configure(bg=BG);self.win.transient(o);self.win.geometry('780x730');self.win.minsize(660,680);self.win.grab_set()
  body=ttk.Frame(self.win,padding=18);body.pack(fill='both',expand=True)
  o.label(body,'Efeitos de voz',font=('Segoe UI',16,'bold')).pack(anchor='w')
  o.label(body,'A prévia usa a voz selecionada. Escolha onde aplicar os efeitos.',style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=(4,10))
  line=ttk.Frame(body);line.pack(fill='x');o.label(line,'Preset').pack(side='left',padx=(0,12))
  self.preset=tk.StringVar(value='Personalizado');self.user_presets={};self.preset_error=None
  try:self.user_presets=voice_effect_presets.load()
  except (OSError,ValueError,KeyError,TypeError) as error:self.preset_error=str(error)
  self.choice=o.choice(line,self.preset,self.preset_options(),width=22,translate=False);self.choice.pack(side='left')
  self.save_preset_btn=o.button(line,'Salvar preset',self.save_preset);self.save_preset_btn.pack(side='left',padx=(10,0))
  self.delete_preset_btn=o.button(line,'Excluir preset',self.delete_preset);self.delete_preset_btn.pack(side='left',padx=(8,0))
  self.values={key:tk.DoubleVar(value=default) for key,default in voice_effects.DEFAULT.items() if key!='tail'}
  self.scope=tk.StringVar(value='selected')
  scope_line=ttk.Frame(body);scope_line.pack(fill='x',pady=(8,0));o.label(scope_line,'Aplicar em').pack(side='left',padx=(0,10))
  self.scope_choice=o.choice(scope_line,self.scope,[('selected','Voz selecionada'),('edited','Todas as vozes editadas do banco atual')],width=39);self.scope_choice.pack(side='left')
  self.tail=tk.BooleanVar(value=True);widgets=[self.choice,self.scope_choice,self.save_preset_btn,self.delete_preset_btn]
  labels={'reverb':'Reverb','echo':'Echo','echo_ms':'Intervalo do echo (ms)','pitch':'Pitch (semitons)','bass':'Graves (dB)','treble':'Agudos (dB)','double':'Voz dupla','distortion':'Distorção','radio':'Filtro de rádio','mix':'Intensidade geral'}
  rack=ttk.Frame(body);rack.pack(fill='x',pady=10);rack.columnconfigure(1,weight=1)
  self.readouts={}
  for index,key in enumerate(labels):
   o.label(rack,labels[key],width=23).grid(row=index,column=0,sticky='w',pady=3)
   low,high=voice_effects.LIMITS[key];scale=ttk.Scale(rack,from_=low,to=high,variable=self.values[key]);scale.grid(row=index,column=1,sticky='ew',padx=10);widgets.append(scale)
   var=tk.StringVar();self.readouts[key]=var;ttk.Label(rack,textvariable=var,width=8,anchor='e').grid(row=index,column=2)
  self.tail_box=ttk.Checkbutton(body,text=o.tr('Preservar final do reverb/echo'),variable=self.tail);self.tail_box.pack(anchor='w');widgets.append(self.tail_box)
  o.label(body,'Pitch altera o tom sem mudar a velocidade.',style='Muted.TLabel').pack(anchor='w',pady=(4,8))
  self.generate_btn=o.button(body,'Gerar prévia',self.generate,True);self.generate_btn.pack(anchor='w')
  preview=ttk.Frame(body);preview.pack(fill='x',pady=10)
  self.before_btn=o.button(preview,'Ouvir sem efeitos',lambda:self.listen(False));self.before_btn.pack(side='left',padx=(0,8))
  self.after_btn=o.button(preview,'Ouvir com efeitos',lambda:self.listen(True));self.after_btn.pack(side='left')
  import preview_compare
  preview_compare.setup(self,preview)
  self.info=tk.StringVar(value=o.tr('A prévia não altera o projeto.'));ttk.Label(body,textvariable=self.info,wraplength=700,style='Muted.TLabel').pack(anchor='w',fill='x')
  bottom=ttk.Frame(body);bottom.pack(side='bottom',fill='x',pady=(10,0))
  self.restore_btn=o.button(bottom,'Restaurar antes dos efeitos',self.restore);self.restore_btn.pack(side='left')
  self.close_btn=o.button(bottom,'Fechar',self.close);self.close_btn.pack(side='right')
  self.apply_btn=o.button(bottom,'Aplicar efeitos',self.apply,True);self.apply_btn.pack(side='right',padx=8)
  self.scale=Controls(widgets)
  for var in self.values.values():var.trace_add('write',self.changed)
  self.tail.trace_add('write',self.changed);self.preset.trace_add('write',self.load_preset);self.scope.trace_add('write',self.scope_changed)
  self.changed();self.update_delete_button();self.win.protocol('WM_DELETE_WINDOW',self.close)
  self.win.bind('<Destroy>',lambda e:self.cleanup() if e.widget is self.win else None,add='+')
 def changed(self,*_):
  if self.setting:return
  self.result=None;self.owner.stop()
  for key,var in self.values.items():self.readouts[key].set(f'{var.get():.1f}' if key in ('pitch','bass','treble') else str(round(var.get())))
  self.after_btn.configure(state='disabled');self.apply_btn.configure(state='normal' if self.scope.get()=='edited' else 'disabled');self.compare_btn.configure(state='disabled')
  self.restore_btn.configure(state='normal' if self.key in trim_history.active(self.owner.effects_originals,self.owner.replacements) else 'disabled')
  self.info.set(self.owner.tr('A prévia não altera o projeto.'))
 def scope_changed(self,*_):
  if self.pending:return
  self.apply_btn.configure(state='normal' if self.result or self.scope.get()=='edited' else 'disabled')
  if self.scope.get()=='edited':
   count=len(batch_voice_effects.edited_rows(self.bank,self.owner.replacements))
   self.info.set(self.owner.tr('Vozes editadas no banco atual: ')+str(count))
  else:self.info.set(self.owner.tr('A prévia não altera o projeto.'))
 def preset_options(self):
  return [(key,self.owner.tr(key)) for key in voice_effects.PRESETS]+[(key,item['name'] or self.owner.tr('Preset sem nome')) for key,item in self.user_presets.items()]
 def save_preset(self):
  if self.pending or self.owner.busy:return
  name=localized_dialogs.askstring(self.owner,self.owner.tr('Salvar preset'),self.owner.tr('Nome do preset:'),parent=self.win)
  if name is None:
   self.win.grab_set();return
  # Opening a naming dialog must preserve the effects dialog's modal grab.
  self.win.grab_set()
  try:
   settings={key:value.get() for key,value in self.values.items()};settings['tail']=self.tail.get()
   if name.strip().casefold() in {self.owner.tr(key).casefold() for key in voice_effects.PRESETS}:
    raise ValueError('Esse nome já está em uso. Escolha outro.')
   key=voice_effect_presets.save(name,settings);self.user_presets=voice_effect_presets.load()
   # Preserve the current preview: saving settings does not edit any audio.
   self.setting=True
   try:self.owner.update_choice(self.choice,self.preset_options());self.preset.set(key)
   finally:self.setting=False
   self.update_delete_button()
   self.info.set(self.owner.tr('Preset salvo: ')+self.user_presets[key]['name'])
  except (OSError,ValueError,KeyError,TypeError) as error:
   support_report.show(self.owner,str(error),parent=self.win,title=self.owner.tr('Salvar preset'))
 def update_delete_button(self):
  self.delete_preset_btn.configure(state='normal' if not self.pending and not self.owner.busy and self.preset.get() in self.user_presets else 'disabled')
 def delete_preset(self):
  key=self.preset.get()
  if self.pending or self.owner.busy or key not in self.user_presets:return
  name=self.user_presets[key]['name'] or self.owner.tr('Preset sem nome')
  if not messagebox.askyesno(self.owner.tr('Excluir preset'),self.owner.tr('Excluir o preset "{name}"?').format(name=name),parent=self.win):return
  try:
   voice_effect_presets.delete(key);self.user_presets=voice_effect_presets.load()
   # Deleting stored settings preserves the current knobs, preview and audio.
   self.setting=True
   try:self.owner.update_choice(self.choice,self.preset_options());self.preset.set('Personalizado')
   finally:self.setting=False
   self.update_delete_button();self.info.set(self.owner.tr('Preset excluído: ')+name)
  except (OSError,ValueError,KeyError,TypeError) as error:
   support_report.show(self.owner,str(error),parent=self.win,title=self.owner.tr('Excluir preset'))
 def load_preset(self,*_):
  if self.pending or self.setting:return
  self.setting=True
  try:
   key=self.preset.get()
   settings=self.user_presets[key]['settings'] if key in self.user_presets else voice_effects.PRESETS[key]
   for key,var in self.values.items():var.set(settings[key])
   self.tail.set(settings['tail'])
  finally:self.setting=False
  self.changed();self.update_delete_button()
 def job(self,work,done,text,edit_label=None):
  if self.owner.busy or self.pending:return
  self.pending=True;self.compare_btn.configure(state='disabled')
  for b in (self.generate_btn,self.before_btn,self.after_btn,self.apply_btn,self.restore_btn):b.configure(state='disabled')
  self.scale.configure(state='disabled');self.info.set(self.owner.tr(text))
  self.owner.job(work,done,self.owner.tr(text),edit_label=edit_label)
  def ready():
   if self.closed:return
   if self.owner.busy:self.owner.after(100,ready);return
   self.pending=False;self.scale.configure(state='normal');self.update_delete_button();self.generate_btn.configure(state='normal');self.before_btn.configure(state='normal')
   if self.result:
    self.after_btn.configure(state='normal');self.apply_btn.configure(state='normal');self.compare_btn.configure(state='normal')
   else:self.info.set(self.owner.status.get())
   if self.scope.get()=='edited':self.apply_btn.configure(state='normal')
   self.restore_btn.configure(state='normal' if self.key in trim_history.active(self.owner.effects_originals,self.owner.replacements) else 'disabled')
  self.owner.after(100,ready)
 def generate(self):
  if not self.current():self.info.set(self.owner.tr('A voz mudou. Feche e abra a ferramenta novamente.'));return
  self.owner.stop();self.result=None;settings={k:v.get() for k,v in self.values.items()};settings['tail']=self.tail.get();output=self.folder/(uuid.uuid4().hex+'.wav')
  def work():
   source=self.source or str(self.bank.original(self.row));return str(output),voice_effects.render(source,output,settings)
  def done(result):
   self.result=result[0];self.info.set(self.owner.tr('Prévia pronta. Ouça antes de aplicar.')+' '+self.owner.tr('Cauda do efeito (s): ')+f"{result[1]['tail_seconds']:.3f}")
  self.job(work,done,'Processando efeitos de voz...')
 def listen(self,after):
  import preview_compare
  return preview_compare.listen(self,after)
 def apply(self):
  if self.scope.get()=='edited':return self.apply_all()
  if not self.result or not self.current():return
  o=self.owner;result=self.result;dest=o.project/'Replacements'/(self.key+'_effects_'+uuid.uuid4().hex+'.wav')
  prior=trim_history.active(o.effects_originals,o.replacements).get(self.key)
  def work():
   source=self.source or self.bank.original(self.row)
   original=Path(prior['original']) if prior else o.project/'EffectsOriginals'/(self.key+'_'+uuid.uuid4().hex+'.wav')
   if not prior:original.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,original)
   dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(result,dest)
   gain=voice_effects.safe_gain(dest,self.row,self.gain,self.variation)
   return {'original':str(original),'trimmed':str(dest)},gain
  def done(result):
   history,gain=result
   o.stop();o.hide_audio_trim();o.replacements[self.key]=str(dest);o.effects_originals[self.key]=history;o.gains[self.key]=gain;o.level_token+=1;o.level_signature=None;o.fill_rows();o.select()
   o.status.set(o.tr('Efeitos aplicados. Salve o projeto para guardar.')+(' '+o.tr('Ganho ajustado automaticamente para evitar clipping: ')+f'{gain:.1f} dB' if gain<self.gain else ''));self.source=str(dest);self.close(force=True)
  self.job(work,done,'Aplicando efeitos de voz...',edit_label='Aplicar efeitos')
 def apply_all(self):
  if not self.current():self.info.set(self.owner.tr('A voz mudou. Feche e abra a ferramenta novamente.'));return
  o=self.owner;bank=self.bank;project=o.project;replacements=dict(o.replacements);originals=dict(o.effects_originals);gains=dict(o.gains);variations=dict(o.variations)
  if not batch_voice_effects.edited_rows(bank,replacements):self.info.set(o.tr('Não há áudios editados neste banco.'));return
  settings={k:v.get() for k,v in self.values.items()};settings['tail']=self.tail.get();o.stop()
  def work():
   return batch_voice_effects.stage(bank,project,replacements,originals,settings,
       lambda text:o.jobs.put(('status',o.tr('Aplicando efeitos às vozes editadas: ')+text)),gains=gains,variations=variations)
  def done(result):
   if o.bank is not bank or o.project!=project or o.replacements!=replacements:raise ValueError('O projeto mudou durante o processamento.')
   o.stop();o.hide_audio_trim();o.replacements.update(result['replacements']);o.effects_originals.update(result['originals']);o.gains.update(result['gains']);o.level_token+=1;o.level_signature=None;o.fill_rows();o.select()
   o.status.set(o.tr('Vozes editadas com efeitos aplicados: ')+str(result['count'])+'. '+o.tr('Salve o projeto para guardar.'))
   self.close(force=True)
  self.job(work,done,'Aplicando efeitos às vozes editadas...',edit_label='Aplicar efeitos em todas as vozes editadas')
 def restore(self):
  o=self.owner
  if o.busy or not self.current():return
  history=trim_history.active(o.effects_originals,o.replacements).get(self.key)
  if not history:return
  before=o.history.begin();o.stop();o.hide_audio_trim();o.replacements[self.key]=history['original'];o.effects_originals.pop(self.key,None);o.level_token+=1;o.level_signature=None;o.fill_rows();o.select();o.history.finish(before,'Restaurar antes dos efeitos');o.status.set(o.tr('Áudio anterior restaurado. Os ajustes de ganho e variação foram mantidos.'));self.close(force=True)
 def cleanup(self):
  if self.closed:return
  self.closed=True;self.owner.stop()
  if self.folder.resolve().is_relative_to((core.APP/'Cache/VoiceEffects/Previews').resolve()):shutil.rmtree(self.folder,ignore_errors=True)

def install(Studio):
 def show(self):
  if self.busy:return
  if not self.can_trim_audio():self.fail('Selecione uma voz substituída ou uma voz importada confirmada como diferente.');return
  self.voice_effects_window=Dialog(self)
 Studio.show_voice_effects=show
 def menu(self):
  if self.busy:return
  import modern_theme
  popup=tk.Menu(self,tearoff=False,bg=modern_theme.CARD,fg=modern_theme.FG,activebackground='#30291e',activeforeground=modern_theme.FG)
  popup.add_command(label=self.tr('Personalizar efeitos'),command=self.show_voice_effects)
  popup.add_command(label=self.tr('Velocidade da voz'),command=self.show_voice_speed)
  popup.add_separator()
  for preset in voice_effects.PRESETS:
   if preset in ('Personalizado','Sem efeitos'):continue
   def choose(preset=preset):
    if not self.can_trim_audio():self.show_voice_effects();return
    self.show_voice_effects();self.voice_effects_window.preset.set(preset)
   popup.add_command(label=self.tr(preset),command=choose)
  try:popup.tk_popup(self.effects_btn.winfo_rootx(),self.effects_btn.winfo_rooty()+self.effects_btn.winfo_height())
  finally:popup.grab_release()
  old=getattr(self,'_effects_menu',None)
  if old:old.destroy()
  self._effects_menu=popup
 Studio.show_voice_effects_menu=menu
 import session_features
 session_features.HELP['Efeitos de voz']='Use Efeitos de voz na voz selecionada para ajustar reverb, echo, pitch sem mudar a velocidade, graves, agudos, voz dupla, distorção e filtro de rádio. Use um preset ou ajuste as intensidades. Gerar prévia não altera o projeto; Ouvir sem efeitos e Ouvir com efeitos permitem comparar usando o mesmo ganho e variação. Preservar final do reverb/echo mantém a cauda do efeito (até 30 segundos adicionais). Em Aplicar em, escolha Voz selecionada ou Todas as vozes editadas do banco atual. A aplicação em lote inclui substituições e vozes importadas confirmadas como diferentes, exclui originais e independe dos filtros da lista. Os mesmos parâmetros são aplicados a cada áudio, mantendo os ganhos e variações individuais. Se algum áudio falhar, nenhuma edição é aplicada ao projeto. Ctrl+Z desfaz o lote inteiro. Aplicar efeitos grava um WAV completo, sem cortar a duração original. Salve o projeto. Restaurar antes dos efeitos recupera o áudio anterior ao primeiro efeito da sequência. Ctrl+Z desfaz e Ctrl+Y refaz. Os originais também são preservados no projeto salvo, recuperação automática e projeto compartilhado. Se o ganho anterior causar clipping após os efeitos, ele é reduzido automaticamente só até o limite seguro. A prévia não altera o projeto; o ganho corrigido é mantido ao aplicar. O processamento é local. Picos que ultrapassariam 0 dBFS são reduzidos sem aumentar o volume de gravações baixas.'
