"""Bounded audio jobs; workers never touch Tk or assemble shared bank metadata."""
import os,threading,subprocess,ctypes
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED,Future

MODES=(("auto","Automático"),("economy","Econômico"),("fast","Rápido"),("sequential","Sequencial"))
_local=threading.local()
_slots=threading.BoundedSemaphore(min(8,max(1,(os.cpu_count() or 1)-1)))

def available_memory():
    if os.name!='nt':return None
    class Status(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ('total','available','page','free_page','virtual','free_virtual','extended')]
    value=Status();value.length=ctypes.sizeof(value)
    try:return value.available if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)) else None
    except (AttributeError,OSError):return None

def worker_count(cfg=None,count=100,cpus=None,memory=None):
    mode=(cfg or {}).get('cpu_mode','auto')
    cpus=max(1,cpus if cpus is not None else (os.cpu_count() or 1))
    usable=max(1,cpus-1) # Leave scheduling capacity for the window and other apps.
    limit=1 if mode=='sequential' else min(2,max(1,usable//2)) if mode=='economy' else min(8,usable) if mode=='fast' else min(4,max(1,usable//2))
    memory=available_memory() if memory is None else memory
    if memory is not None:limit=min(limit,max(1,(memory-512*1024**2)//(768*1024**2)))
    return max(1,min(limit,max(1,count)))

def subprocess_options(arguments):
    arguments=list(map(str,arguments))
    if not getattr(_local,'parallel',False):return arguments,{}
    env=os.environ.copy()
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):env[name]='1'
    if os.path.basename(arguments[0]).lower() in ('ffmpeg','ffmpeg.exe'):
        arguments[1:1]=['-threads','1','-filter_threads','1','-filter_complex_threads','1']
    return arguments,{'env':env}

def map_ordered(function,items,cfg=None,progress=None,checkpoint=None):
    """Bound in-flight work, return input order, retry tool failures serially once.

    Format/validation errors are never retried. Cancellation drains active tools
    before the caller can clean staging files; no output is published here.
    """
    items=list(items);workers=worker_count(cfg,len(items));results=[None]*len(items)
    def check():
        if checkpoint:checkpoint()
    def invoke(item):
        acquired=False;before=getattr(_local,'parallel',False)
        try:
            while not acquired:check();acquired=_slots.acquire(timeout=.05)
            _local.parallel=workers>1;check();return function(item)
        finally:
            _local.parallel=before
            if acquired:_slots.release()
    if workers==1:
        for i,item in enumerate(items):
            check();results[i]=function(item)
            if progress:progress(i+1,len(items),item)
        return results
    failed=[];completed=0;next_index=0
    executor=ThreadPoolExecutor(max_workers=workers,thread_name_prefix='VoiceCPU');pending={}
    try:
        while pending or next_index<len(items):
            check()
            while len(pending)<workers and next_index<len(items):
                check();pending[executor.submit(invoke,items[next_index])]=next_index;next_index+=1
            done,_=wait(pending,timeout=.05,return_when=FIRST_COMPLETED)
            for future in done:
                index=pending.pop(future)
                try:results[index]=future.result()
                except (OSError,RuntimeError,subprocess.SubprocessError):failed.append(index);continue
                completed+=1
                if progress:progress(completed,len(items),items[index])
        check()
    finally:
        for future in pending:future.cancel()
        executor.shutdown(wait=True,cancel_futures=True)
    # A process that failed under contention gets one attempt with no other jobs.
    for index in failed:
        check();results[index]=function(items[index]);completed+=1
        if progress:progress(completed,len(items),items[index])
    return results

class SingleFlight:
    """Encode each identical PCM/key once, including concurrent duplicates."""
    def __init__(self):self.lock=threading.Lock();self.values={}
    def get(self,key,build):
        with self.lock:
            future=self.values.get(key);owner=future is None
            if owner:future=Future();self.values[key]=future
        if owner:
            try:future.set_result(build())
            except BaseException as error:
                future.set_exception(error)
                with self.lock:self.values.pop(key,None)
                raise
        return future.result()
