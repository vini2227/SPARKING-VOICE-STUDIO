"""Inline beginning/end trim controls for customized voice clips."""
import tkinter as tk
from tkinter import ttk
import wave,uuid,time,winsound,shutil
import audio_trim
import playback_controls
import trim_history
import core
from pathlib import Path
import numpy as np
from modern_theme import PANEL,FG,MUTED,SUCCESS,WARNING,EDGE

class AudioTrimMixin:
    def setup_audio_trim(self,detail):
        self.audio_edit_group=ttk.Frame(self.audio_action_frame)
        self.audio_edit_group.pack(side='left',padx=6)
        self.trim_button=self.button(self.audio_edit_group,'Cortar áudio',self.toggle_audio_trim)
        self.trim_button.pack(side='left');self.trim_button.configure(state='disabled')
        self.enhance_voice_btn=self.button(self.audio_edit_group,'Aprimorar voz',lambda:self.voice_ai_dialog('enhance'))
        self.enhance_voice_btn.pack(side='left',padx=(8,0));self.enhance_voice_btn.configure(state='disabled')
        self.isolate_voice_btn=self.button(self.audio_edit_group,'Isolar voz',lambda:self.voice_ai_dialog('isolate'))
        self.isolate_voice_btn.pack(side='left',padx=(8,0));self.isolate_voice_btn.configure(state='disabled')
        self.trim_restore_btn=self.button(self.audio_action_frame,'Restaurar sem corte',self.restore_untrimmed_audio)
        self.trim_restore_btn.pack(side='right',padx=6);self.trim_restore_btn.configure(state='disabled')
        self.trim_panel=ttk.Frame(detail);self.trim_key=None;self.trim_detail=detail
        self.trim_detail_padding=detail.cget('padding')
        self.trim_start=tk.StringVar(value='0.000');self.trim_end=tk.StringVar(value='0.000')
        self.trim_exact={};self.trim_preview_after=None;self.trim_preview_path=None
        self.trim_wave_panel=ttk.Frame(detail);self.trim_audio=None;self.trim_drag=None
        self.trim_canvas=tk.Canvas(self.trim_wave_panel,height=74,bg=PANEL,highlightthickness=1,highlightbackground=EDGE,cursor='sb_h_double_arrow')
        self.trim_canvas.pack(fill='x')
        self.trim_canvas.bind('<Configure>',lambda event:self.draw_trim_wave())
        self.trim_canvas.bind('<Button-1>',self.begin_trim_drag)
        self.trim_canvas.bind('<B1-Motion>',self.drag_trim_marker)
        self.trim_canvas.bind('<ButtonRelease-1>',lambda event:setattr(self,'trim_drag',None))
        for variable in (self.trim_start,self.trim_end):variable.trace_add('write',lambda *_:self.trim_values_changed())
        for caption,variable in [('Cortar começo (s)',self.trim_start),('Cortar fim (s)',self.trim_end)]:
            self.label(self.trim_panel,caption).pack(side='left',padx=(0,8))
            entry=ttk.Entry(self.trim_panel,textvariable=variable,width=7);entry.pack(side='left',padx=(0,8))
            entry.bind('<FocusOut>',lambda event,var=variable:self.format_trim_seconds(var))
            entry.bind('<Return>',lambda event,var=variable:self.format_trim_seconds(var))
        self.trim_preview_button=self.button(self.trim_panel,'▶ Ouvir corte',self.preview_audio_trim)
        self.trim_preview_button.pack(side='left',padx=(0,8))
        self.trim_apply_button=self.button(self.trim_panel,'Aplicar corte',self.apply_audio_trim)
        self.trim_apply_button.pack(side='left',padx=(0,8))
        self.button(self.trim_panel,'Fechar corte',self.hide_audio_trim).pack(side='left',padx=(0,8))

    def can_trim_audio(self):
        if not self.bank or not self.selected:return False
        key=self.selected['key']
        return key in self.replacements or core.imported_can_preview(self.bank,self.selected,allow_uncertain=False)

    def update_trim_controls(self):
        if not hasattr(self,'trim_button'):return
        allowed=self.can_trim_audio()
        for button in (self.trim_button,self.enhance_voice_btn,self.isolate_voice_btn):
            button.configure(state='normal' if allowed and not self.busy else 'disabled')
        history=trim_history.active(self.trim_originals,self.replacements)
        self.trim_restore_btn.configure(state='normal' if self.selected and self.selected['key'] in history and not self.busy else 'disabled')
        identity=(id(self.bank),self.selected['key']) if self.selected else None
        if not allowed or self.trim_key!=identity:self.hide_audio_trim()

    def hide_audio_trim(self):
        self.stop_trim_preview()
        active=self.trim_key is not None
        if active and self.audio_action_frame.winfo_manager()!='pack':
            self.audio_action_frame.pack(fill='x',pady=4,before=self.trim_wave_panel)
        self.trim_panel.pack_forget();self.trim_key=None
        self.trim_wave_panel.pack_forget();self.trim_audio=None;self.trim_drag=None
        self.trim_detail.configure(padding=self.trim_detail_padding)
        if active:self.update_responsive()

    def toggle_audio_trim(self):
        if self.busy or not self.can_trim_audio():return
        if self.trim_panel.winfo_ismapped():self.hide_audio_trim();return
        self.trim_key=(id(self.bank),self.selected['key']);self.trim_exact.clear();self.trim_start.set('0.000');self.trim_end.set('0.000')
        self.stop();self.trim_audio=None;self.trim_canvas.delete('all')
        self.trim_wave_panel.pack(fill='x',before=self.audio_controls if self.audio_controls.winfo_manager()=='pack' else self.audio_action_frame)
        options={'before':self.audio_controls} if self.audio_controls.winfo_manager()=='pack' else {}
        self.trim_panel.pack(fill='x',**options)
        # Keep the waveform and editing controls visible even on short screens.
        self.update_responsive()
        self.queue_inspector_fit()
        identity=self.trim_key;bank=self.bank;row=self.selected.copy();source=self.replacements.get(row['key'])
        def read():
            with self.level_lock:
                path=source or bank.original(row)
                with wave.open(str(path),'rb') as w:
                    rate=w.getframerate();channels=w.getnchannels();frames=w.getnframes();width=w.getsampwidth();raw=w.readframes(frames)
                if width==1:samples=(np.frombuffer(raw,dtype=np.uint8).astype(float)-128)/128
                elif width==2:samples=np.frombuffer(raw,dtype='<i2').astype(float)/32768
                elif width==4:samples=np.frombuffer(raw,dtype='<i4').astype(float)/2147483648
                elif width==3:
                    b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
                    values=b[:,0]|(b[:,1]<<8)|(b[:,2]<<16);samples=((values^0x800000)-0x800000)/8388608
                else:raise ValueError('Formato WAV não suportado.')
                samples=np.max(np.abs(samples.reshape(-1,channels)),axis=1)
                count=min(4096,frames);edges=np.linspace(0,frames,count+1).astype(int)
                peaks=np.array([np.max(samples[edges[i]:edges[i+1]]) for i in range(count)])
                return {'rate':rate,'frames':frames,'duration':frames/rate,'peaks':peaks}
        def loaded(data):
            if self.trim_key!=identity:return
            self.trim_audio=data;self.draw_trim_wave()
            self.status.set('Arraste as linhas para definir o começo e o fim. As áreas escuras serão removidas.')
        self.job(read,loaded,'Carregando áudio para corte...')

    def stable_inspector_height(self,detail,height):
        # Reserve the larger of the regular and trim views before opening trim.
        # Cached regular measurements include expanded tabs and responsive rows.
        scale=max(1,float(self.tk.call('tk','scaling'))/(96/72))
        short=self.winfo_height()<820*scale
        key=(self.split.winfo_width(),height,self.function_language.get(),self.inspector_expanded.get(),short)
        cache=getattr(self,'_regular_inspector_heights',{})
        self._regular_inspector_heights=cache
        flow=next((f for f in getattr(self,'flows',[]) if f.frame is self.trim_panel),None)
        width=max(1,detail.winfo_width())
        controls=0;used=0;row_height=0
        for widget in flow.widgets if flow else self.trim_panel.pack_slaves():
            size=widget.winfo_reqwidth()
            if used and used+8+size>width:
                controls+=row_height+3;used=0;row_height=0
            used+=size+(8 if used else 0);row_height=max(row_height,widget.winfo_reqheight())
        controls+=row_height
        wave_height=(50 if short and self.winfo_height()<680*scale else 74)+2
        added=wave_height+controls
        removed=(self.audio_action_frame.winfo_reqheight()+8 if short else self.audio_controls.winfo_reqheight()+3)
        actual=detail.winfo_reqheight()
        if not self.trim_key:cache[key]=actual
        regular=cache.get(key,actual+removed-added)
        return max(regular,regular-removed+added)

    def layout_trim_editor(self,short):
        scale=max(1,float(self.tk.call('tk','scaling'))/(96/72))
        self.trim_canvas.configure(height=50 if short and self.winfo_height()<680*scale else 74)
        if short:self.audio_action_frame.pack_forget()
        elif self.audio_action_frame.winfo_manager()!='pack':self.audio_action_frame.pack(fill='x',pady=4,before=self.trim_wave_panel)

    def trim_positions(self):
        if not self.trim_audio:return None
        duration=self.trim_audio['duration']
        try:start,end=self.trim_values();end=duration-end
        except ValueError:return None
        return max(0,min(duration,start)),max(0,min(duration,end))

    def trim_value(self,var):
        cached=self.trim_exact.get(str(var))
        if cached and var.get()==cached[0]:return cached[1]
        return audio_trim.seconds(var.get())

    def trim_values(self):return self.trim_value(self.trim_start),self.trim_value(self.trim_end)

    def set_trim_seconds(self,var,value):
        display=f'{value:.3f}';self.trim_exact[str(var)]=(display,value);var.set(display)

    def format_trim_seconds(self,var):
        try:self.set_trim_seconds(var,self.trim_value(var))
        except ValueError:pass

    def trim_values_changed(self):
        self.stop_trim_preview();self.draw_trim_wave()

    def draw_trim_wave(self):
        if not hasattr(self,'trim_canvas') or not self.trim_key:return
        c=self.trim_canvas;c.delete('all');width=c.winfo_width();height=c.winfo_height();padding=14
        if not self.trim_audio or width<30:return
        duration=self.trim_audio['duration'];positions=self.trim_positions()
        if not positions:return
        start,end=positions;usable=width-2*padding
        x1=padding+usable*start/duration;x2=padding+usable*end/duration
        c.create_line(padding,height/2,width-padding,height/2,fill=EDGE)
        peaks=self.trim_audio['peaks'];count=max(1,usable//3);edges=np.linspace(0,len(peaks),count+1).astype(int)
        c.create_rectangle(padding,20,x1,height-2,fill='#090c11',outline='')
        c.create_rectangle(x2,20,width-padding,height-2,fill='#090c11',outline='')
        for i in range(count):
            chunk=peaks[edges[i]:min(len(peaks),max(edges[i]+1,edges[i+1]))]
            if not len(chunk):continue
            x=padding+(i+.5)*usable/count;amp=min(1,float(np.max(chunk)))*(height/2-18)
            c.create_line(x,height/2+6-amp,x,height/2+6+amp,fill=SUCCESS if x1<=x<=x2 else '#404852',width=2)
        for name,x,value,color in [('Começo',x1,start,SUCCESS),('Fim',x2,end,WARNING)]:
            c.create_line(x,19,x,height-1,fill=color,width=2,tags=name)
            c.create_polygon(x-6,19,x+6,19,x,27,fill=color,outline='',tags=name)
            c.create_text(x,9,text=self.tr(name)+f' {value:.3f}s',fill=color,anchor='w' if name=='Começo' else 'e',font=('Segoe UI',9,'bold'))

    def begin_trim_drag(self,event):
        if self.busy or not self.trim_audio:return
        positions=self.trim_positions()
        if not positions:return
        usable=self.trim_canvas.winfo_width()-28;duration=self.trim_audio['duration']
        x1=14+usable*positions[0]/duration;x2=14+usable*positions[1]/duration
        self.trim_drag='start' if abs(event.x-x1)<=abs(event.x-x2) else 'end'
        self.drag_trim_marker(event)

    def drag_trim_marker(self,event):
        if self.busy or not self.trim_drag or not self.trim_audio:return
        data=self.trim_audio;positions=self.trim_positions()
        if not positions:return
        rate=data['rate'];frames=data['frames'];usable=max(1,self.trim_canvas.winfo_width()-28)
        frame=round(max(0,min(1,(event.x-14)/usable))*frames)
        begin=round(positions[0]*rate);finish=round(positions[1]*rate)
        if self.trim_drag=='start':
            frame=max(0,min(frame,finish-1));self.set_trim_seconds(self.trim_start,frame/rate)
        else:
            frame=min(frames,max(frame,begin+1));self.set_trim_seconds(self.trim_end,(frames-frame)/rate)

    def stop_trim_preview(self):
        if self.trim_preview_after is not None:self.after_cancel(self.trim_preview_after);self.trim_preview_after=None
        path=self.trim_preview_path
        if path is not None and self.playing==path:self.stop()
        self.trim_preview_path=None
        if hasattr(self,'trim_canvas'):self.trim_canvas.delete('trim_playhead')
        if path is not None:
            try:path.unlink(missing_ok=True)
            except OSError:pass

    def preview_audio_trim(self):
        if self.busy or not self.can_trim_audio() or not self.trim_audio:return
        try:
            start,end=self.trim_values()
            if start or end:audio_trim.bounds(self.trim_audio['frames'],self.trim_audio['rate'],start,end)
        except ValueError as error:self.status.set(self.tr(str(error)));return
        row=self.selected.copy();bank=self.bank;identity=self.trim_key;source=self.replacements.get(row['key'])
        gain=self.gains.get(row['key'],0);variation=self.variations.get(row['key'],1)
        folder=core.APP/'Cache/TrimPreview';token=uuid.uuid4().hex
        raw=folder/(token+'_raw.wav');rendered=folder/(token+'.wav')
        self.stop_trim_preview();self.stop()
        def work():
            with self.level_lock:
                folder.mkdir(parents=True,exist_ok=True)
                try:
                    path=source or bank.original(row)
                    if start or end:audio_trim.trim(path,raw,start,end)
                    else:shutil.copyfile(path,raw)
                    core.normalize_wav(raw,rendered,row['rate'],row['channels'],row['samples'],gain,variation)
                    with wave.open(str(rendered),'rb') as w:duration=w.getnframes()/w.getframerate()
                    return duration
                except Exception:
                    rendered.unlink(missing_ok=True);raise
                finally:raw.unlink(missing_ok=True)
        def done(duration):
            try:current_values=self.trim_values()
            except ValueError:current_values=None
            if self.trim_key!=identity or current_values!=(start,end):
                rendered.unlink(missing_ok=True);return
            self.trim_preview_path=rendered
            playback_controls.start(self,rendered,self.trim_preview_button,finish=False,cleanup=self.stop_trim_preview)
            started=time.perf_counter();positions=self.trim_positions()
            def tick():
                self.trim_preview_after=None
                if not self.trim_key or self.playing!=rendered:self.stop_trim_preview();return
                progress=min(1,(time.perf_counter()-started)/duration)
                position=positions[0]+(positions[1]-positions[0])*progress
                c=self.trim_canvas;c.delete('trim_playhead');x=14+(c.winfo_width()-28)*position/self.trim_audio['duration']
                c.create_line(x,20,x,c.winfo_height(),fill=FG,width=2,tags='trim_playhead')
                if progress>=1:self.stop_trim_preview()
                else:self.trim_preview_after=self.after(16,tick)
            tick();self.status.set('Ouvindo prévia do corte. O áudio ainda não foi alterado.')
        self.job(work,done,'Preparando prévia do corte...')

    def apply_audio_trim(self):
        if self.busy or not self.can_trim_audio():return
        row=self.selected.copy();bank=self.bank;key=row['key'];source=self.replacements.get(key)
        try:
            start,end=self.trim_values()
            if source:
                with wave.open(source,'rb') as w:audio_trim.bounds(w.getnframes(),w.getframerate(),start,end)
            elif start==end==0:raise ValueError('Defina um corte no começo e/ou no fim.')
        except (ValueError,OSError,wave.Error) as error:self.status.set(self.tr(str(error)));return
        destination=self.project/'Replacements'/(key+'_trim_'+uuid.uuid4().hex+'.wav')
        self.stop();self.level_token+=1;self.level_signature=None
        prior=trim_history.active(self.trim_originals,self.replacements).get(key)
        def work():
            with self.level_lock:
                path=source or bank.original(row)
                original=Path(prior['original']) if prior else self.project/'TrimOriginals'/(key+'_'+uuid.uuid4().hex+'.wav')
                try:
                    if not prior:
                        original.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,original)
                    result=audio_trim.trim(path,destination,start,end)
                    result['history']={'original':str(original),'trimmed':str(destination)}
                    return result
                except Exception:
                    if not prior:original.unlink(missing_ok=True)
                    raise
        def done(info):
            self.replacements[key]=str(destination);self.trim_originals[key]=info['history']
            # Gain and voice variation remain separate and are applied once by
            # the existing preview/export pipeline to the trimmed base waveform.
            self.hide_audio_trim();self.level_signature=None;self.fill_rows();self.select()
            self.status.set('Corte aplicado sem fade. Clique em Salvar projeto para guardar a alteração.')
        self.job(work,done,'Cortando áudio selecionado...',edit_label='Cortar áudio')

    def restore_untrimmed_audio(self):
        if self.busy or not self.selected:return
        key=self.selected['key'];history=trim_history.active(self.trim_originals,self.replacements).get(key)
        if not history:return
        self.stop();self.hide_audio_trim();self.level_token+=1;self.level_signature=None
        self.replacements[key]=history['original'];self.trim_originals.pop(key,None)
        self.fill_rows();self.select()
        self.status.set('Áudio completo restaurado. Os ajustes de ganho e variação foram mantidos. Salve o projeto para guardar.')

