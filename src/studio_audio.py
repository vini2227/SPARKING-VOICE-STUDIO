"""Unified language and per-voice level controls for Studio."""
import threading
from pathlib import Path
import core
import audio_levels
import audio_variations
import voice_context
import hashlib
from modern_theme import MUTED,SUCCESS,WARNING,ERROR,FG

class AudioStudioMixin:
    def function_text(self,row):
        language=self.function_language.get()
        scope=self.function_scope.get()
        english=list(dict.fromkeys(v for v in row.get('english',[]) if v!='Unclassified')) if scope not in ('interactions','emotes') else []
        import compact_functions
        values=[compact_functions.function(v,language) for v in english]
        values+=voice_context.descriptions(row,language,scope)
        values=list(dict.fromkeys(values))
        return self.translator.display(' / '.join(values)) if values else self.tr('Não identificada')

    def tag_label(self,tag):
        english=self.function_catalog['tags'].get(tag,[])
        descriptions=[self.function_catalog.get(self.function_language.get(),{}).get(v,v) for v in english]
        return (' / '.join(descriptions)+' — '+tag) if descriptions else tag

    def change_function_language(self):
        self.apply_language(self.function_language.get())
        self.cfg['ui_language']=self.translator.language
        self.cfg['function_language']=self.translator.language
        core.write_json(core.APP/'settings.json',self.cfg)

    def fit_inspector(self):
        if not hasattr(self,'split') or len(self.split.panes())<2:return
        if getattr(self,'_fitting_inspector',False):return
        # Configure/idle callbacks supply geometry updates. Do not recursively
        # flush the whole UI while handling a layout event.
        detail=self.nametowidget(self.split.panes()[1])
        height=self.split.winfo_height()
        # Fit for structural changes only, never for a new voice or meter text.
        # Flow rows settle after the first geometry pass. Their requested height
        # can still change with the same window size (including at startup).
        # Numeric meter updates have fixed-size labels and do not change this.
        requested=self.stable_inspector_height(detail,height)
        signature=(height,self.split.winfo_width(),self.inspector_expanded.get(),
                   self.function_language.get(),requested)
        if signature==getattr(self,'_inspector_geometry',None) or height<100:return
        self._inspector_geometry=signature
        target=max(0,height-requested-5)
        if self.split.sashpos(0)!=target:self.split.sashpos(0,target)

    def request_levels(self):
        if not self.bank or not self.selected:return
        key=self.selected['key'];source=self.replacements.get(key)
        variation=self.variations.get(key,1)
        signature=(id(self.bank),key,source,variation)
        if signature==self.level_signature:
            self.update_levels();return
        self.level_signature=signature;self.level_token+=1;token=self.level_token
        self.level_data={};self.update_levels()
        if self.level_after:
            self.after_cancel(self.level_after);self.level_after=None
        bank=self.bank;reference=self.reference_bank;row=self.selected.copy()
        def launch():
            self.level_after=None
            def measure():
                with self.level_lock:
                    if token!=self.level_token:return
                    result={'key':key,'reference':None,'source':None,'source_path':None}
                    try:
                        reference_voice=core.reference_row(bank,reference,row)
                        if reference_voice is not None:
                            original=reference.original(reference_voice)
                            result['reference']=audio_levels.analyze(original)
                    except Exception as error:result['reference_error']=str(error)
                    if token!=self.level_token:return
                    try:
                        path=Path(source) if source else bank.original(row) if bank.external else None
                        if path:
                            result['source']=audio_levels.analyze(path);result['raw_source']=result['source'];result['source_path']=str(path)
                            if variation!=1:
                                digest=hashlib.sha256(path.read_bytes()).hexdigest()[:20]
                                processed=core.APP/'Cache/Variations'/(digest+'_'+audio_variations.CACHE_VERSION+'_'+str(variation)+'.wav')
                                if not processed.exists():core.normalize_wav(path,processed,row['rate'],row['channels'],row['samples'],variation=variation)
                                result['source']=audio_levels.analyze(processed)
                    except Exception as error:result['source_error']=str(error)
                    self.jobs.put(('levels',(token,result)))
            threading.Thread(target=measure,daemon=True).start()
        self.level_after=self.after(180,launch)

    def update_levels(self):
        if not hasattr(self,'volume_slider'):return
        self.update_trim_controls()
        if hasattr(self,'detail_tabs'):
            self.detail_tabs.tab(0,text=self.tr('Áudio e volume'));self.detail_tabs.tab(1,text=self.tr('Detalhes e tags'))
        result=self.level_data;reference=result.get('reference');source=result.get('source')
        gain=self.gains.get(self.selected['key'],0.0) if self.selected else 0.0
        def meter(stats,offset=0):
            if stats is None:return '—'
            def value(key):return '−∞' if stats[key] is None else f'{stats[key]+offset:.1f}'
            return self.tr('Pico')+f': {value("peak_dbfs")} dBFS\n'+self.tr('RMS ativo')+f': {value("active_dbfs")} dBFS'
        self.original_level.set(meter(reference));self.import_level.set(meter(result.get("raw_source",source)));self.adjusted_level.set(meter(source,gain))
        for title,stats,offset in [('ORIGINAL',reference,0),('IMPORTADA',result.get('raw_source',source),0),('APÓS AJUSTE',source,gain)]:
            for variable,key in zip(self.meter_values.get(title,[]),('peak_dbfs','active_dbfs')):
                variable.set('—' if stats is None else '−∞ dBFS' if stats[key] is None else f'{stats[key]+offset:.1f} dBFS')
        self.gain_text.set(f'{gain:+.1f} dB')
        usable=bool(self.selected and source and not self.busy)
        for button in self.variation_buttons:button.configure(state='normal' if usable else 'disabled')
        choice=self.variations.get(self.selected['key'],1) if self.selected else 1
        self.variation.set(choice)
        _,speed=audio_variations.PRESETS[choice]
        self.variation_hint.set('' if choice==1 else f'{(speed-1)*100:+.0f}% '+self.tr('ritmo'))
        self.volume_slider.configure(state='normal' if usable else 'disabled')
        self.reset_gain_btn.configure(state='normal' if usable else 'disabled')
        comparable=usable and reference and reference['active_dbfs'] is not None and source['active_dbfs'] is not None
        self.match_btn.configure(state='normal' if comparable else 'disabled')
        warning=self.tr('Importe um áudio ou abra um banco editado para ajustar o volume.')
        color=MUTED
        if self.selected and not result:warning=self.tr('Medindo áudio selecionado...')
        elif result.get('source_error') or result.get('reference_error'):
            warning=self.tr('Não foi possível medir: ')+self.tr(result.get('source_error') or result.get('reference_error'));color=WARNING
        elif usable:
            peak=source['peak_dbfs']
            if peak is not None and peak+gain>-0.00026:
                warning=self.tr('Clipping: reduza o ganho antes de ouvir ou exportar.');color=ERROR
            elif peak is not None and peak+gain>-1:
                warning=self.tr('Pico próximo de 0 dBFS; reduza um pouco o ganho.');color=WARNING
            elif comparable:
                delta=source['active_dbfs']+gain-reference['active_dbfs']
                warning=self.tr('Diferença para o original: ')+f'{delta:+.1f} dB. '+self.tr('O ganho afeta a prévia e a exportação.')
                color=SUCCESS if abs(delta)<=1 else WARNING if abs(delta)>=3 else MUTED
            elif source['active_dbfs'] is None:warning=self.tr('Sem fala ativa mensurável. Ajuste automático indisponível.')
            else:warning=self.tr('Referência original indisponível. O ganho afeta a prévia e a exportação.')
        for label in getattr(self,'adjusted_meter_labels',[]):label.configure(fg=color if usable and color!=MUTED else FG)
        self.volume_warning.set(warning)
        if hasattr(self,'volume_note'):self.volume_note.configure(foreground=color)
        self.queue_inspector_fit()

    def change_gain(self,value):
        if self._setting_gain:return
        if not self.selected or not self.level_data.get('source') or self.busy:
            self._setting_gain=True;self.gain.set(self.gains.get(self.selected['key'],0.0) if self.selected else 0.0);self._setting_gain=False
            return
        key=self.selected['key'];gain=round(audio_levels.valid_gain(value),1)
        source=self.level_data.get('source_path')
        if not source:return
        if self.playing:self.stop()
        # For an external bank, materialize only the edited voice as a replacement.
        if key not in self.replacements:
            self.replacements[key]=source
            self.level_signature=(id(self.bank),key,source,self.variations.get(key,1))
            self.fill_rows()
        self.gains[key]=gain;self.gain_text.set(f'{gain:+.1f} dB')
        self.custom_btn.configure(state='normal');self.update_levels()
        if self.gain_save_after:self.after_cancel(self.gain_save_after)
        self.gain_save_after=self.after(200,self._save_gain)

    def change_variation(self):
        if not self.selected or self.busy or not self.level_data.get('source_path'):
            self.variation.set(self.variations.get(self.selected['key'],1) if self.selected else 1);return
        key=self.selected['key'];choice=audio_variations.valid(self.variation.get())
        if key not in self.replacements:self.replacements[key]=self.level_data['source_path']
        if choice==1:self.variations.pop(key,None)
        else:self.variations[key]=choice
        self.stop();self.level_signature=None;self.request_levels();self.fill_rows()
        self.custom_btn.configure(state='normal')

    def _save_gain(self):
        self.gain_save_after=None

    def match_original(self):
        if not self.level_data.get('reference') or not self.level_data.get('source'):return
        try:gain=audio_levels.matching_gain(self.level_data['reference'],self.level_data['source'])
        except ValueError as error:self.status.set(str(error));return
        self._setting_gain=True;self.gain.set(gain);self._setting_gain=False
        self.change_gain(gain)

    def reset_gain(self):
        self._setting_gain=True;self.gain.set(0);self._setting_gain=False
        self.change_gain(0)
