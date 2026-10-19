"""Image-backed ttk surfaces with keyboard focus and standard widget behavior."""
import ctypes
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk

BG='#090c11'
PANEL='#111720'
CARD='#1a212b'
FG='#edf0f5'
MUTED='#9aa4b2'
ACCENT='#e51d36'
SUCCESS='#70d6a0'
MANUAL='#f472b6'
WARNING='#ffb23f'
INFO='#71b7ff'
ERROR='#ff8291'
EDGE='#2b3441'
ALTERNATE='#151c26'
SELECTED='#44202b'

def surface(master,fill,outline=EDGE,size=(48,36),radius=7):
    scale=3
    image=Image.new('RGBA',(size[0]*scale,size[1]*scale))
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((1,1,size[0]*scale-2,size[1]*scale-2),radius=radius*scale,
                           fill=fill,outline=outline,width=scale)
    return ImageTk.PhotoImage(image.resize(size,Image.Resampling.LANCZOS),master=master)

class RoundedPanel(tk.Frame):
    """Compact count card; labels remain real accessible Tk widgets."""
    def __init__(self,parent,**kw):
        super().__init__(parent,bg=BG,**kw)
        self.background=tk.Canvas(self,bg=BG,highlightthickness=0)
        self.background.place(x=0,y=0,relwidth=1,relheight=1,bordermode='outside')
        self.tk.call('lower',self.background._w)
        self._paint_pending=None;self._paint_size=None;self._background_item=None
        self.bind('<Configure>',self.paint)
        self.bind('<Destroy>',self._cancel_paint,add='+')
    def paint(self,event):
        if event.widget is not self or event.width<2 or event.height<2:return
        if (event.width,event.height)==self._paint_size:return
        if self._paint_pending is None:self._paint_pending=self.after_idle(self._paint_background)
    def _cancel_paint(self,event):
        if event.widget is self and self._paint_pending is not None:
            self.after_cancel(self._paint_pending);self._paint_pending=None
    def _paint_background(self):
        self._paint_pending=None
        size=(self.winfo_width(),self.winfo_height())
        if min(size)<2 or size==self._paint_size:return
        self.image=surface(self,PANEL,size=size,radius=8);self._paint_size=size
        if self._background_item is None:self._background_item=self.background.create_image(0,0,anchor='nw',image=self.image)
        else:self.background.itemconfigure(self._background_item,image=self.image)


class CounterBadge(tk.Canvas):
    """Quiet rounded status badge, with numeric values emphasized."""
    def __init__(self,parent,variable,duplicates=False,compact=False):
        self.badge_height=22 if compact else 32
        super().__init__(parent,width=248,height=self.badge_height,bg=BG,highlightthickness=0)
        from tkinter import font
        import re
        self.variable=variable;self.duplicates=duplicates;self.split=re.compile(r'(\d+)')
        self.caption_font=font.Font(self,family='Segoe UI',size=9)
        self.number_font=font.Font(self,family='Segoe UI',size=10,weight='bold')
        self.token=variable.trace_add('write',self.refresh)
        self.bind('<Configure>',self.refresh)
        self.bind('<Destroy>',self.cleanup,add='+')
        self.refresh()
    def cleanup(self,event):
        if event.widget is self:self.variable.trace_remove('write',self.token)
    def refresh(self,*args):
        signature=(self.variable.get(),float(self.tk.call('tk','scaling')))
        if signature==getattr(self,'_render_signature',None):return
        self._render_signature=signature
        parts=self.split.split(signature[0])
        width=max(248,34+sum((self.number_font if p.isdigit() else self.caption_font).measure(p) for p in parts))
        if int(self.cget('width'))!=width:self.configure(width=width)
        self.image=surface(self,PANEL,size=(width,self.badge_height),radius=7 if self.badge_height<32 else 8)
        self.delete('all');self.create_image(0,0,image=self.image,anchor='nw')
        numbers=[int(p) for p in parts if p.isdigit()]
        has_duplicates=bool(self.duplicates and numbers and numbers[0]>0)
        color=WARNING if has_duplicates else MUTED
        center=self.badge_height/2
        self.create_oval(11,center-3,17,center+3,fill=color,outline='')
        x=25
        for part in parts:
            font=self.number_font if part.isdigit() else self.caption_font
            self.create_text(x,center,text=part,anchor='w',fill=(WARNING if has_duplicates else FG) if part.isdigit() else MUTED,font=font)
            x+=font.measure(part)


def install(root):
    s=ttk.Style(root)
    images=[]
    def element(name,normal,states=(),border=7,sticky='nsew'):
        images.append(normal)
        for _,img in states:images.append(img)
        s.element_create(name,'image',normal,*[(state,img) for state,img in states],border=border,padding=0,sticky=sticky)
    for style,prefix,fill,hover,pressed,edge in (
        ('TButton','Studio.Button',CARD,'#252e3b','#121923',EDGE),
        ('Primary.TButton','Studio.Primary',ACCENT,'#f12c46','#bd152d',ACCENT)):
        element(prefix,surface(root,fill,edge),[
            ('disabled',surface(root,'#111720','#1b222c')),
            ('pressed',surface(root,pressed,ACCENT)),
            ('active',surface(root,hover,edge)),
            ('focus',surface(root,fill,'#ef5a6c'))])
        s.layout(style,[(prefix,{'sticky':'nsew','children':[
            ('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
        s.configure(style,padding=(12,8),foreground=FG,background=BG,anchor='center')
        s.map(style,foreground=[('disabled','#596270'),('!disabled',FG)])

    # Small controls in the voice status panel retain the rounded button design.
    element('Studio.CompactFilter',surface(root,CARD,EDGE,size=(120,26),radius=7),[
        ('disabled',surface(root,'#111720','#1b222c',size=(120,26),radius=7)),
        ('pressed',surface(root,'#121923',ACCENT,size=(120,26),radius=7)),
        ('active',surface(root,'#252e3b',EDGE,size=(120,26),radius=7)),
        ('focus',surface(root,CARD,'#ef5a6c',size=(120,26),radius=7))])
    s.layout('CompactFilter.TButton',[('Studio.CompactFilter',{'sticky':'nsew','children':[
        ('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
    s.configure('CompactFilter.TButton',padding=(6,3),foreground=FG,background=BG,anchor='center')
    s.map('CompactFilter.TButton',foreground=[('disabled','#596270'),('!disabled',FG)])

    for style,name,fill,border in (
        ('TEntry','Studio.Entry.field',CARD,EDGE),
        ('Required.TEntry','Studio.Required.field',CARD,'#847143'),
        ('Invalid.TEntry','Studio.Invalid.field','#351b26','#d54b62')):
        element(name,surface(root,fill,border),[
            ('disabled',surface(root,PANEL,'#202733')),
            ('focus',surface(root,fill,WARNING if style=='Required.TEntry' else '#da4256'))])
        s.layout(style,[(name,{'sticky':'nsew','children':[
            ('Entry.padding',{'sticky':'nsew','children':[('Entry.textarea',{'sticky':'nsew'})]})]})])
        s.configure(style,padding=8,fieldbackground=fill,foreground=FG,insertcolor=FG,
                    bordercolor=border,lightcolor=border,darkcolor=border)
        s.map(style,fieldbackground=[('disabled',PANEL),('readonly',fill)],foreground=[('disabled','#67717e'),('readonly',FG)])

    element('Studio.Combobox.field',surface(root,CARD),[
        ('disabled',surface(root,PANEL,'#202733')),
        ('focus',surface(root,CARD,'#da4256')),
        ('active',surface(root,'#222b37','#3a4656'))])
    arrow=Image.new('RGBA',(22*3,22*3))
    ImageDraw.Draw(arrow).line([(8*3,9*3),(11*3,12*3),(14*3,9*3)],fill=MUTED,width=4)
    arrow=ImageTk.PhotoImage(arrow.resize((22,22),Image.Resampling.LANCZOS),master=root)
    element('Studio.Combobox.downarrow',arrow,border=0,sticky='')
    s.layout('TCombobox',[('Studio.Combobox.field',{'sticky':'nsew','children':[
        ('Studio.Combobox.downarrow',{'side':'right','sticky':''}),
        ('Combobox.padding',{'sticky':'nsew','children':[('Combobox.textarea',{'sticky':'nsew'})]})]})])
    s.configure('TCombobox',padding=6,fieldbackground=CARD,foreground=FG,background=BG,
                bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,arrowcolor=MUTED)
    s.map('TCombobox',fieldbackground=[('readonly',CARD),('disabled',PANEL)],
          foreground=[('disabled','#67717e'),('readonly',FG)],selectbackground=[('readonly',CARD)],
          selectforeground=[('readonly',FG)])
    root.option_add('*TCombobox*Listbox.background',CARD)
    root.option_add('*TCombobox*Listbox.foreground',FG)
    root.option_add('*TCombobox*Listbox.selectBackground',SELECTED)
    root.option_add('*TCombobox*Listbox.selectForeground',FG)
    root.option_add('*TCombobox*Listbox.font','{Segoe UI} 10')
    root.option_add('*TCombobox*Listbox.relief','flat')
    root.option_add('*TCombobox*Listbox.highlightThickness',0)

    for orientation in ('Vertical','Horizontal'):
        style=orientation+'.TScrollbar'
        s.configure(style,background='#46505e',troughcolor=BG,arrowcolor=MUTED,
                    bordercolor=BG,lightcolor=BG,darkcolor=BG,arrowsize=16,gripcount=0,
                    relief='flat',borderwidth=0)
        s.map(style,background=[('pressed',ACCENT),('active','#667383')])
        name=orientation+'.Studio.Scrollbar.thumb'
        size=(12,30) if orientation=='Vertical' else (30,12)
        element(name,surface(root,'#46505e','#46505e',size,5),[
            ('pressed',surface(root,ACCENT,ACCENT,size,5)),
            ('active',surface(root,'#667383','#667383',size,5))],border=5)
        layout=s.layout(style)
        def swap(items):
            return [(name if key.endswith('.thumb') else key,dict(value,**({'children':swap(value['children'])} if 'children' in value else {}))) for key,value in items]
        s.layout(style,swap(layout))

    for style,shape in [('TCheckbutton','check'),('TRadiobutton','radio')]:
        def indicator(selected,disabled=False):
            scale=3;img=Image.new('RGBA',(20*scale,20*scale));d=ImageDraw.Draw(img)
            bounds=(2*scale,2*scale,16*scale,16*scale)
            fill=ACCENT if selected and not disabled else '#282e38' if selected else CARD
            outline='#49515d' if disabled else ACCENT if selected else '#586272'
            if shape=='radio':
                d.ellipse(bounds,fill=CARD,outline=outline,width=scale)
                if selected:d.ellipse((6*scale,6*scale,12*scale,12*scale),fill=fill)
            else:
                d.rounded_rectangle(bounds,radius=3*scale,fill=fill,outline=outline,width=scale)
                if selected:d.line([(5*scale,9*scale),(8*scale,12*scale),(13*scale,6*scale)],fill='#b4bbc5' if disabled else FG,width=2*scale)
            return ImageTk.PhotoImage(img.resize((20,20),Image.Resampling.LANCZOS),master=root)
        name='Studio.'+shape+'.indicator'
        element(name,indicator(False),[('disabled selected',indicator(True,True)),('selected',indicator(True)),('disabled',indicator(False,True))],border=0,sticky='')
        layout=s.layout(style)
        def swap_indicator(items):
            return [(name if key.endswith('.indicator') else key,dict(value,**({'children':swap_indicator(value['children'])} if 'children' in value else {}))) for key,value in items]
        s.layout(style,swap_indicator(layout))
        s.configure(style,background=BG,foreground=MUTED,padding=0)
        s.map(style,background=[('active',BG)],foreground=[('disabled','#68717f'),('active',FG)])

    s.configure('Compact.TRadiobutton',background=PANEL,font=('Segoe UI',9))
    s.map('Compact.TRadiobutton',background=[('active',PANEL),('disabled',PANEL)])
    s.configure('TNotebook',background=BG,borderwidth=0,tabmargins=(0,0,0,0))
    s.configure('TNotebook.Tab',background=CARD,foreground=MUTED,padding=(14,6),bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE)
    s.map('TNotebook.Tab',background=[('selected',SELECTED),('active','#252e3b')],foreground=[('selected',FG)])
    s.configure('TScale',background=PANEL,troughcolor=CARD,bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE)
    s.configure('TProgressbar',background=ACCENT,troughcolor=PANEL,bordercolor=BG,lightcolor=BG,darkcolor=BG,borderwidth=0)
    s.configure('TPanedwindow',background=BG)
    s.configure('Sash',sashthickness=5,background=BG,gripcount=0)
    # A Tcl interpreter owns the elements; keep their images alive for its lifetime.
    root._studio_theme_images=images
    def dark_title():
        try:
            hwnd=ctypes.windll.user32.GetParent(root.winfo_id())
            value=ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd,20,ctypes.byref(value),ctypes.sizeof(value))
        except (AttributeError,OSError):pass
    root.after_idle(dark_title)

