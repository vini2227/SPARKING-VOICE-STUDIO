"""Local offline voice effects. Preserve source format/duration and optional effect tail."""
import math,sys
import numpy as np
import core,audio_levels,voice_ai

DEFAULT={'reverb':0,'echo':0,'echo_ms':280,'pitch':0,'bass':0,'treble':0,'double':0,'distortion':0,'radio':0,'mix':100,'tail':True}
PRESETS={
 'Personalizado':DEFAULT,
 'Sem efeitos':DEFAULT,
 'Voz divina':dict(DEFAULT,reverb=48,echo=15,pitch=-2,double=22),
 'Fusão':dict(DEFAULT,double=65,pitch=-1,bass=3,reverb=12),
 'Monstro':dict(DEFAULT,pitch=-6,bass=5,double=35,distortion=25),
 'Comunicador':dict(DEFAULT,radio=80,distortion=8,echo=8,echo_ms=110),
 'Herói':dict(DEFAULT,bass=2,treble=2,reverb=10),
 'Vilão':dict(DEFAULT,pitch=-3,bass=4,reverb=20,double=18),
 'Robô':dict(DEFAULT,double=50,radio=45,distortion=18,pitch=-1),
 'Eco dramático':dict(DEFAULT,echo=20,echo_ms=240,reverb=25),
 'Voz grave':dict(DEFAULT,pitch=-4,bass=3),
 'Voz aguda':dict(DEFAULT,pitch=4,treble=2)}
LIMITS={'reverb':(0,100),'echo':(0,100),'echo_ms':(80,800),'pitch':(-12,12),'bass':(-12,12),'treble':(-12,12),'double':(0,100),'distortion':(0,100),'radio':(0,100),'mix':(0,100)}

def validated(settings):
 result=dict(DEFAULT)
 for key,(low,high) in LIMITS.items():
  value=float(settings.get(key,result[key]))
  if not math.isfinite(value) or not low<=value<=high:raise ValueError('Parâmetro de efeito inválido: '+key)
  result[key]=value
 result['tail']=bool(settings.get('tail',True));return result

def render(source,destination,settings):
 settings=validated(settings)
 dependency=str(core.APP/'Tools/PythonDeps')
 if dependency not in sys.path:sys.path.insert(0,dependency)
 import pedalboard as p
 values,rate=audio_levels.read_pcm(source)
 if not len(values) or len(values)>rate*60*20:raise ValueError('Use áudio de até 20 minutos para os efeitos.')
 length=len(values);original=values.T.astype(np.float32)
 echo=settings['echo']/100;reverb=settings['reverb']/100
 tail=0
 if settings['tail'] and settings['mix'] and (echo or reverb):
  if echo:tail=settings['echo_ms']/1000*math.ceil(math.log(1e-5)/math.log(.2+.45*echo))
  if reverb:tail=max(tail,2+20*reverb)
 tail=min(30,tail)
 padded=np.pad(original,((0,0),(0,math.ceil(rate*tail))))
 chain=[]
 if settings['pitch']:chain.append(p.PitchShift(semitones=settings['pitch']))
 if settings['bass']:chain.append(p.LowShelfFilter(cutoff_frequency_hz=min(180,rate*.1),gain_db=settings['bass']))
 if settings['treble']:chain.append(p.HighShelfFilter(cutoff_frequency_hz=min(3500,rate*.35),gain_db=settings['treble']))
 processed=p.Pedalboard(chain)(padded,rate) if chain else padded.copy()
 if processed.shape!=padded.shape:raise ValueError('O processamento alterou a duração inesperadamente.')
 if settings['radio']:
  radio=p.Pedalboard([p.HighpassFilter(cutoff_frequency_hz=min(350,rate*.1)),p.LowpassFilter(cutoff_frequency_hz=min(3200,rate*.35))])(processed,rate)
  amount=settings['radio']/100;processed=processed*(1-amount)+radio*amount
 if settings['double']:
  second=p.PitchShift(semitones=.18)(processed,rate)
  delayed=np.zeros_like(processed);delay=min(math.ceil(.035*rate),processed.shape[1])
  if delay<processed.shape[1]:delayed[:,delay:]=second[:,:-delay]
  amount=settings['double']/100*.65;processed=(processed+delayed*amount)/(1+amount)
 if settings['distortion']:
  amount=settings['distortion']/100;drive=1+amount*9
  distorted=np.tanh(processed*drive)/drive
  processed=processed*(1-amount)+distorted*amount
 spatial=[]
 if echo:spatial.append(p.Delay(delay_seconds=settings['echo_ms']/1000,feedback=.2+.45*echo,mix=.55*echo))
 if reverb:spatial.append(p.Reverb(room_size=.15+.75*reverb,damping=.45,wet_level=.65*reverb,dry_level=1-.35*reverb,width=1))
 if spatial:processed=p.Pedalboard(spatial)(processed,rate)
 amount=settings['mix']/100;processed=padded*(1-amount)+processed*amount
 if tail:
  audible=np.where(np.max(np.abs(processed),axis=0)>1e-5)[0]
  end=max(length,min(processed.shape[1],int(audible[-1])+1+math.ceil(.04*rate))) if len(audible) else length
  processed=processed[:,:end]
 else:processed=processed[:,:length]
 if not np.isfinite(processed).all():raise ValueError('O processamento gerou áudio inválido.')
 peak=float(np.max(np.abs(processed)));attenuation=max(1.,peak/(1-1/2147483648))
 if attenuation>1:processed/=attenuation
 voice_ai.write_pcm(destination,processed.T,rate)
 return {'frames':processed.shape[1],'source_frames':length,'rate':rate,'channels':values.shape[1],'tail_seconds':max(0,(processed.shape[1]-length)/rate),'attenuation_db':20*math.log10(attenuation)}


def safe_gain(source,row,gain,variation=1):
 """Reduce only an unsafe gain; account for the actual export format/variation."""
 gain=audio_levels.valid_gain(gain)
 samples,_,_=core.prepare_wav_samples(source,row['rate'],row['channels'],variation)
 original,_=audio_levels.read_pcm(source)
 peak=max(float(np.max(np.abs(samples))) if len(samples) else 0.,float(np.max(np.abs(original))) if len(original) else 0.)
 ceiling=32767/32768
 if not peak or peak*10**(gain/20)<=ceiling:return gain
 allowed=math.floor(20*math.log10(ceiling/peak)*10)/10
 return audio_levels.valid_gain(min(gain,allowed))
