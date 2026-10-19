"""Scrollable bank table with measured word wrapping and variable row heights."""
import bisect
from modern_theme import PANEL,CARD,MUTED,SELECTED,ALTERNATE,EDGE,FG,ACCENT
import tkinter as tk
from tkinter import ttk,font

def wrap_words(text,width,measure):
    lines=[];line=''
    for word in text.split():
        candidate=(line+' '+word).strip()
        if line and measure(candidate)>width:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines or ['']

class BankTable(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.rows=[];self.bounds=[0];self.selected=None
        self.headers=('Personagem','ID','BTLCV')
        self.font=font.Font(self,family='Segoe UI',size=9)
        self.bold=font.Font(self,family='Segoe UI',size=9,weight='bold')
        self.header=tk.Canvas(self,height=30,bg=CARD,highlightthickness=0)
        self.header.pack(fill='x')
        self.canvas=tk.Canvas(self,bg=PANEL,highlightthickness=0,takefocus=1)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda event:self.redraw())
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<MouseWheel>',self.wheel)
        self.canvas.bind('<Up>',lambda event:self.move(-1))
        self.canvas.bind('<Down>',lambda event:self.move(1))
        self.canvas.bind('<Home>',lambda event:self.move_to(0))
        self.canvas.bind('<End>',lambda event:self.move_to(len(self.rows)-1))

    def bind(self,sequence=None,func=None,add=None):
        return self.canvas.bind(sequence,func,add)

    def set_headers(self,headers):self.headers=tuple(headers);self.redraw()
    def set_rows(self,rows):
        position=self.canvas.yview()[0]
        self.rows=list(rows);self.selected=None;self.redraw();self.canvas.yview_moveto(position)

    def columns(self):
        width=max(360,self.canvas.winfo_width())
        codewidth=max(152,max((self.font.measure(row[2])+16 for row in self.rows),default=0))
        return [0,width-codewidth-70,width-codewidth,width]

    def redraw(self):
        x=self.columns();width=x[-1];self.header.delete('all');self.canvas.delete('all')
        for index,title in enumerate(self.headers):
            self.header.create_text(x[index]+8,15,text=title,anchor='w',fill=MUTED,font=self.bold)
        self.bounds=[0];y=0;lineheight=self.font.metrics('linespace')
        for index,row in enumerate(self.rows):
            cells=[wrap_words(value,x[c+1]-x[c]-16,self.font.measure) for c,value in enumerate(row)]
            height=max(42,max(map(len,cells))*lineheight+16)
            color=SELECTED if self.selected==index else ALTERNATE if index%2 else PANEL
            self.canvas.create_rectangle(0,y,width,y+height,fill=color,outline=EDGE)
            if self.selected==index:self.canvas.create_rectangle(0,y,3,y+height,fill=ACCENT,outline='')
            for c,lines in enumerate(cells):
                self.canvas.create_text(x[c]+8,y+8,text='\n'.join(lines),anchor='nw',font=self.font,fill=FG)
                if c:self.canvas.create_line(x[c],y,x[c],y+height,fill=EDGE)
            y+=height;self.bounds.append(y)
        self.canvas.configure(scrollregion=(0,0,width,y))

    def click(self,event):
        index=bisect.bisect_right(self.bounds,self.canvas.canvasy(event.y))-1
        if 0<=index<len(self.rows):self.selection_set(index)
        self.canvas.focus_set()
    def wheel(self,event):self.canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
    def move(self,delta):return self.move_to((self.selected if self.selected is not None else 0)+delta)
    def move_to(self,index):
        if self.rows:
            index=max(0,min(index,len(self.rows)-1));self.selection_set(index);self.see(index)
        return 'break'
    def curselection(self):return () if self.selected is None else (self.selected,)
    def selection_set(self,index):
        index=int(index)
        if 0<=index<len(self.rows):self.selected=index;self.redraw()
    def get(self,index):return '  •  '.join(self.rows[-1 if index=='end' else int(index)])
    def yview(self,*args):return self.canvas.yview(*args)
    def see(self,index):
        if not self.rows:return
        top=self.canvas.canvasy(0);bottom=top+self.canvas.winfo_height()
        start,end=self.bounds[index:index+2];total=max(1,self.bounds[-1])
        if start<top:self.canvas.yview_moveto(start/total)
        elif end>bottom:self.canvas.yview_moveto(max(0,end-self.canvas.winfo_height())/total)
