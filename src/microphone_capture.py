"""Bounded-memory microphone capture into an atomically finalized PCM WAV."""
import sys,queue,threading,wave,os
from pathlib import Path
from collections import deque
import numpy as np
import core

def backend():
    dependency=core.APP/'Tools/PythonDeps'
    if str(dependency) not in sys.path:sys.path.insert(0,str(dependency))
    import sounddevice
    return sounddevice

def input_devices():
    sd=backend();hosts=sd.query_hostapis();default=int(sd.default.device[0]);devices=[]
    for index,item in enumerate(sd.query_devices()):
        if item['max_input_channels']>0:
            devices.append({'index':index,'name':item['name'],'host':hosts[item['hostapi']]['name'],
                'rate':int(item['default_samplerate']),'default':index==default})
    return devices

class Capture:
    def __init__(self,path,device,rate,sd=None):
        self.path=core.owned(path);self.part=self.path.with_suffix('.wav.part');self.device=device;self.rate=rate
        self.sd=sd;self.active=False;self.frames=0;self.level=0.;self.clipped=False;self.error=None;self.write_error=None
        self.levels=deque(maxlen=100);self.queue=queue.Queue(maxsize=256);self.ready=threading.Event()
        self.writer=None;self.stream=None;self.finalized=False
    def callback(self,data,frames,time_info,status):
        if not self.active:return
        if status:self.error='O microfone perdeu amostras. Confira a gravação ou grave novamente.'
        pcm=bytes(data)
        if len(pcm)!=frames*2:self.error='O microfone retornou dados de áudio inválidos.';return
        values=np.frombuffer(pcm,dtype='<i2').astype(np.int32)
        peak=int(np.max(np.abs(values))) if values.size else 0
        self.level=peak/32768.;self.levels.append(self.level);self.clipped=self.clipped or peak>=32767
        try:self.queue.put_nowait(pcm)
        except queue.Full:self.error='A gravação não acompanhou o microfone. Grave novamente.'
    def write(self):
        try:
            with wave.open(str(self.part),'wb') as output:
                output.setparams((1,2,self.rate,0,'NONE','not compressed'));self.ready.set()
                while True:
                    block=self.queue.get()
                    if block is None:break
                    output.writeframesraw(block);self.frames+=len(block)//2
        except Exception as error:self.write_error=str(error);self.error='Não foi possível salvar a gravação.'
        finally:self.ready.set()
    def start(self):
        self.sd=self.sd or backend()
        self.sd.check_input_settings(device=self.device,channels=1,dtype='int16',samplerate=self.rate)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.writer=threading.Thread(target=self.write,name='VoiceRecordingWriter',daemon=True);self.writer.start()
        if not self.ready.wait(5):raise RuntimeError('Não foi possível iniciar a gravação.')
        if self.write_error:raise OSError(self.write_error)
        try:
            self.stream=self.sd.RawInputStream(device=self.device,samplerate=self.rate,channels=1,
                dtype='int16',blocksize=1024,latency='high',callback=self.callback)
            self.active=True;self.stream.start()
        except Exception:
            self.stop(allow_empty=True);raise
    def stop(self,allow_empty=False):
        if self.finalized:return self.path if self.path.is_file() else None
        self.active=False
        if self.stream:
            try:self.stream.stop()
            except Exception:self.error='O microfone foi interrompido. Confira a gravação.'
            finally:
                try:self.stream.close()
                except Exception:self.error='O microfone foi interrompido. Confira a gravação.'
                self.stream=None
        if self.writer and self.writer.is_alive():
            # A full queue drains on the writer; never discard its accepted samples.
            self.queue.put(None,timeout=5);self.writer.join(timeout=5)
            if self.writer.is_alive():raise RuntimeError('Aguarde a finalização do arquivo de gravação.')
        if self.write_error:raise OSError(self.write_error)
        if not self.frames:
            if self.part.exists():self.part.unlink()
            self.finalized=True
            if not allow_empty:raise ValueError('A gravação está vazia. Grave antes de usar.')
            return None
        os.replace(self.part,self.path);self.finalized=True
        return self.path

