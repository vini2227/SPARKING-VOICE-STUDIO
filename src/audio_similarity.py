"""Conservative perceptual hints for row colors only; never a mute decision."""
import wave
import numpy as np

RATE=12000

def read(path):
    with wave.open(str(path),'rb') as f:
        rate=f.getframerate();channels=f.getnchannels();width=f.getsampwidth()
        raw=f.readframes(min(f.getnframes(),rate*120))
    if width==2:data=np.frombuffer(raw,dtype='<i2').astype(float)/32768
    elif width==1:data=(np.frombuffer(raw,dtype=np.uint8).astype(float)-128)/128
    elif width==4:data=np.frombuffer(raw,dtype='<i4').astype(float)/2147483648
    else:raise ValueError('Unsupported PCM width for similarity')
    data=data.reshape(-1,channels).mean(axis=1)
    if len(data) and rate!=RATE:
        data=np.interp(np.arange(round(len(data)*RATE/rate))*rate/RATE,np.arange(len(data)),data)
    # Remove tiny edge padding, leaving breathing and the body of the sound intact.
    if len(data):
        peak=np.max(np.abs(data));active=np.flatnonzero(np.abs(data)>max(1e-5,peak*.005))
        if len(active):data=data[max(0,active[0]-120):min(len(data),active[-1]+121)]
    return data

def spectrum(x):
    if len(x)<240:x=np.pad(x,(0,240-len(x)))
    frames=np.lib.stride_tricks.sliding_window_view(x,240)[::120]
    power=np.abs(np.fft.rfft(frames*np.hanning(240),n=512))**2
    # Time-averaged log frequency bands distinguish timbre, while tolerating coding noise.
    edges=np.unique(np.geomspace(2,257,33).astype(int))
    values=np.array([np.mean(power[:,a:b]) for a,b in zip(edges[:-1],edges[1:])])
    values=np.log(np.maximum(values,1e-12));values-=values.mean()
    return values

def compare(a,b):
    x=read(a);y=read(b)
    ex=float(np.dot(x,x));ey=float(np.dot(y,y))
    silent_x=ex/max(1,len(x))<1e-9;silent_y=ey/max(1,len(y))<1e-9
    if silent_x or silent_y:
        return {'status':'similar' if silent_x and silent_y else 'different','correlation':1.0 if silent_x and silent_y else 0.0,'spectral_similarity':None,'duration_ratio':None}
    ratio=min(len(x),len(y))/max(len(x),len(y))
    # FFT alignment within 150 ms; score remains penalized for missing/different content.
    size=1<<(len(x)+len(y)-1).bit_length()
    cross=np.fft.irfft(np.fft.rfft(x,size)*np.conj(np.fft.rfft(y,size)),size)
    lag=min(1800,len(x)-1,len(y)-1)
    corr=float(np.max(np.abs(np.concatenate((cross[:lag+1],cross[-lag:] if lag else []))))/np.sqrt(ex*ey))
    corr=min(1.0,corr)
    sx=spectrum(x);sy=spectrum(y)
    spectral=float(np.dot(sx,sy)/max(1e-12,np.linalg.norm(sx)*np.linalg.norm(sy)))
    if ratio>=.94 and corr>=.96 and spectral>=.94:status='similar'
    elif (corr<.40 and spectral<.86) or (ratio<.65 and corr<.70):status='different'
    else:status='uncertain'
    return {'status':status,'correlation':round(corr,5),'spectral_similarity':round(spectral,5),'duration_ratio':round(ratio,5)}
