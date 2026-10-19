"""Shared restrained button colors and crisp, font-independent action icons."""
from tkinter import ttk
from PIL import Image,ImageDraw,ImageTk
from modern_theme import surface,CARD,FG,EDGE

PALETTE={
    'Navigate':('#97bde6',CARD,'#344558','#222d3a'),
    'Required':('#251c0a','#e7bd58','#f0ca70','#f2ce78'),
    'Save':('#70d6a0','#1a2522','#345044','#25382f'),
    'Audio':('#ffb23f',CARD,'#49402f','#30291e'),
    'Remove':('#dba3ad',CARD,'#49323b','#33232b'),
    'Neutral':('#aab4c2',CARD,EDGE,'#252e3b'),
}

def install(root):
    style=ttk.Style(root)
    for category,(color,fill,border,hover) in PALETTE.items():
        name='Identity.'+category+'.button';label=category+'.TButton'
        normal=surface(root,fill,border);active=surface(root,hover,color);disabled=surface(root,'#111720','#1b222c')
        pressed=surface(root,fill,color)
        root._studio_theme_images.extend((normal,active,disabled,pressed))
        style.element_create(name,'image',normal,('disabled',disabled),('pressed',pressed),('active',active),('focus',active),border=7,padding=0,sticky='nsew')
        style.layout(label,[(name,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
        foreground=color if category=='Required' else FG
        style.configure(label,padding=(10,8),foreground=foreground,anchor='center')
        style.map(label,foreground=[('disabled','#596270'),('!disabled',foreground)])
    root._button_icon_cache={}

def identity(text,primary=False):
    exact={
      'Configurações':('Navigate','settings'),'Escolher pasta':('Navigate','folder'),
      'Abrir pasta ▾':('Navigate','folder'),
      'Abrir pasta dos exports':('Navigate','folder'),'Abrir pasta dos projetos':('Navigate','folder'),'Abrir áudios editados':('Audio','folder'),'Abrir destino':('Navigate','folder'),'Abrir banco':('Navigate','bank'),
      'Abrir voz externa':('Navigate','import'),'Continuar projeto':('Navigate','folder'),
      'Ferramentas':('Navigate','projects'),'Ferramentas de Projeto':('Navigate','projects'),'Projetos':('Navigate','projects'),'Nome do projeto':('Navigate','edit'),
      'Migrar banco antigo':('Navigate','migrate'),'Mostrar detalhes':('Neutral','info'),
      'Mostrar filtros e legenda':('Navigate','filters'),'Ocultar bancos':('Navigate','bank'),
      'Mostrar áudio e volume':('Audio','sliders'),'Cortar áudio':('Audio','cut'),'Efeitos de voz ▾':('Audio','sliders'),
      'Gravar voz':('Audio','microphone'),'Usar gravação':('Save','check'),'Atualizar microfones':('Navigate','reset'),
      'Corrigir clipping':('Audio','shield'),'Maximizar volume':('Audio','volume'),
      'Igualar ao original':('Audio','sliders'),'Zerar ganho':('Neutral','reset'),'Restaurar sem corte':('Navigate','reset'),
      'Remover substituição':('Remove','remove'),'Todas as repetidas':('Navigate','compare'),
      'Comparar repetidas da selecionada':('Navigate','compare'),
      'Importar áudio':('Primary','import'),'Exportar banco':('Primary','export'),
      'Aplicar corte':('Save','check'),'Fechar corte':('Neutral','close'),
      'Salvar projeto':('Save','save'),'Salvar configurações':('Save','save'),
      'Compartilhar projeto':('Navigate','export'),'Copiar vozes por tags':('Navigate','copy'),
      'Mesclar projetos neste banco':('Navigate','migrate'),'Abrir projeto compartilhado':('Navigate','folder'),
      'Criar projeto atualizado':('Save','save'),'Aplicar mescla':('Save','check'),
      'Copiar vozes escolhidas':('Save','copy'),'Importar faixa':('Primary','import'),
      'Fechar':('Neutral','close'),'Cancelar':('Neutral','close'),
    }
    if text in exact:return exact[text]
    if 'Ouvir' in text or 'Parar' in text:return 'Audio',None if text.startswith(('▶','■')) else 'play' if 'Ouvir' in text else 'stop'
    return ('Primary' if primary else 'Neutral'),None

def icon(root,shape,color):
    size=max(14,round(14*float(root.tk.call('tk','scaling'))/(96/72)))
    key=(shape,color,size)
    if key in root._button_icon_cache:return root._button_icon_cache[key]
    image=Image.new('RGBA',(48,48));d=ImageDraw.Draw(image)
    def line(points):d.line(points,fill=color,width=4,joint='curve')
    def box(bounds):d.rounded_rectangle(bounds,radius=3,outline=color,width=4)
    if shape=='save':
        box((6,4,42,44));box((14,4,33,17));box((14,27,34,44))
    elif shape=='microphone':
        d.rounded_rectangle((16,3,32,29),radius=8,outline=color,width=4)
        d.arc((8,15,40,38),0,180,fill=color,width=4);line([(8,15),(8,23)]);line([(40,15),(40,23)]);line([(24,38),(24,44)]);line([(15,44),(33,44)])
    elif shape=='folder':
        line([(4,39),(4,12),(18,12),(22,6),(41,6),(41,20)]);box((5,20,44,40))
    elif shape in ('import','export','migrate'):
        line([(6,30),(6,42),(42,42),(42,30)])
        if shape=='import':line([(24,3),(24,31)]);line([(14,22),(24,32),(34,22)])
        else:line([(24,33),(24,6)]);line([(14,15),(24,5),(34,15)])
    elif shape=='settings':
        d.ellipse((11,11,37,37),outline=color,width=4);d.ellipse((19,19,29,29),outline=color,width=4)
        for points in ([(24,2),(24,12)],[(24,36),(24,46)],[(2,24),(12,24)],[(36,24),(46,24)],[(8,8),(15,15)],[(33,33),(40,40)],[(8,40),(15,33)],[(33,15),(40,8)]):line(points)
    elif shape in ('projects','bank'):
        for bounds in ((5,5,20,20),(28,5,43,20),(5,28,20,43),(28,28,43,43)):box(bounds)
    elif shape=='edit':
        line([(8,33),(33,8),(40,15),(15,40),(6,42),(8,33)]);line([(28,13),(35,20)])
    elif shape=='cut':
        d.ellipse((3,5,17,19),outline=color,width=4);d.ellipse((3,29,17,43),outline=color,width=4);line([(15,16),(42,40)]);line([(15,32),(42,8)])
    elif shape in ('sliders','filters'):
        for y,x in ((10,17),(24,32),(38,12)):
            line([(4,y),(44,y)]);d.ellipse((x-5,y-5,x+5,y+5),fill=CARD,outline=color,width=3)
    elif shape=='shield':line([(24,4),(41,11),(39,31),(24,44),(9,31),(7,11),(24,4)]);line([(15,24),(22,31),(34,17)])
    elif shape=='volume':
        line([(5,29),(5,18),(14,18),(23,9),(23,39),(14,29),(5,29)]);line([(34,33),(34,12)]);line([(28,18),(34,11),(40,18)])
    elif shape=='remove':
        line([(9,14),(12,42),(36,42),(39,14)]);line([(5,13),(43,13)]);line([(17,12),(17,5),(31,5),(31,12)]);line([(20,21),(20,35)]);line([(28,21),(28,35)])
    elif shape in ('compare','copy'):
        box((5,5,29,30));box((19,18,43,43))
    elif shape=='info':
        d.ellipse((3,3,45,45),outline=color,width=4);line([(24,21),(24,35)]);d.ellipse((22,11,26,15),fill=color)
    elif shape=='reset':
        d.arc((8,8,41,41),15,300,fill=color,width=4);line([(5,8),(5,21),(18,21)])
    elif shape=='check':line([(5,24),(18,37),(43,9)])
    elif shape=='close':line([(9,9),(39,39)]);line([(39,9),(9,39)])
    elif shape=='play':d.polygon([(11,5),(42,24),(11,43)],fill=color)
    elif shape=='stop':d.rectangle((8,8,40,40),fill=color)
    result=ImageTk.PhotoImage(image.resize((size,size),Image.Resampling.LANCZOS),master=root)
    root._button_icon_cache[key]=result;return result

def options(root,text,primary=False):
    category,shape=identity(text,primary)
    result={'style':category+'.TButton'}
    if shape:
        color='#ffffff' if category=='Primary' else PALETTE[category][0]
        result['image']=(icon(root,shape,color),'disabled',icon(root,shape,'#596270'))
        result['compound']='left'
    return result
