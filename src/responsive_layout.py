"""Wrapping control rows and width/height-aware navigation for the desktop studio."""
import tkinter as tk
from tkinter import ttk
import compact_export_layout
import current_bank_identity
import time

class LocalTransition:
    """A brief accent on regrouped rows; placement never changes geometry."""
    def __init__(self, frame):
        self.frame=frame;self.pending=None;self.lines=[];self.starts=0
        frame.bind("<Destroy>",self.destroy,add="+")
    def destroy(self,event=None):
        if event is not None and event.widget is not self.frame:return
        if self.pending is not None:
            try:self.frame.after_cancel(self.pending)
            except tk.TclError:pass
            self.pending=None
        for line in self.lines:
            try:line.destroy()
            except tk.TclError:pass
        self.lines=[]
    def start(self,rows,bg):
        self.destroy()
        if not rows or not self.frame.winfo_ismapped():return
        self.base=self.frame.winfo_rgb(bg)
        self.accent=self.frame.winfo_rgb("#71b7ff")
        self.started=time.monotonic();self.starts+=1
        for row in rows:
            line=tk.Frame(row,height=1,borderwidth=0,takefocus=0)
            line.place(relx=0,rely=1,relwidth=1,height=1,anchor="sw")
            line.lift();self.lines.append(line)
        self.tick()
    def tick(self):
        self.pending=None
        elapsed=(time.monotonic()-self.started)/0.22
        if elapsed>=1:
            self.destroy();return
        # Smooth fade, subdued enough to keep attention on the content.
        opacity=0.42*(1-elapsed)**2
        color="#"+"".join(f"{round((a*opacity+b*(1-opacity))/257):02x}" for a,b in zip(self.accent,self.base))
        try:
            for line in self.lines:line.configure(bg=color)
            self.pending=self.frame.after(16,self.tick)
        except tk.TclError:self.destroy()


class Flow:
    def __init__(self,frame,flex=()):
        self.frame=frame;self.flex=set(flex);self.rows=[];self.signature=None;self.pending=None;self.header_separation=False;self.trailing=set();self.equal_columns=False;self.summary_mode=False;self.summary_width_index=0;self.summary_reserve=None;self.placements={}
        self.transition=LocalTransition(frame)
        packed=frame.pack_slaves()
        if packed:
            left=[w for w in packed if w.pack_info().get('side')!='right']
            right=[w for w in packed if w.pack_info().get('side')=='right']
            self.widgets=left+list(reversed(right))
            for w in self.widgets:w.pack_forget()
        else:
            self.widgets=sorted(frame.grid_slaves(),key=lambda w:(int(w.grid_info()['row']),int(w.grid_info()['column'])))
            for w in self.widgets:w.grid_forget()
            for i in range(20):frame.columnconfigure(i,weight=0,minsize=0)
        frame.columnconfigure(0,weight=1)
        self.configured_width=None
        frame.bind('<Configure>',self.on_configure,add='+');self.schedule()
    def on_configure(self,event):
        if event.widget is not self.frame or event.width==self.configured_width:return
        self.configured_width=event.width;self.schedule()
    def schedule(self):
        # Coalesce one frame of events without postponing work during a drag.
        if self.pending is None:self.pending=self.frame.after_idle(self.layout) if self.signature is None else self.frame.after(16,self.layout)
    def layout(self):
        self.pending=None
        if not self.frame.winfo_exists():return
        width=self.frame.winfo_width()
        if width<10:return
        widths=[min(width,max(100,w.winfo_reqwidth())) if w in self.flex else w.winfo_reqwidth() for w in self.widgets]
        if self.equal_columns:widths=[max(1,(width-8*len(self.widgets))/len(self.widgets))]*len(self.widgets)
        if self.summary_mode:
            bank_index=self.summary_width_index
            project_index=0
            widths[bank_index]=min(width,max(300,self.summary_reserve()))
            remaining=width-8*(len(self.widgets)-1)-sum(size for i,size in enumerate(widths) if i!=project_index)
            widths[project_index]=max(180,remaining)
        groups=[];group=[];used=0
        header_gap=max(64,round(64*float(self.frame.tk.call('tk','scaling'))/(96/72)))
        separated=self.header_separation and sum(widths)+8*(len(widths)-1)+header_gap>width
        entries=list(zip(self.widgets,widths))
        if separated:
            groups.append([self.widgets[0]])
            entries=entries[1:]
        for index,(w,size) in enumerate(entries):
            # Keep the trailing action pair together when wrapping.
            if w in self.trailing and (index==0 or entries[index-1][0] not in self.trailing):
                block=sum(n for item,n in entries[index:] if item in self.trailing)+8*(sum(item in self.trailing for item,n in entries[index:])-1)
                if group and used+block+8>width:groups.append(group);group=[];used=0
            if group and used+size+8>width:groups.append(group);group=[];used=0
            used+=size+(8 if group else 0);group.append(w)
        if group:groups.append(group)
        # Grid stretches the existing rows automatically. Only regroup widgets
        # when their actual row membership changes, never for each pixel.
        signature=(tuple(tuple(str(w) for w in group) for group in groups),separated,header_gap,tuple(sorted(str(w) for w in self.trailing)))
        if signature==self.signature:
            # Width changes alone do not require unmapping and regridding labels.
            if self.summary_mode:
                for i,group in enumerate(groups):
                    trailing_index=next((j for j,w in enumerate(group) if w in self.trailing),None)
                    for j,w in enumerate(group):
                        column=j+int(trailing_index is not None and j>=trailing_index)
                        size=round(widths[self.widgets.index(w)])+(8 if j<len(group)-1 else 0) if w not in self.flex else 0
                        if int(self.rows[i].columnconfigure(column,'minsize'))!=size:self.rows[i].columnconfigure(column,minsize=size)
            return
        previous=self.signature
        changed_rows=[] if previous is None else [i for i,members in enumerate(signature[0]) if i>=len(previous[0]) or members!=previous[0][i]]
        self.transition.destroy()
        self.signature=signature
        # Keep mapped controls alive; grid moves only widgets whose row changes.
        for index,row in enumerate(self.rows):
            if index>=len(groups):row.grid_remove()
            for column in range(len(self.widgets)+2):row.columnconfigure(column,weight=0,minsize=0,uniform='')
        try:bg=self.frame.cget('background')
        except tk.TclError:bg=ttk.Style(self.frame).lookup(self.frame.cget('style') or 'TFrame','background')
        for i,group in enumerate(groups):
            if i==len(self.rows):self.rows.append(tk.Frame(self.frame,bg=bg))
            row=self.rows[i];row.configure(bg=bg);row.grid(row=i,column=0,sticky='ew',pady=(0,10 if self.header_separation and separated and i==0 else 3 if i<len(groups)-1 else 0));row.lower()
            trailing_index=next((j for j,w in enumerate(group) if w in self.trailing),None)
            if trailing_index is not None:row.columnconfigure(trailing_index,weight=1)
            for j,w in enumerate(group):
                column=j+int(trailing_index is not None and j>=trailing_index)
                row.columnconfigure(column,weight=1 if w in self.flex else 0,minsize=round(widths[self.widgets.index(w)])+(8 if j<len(group)-1 else 0) if self.summary_mode and w not in self.flex else 0,uniform='summary' if self.equal_columns else '')
                sticky='nsew' if self.equal_columns or self.summary_mode else 'ew' if w in self.flex else 'w'
                padding=(0,8 if self.equal_columns else header_gap if self.header_separation and not separated and j==0 else 8 if j<len(group)-1 else 0)
                placement=(str(row),column,sticky,padding)
                if self.placements.get(w)!=placement or not w.winfo_manager():
                    w.grid(in_=row,row=0,column=column,sticky=sticky,padx=padding)
                    self.placements[w]=placement

        # Keep regrouping visually neutral; an accent on every wrap looks like a flash.

class ResponsiveMixin:
    def setup_responsive(self,body,left,right,frames,flex,actions):
        self.body_frame=body;self.bank_sidebar=left;self.voice_area=right
        self.sidebar_override=None;self.audio_override=None;self.filters_override=None;self.responsive_pending=None;self.responsive_signature=None
        self.sidebar_caption=self.localized_var('Ocultar bancos')
        self.sidebar_button=self.button(actions,'Ocultar bancos',self.toggle_sidebar)
        self.sidebar_button.configure(textvariable=self.sidebar_caption);self.sidebar_button.pack(side='right',padx=(8,0))
        self.audio_caption=self.localized_var('Mostrar áudio e volume')
        self.compact_audio_button=self.button(self.audio_action_frame,'Mostrar áudio e volume',self.toggle_compact_audio)
        self.compact_audio_button.configure(textvariable=self.audio_caption)
        self.advanced_caption=self.localized_var('Mostrar filtros e legenda')
        self.advanced_button=self.button(self.filter_frame,'Mostrar filtros e legenda',self.toggle_filters)
        self.advanced_button.configure(textvariable=self.advanced_caption)
        self.flows=[Flow(frame,flex.get(frame,())) for frame in frames]
        self.summary_flow=next(f for f in self.flows if self.bank_identity_panel in f.widgets)
        self.summary_flow.summary_mode=True
        self.summary_flow.summary_width_index=self.summary_flow.widgets.index(self.bank_identity_panel)
        self.summary_flow.summary_reserve=lambda:current_bank_identity.reserved_width(self)
        self.summary_flow.flex={self.project_identity_panel}
        self.header_flow=next(f for f in self.flows if f.frame is actions)
        self.header_flow.header_separation=True
        self.header_flow.flex.add(self.header_flow.widgets[0])
        self.filter_flow=next(f for f in self.flows if f.frame is self.filter_frame)
        self.action_flow=next(f for f in self.flows if f.frame is self.audio_action_frame)
        self.action_flow.trailing={self.trim_restore_btn,self.remove_btn,self.microphone_btn,self.import_btn}
        self.output_flow=next(f for f in self.flows if f.frame is self.export_name_entry.master)
        self.output_flow.trailing={self.audio_treatment_label,self.effects_btn,self.volume_scope_choice,self.clipping_btn,self.maximize_btn}
        self.export_flow=next(f for f in self.flows if self.destination_label in f.widgets)
        self.export_flow.trailing={self.project_name_btn,self.save_project_btn,self.folders_btn,self.export_btn}
        import replacer_folder
        replacer_folder.sync_button(self)
        self.bind('<Configure>',self.queue_responsive,add='+');self.after_idle(self.prepare_startup_layout)
    def prepare_startup_layout(self):
        # Resolve initial dependencies together instead of spreading the first
        # panel/row adjustments across successive resize timers.
        self._priming_layout=True
        try:
            for _ in range(3):
                self.update_idletasks()
                self.update_responsive()
                for flow in self.flows:
                    if flow.pending is not None:flow.frame.after_cancel(flow.pending)
                    flow.layout()
            self.update_idletasks()
            self.fit_inspector()
        finally:self._priming_layout=False

    def queue_responsive(self,event=None):
        if event is not None:
            if event.widget is not self:return
            size=(event.width,event.height)
            if size==getattr(self,'_responsive_window_size',None):return
            self._responsive_window_size=size
        if self.responsive_pending is None:self.responsive_pending=self.after(16,self.update_responsive)
    def toggle_sidebar(self):
        self.sidebar_override=not self.bank_sidebar.winfo_ismapped();self.responsive_signature=None;self.update_responsive()
    def toggle_filters(self):
        self.filters_override=not self.advanced_frames[0].winfo_ismapped();self.update_responsive()
    def toggle_compact_audio(self):
        import window_toggle
        if window_toggle.existing(self,'compact_audio_window'):return
        win=tk.Toplevel(self);self.compact_audio_window=win;win.title(self.tr('Áudio e volume'))
        win.configure(bg=self.cget('background'));win.geometry('700x360');win.minsize(580,320)
        panel=ttk.Frame(win,padding=18);panel.pack(fill='both',expand=True)
        for title,var in [('ORIGINAL',self.original_level),('IMPORTADA',self.import_level),('APÓS AJUSTE',self.adjusted_level)]:
            row=ttk.Frame(panel);row.pack(fill='x',pady=4)
            self.label(row,title).pack(side='left',padx=(0,20))
            ttk.Label(row,textvariable=var).pack(side='right')
        presets=ttk.Frame(panel);presets.pack(fill='x',pady=8)
        radios=[]
        for value,title in [(1,'1 — Original'),(2,'2 — Mais rápida'),(3,'3 — Mais lenta')]:
            button=ttk.Radiobutton(presets,variable=self.variation,value=value,command=self.change_variation)
            self.localize_widget(button,title);button.pack(side='left',padx=6);radios.append(button)
        ttk.Label(panel,textvariable=self.gain_text).pack(anchor='e')
        slider=ttk.Scale(panel,from_=-48,to=24,variable=self.gain,command=self.change_gain);slider.pack(fill='x',pady=6)
        buttons=ttk.Frame(panel);buttons.pack(fill='x',pady=6)
        match=self.button(buttons,'Igualar ao original',self.match_original);match.pack(side='left')
        reset=self.button(buttons,'Zerar ganho',self.reset_gain);reset.pack(side='left',padx=8)
        self.button(buttons,'Fechar',win.destroy).pack(side='right')
        note=ttk.Label(panel,textvariable=self.volume_warning,wraplength=630);note.pack(fill='x',pady=4)
        note.bind('<Configure>',lambda e:note.configure(wraplength=max(200,e.width)))
        def sync():
            if not win.winfo_exists():return
            for target,source in [(slider,self.volume_slider),(match,self.match_btn),(reset,self.reset_gain_btn)]+list(zip(radios,self.variation_buttons)):
                target.configure(state=source.cget('state'))
            win.after(150,sync)
        sync()
    def update_responsive(self):
        if self.responsive_pending is not None:self.after_cancel(self.responsive_pending)
        self.responsive_pending=None
        if not self.winfo_exists():return
        scale=max(1,float(self.tk.call('tk','scaling'))/(96/72))
        narrow=self.winfo_width()<int(1500*scale);short=self.winfo_height()<int(820*scale)
        if hasattr(self,'activity_slot'):
            self.progress.fit_size()
        visible=not narrow if self.sidebar_override is None else self.sidebar_override
        sidebar_width=min(int(400*scale),max(int(270*scale),int(self.winfo_width()*.23)))
        
        if int(self.bank_sidebar.cget('width'))!=sidebar_width:self.bank_sidebar.configure(width=sidebar_width)
        if visible and not self.bank_sidebar.winfo_manager():self.bank_sidebar.pack(side='left',fill='y',padx=(0,16),before=self.voice_area)
        elif not visible and self.bank_sidebar.winfo_manager():self.bank_sidebar.pack_forget()
        self.sidebar_caption.set('Ocultar bancos' if visible else 'Mostrar bancos')
        if hasattr(self,"trim_key") and self.trim_key:self.layout_trim_editor(short)
        show_audio=not short and not getattr(self,"trim_key",None)
        if show_audio and not self.audio_controls.winfo_manager():self.audio_controls.pack(fill='x',pady=(3,0))
        elif not show_audio and self.audio_controls.winfo_manager():self.audio_controls.pack_forget()
        self.audio_caption.set('Mostrar áudio e volume')
        # On short windows the extra controls are available on demand, keeping the table usable.
        toggle_present=self.compact_audio_button in self.action_flow.widgets
        if short and not toggle_present:self.action_flow.widgets.append(self.compact_audio_button)
        elif not short and toggle_present:
            self.action_flow.widgets.remove(self.compact_audio_button);self.compact_audio_button.grid_forget()
        show_filters=not short if self.filters_override is None else self.filters_override
        for frame in self.advanced_frames:
            if show_filters and not frame.winfo_manager():
                options={'before':self.split} if frame.master is self.voice_area else {}
                frame.pack(fill='x',pady=(0,6),**options)
            elif not show_filters and frame.winfo_manager():frame.pack_forget()
        self.advanced_caption.set('Ocultar filtros e legenda' if show_filters else 'Mostrar filtros e legenda')
        present=self.advanced_button in self.filter_flow.widgets
        if short and not present:self.filter_flow.widgets.append(self.advanced_button)
        elif not short and present:self.filter_flow.widgets.remove(self.advanced_button);self.advanced_button.grid_forget()
        compact_export_layout.update(self)
        for flow in self.flows:flow.schedule()
        self.queue_inspector_fit()
    def queue_inspector_fit(self,event=None):
        if getattr(self,'_resize_inspector_after',None) is not None:return
        def fit():
            self._resize_inspector_after=None
            # Fit only after pending flow rows have settled, avoiding a sash move
            # based on the old row height followed by another correction.
            if any(flow.pending is not None for flow in getattr(self,'flows',[])):
                self._resize_inspector_after=self.after(16,fit);return
            self.fit_inspector()
        self._resize_inspector_after=self.after_idle(fit)

