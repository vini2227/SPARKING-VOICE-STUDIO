"""Session undo/redo with immutable audio copies and one entry per operation."""
import copy,hashlib,shutil,time
from pathlib import Path
from functools import wraps

class EditHistory:
    LIMIT=80
    def __init__(self,owner):
        self.owner=owner;self.undo_stack=[];self.redo_stack=[];self.files={};self.last_group=None
    def state(self):
        return copy.deepcopy({name:getattr(self.owner,name,{}) for name in ('replacements','gains','variations','trim_originals','processing_originals','effects_originals','speed_originals','duplicate_originals','manual_identifications')})
    def begin(self):
        if not self.owner.bank or self.owner.busy:return None
        state=self.state();self.pin(state)
        return (self.owner.bank,state)
    def pin(self,state):
        paths=set(state['replacements'].values())
        paths.update(item['original'] for item in list(state['trim_originals'].values())+list(state['processing_originals'].values())+list(state.get('effects_originals',{}).values())+list(state.get('speed_originals',{}).values())+list(state.get('duplicate_originals',{}).values()) if item.get('original'))
        for value in paths:
            p=Path(value);stat=p.stat();signature=(stat.st_size,stat.st_mtime_ns)
            if value in self.files and self.files[value]['signature']==signature:continue
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            dest=self.owner.project/'UndoHistory'/(digest+'.wav')
            if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            self.files[value]={'signature':signature,'digest':digest,'backup':str(dest)}
        state['_files']={value:dict(self.files[value]) for value in paths}
    def finish(self,before,label,group=None):
        if before is None or before[0] is not self.owner.bank:return
        import duplicate_wavs
        origins_changed=duplicate_wavs.preserve_origins(self.owner,before[1],label)
        after=self.state()
        if all(before[1][name]==after[name] for name in after):return
        self.pin(after);now=time.monotonic()
        if group and self.last_group and self.last_group[0]==group and now-self.last_group[1]<.8 and self.undo_stack and self.undo_stack[-1]['after']==before[1]:
            self.undo_stack[-1]['after']=after
        else:self.undo_stack.append({'before':before[1],'after':after,'label':label})
        self.undo_stack=self.undo_stack[-self.LIMIT:];self.redo_stack.clear()
        self.last_group=(group,now) if group else None;self.update_buttons()
        if origins_changed:self.owner.fill_rows()
    def reset(self):
        self.undo_stack.clear();self.redo_stack.clear();self.files.clear();self.last_group=None;self.update_buttons()
    def relocate(self,old,new):
        old=Path(old).resolve();new=Path(new)
        def moved(value):
            p=Path(value).resolve()
            return str(new/p.relative_to(old)) if p.is_relative_to(old) else value
        for entry in self.undo_stack+self.redo_stack:
            for state in (entry['before'],entry['after']):
                state['replacements']={k:moved(v) for k,v in state['replacements'].items()}
                for item in list(state['trim_originals'].values())+list(state['processing_originals'].values())+list(state.get('effects_originals',{}).values())+list(state.get('speed_originals',{}).values())+list(state.get('duplicate_originals',{}).values()):
                    for field in ('original','trimmed'):
                        if field in item:item[field]=moved(item[field])
                versions={}
                for value,info in state['_files'].items():
                    item=dict(info);backup=moved(item['backup'])
                    if Path(backup).is_file():item['backup']=backup
                    versions[moved(value)]=item
                state['_files']=versions
        files={}
        for value,info in self.files.items():
            item=dict(info);backup=moved(item['backup'])
            if Path(backup).is_file():item['backup']=backup
            files[moved(value)]=item
        self.files=files;self.last_group=None
    def resolve(self,value,item):
        p=Path(value)
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['digest']:return value
        backup=Path(item['backup'])
        if not backup.is_file() or hashlib.sha256(backup.read_bytes()).hexdigest()!=item['digest']:
            raise ValueError('O áudio preservado para desfazer não está disponível.')
        dest=self.owner.project/'Replacements'/('undo_'+item['digest']+'.wav')
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup,dest)
        return str(dest)
    def apply(self,state):
        # Resolve everything before changing the editor; a missing copy leaves it intact.
        self.owner.stop()
        restored=copy.deepcopy(state);values=set(restored['replacements'].values())
        values.update(v['original'] for v in list(restored['trim_originals'].values())+list(restored['processing_originals'].values())+list(restored.get('effects_originals',{}).values())+list(restored.get('speed_originals',{}).values())+list(restored.get('duplicate_originals',{}).values()) if v.get('original'))
        versions=restored.pop('_files')
        resolved={value:self.resolve(value,versions[value]) for value in values}
        restored['replacements']={k:resolved[v] for k,v in restored['replacements'].items()}
        for key,item in list(restored['trim_originals'].items())+list(restored['processing_originals'].items())+list(restored.get('effects_originals',{}).items())+list(restored.get('speed_originals',{}).items())+list(restored.get('duplicate_originals',{}).items()):
            item['original']=resolved[item['original']]
            item['trimmed']=restored['replacements'].get(key,item.get('trimmed'))
        o=self.owner;o.stop();o.hide_audio_trim();o.level_token+=1
        if o.level_after:o.after_cancel(o.level_after);o.level_after=None
        if o.gain_save_after:o.after_cancel(o.gain_save_after);o.gain_save_after=None
        for name,value in restored.items():setattr(o,name,value)
        o.level_signature=None;o.level_data={};o.fill_rows();o.refresh_function_choices();o.fill_rows();o.select()
    def move(self,redo=False):
        o=self.owner
        if o.busy or not o.bank:return
        source=self.redo_stack if redo else self.undo_stack
        target=self.undo_stack if redo else self.redo_stack
        if not source:return
        entry=source[-1]
        try:self.apply(entry['after' if redo else 'before'])
        except Exception as error:o.fail(str(error));return
        source.pop();target.append(entry);self.last_group=None
        o.status.set(o.tr('Refeito: ' if redo else 'Desfeito: ')+o.tr(entry['label']))
        self.update_buttons()
    def shortcut(self,event,redo=False):
        o=self.owner
        if event.widget.winfo_class() in ('Entry','TEntry','Text','Spinbox','TSpinbox'):return
        grab=o.grab_current()
        if grab is not None and grab is not o:return
        self.move(redo);return 'break'
    def setup(self,parent):
        o=self.owner
        o.bind('<Control-z>',self.shortcut,add='+')
        o.bind('<Control-y>',lambda e:self.shortcut(e,True),add='+')
        o.bind('<Control-Shift-Z>',lambda e:self.shortcut(e,True),add='+')
        self.update_buttons()
    def update_buttons(self):
        for name,stack in [('undo_btn',self.undo_stack),('redo_btn',self.redo_stack)]:
            button=getattr(self.owner,name,None)
            if button is not None and button.winfo_exists():button.configure(state='normal' if stack and not self.owner.busy else 'disabled')

def install(studio):
    labels={'remove':'Remover substituição','change_gain':'Ajustar ganho','change_variation':'Alterar variação','restore_untrimmed_audio':'Restaurar sem corte'}
    for method,label in labels.items():
        original=getattr(studio,method)
        def decorate(fn,label,method):
            @wraps(fn)
            def edited(self,*args,**kwargs):
                if method=='change_gain' and self._setting_gain:return fn(self,*args,**kwargs)
                try:before=self.history.begin()
                except Exception as error:self.fail(str(error));return
                result=fn(self,*args,**kwargs)
                key=self.selected['key'] if self.selected else None
                self.history.finish(before,label,('gain',key) if method=='change_gain' else None)
                return result
            return edited
        setattr(studio,method,decorate(original,label,method))
