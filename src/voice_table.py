"""Virtual voice table: measured word wrapping and independent row heights."""
import bisect
from modern_theme import PANEL,CARD,MUTED,SELECTED,ALTERNATE,EDGE,FG,ACCENT,WARNING
import tkinter as tk
from tkinter import ttk,font
from bank_table import wrap_words


def wrap_cell(text,width,measure):
    """Prefer whole words; exceptionally long identifiers continue on the next line."""
    lines=[];line=''
    for word in str(text).split():
        if measure(word)>width:
            if line:lines.append(line);line=''
            chunk=''
            for char in word:
                if chunk and measure(chunk+char)>width:lines.append(chunk);chunk=''
                chunk+=char
            line=chunk
        else:
            candidate=(line+' '+word).strip()
            if line and measure(candidate)>width:lines.append(line);line=word
            else:line=candidate
    if line:lines.append(line)
    return lines or ['']

class VoiceTable(ttk.Frame):
    def __init__(self,parent,columns,**ignored):
        super().__init__(parent)
        self.columns=tuple(columns);self.records={};self.selected=None;self.bounds=[0];self.cells={};self.widths={c:160 for c in columns};self.titles={c:c for c in columns};self.colors={};self.pending=None
        self.font=font.Font(self,family='Segoe UI',size=9);self.bold=font.Font(self,family='Segoe UI',size=9,weight='bold')
        self.header=tk.Canvas(self,height=30,bg=CARD,highlightthickness=0);self.header.pack(fill='x')
        self.canvas=tk.Canvas(self,bg=PANEL,highlightthickness=0,takefocus=1,yscrollincrement=24);self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda e:self.schedule())
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<MouseWheel>',self.wheel)
        for key,delta in (('<Up>',-1),('<Down>',1),('<Prior>',-10),('<Next>',10)):
            self.canvas.bind(key,lambda e,d=delta:self.move(d))
        self.canvas.bind('<Home>',lambda e:self.move_to(0));self.canvas.bind('<End>',lambda e:self.move_to(len(self.records)-1))
        self.header.bind('<Button-1>',self.resize_start);self.header.bind('<B1-Motion>',self.resize_drag)
        self.header.bind('<Motion>',self.resize_cursor);self.drag=None
        self.bind('<Destroy>',self.cancel_layout,add='+')
    def bind(self,sequence=None,func=None,add=None):
        if sequence in ('<Double-1>','<Button-3>') and hasattr(self,'canvas'):return self.canvas.bind(sequence,func,add)
        return super().bind(sequence,func,add)
    def configure(self,cnf=None,**kw):
        if hasattr(self,'canvas'):
            for name in ('yscrollcommand','xscrollcommand'):
                if name in kw:
                    callback=kw.pop(name)
                    if name=='xscrollcommand':
                        self.canvas.configure(xscrollcommand=lambda a,b,cb=callback:(self.header.xview_moveto(a),cb(a,b)))
                    else:self.canvas.configure(yscrollcommand=callback)
        return super().configure(cnf,**kw)
    config=configure
    def heading(self,col,option=None,**kw):
        if 'text' in kw:self.titles[col]=kw['text'];self.schedule()
        return self.titles[col] if option=='text' else {'text':self.titles[col]}
    def column(self,col,option=None,**kw):
        if 'width' in kw:self.widths[col]=kw['width'];self.schedule()
        return self.widths[col] if option=='width' else {'width':self.widths[col]}
    def tag_configure(self,tag,**kw):self.colors[tag]=kw;self.schedule()
    def insert(self,parent,index,iid=None,values=(),tags=()):
        self.records[iid]={'values':tuple(values),'tags':tuple(tags)};self.schedule();return iid
    def replace_rows(self,rows):
        """Commit a filtered view once, preserving selection and unchanged records."""
        incoming={key:{'values':tuple(item['values']),'tags':tuple(item['tags'])} for key,item in rows}
        if tuple(incoming)==tuple(self.records) and incoming==self.records:return False
        self.records={key:self.records[key] if self.records.get(key)==item else item for key,item in incoming.items()}
        if self.selected not in self.records:self.selected=None
        self.schedule();return True
    def delete(self,*keys):
        for key in keys:self.records.pop(key,None)
        if self.selected not in self.records:self.selected=None
        self.schedule()
    def get_children(self,*args):return tuple(self.records)
    def exists(self,key):return key in self.records
    def item(self,key,option=None,**kw):
        if kw:self.records[key].update(kw);self.schedule()
        return self.records[key].get(option) if option else self.records[key].copy()
    def selection(self):return (self.selected,) if self.selected in self.records else ()
    def selection_set(self,key):
        if isinstance(key,(list,tuple)):key=key[0] if key else None
        if key in self.records:
            self.ensure_layout()
            changed=key!=self.selected;self.selected=key
            if changed:self.draw()
            if changed:self.event_generate('<<TreeviewSelect>>',when='tail')
    def schedule(self):
        if self.pending is None:self.pending=self.after_idle(self.layout)
    def cancel_layout(self,event=None):
        if event is not None and event.widget is not self:return
        if self.pending is not None:
            self.after_cancel(self.pending);self.pending=None
    def ensure_layout(self):
        # Records may have been replaced while the idle measurement is queued.
        # Flush once before painting or interpreting row coordinates.
        if self.pending is not None:self.layout()
    def layout(self):
        self.cancel_layout()
        available=max(1,self.canvas.winfo_width())
        signature=(available,tuple(self.widths.items()),tuple(self.titles.items()),
                   tuple((key,tuple(row['values'])) for key,row in self.records.items()),
                   tuple(sorted(self.font.actual().items())),tuple(sorted(self.bold.actual().items())))
        if signature==getattr(self,'_measure_signature',None):
            height=max(1,self.canvas.winfo_height())
            self.canvas.configure(scrollregion=(0,0,self.x[-1],max(height,self.bounds[-1])))
            if self.bounds[-1]<=height:self.canvas.yview_moveto(0)
            self.draw();return
        self._measure_signature=signature
        minima=[]
        for i,c in enumerate(self.columns):
            longest=max((self.font.measure(word) for r in self.records.values() for word in str(r['values'][i]).split()),default=0)
            header=max((self.bold.measure(word) for word in self.titles[c].split()),default=0)
            minima.append(max(48,longest+16,header+16))
        desired=[max(self.widths[c],minima[i]) for i,c in enumerate(self.columns)]
        if sum(minima)<=available:
            room=available-sum(minima)
            extras=[desired[i]-minima[i] for i in range(len(desired))]
            if sum(extras)>room:
                total=max(1,sum(extras));widths=[minima[i]+room*extras[i]/total for i in range(len(desired))]
            else:
                widths=desired[:]
                widths[self.columns.index('function') if 'function' in self.columns else 0]+=available-sum(widths)
        else:
            # Narrow windows and unusual tags must still show every column.
            total=max(1,sum(desired));widths=[available*w/total for w in desired]
        # Integer boundaries fill the viewport exactly, including after resizing.
        edges=[0];position=0
        for width in widths:position+=width;edges.append(round(position))
        edges[-1]=available
        widths=[edges[i+1]-edges[i] for i in range(len(self.columns))]
        self.x=[0]
        for width in widths:self.x.append(self.x[-1]+width)
        self.bounds=[0];self.cells={}
        for key,r in self.records.items():
            cells=[wrap_cell(str(value),max(1,widths[i]-16),self.font.measure) for i,value in enumerate(r['values'])]
            height=max(30,max(map(len,cells))*self.font.metrics('linespace')+10)
            self.cells[key]=cells;self.bounds.append(self.bounds[-1]+height)
        # Canvas permits shifting short scroll regions, especially with unit rounding.
        # Give fitting content a viewport-sized region and pin it to the top.
        height=max(1,self.canvas.winfo_height())
        self.canvas.configure(scrollregion=(0,0,self.x[-1],max(height,self.bounds[-1])));self.canvas.xview_moveto(0)
        if self.bounds[-1]<=height:self.canvas.yview_moveto(0)
        header_cells=[wrap_cell(self.titles[c],max(1,widths[i]-16),self.bold.measure) for i,c in enumerate(self.columns)]
        header_height=max(30,max(map(len,header_cells))*self.bold.metrics('linespace')+10)
        self.header.configure(height=header_height)
        self.header.configure(scrollregion=(0,0,self.x[-1],header_height));self.header.xview_moveto(0);self.header.delete('all')
        for i,c in enumerate(self.columns):
            self.header.create_rectangle(self.x[i],0,self.x[i+1],header_height,outline=EDGE)
            self.header.create_text(self.x[i]+8,5,text='\n'.join(header_cells[i]),anchor='nw',font=self.bold,fill=MUTED)
        self.draw()
    def draw(self):
        if self.pending is not None:
            self.ensure_layout();return
        if not hasattr(self,'x'):return
        top=self.canvas.canvasy(0);bottom=top+self.canvas.winfo_height();keys=list(self.records)
        start=max(0,bisect.bisect_right(self.bounds,top)-1)
        end=min(len(keys),bisect.bisect_left(self.bounds,bottom)+1)
        signature=(tuple(self.x),top,bottom,self.selected,tuple(sorted(self.font.actual().items())),
                   repr(self.colors),tuple((key,self.bounds[i],self.bounds[i+1],self.records[key]['values'],self.records[key]['tags'],self.cells.get(key)) for i,key in enumerate(keys) if start<=i<end))
        if signature==getattr(self,'_paint_signature',None):return
        self._paint_signature=signature;self.canvas.delete('all')
        for i in range(start,end):
            key=keys[i]
            if key not in self.cells:continue
            r=self.records[key];y=self.bounds[i];height=self.bounds[i+1]-y;color=SELECTED if key==self.selected else ALTERNATE if i%2 else PANEL;fg=FG
            for tag in r['tags']:fg=self.colors.get(tag,{}).get('foreground',fg)
            self.canvas.create_rectangle(0,y,self.x[-1],y+height,fill=color,outline=EDGE)
            if key==self.selected:self.canvas.create_rectangle(0,y,3,y+height,fill=ACCENT,outline='')
            for c,lines in enumerate(self.cells[key]):
                cell_color=WARNING if self.columns[c]=='duplicate' and str(r['values'][c]) not in ('','—') else fg
                for tag in r['tags']:
                    cell_color=self.colors.get(tag,{}).get('column_foregrounds',{}).get(self.columns[c],cell_color)
                self.canvas.create_text(self.x[c]+8,y+5,text='\n'.join(lines),anchor='nw',font=self.font,fill=cell_color)
                if c:self.canvas.create_line(self.x[c],y,self.x[c],y+height,fill=EDGE)
    def yview(self,*args):
        self.ensure_layout()
        if self.bounds[-1]<=self.canvas.winfo_height():
            self.canvas.yview_moveto(0)
            if args:self.draw()
            return (0.0,1.0) if not args else None
        result=self.canvas.yview(*args)
        if args:self.draw()
        return result
    def xview(self,*args):return self.canvas.xview(*args)
    def wheel(self,e):self.yview('scroll',-int(e.delta/120),'units');return 'break'
    def identify_row(self,y):
        self.ensure_layout()
        position=self.canvas.canvasy(y)
        index=bisect.bisect_right(self.bounds,position)-1
        keys=list(self.records)
        return keys[index] if 0<=index<len(keys) else ''
    def click(self,e):
        self.ensure_layout()
        i=bisect.bisect_right(self.bounds,self.canvas.canvasy(e.y))-1;keys=list(self.records)
        if 0<=i<len(keys):self.selection_set(keys[i])
        self.canvas.focus_set()
    def move(self,delta):
        keys=list(self.records);i=keys.index(self.selected) if self.selected in keys else 0
        return self.move_to(i+delta)
    def move_to(self,i):
        keys=list(self.records)
        if keys:key=keys[max(0,min(i,len(keys)-1))];self.selection_set(key);self.see(key)
        return 'break'
    def see(self,key):
        self.ensure_layout()
        if key not in self.records:return
        i=list(self.records).index(key);a,b=self.bounds[i:i+2];top=self.canvas.canvasy(0);height=self.canvas.winfo_height();total=max(1,self.bounds[-1])
        if a<top:self.yview('moveto',a/total)
        elif b>top+height:self.yview('moveto',max(a,b-height)/total)
    def resize_cursor(self,e):
        if hasattr(self,'x'):self.header.configure(cursor='sb_h_double_arrow' if any(abs(self.header.canvasx(e.x)-x)<6 for x in self.x[1:]) else '')
    def resize_start(self,e):
        if not hasattr(self,'x'):return
        x=self.header.canvasx(e.x)
        for i,edge in enumerate(self.x[1:]):
            if abs(x-edge)<6:self.drag=(self.columns[i],x,self.x[i+1]-self.x[i]);return
        self.drag=None
    def resize_drag(self,e):
        if self.drag:
            col,start,width=self.drag;self.widths[col]=max(70,width+self.header.canvasx(e.x)-start);self.schedule()
