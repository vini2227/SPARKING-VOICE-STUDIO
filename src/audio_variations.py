"""Fixed tempo variations rendered with the shared pitch-preserving speed engine."""
import tempfile,wave
import numpy as np

# Keep IDs and tuple shape compatible with saved projects and existing callers.
PRESETS={1:(0.0,1.0),2:(0.0,1.10),3:(0.0,0.90)}
CACHE_VERSION='tempo_v3'

def valid(value):
    if isinstance(value,bool) or value not in PRESETS:raise ValueError('Variação de voz inválida.')
    return int(value)

def apply(samples,rate,variation=1):
    variation=valid(variation)
    if variation==1 or not len(samples):return samples
    _,speed=PRESETS[variation]
    frames=max(1,round(len(samples)/speed))
    if not np.abs(samples).any():return np.zeros((frames,samples.shape[1]),dtype=np.float64)
    # A fragment below the overlap window has no usable tempo context. Preserve
    # its samples rather than losing a short grunt or manufacturing a silent tail.
    if len(samples)<round(rate*.05):return samples.copy()
    # Import lazily: core imports this module during startup.
    import core,audio_levels,voice_speed
    parent=core.owned(core.APP/'Cache/Variations');parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tempo_',dir=parent) as temporary:
        from pathlib import Path
        source=Path(temporary)/'source.wav';destination=Path(temporary)/'result.wav'
        pcm=np.clip(np.rint(samples*2147483648),-2147483648,2147483647).astype('<i4').tobytes()
        with wave.open(str(source),'wb') as out:
            out.setparams((samples.shape[1],4,rate,len(samples),'NONE','not compressed'));out.writeframes(pcm)
        voice_speed.render(source,destination,speed,preserve_pitch=True)
        output,output_rate=audio_levels.read_pcm(destination)
    if output_rate!=rate or output.shape[1]!=samples.shape[1] or not np.isfinite(output).all():
        raise ValueError('Falha ao processar a variação de voz.')
    return output
