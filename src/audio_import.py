"""Decode common audio formats using the already-bundled audio runtime."""
import sys,uuid,wave
from pathlib import Path
import numpy as np
import core
import video_audio

AUDIO_EXTENSIONS=('.wav','.mp3','.flac','.ogg','.aiff','.aif')
EXTENSIONS=AUDIO_EXTENSIONS+video_audio.MEDIA_EXTENSIONS

def convert(source,destination,rate,channels,samples,stream_index=None):
    source=Path(source)
    if source.suffix.lower() in video_audio.MEDIA_EXTENSIONS:
        return video_audio.convert(source,destination,rate,channels,samples,stream_index)
    if source.suffix.lower() not in EXTENSIONS:
        raise ValueError('Formato não suportado. Use WAV, MP3, FLAC, OGG ou AIFF.')
    if not source.is_file():raise ValueError('Arquivo de áudio não encontrado.')
    # Decode integer PCM directly; normalize_wav converts 8/16/24/32-bit inputs to verified PCM16.
    if source.suffix.lower()=='.wav':
        try:
            with wave.open(str(source),'rb') as f:
                pcm=f.getcomptype()=='NONE' and f.getsampwidth() in (1,2,3,4)
        except (wave.Error,EOFError):pcm=False
        if pcm:return core.normalize_wav(source,destination,rate,channels,samples)
    dependency=core.APP/'Tools/PythonDeps'
    if str(dependency) not in sys.path:sys.path.insert(0,str(dependency))
    from pedalboard.io import AudioFile
    work=core.owned(core.APP/'Cache/AudioImport');work.mkdir(parents=True,exist_ok=True)
    temporary=work/(uuid.uuid4().hex+'.wav')
    try:
        try:
            with AudioFile(str(source),'r') as audio:
                if not audio.frames or not audio.num_channels:raise ValueError('O arquivo de áudio está vazio.')
                with wave.open(str(temporary),'wb') as output:
                    output.setparams((audio.num_channels,4,int(audio.samplerate),0,'NONE','not compressed'))
                    while audio.tell()<audio.frames:
                        block=audio.read(min(65536,audio.frames-audio.tell()))
                        if not block.size:break
                        if not np.isfinite(block).all():raise ValueError('O arquivo de áudio contém amostras inválidas.')
                        values=np.asarray(block.T,dtype=np.float64)
                        if float(np.abs(values).max())>1.000001:
                            raise ValueError('O áudio contém picos acima de 0 dBFS. Reduza o volume do arquivo antes de importar.')
                        pcm=np.clip(np.round(values*2147483648),-2147483648,2147483647).astype('<i4')
                        output.writeframes(pcm.tobytes())
        except (RuntimeError,OSError) as error:
            raise ValueError('Não foi possível ler este áudio. Verifique se o arquivo não está corrompido e se usa WAV, MP3, FLAC, OGG ou AIFF.') from error
        return core.normalize_wav(temporary,destination,rate,channels,samples)
    finally:temporary.unlink(missing_ok=True)
