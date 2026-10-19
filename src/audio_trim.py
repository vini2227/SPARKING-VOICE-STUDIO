"""Frame-exact PCM trimming: retained samples are copied without envelopes."""
import math,wave
from pathlib import Path
import core

def seconds(value):
    try:value=float(str(value).strip().replace(',','.'))
    except (TypeError,ValueError):raise ValueError('Informe tempos válidos, em segundos, maiores ou iguais a zero.')
    if not math.isfinite(value) or value<0:raise ValueError('Informe tempos válidos, em segundos, maiores ou iguais a zero.')
    return value

def bounds(frames,rate,start,end):
    start=seconds(start);end=seconds(end)
    if start+end>=frames/rate:raise ValueError('O corte precisa deixar pelo menos uma amostra de áudio.')
    start=round(start*rate);end=round(end*rate)
    if start+end>=frames:raise ValueError('O corte precisa deixar pelo menos uma amostra de áudio.')
    if start+end==0:raise ValueError('Defina um corte no começo e/ou no fim.')
    return start,frames-end

def trim(source,destination,start,end):
    source=Path(source);destination=core.owned(destination)
    if source.resolve()==destination.resolve():raise ValueError('O arquivo de origem deve ser preservado.')
    # Validate before creating any output. The UI always supplies a unique name.
    with wave.open(str(source),'rb') as reader:
        begin,finish=bounds(reader.getnframes(),reader.getframerate(),start,end)
        params=reader.getparams();rate=reader.getframerate()
        destination.parent.mkdir(parents=True,exist_ok=True)
        try:
            with destination.open('xb') as handle:
                with wave.open(handle,'wb') as writer:
                    writer.setparams(params);reader.setpos(begin);remaining=finish-begin
                    while remaining:
                        count=min(65536,remaining);data=reader.readframes(count)
                        if len(data)!=count*params.sampwidth*params.nchannels:raise ValueError('Áudio incompleto.')
                        writer.writeframesraw(data);remaining-=count
        except FileExistsError:raise
        except Exception:
            destination.unlink(missing_ok=True);raise
    return {'frames':finish-begin,'rate':rate,'duration':(finish-begin)/rate}
