"""Font-sized header activity with a circular spinner beside its caption."""
import time,tkinter as tk
from tkinter import font
from modern_theme import EDGE,MUTED,WARNING

class ActivityIndicator(tk.Canvas):
    def __init__(self,parent,caption,detail=None):
        super().__init__(parent,bg=parent.cget('bg'),highlightthickness=0)
        self.caption=caption;self.detail=detail;self.pending=None;self.active=False;self.started=0
        self.caption_font=font.Font(root=self,family='Segoe UI',size=10,weight='bold')
        self.detail_font=font.Font(root=self,family='Segoe UI',size=8)
        self.trace=caption.trace_add('write',lambda *_:self.refresh_caption())
        self.detail_trace=detail.trace_add('write',lambda *_:self.draw()) if detail is not None else None
        self.bind('<Configure>',lambda event:self.draw())
        self.bind('<Destroy>',self.cleanup,add='+')
        self.fit_size()

    def fit_size(self):
        self.scale=max(1,float(self.tk.call('tk','scaling'))/(96/72))
        self.inset=round(4*self.scale);self.text_x=round(28*self.scale)
        self.caption_height=self.caption_font.metrics('linespace')
        self.detail_y=self.inset+self.caption_height+round(3*self.scale)
        height=self.detail_y+self.detail_font.metrics('linespace')+self.inset
        width=max(round(208*self.scale),self.text_x+self.caption_font.measure(self.caption.get())+self.inset)
        if int(float(self.cget('height')))!=height or int(float(self.cget('width')))!=width:
            self.configure(width=width,height=height)
            self.master.configure(width=width,height=height)
        self.draw()

    def refresh_caption(self):
        self.fit_size()

    def start(self,interval=None):
        self.stop();self.fit_size();self.active=True;self.started=time.perf_counter()
        self.pack(side='left',fill='both',expand=True);self.tick()

    def stop(self):
        self.active=False
        if self.pending is not None:
            self.after_cancel(self.pending);self.pending=None
        self.delete('all');self.pack_forget()

    def tick(self):
        self.pending=None
        if not self.active:return
        self.draw();self.pending=self.after(32,self.tick)

    def draw(self):
        if not self.active or not hasattr(self,'scale'):return
        self.delete('all');width=max(40,self.winfo_width())
        radius=round(7*self.scale);center_x=round(11*self.scale);center_y=self.inset+self.caption_height/2
        bounds=(center_x-radius,center_y-radius,center_x+radius,center_y+radius)
        stroke=max(2,round(2*self.scale))
        self.create_oval(*bounds,outline=EDGE,width=stroke,tags='spinner_track')
        angle=-((time.perf_counter()-self.started)*270)%360
        self.create_arc(*bounds,start=angle,extent=260,style='arc',outline=WARNING,width=stroke,tags='activity_segment')
        self.create_text(self.text_x,self.inset,text=self.caption.get(),anchor='nw',fill=WARNING,font=self.caption_font,tags='activity_caption')
        value=self.detail.get().splitlines()[0] if self.detail is not None and self.detail.get() else ''
        available=max(1,width-self.text_x-self.inset)
        if self.detail_font.measure(value)>available:
            while value and self.detail_font.measure(value+'…')>available:value=value[:-1]
            value=value.rstrip()+'…'
        self.create_text(self.text_x,self.detail_y,text=value,anchor='nw',fill=MUTED,font=self.detail_font,tags='operation_detail')

    def cleanup(self,event):
        if event.widget is not self:return
        if self.pending is not None:
            self.after_cancel(self.pending);self.pending=None
        self.active=False;self.caption.trace_remove('write',self.trace)
        if self.detail_trace is not None:self.detail.trace_remove('write',self.detail_trace)
