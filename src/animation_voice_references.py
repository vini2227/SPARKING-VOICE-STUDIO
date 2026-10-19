"""Exact animation notify -> Atom Cue -> cue-sheet relationships; no inference from filenames."""
import hashlib,re

def animation_hits(game,relative,index=0,seen=None,report=None):
 seen=set() if seen is None else seen
 marker=(relative,index)
 if marker in seen or len(seen)>32:return []
 seen=seen|{marker};hits=[]
 try:
  pkg,cls,obj,tail=game.properties(relative,index)
  if cls not in ('AnimMontage','AnimSequence','AnimComposite'):return []
  source_hash=hashlib.sha256(pkg['bytes']).hexdigest()
  for i,notify in enumerate(obj.get('Notifies') or []):
   ptr=notify.get('Notify')
   if not ptr:continue
   ref=game.resolve(pkg,ptr)
   if not ref or 'relative' not in ref:continue
   np=game.package(ref['relative']);nc=game.resolve_global(np,np['exports'][ref['export']]['class_index'])
   if not nc or nc.get('script') not in ('SSAnimNotifyKoratPlaySound','AnimNotify_PlaySound'):continue
   np,ncls,nobj,_=game.properties(ref['relative'],ref['export']);sound=game.resolve(np,nobj.get('Sound'))
   if not sound or 'relative' not in sound:continue
   sp,scls,sobj,_=game.properties(sound['relative'],sound['export'])
   if scls!='SoundAtomCue':continue
   cue=sobj.get('CueName');sheet=game.resolve(sp,sobj.get('CueSheet'))
   if not re.fullmatch(r'\d{4}_\d{2}_\d{4}',cue or '') or not sheet or 'relative' not in sheet:continue
   path=sheet['relative'];bank=path.rsplit('/',1)[-1].removesuffix('.uasset')
   if not re.fullmatch(r'SS/Sounds/Battle_VOICE/(JP|US)/BTLCV_\d{4}_\d{2}(?:_[A-Z])?_(JP|US)\.uasset',path) or not bank.endswith('_'+path.split('/')[-2]):continue
   sources={relative:source_hash,ref['relative']:hashlib.sha256(np['bytes']).hexdigest(),sound['relative']:hashlib.sha256(sp['bytes']).hexdigest()}
   hits.append({'cue_name':cue,'bank':bank,'source_kind':'animation_notify','notify_name':notify.get('NotifyName') or ncls,'notify_time':notify.get('LinkValue'),'native_animation_bytes_unread':tail,'source_hashes':sources,'chain':[relative,ref['relative'],sound['relative'],path],'root':relative,'child':sound['relative']})
  tracks=obj.get('SlotAnimTracks') or []
  segments=(obj.get('AnimationTrack') or {}).get('AnimSegments') or []
  for track in tracks:segments+=(track.get('AnimTrack') or {}).get('AnimSegments') or []
  for segment in segments:
   ptr=segment.get('AnimReference')
   if not isinstance(ptr,int) or not ptr:continue
   ref=game.resolve(pkg,ptr)
   if not ref or 'relative' not in ref:continue
   for hit in animation_hits(game,ref['relative'],ref['export'],seen,report):
    hit=dict(hit,chain=[relative]+hit['chain'],source_hashes=dict(hit['source_hashes'],**{relative:source_hash}));hits.append(hit)
 except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:
  if report is not None:report.append({'asset':relative,'error':str(exc)})
 return hits
