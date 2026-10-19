"""Keep the voice editor usable when wrapped export controls become tall."""
import tkinter as tk
from tkinter import ttk
from modern_theme import BG

def create(owner):
    container=ttk.Frame(owner)
    container.pack(side='bottom',fill='x',padx=22,pady=(0,12))
    canvas=tk.Canvas(container,bg=BG,highlightthickness=0,borderwidth=0,width=1,height=1)
    canvas.pack(side='left',fill='both',expand=True)
    scrollbar=ttk.Scrollbar(container,orient='vertical',command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    owner.export_scroll_container=container;owner.export_scroll_canvas=canvas
    owner.export_scrollbar=scrollbar;owner.export_scroll_active=False
    return canvas

def install(owner,panel):
    owner.export_scroll_window=owner.export_scroll_canvas.create_window(0,0,anchor='nw',window=panel)
    def configure(event=None):
        canvas=owner.export_scroll_canvas
        width=canvas.winfo_width()
        if width>1 and int(float(canvas.itemcget(owner.export_scroll_window,'width')))!=width:canvas.itemconfigure(owner.export_scroll_window,width=width)
        update(owner)
    panel.bind('<Configure>',configure,add='+')
    owner.export_scroll_canvas.bind('<Configure>',configure,add='+')
    def wheel(event):
        if not owner.export_scroll_active:return
        # Only consume wheel events from the export panel; other lists and
        # dialog windows retain their own scrolling and input behavior.
        widget=event.widget
        if widget.winfo_class() in ('TCombobox','TScale','TEntry','Entry'):return
        while widget is not None:
            if widget is owner.export_scroll_container:
                owner.export_scroll_canvas.yview_scroll(-int(event.delta/120),'units')
                return 'break'
            widget=getattr(widget,'master',None)
    owner.bind('<MouseWheel>',wheel,add='+')

def update(owner):
    if not hasattr(owner,'export_scroll_window'):return
    canvas=owner.export_scroll_canvas;panel=owner.export_panel
    scale=max(1,float(owner.tk.call('tk','scaling'))/(96/72))
    requested=panel.winfo_reqheight()
    compact=owner.winfo_height()<680*scale
    limit=round(115*scale)
    active=compact and requested>limit
    height=min(requested,limit) if active else requested
    if int(canvas.cget('height'))!=height:canvas.configure(height=height)
    region=(0,0,max(1,canvas.winfo_width()),requested)
    if region!=getattr(owner,'_export_scroll_region',None):
        canvas.configure(scrollregion=region);owner._export_scroll_region=region
    owner.export_scroll_active=active
    if active and not owner.export_scrollbar.winfo_manager():owner.export_scrollbar.pack(side='right',fill='y')
    elif not active and owner.export_scrollbar.winfo_manager():
        owner.export_scrollbar.pack_forget();canvas.yview_moveto(0)
