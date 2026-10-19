"""Local voice tempo using waveform overlap; natural speed uses resampling."""
import math,shutil,wave,tempfile
from pathlib import Path
import numpy as np
import core,audio_levels,video_audio

def valid(value):
    if isinstance(value,bool):raise ValueError('Use uma velocidade entre 0.25x e 3.00x.')
    try:factor=float(value)
    except (TypeError,ValueError):raise ValueError('Use uma velocidade entre 0.25x e 3.00x.') from None
    if not math.isfinite(factor) or not .25<=factor<=3:raise ValueError('Use uma velocidade entre 0.25x e 3.00x.')
    return factor

def tempo_filters(factor):
    # Keep every stage in [0.5, 2] to blend rather than skip waveform samples.
    stages=[]
    while factor<.5:stages.append(.5);factor/=.5
    while factor>2:stages.append(math.sqrt(factor));factor=math.sqrt(factor)
    stages.append(factor)
    return ','.join('atempo='+format(value,'.12g') for value in stages)

def render(source,destination,factor=1,preserve_pitch=True):
    factor=valid(factor);destination=core.owned(destination)
    values,rate=audio_levels.read_pcm(source)
    if not len(values) or len(values)>rate*60*20:raise ValueError('Use áudio de até 20 minutos para os efeitos.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    if factor==1:
        shutil.copy2(source,destination)
        return {'before':len(values)/rate,'after':len(values)/rate}
    frames=max(1,round(len(values)/factor));peak=float(np.abs(values).max());channels=values.shape[1]
    if peak:
        resample=':filter_size=64:phase_shift=10:cutoff=0.97:internal_sample_fmt=dblp'
        if preserve_pitch:
            # Process at the original sample rate, matching the reference waveform.
            # Keep the native overlap duration instead of adding silence or cutting a tail.
            filters=tempo_filters(factor)
        else:
            # Natural rate/pitch change needs no pitch shifting or formant processing.
            filters='asetrate='+str(round(rate*factor))+',aresample='+str(rate)+resample
        with tempfile.TemporaryDirectory(prefix='speed_',dir=destination.parent) as tmp:
            raw=Path(tmp)/'processed.wav'
            video_audio.run([video_audio.tool('ffmpeg'),'-nostdin','-v','error','-y','-protocol_whitelist','file,pipe',
                '-i',str(source),'-map','0:a:0','-af',filters,'-ar',str(rate),'-ac',str(channels),'-c:a','pcm_s32le',str(raw)],timeout=900)
            output,output_rate=audio_levels.read_pcm(raw)
            if output_rate!=rate or output.shape[1]!=channels or not len(output):raise ValueError('Falha ao processar a variação de voz.')
        if preserve_pitch:frames=len(output)
        else:output=output[:frames] if len(output)>=frames else np.pad(output,((0,frames-len(output)),(0,0)))
        if not np.isfinite(output).all():raise ValueError('Falha ao processar a variação de voz.')
        result_peak=float(np.abs(output).max())
        if result_peak>peak:output*=peak/result_peak
    else:output=np.zeros((frames,channels),dtype=np.float64)
    pcm=np.clip(np.rint(output*2147483648),-2147483648,2147483647).astype('<i4').tobytes()
    with wave.open(str(destination),'wb') as out:
        out.setparams((channels,4,rate,frames,'NONE','not compressed'));out.writeframes(pcm)
    return {'before':len(values)/rate,'after':frames/rate}
