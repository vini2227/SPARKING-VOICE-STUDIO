"""Local speech cleanup and MDX voice separation; no network access at runtime."""
import sys,os,math,wave,shutil,subprocess,uuid,json
from pathlib import Path
import numpy as np
import core,audio_levels,video_audio

ROOT=core.APP/'Tools/VoiceAI'

def write_pcm(path,values,rate):
    values=np.asarray(values,dtype=np.float64)
    if values.ndim!=2 or not len(values) or not np.isfinite(values).all():raise ValueError('O processamento gerou áudio inválido.')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(path),'wb') as out:
        out.setparams((values.shape[1],4,int(rate),0,'NONE','not compressed'))
        out.writeframes(np.clip(np.rint(values*2147483648),-2147483648,2147483647).astype('<i4').tobytes())

def run(args,timeout=900):
    result=subprocess.run(list(map(str,args)),capture_output=True,creationflags=core.CREATE_NO_WINDOW,timeout=timeout)
    if result.returncode:raise RuntimeError(result.stderr.decode('utf-8',errors='replace')[-1800:] or 'Falha no processamento local de voz.')

def resample(source,dest,rate,channels,width='pcm_s32le'):
    run([video_audio.tool('ffmpeg'),'-nostdin','-v','error','-y','-protocol_whitelist','file,pipe','-i',source,'-ac',channels,'-ar',rate,'-c:a',width,dest])

def stft(values,n_fft,hop,dim_f):
    padded=np.pad(values,((0,0),(n_fft//2,n_fft//2)),mode='reflect')
    windows=np.lib.stride_tricks.sliding_window_view(padded,n_fft,axis=1)[:,::hop,:]
    window=(.5-.5*np.cos(2*np.pi*np.arange(n_fft)/n_fft)).astype(np.float32)
    spectrum=np.fft.rfft(windows*window,axis=-1).transpose(0,2,1)[:,:dim_f,:]
    return np.stack((spectrum.real,spectrum.imag),axis=1).reshape(1,4,dim_f,-1).astype(np.float32)

def istft(spectrum,n_fft,hop):
    _,_,dim_f,frames=spectrum.shape
    parts=spectrum.reshape(2,2,dim_f,frames)
    complex_values=parts[:,0]+1j*parts[:,1]
    complex_values=np.pad(complex_values,((0,0),(0,n_fft//2+1-dim_f),(0,0)))
    window=.5-.5*np.cos(2*np.pi*np.arange(n_fft)/n_fft)
    waves=np.fft.irfft(complex_values.transpose(0,2,1),n=n_fft,axis=-1)*window
    output=np.zeros((2,hop*(frames-1)+n_fft));weights=np.zeros(output.shape[1])
    for frame in range(frames):
        start=frame*hop;output[:,start:start+n_fft]+=waves[:,frame];weights[start:start+n_fft]+=window*window
    valid=weights>1e-9;output[:,valid]/=weights[valid]
    return output[:,n_fft//2:-(n_fft//2)]

def isolate(input_path,output_path,progress=lambda _:None):
    sys.path.insert(0,str(ROOT/'PythonDeps'))
    import onnxruntime as ort
    metadata=json.loads((ROOT/'models.json').read_text(encoding='utf-8'))['isolation']
    options=ort.SessionOptions();options.intra_op_num_threads=min(4,os.cpu_count() or 1);options.inter_op_num_threads=1
    session=ort.InferenceSession(str(ROOT/metadata['file']),sess_options=options,providers=['CPUExecutionProvider'])
    channels,rate=audio_levels.read_pcm(input_path);mix=channels.T.astype(np.float32)
    if rate!=44100 or mix.shape[0]!=2:raise ValueError('Formato interno inválido para isolamento de voz.')
    fft=metadata['n_fft'];hop=1024;frames=256;chunk=hop*(frames-1);trim=fft//2;usable=chunk-2*trim
    # Discard edge context, overlap predictions by half a window, then average.
    step=usable//2;length=mix.shape[1];output=np.zeros((2,length),np.float64);weight=np.zeros(length)
    starts=list(range(0,length,step));window=np.hanning(usable+2)[1:-1]
    for index,start in enumerate(starts):
        progress(f'{index+1}/{len(starts)}')
        begin=start-trim;end=begin+chunk
        part=np.pad(mix[:,max(0,begin):min(length,end)],((0,0),(max(0,-begin),max(0,end-length))))
        spec=stft(part,fft,hop,metadata['dim_f']);spec[:,:,:3,:]=0
        positive=session.run(None,{session.get_inputs()[0].name:spec})[0]
        negative=session.run(None,{session.get_inputs()[0].name:-spec})[0]
        predicted=istft((positive-negative)*.5,fft,hop)[:,trim:trim+usable]*metadata['compensate']
        count=min(usable,length-start);output[:,start:start+count]+=predicted[:,:count]*window[:count];weight[start:start+count]+=window[:count]
    output/=np.maximum(weight,1e-12)
    peak=float(np.abs(output).max())
    if peak>=1:output*=.999999999/peak
    write_pcm(output_path,output.T,rate)

def process(source,destination,mode,strength=75,progress=lambda _:None):
    if mode not in ('enhance','isolate'):raise ValueError('Modo de processamento de voz inválido.')
    strength=float(strength)
    if not math.isfinite(strength) or not 0<=strength<=100:raise ValueError('A intensidade deve ficar entre 0 e 100.')
    source=Path(source);destination=Path(destination)
    original,rate=audio_levels.read_pcm(source)
    if not len(original):raise ValueError('O WAV customizado deve conter áudio.')
    if original.shape[1] not in (1,2):raise ValueError('Use áudio mono ou estéreo.')
    if strength==0 or np.max(np.abs(original))==0:
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination);return {'peak_reduction_db':0,'frames':len(original)}
    folder=core.APP/'Cache/VoiceAI'/uuid.uuid4().hex;folder.mkdir(parents=True)
    try:
        input_path=folder/'input.wav';processed=folder/'processed.wav';restored=folder/'restored.wav'
        progress('Preparando áudio...')
        if mode=='enhance':
            resample(source,input_path,48000,original.shape[1],'pcm_s16le')
            progress('Limpando ruído da voz...')
            run([ROOT/'deep-filter.exe','-D','-o',folder/'enhanced',input_path])
            processed=folder/'enhanced/input.wav'
            if not processed.is_file():raise ValueError('O motor de voz não gerou o resultado esperado.')
        else:
            resample(source,input_path,44100,2)
            progress('Separando voz do fundo...')
            # Native model inference stays outside the UI process.
            request=folder/'request.json';request.write_text(json.dumps({'input':str(input_path),'output':str(processed)}),encoding='utf-8')
            run([sys.executable,'-E','-B',Path(__file__),request])
        resample(processed,restored,rate,original.shape[1]);enhanced,_=audio_levels.read_pcm(restored)
        # Delay compensation and fixed-length padding prevent cue timing changes.
        enhanced=enhanced[:len(original)]
        if len(enhanced)<len(original):enhanced=np.pad(enhanced,((0,len(original)-len(enhanced)),(0,0)))
        mixed=original*(1-strength/100)+enhanced*(strength/100)
        peak=float(np.abs(mixed).max());limit=1-1/2147483648
        reduction=max(0,20*math.log10(peak/limit)) if peak>0 else 0
        if peak>limit:mixed*=limit/peak
        write_pcm(destination,mixed,rate)
        return {'peak_reduction_db':reduction,'frames':len(mixed)}
    finally:
        # This folder is created for this invocation, inside the private cache.
        if folder.resolve().is_relative_to((core.APP/'Cache/VoiceAI').resolve()):shutil.rmtree(folder)

if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));isolate(request['input'],request['output'])
