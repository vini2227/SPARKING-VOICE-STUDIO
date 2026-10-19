"""Bounded diagnostics and UI heartbeat; no audio/project payloads are recorded."""
import datetime,faulthandler,io,json,os,threading,time,traceback
from pathlib import Path
import core

_lock=threading.RLock()
ROOT=core.APP/'Reports/Diagnostics'
LIMITS={'events.log':128*1024,'interface_errors.log':512*1024,'hangs.log':256*1024}

def append(name,text):
    try:
        with _lock:
            ROOT.mkdir(parents=True,exist_ok=True)
            path=ROOT/name;limit=LIMITS[name]
            payload=text.encode('utf-8','replace')[-limit:]
            old=path.read_bytes() if path.is_file() else b''
            if len(old)+len(payload)>limit:
                keep=max(0,limit-len(payload))
                old=old[-keep:] if keep else b''
                if b'\n' in old:old=old.split(b'\n',1)[1]
            path.write_bytes(old+payload)
    except OSError:pass

def event(kind,**fields):
    data={'time':datetime.datetime.now().astimezone().isoformat(timespec='seconds'),'pid':os.getpid(),'event':kind}
    data.update(fields);append('events.log',json.dumps(data,ensure_ascii=False,default=str)+'\n')

def record_error(exc,value,tb,context):
    timestamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    append('interface_errors.log',f'\n{timestamp} PID {os.getpid()} [{context}]\n'+''.join(traceback.format_exception(exc,value,tb)))
    event('error',context=context,error_type=exc.__name__,message=str(value)[:400])

def callback_error(owner,exc,value,tb,context='Tk callback'):
    record_error(exc,value,tb,context)
    if getattr(owner,'_destroyed',False):return
    try:owner.fail(str(value))
    except Exception:record_error(*__import__('sys').exc_info(),'show error')

def heartbeat(owner):
    owner._ui_heartbeat=time.monotonic()
    if owner._ui_heartbeat-getattr(owner,'_window_check_time',0)<1:return
    owner._window_check_time=owner._ui_heartbeat
    try:
        grab=owner.grab_current()
        state=(owner.state(),str(grab) if grab is not None else None,grab.winfo_class() if grab is not None else None,bool(grab.winfo_ismapped()) if grab is not None else None)
        if state!=getattr(owner,'_last_window_state',None):
            owner._last_window_state=state
            event('window_state',state=state[0],modal=state[1],modal_type=state[2],modal_visible=state[3])
    except Exception:pass

def start(owner):
    owner._ui_heartbeat=time.monotonic();owner._diagnostic_stop=threading.Event()
    stop=owner._diagnostic_stop
    def destroyed(event_data):
        if event_data.widget is owner:
            stop.set();event('app_closed')
            # Cancel pending layout/animation callbacks before Tk deletes them.
            try:
                for timer in owner.tk.splitlist(owner.tk.call('after','info')):owner.after_cancel(timer)
            except Exception:pass
    owner.bind('<Destroy>',destroyed,add='+')
    def watch():
        last_dump=0
        while not stop.wait(5):
            now=time.monotonic();delay=now-owner._ui_heartbeat
            if delay<15 or now-last_dump<60:continue
            last_dump=now
            event('ui_unresponsive',seconds=round(delay,1),operation=getattr(owner,'_diagnostic_operation',None))
            # A temporary unnamed stream avoids additional permanent files.
            import tempfile
            try:
                with tempfile.TemporaryFile(mode='w+b') as stream:
                    faulthandler.dump_traceback(file=stream,all_threads=True)
                    stream.seek(0);stack=stream.read(256*1024).decode('utf-8','replace')
                append('hangs.log',f'\n{datetime.datetime.now().astimezone().isoformat()} PID {os.getpid()} UI stalled {delay:.1f}s\n'+stack)
            except (OSError,RuntimeError):pass
    threading.Thread(target=watch,name='VoiceUiDiagnostics',daemon=True).start()
    event('app_started')
