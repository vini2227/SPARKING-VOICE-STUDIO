"""Audio-only extraction from local media using bundled FFmpeg executables."""
import json,subprocess,uuid
from pathlib import Path
import core

VIDEO_EXTENSIONS=('.mp4','.mkv','.mov','.avi','.webm','.m4v','.wmv','.mpeg','.mpg','.ts','.m2ts','.3gp')
EXTRA_AUDIO=('.m4a','.aac','.opus','.wma')
MEDIA_EXTENSIONS=VIDEO_EXTENSIONS+EXTRA_AUDIO

def tool(name):
    path=core.APP/'Tools/FFmpeg/bin'/(name+'.exe')
    if not path.is_file():raise ValueError('O FFmpeg incluído no app não foi encontrado. Reinstale a pasta Tools/FFmpeg.')
    return path

def run(arguments,timeout):
    arguments,options=core.cpu_jobs.subprocess_options(arguments)
    try:
        result=subprocess.run(arguments,capture_output=True,
            creationflags=core.CREATE_NO_WINDOW,timeout=timeout,**options)
    except subprocess.TimeoutExpired as error:raise ValueError('A leitura do vídeo demorou demais. Tente um arquivo menor.') from error
    if result.returncode:raise ValueError('Não foi possível ler o áudio deste arquivo. Ele pode estar corrompido ou usar um codec não suportado.')
    return result.stdout

def tracks(source):
    source=Path(source).resolve()
    if not source.is_file():raise ValueError('Arquivo de áudio ou vídeo não encontrado.')
    output=run([tool('ffprobe'),'-v','error','-protocol_whitelist','file,pipe','-select_streams','a',
        '-show_entries','stream=index,codec_name,sample_rate,channels:stream_tags=language,title:stream_disposition=default',
        '-of','json',source],30)
    streams=json.loads(output).get('streams',[])
    if not streams:raise ValueError('Este vídeo não contém nenhuma faixa de áudio.')
    result=[]
    for stream in streams:
        tags=stream.get('tags',{})
        result.append({'index':int(stream['index']),'codec':stream.get('codec_name','—'),
            'channels':int(stream.get('channels',0)),'rate':int(stream.get('sample_rate',0)),
            'language':tags.get('language',''),'title':tags.get('title',''),
            'default':bool(stream.get('disposition',{}).get('default'))})
    return result

def convert(source,destination,rate,channels,samples,stream_index=None):
    available=tracks(source)
    if stream_index is None:stream_index=next((item['index'] for item in available if item['default']),available[0]['index'])
    if stream_index not in {item['index'] for item in available}:raise ValueError('A faixa de áudio escolhida não existe neste vídeo.')
    temporary=core.owned(core.APP/'Cache/AudioImport'/(uuid.uuid4().hex+'.wav'));temporary.parent.mkdir(parents=True,exist_ok=True)
    try:
        # Explicit mapping selects one audio track; video, subtitles and other streams
        # are neither decoded nor copied into the voice project.
        run([tool('ffmpeg'),'-nostdin','-hide_banner','-loglevel','error','-y',
            '-protocol_whitelist','file,pipe','-i',Path(source).resolve(),'-map',f'0:{stream_index}',
            '-vn','-sn','-dn','-ac',str(channels),'-c:a','pcm_s32le',temporary],300)
        result=core.normalize_wav(temporary,destination,rate,channels,samples)
        result['audio_stream_index']=stream_index
        return result
    finally:temporary.unlink(missing_ok=True)
