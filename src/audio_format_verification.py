"""High quality resampling and independent WAV/HCA/ACB format verification."""
import os,subprocess,wave
from pathlib import Path
import numpy as np

def resample(values,source_rate,target_rate):
    if source_rate==target_rate:return values
    channels=values.shape[1]
    if not (8000<=source_rate<=192000 and 8000<=target_rate<=192000):
        raise ValueError('Formato do áudio exportado inválido.')
    tool=Path(__file__).resolve().parents[1]/'Tools/FFmpeg/bin/ffmpeg.exe'
    if not tool.is_file():raise ValueError('O FFmpeg incluído no app não foi encontrado. Reinstale a pasta Tools/FFmpeg.')
    arguments=[str(tool),'-nostdin','-v','error','-protocol_whitelist','pipe',
        '-f','f64le','-ar',str(source_rate),'-ac',str(channels),'-i','pipe:0',
        '-af','aresample='+str(target_rate)+':filter_size=64:phase_shift=10:cutoff=0.97:internal_sample_fmt=dblp',
        '-ar',str(target_rate),'-ac',str(channels),'-c:a','pcm_f64le','-f','f64le','pipe:1']
    try:
        process=subprocess.run(arguments,input=np.ascontiguousarray(values,dtype='<f8').tobytes(),
            capture_output=True,timeout=180,creationflags=0x08000000 if os.name=='nt' else 0)
    except subprocess.TimeoutExpired as error:raise ValueError('Falha ao converter a frequência do áudio.') from error
    if process.returncode or not process.stdout or len(process.stdout)%(8*channels):raise ValueError('Falha ao converter a frequência do áudio.')
    output=np.frombuffer(process.stdout,dtype='<f8').reshape(-1,channels).copy()
    frames=max(1,round(len(values)*target_rate/source_rate))
    output=output[:frames] if len(output)>=frames else np.pad(output,((0,frames-len(output)),(0,0)))
    if not np.isfinite(output).all():raise ValueError('Falha ao converter a frequência do áudio.')
    # Filter ringing must not introduce clipping that was absent in the source.
    peak=float(np.abs(values).max());result_peak=float(np.abs(output).max())
    if result_peak>peak:output*=peak/result_peak
    return output

def wav_format(path,row):
    with wave.open(str(path),'rb') as audio:
        actual=(audio.getframerate(),audio.getnchannels(),audio.getnframes())
        pcm16=audio.getcomptype()=='NONE' and audio.getsampwidth()==2
        complete=len(audio.readframes(actual[2]))==actual[2]*actual[1]*audio.getsampwidth()
    if actual[:2]!=(row['rate'],row['channels']) or not pcm16 or not complete or actual[2]<=0:
        raise ValueError('Os formatos do áudio exportado não correspondem: '+f"WAV={actual}; ACB=({row['rate']}, {row['channels']})")
    return actual

def hca_format(payload,row,samples=None,tolerance=0):
    import bank_migration
    try:actual=bank_migration.hca_format(payload)
    except ValueError as error:raise ValueError('Formato do áudio exportado inválido.') from error
    expected=(row['rate'],row['channels'],row['samples'] if samples is None else samples)
    if actual[:2]!=expected[:2] or abs(actual[2]-expected[2])>tolerance:
        raise ValueError('Os formatos do áudio exportado não correspondem: '+f"{row['key']}: HCA={actual}; ACB={expected}")
    return actual
