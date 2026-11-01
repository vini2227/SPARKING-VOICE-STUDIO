"""Full Explorer-visible project audio, independent of UI list filters."""
import csv,hashlib,json,os,threading,wave
from contextlib import nullcontext
from pathlib import Path
import core

def is_edited(bank,row,replacements):
    if row['key'] in replacements:return True
    return bool(bank.external and not core.imported_is_original(bank,row) and (bank.source or {}).get('audio_similarity',{}).get(row['key'],{}).get('status')=='different')

def materialize(bank,project,replacements,gains=None,variations=None,keep_imported=None,io_lock=None,edited_only=False):
    project=core.owned(project);folder=core.owned(project/('Audios editados' if edited_only else 'Audios'));folder.mkdir(parents=True,exist_ok=True)
    keep_imported=bool(bank.external) if keep_imported is None else bool(keep_imported)
    gains=gains or {};variations=variations or {}
    statepath=folder/'index.json'
    try:prior=json.loads(statepath.read_text(encoding='utf-8'))
    except (OSError,ValueError):prior={}
    previous={row['key']:row for row in prior.get('voices',[])}
    rows=[];bank_hash=hashlib.sha256(bank.acb+bank.stream_bytes).hexdigest()
    def render_row(row):
        key=row['key'];source=replacements.get(key)
        action='replace' if source else 'preserve' if core.preserve_unreplaced(bank,row,keep_imported) else 'silence'
        gain=gains.get(key,0.0) if source else 0.0;variation=variations.get(key,1) if source else 1
        stamp=None
        if source:
            stat=Path(source).stat();stamp=(str(source),stat.st_size,stat.st_mtime_ns)
        fingerprint=hashlib.sha256(json.dumps([bank_hash,key,action,stamp,gain,variation,core.SILENCE_DURATION if action=='silence' else None,row['rate'],row['channels'],row['samples']]).encode()).hexdigest()
        name=Path(row['filename']).with_suffix('.wav').name
        output=core.owned(folder/name);sidecar=core.owned(folder/(name+'.json'))
        old=previous.get(key,{})
        if old.get('fingerprint')!=fingerprint or not output.is_file() or not sidecar.is_file():
            pending=core.owned(folder/(name+'.pending.wav'))
            try:
                if source:core.normalize_wav(source,pending,row['rate'],row['channels'],row['samples'],gain,variation)
                elif action=='preserve':
                    # Bank.original protects each cache path independently.
                    original=bank.original(row)
                    pending.write_bytes(original.read_bytes())
                else:core.silent_wav(pending,row)
                os.replace(pending,output)
            finally:pending.unlink(missing_ok=True)
        with wave.open(str(output),'rb') as audio:
            samples=audio.getnframes();rate=audio.getframerate();channels=audio.getnchannels()
        metadata={'key':key,'filename':name,'original_filename':row['filename'],'awb_id':row['id'],
            'cue_ids':list(row['cue_ids']),'cue_names':list(row['cue_names']),
            'tags':list(row['functions']),'pattern_names':list(row['pattern_names']),
            'function_descriptions_en':list(row['english']),'action':action,'gain_db':gain,'variation':variation,
            'samples':samples,'sample_rate':rate,'channels':channels,'duration':samples/rate,'fingerprint':fingerprint}
        if old!=metadata or not sidecar.is_file():core.write_json(sidecar,metadata)
        return metadata
    selected=[row for row in bank.rows if not edited_only or is_edited(bank,row,replacements)]
    rows=core.cpu_jobs.map_ordered(render_row,selected,bank.cfg)
    if edited_only:
        current={row['filename'] for row in rows}
        for old in previous.values():
            name=old.get('filename','')
            if name and name not in current and Path(name).name==name and name.lower().endswith('.wav'):
                for file in (folder/name,folder/(name+'.json')):core.owned(file).unlink(missing_ok=True)
    manifest={'bank':bank.name,'character_id':core.character_id(bank.name),'voice_count':len(rows),
        'keep_imported':bool(keep_imported),'voices':rows}
    core.write_json(statepath,manifest)
    pending=core.owned(folder/'index.csv.tmp')
    columns=['filename','awb_id','cue_ids','tags','cue_names','action','gain_db','variation','duration']
    with pending.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,delimiter=';');writer.writeheader()
        for row in rows:writer.writerow({key:json.dumps(row[key],ensure_ascii=False) if isinstance(row[key],list) else row[key] for key in columns})
    os.replace(pending,folder/'index.csv')
    return manifest

class ProjectAudioWriter:
    def __init__(self,on_error):
        self.on_error=on_error;self.condition=threading.Condition();self.pending={};self.running=False;self.errors={};self.closed=False
        self.thread=threading.Thread(target=self._work,daemon=True);self.thread.start()
    def submit(self,bank,project,replacements,gains,variations,keep_imported,io_lock):
        key=str(project)
        with self.condition:
            if self.closed:return
            self.pending[key]=(bank,project,dict(replacements),dict(gains),dict(variations),keep_imported,io_lock)
            self.errors.pop(key,None);self.condition.notify_all()
    def _work(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda:bool(self.pending) or self.closed)
                if self.closed and not self.pending:return
                key=next(iter(self.pending));args=self.pending.pop(key);self.running=True
            try:
                materialize(*args)
                with self.condition:self.errors.pop(key,None)
            except Exception as error:
                with self.condition:self.errors[key]=str(error)
                self.on_error(str(error))
            finally:
                with self.condition:self.running=False;self.condition.notify_all()
    def wait(self):
        with self.condition:
            self.condition.wait_for(lambda:not self.pending and not self.running)
            if self.errors:raise RuntimeError('Falha ao atualizar os áudios do projeto: '+'; '.join(self.errors.values()))


    def shutdown(self):
        with self.condition:
            self.closed=True;self.pending.clear();self.condition.notify_all()
