"""PCM level measurements and reversible gain. dBFS, not calibrated acoustic dB."""
import math
import wave
import numpy as np

MIN_GAIN=-48.0
MAX_GAIN=24.0

def read_pcm(path):
    with wave.open(str(path),'rb') as w:
        if w.getcomptype()!='NONE':raise ValueError('Use um WAV PCM sem compressão.')
        bits=w.getsampwidth();channels=w.getnchannels();rate=w.getframerate();frames=w.getnframes();raw=w.readframes(frames)
        if len(raw)!=frames*channels*bits:raise ValueError('Áudio incompleto.')
    if bits==1:a=(np.frombuffer(raw,dtype=np.uint8).astype(np.float64)-128)/128
    elif bits==2:a=np.frombuffer(raw,dtype='<i2').astype(np.float64)/32768
    elif bits==3:
        u=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
        a=u[:,0]|u[:,1]<<8|u[:,2]<<16;a=np.where(a&0x800000,a-0x1000000,a).astype(np.float64)/8388608
    elif bits==4:a=np.frombuffer(raw,dtype='<i4').astype(np.float64)/2147483648
    else:raise ValueError('Formato PCM não suportado.')
    return a.reshape(-1,channels),rate

def db(amplitude):
    return 20*math.log10(amplitude) if amplitude>0 else None

def analyze(path):
    a,rate=read_pcm(path)
    if not len(a):raise ValueError('O WAV customizado deve conter áudio.')
    power=np.mean(a*a,axis=1)
    block=max(1,round(rate*.05));starts=np.arange(0,len(a),block)
    sizes=np.minimum(block,len(a)-starts);sums=np.add.reduceat(power,starts);means=sums/sizes
    # Relative -40 dB gate with a -60 dBFS floor excludes pauses; this is not LUFS.
    gate=max(1e-6,float(means.max())*1e-4);active=means>=gate
    active_rms=math.sqrt(float(sums[active].sum()/sizes[active].sum())) if active.any() else 0.0
    return {'peak_dbfs':db(float(np.abs(a).max())), 'rms_dbfs':db(math.sqrt(float(power.mean()))),
            'active_dbfs':db(active_rms),'samples':len(a),'rate':rate,'channels':a.shape[1],'duration':len(a)/rate}

def valid_gain(value):
    gain=float(value)
    if not math.isfinite(gain) or not MIN_GAIN<=gain<=MAX_GAIN:
        raise ValueError('O ganho deve ficar entre -48 e +24 dB.')
    return gain

def apply_gain(samples,gain_db):
    gain=valid_gain(gain_db)
    result=samples*(10**(gain/20)) if gain else samples
    if gain>0 and len(result) and float(np.abs(result).max())>32767/32768+1e-10:
        raise ValueError('O ganho causa clipping. Reduza o volume ou use Igualar ao original.')
    return result

def matching_gain(reference,source):
    target=reference.get('active_dbfs');level=source.get('active_dbfs');peak=source.get('peak_dbfs')
    if target is None or level is None or peak is None:
        raise ValueError('Não há fala ativa suficiente para igualar os volumes.')
    desired=target-level
    # One dB sample-peak headroom. Floor to tenths so rounding never exceeds it.
    limited=max(MIN_GAIN,min(MAX_GAIN,desired,-1.0-peak))
    return math.floor(limited*10+1e-9)/10
