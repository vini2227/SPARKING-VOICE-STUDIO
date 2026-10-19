"""Stage a whole edited-bank effect operation before changing the project state."""
from pathlib import Path
import shutil,uuid
import core,project_audio,trim_history,voice_effects

def edited_rows(bank,replacements):
 return [row for row in bank.rows if project_audio.is_edited(bank,row,replacements)]

def stage(bank,project,replacements,originals,settings,progress=lambda _:None,gains=None,variations=None):
 rows=edited_rows(bank,replacements)
 if not rows:raise ValueError('Não há áudios editados neste banco.')
 settings=voice_effects.validated(settings)
 root=core.owned(Path(project)/'Replacements/EffectsBatch')
 folder=root/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=False)
 prior=trim_history.active(originals,replacements);new={};history={};safe_gains={};gains=gains or {};variations=variations or {}
 try:
  for index,row in enumerate(rows):
   key=row['key'];progress(f'{index+1}/{len(rows)}')
   source=Path(replacements[key]) if key in replacements else bank.original(row)
   if key in prior:original=Path(prior[key]['original'])
   else:
    original=folder/(key+'_before.wav');shutil.copy2(source,original)
   destination=folder/(key+'.wav');voice_effects.render(source,destination,settings)
   safe_gains[key]=voice_effects.safe_gain(destination,row,gains.get(key,0),variations.get(key,1))
   new[key]=str(destination);history[key]={'original':str(original),'trimmed':str(destination)}
 except Exception:
  if folder.resolve().is_relative_to(root.resolve()):shutil.rmtree(folder)
  raise
 return {'replacements':new,'originals':history,'count':len(rows),'folder':str(folder),'gains':safe_gains}
