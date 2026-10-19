"""Unsaved gain edits for one live bank, using the actual export processing."""
import math
import numpy as np
import core,audio_levels,project_audio

TARGET_DBFS=-1.0

def gain_limit(peak):
    if peak is None:return None
    allowed=math.floor((TARGET_DBFS-peak)*10+1e-8)/10
    return max(audio_levels.MIN_GAIN,min(audio_levels.MAX_GAIN,allowed))

def adjust(bank,replacements,gains,variations,keep,mode,selected=None,progress=lambda value:None):
    if mode not in ('correct','maximize'):raise ValueError('Ajuste de volume inválido.')
    replacements=dict(replacements);gains=dict(gains)
    rows=[bank.wave_rows[selected]] if selected is not None else list(bank.rows)
    result={'replacements':replacements,'gains':gains,'changed':0,'silent':0,'muted':0,'limited':0,'errors':[],'examined':0}
    for position,row in enumerate(rows):
        key=row['key'];path=replacements.get(key)
        # Batch adjustments include only explicit replacements and confirmed custom
        # audio from external banks; preservation policy does not make audio custom.
        if selected is None and not project_audio.is_edited(bank,row,replacements):
            if path is None and not core.preserve_unreplaced(bank,row,keep):result['muted']+=1
            continue
        progress(f'{position+1}/{len(rows)} • '+row['filename'])
        try:
            path=path or str(bank.original(row))
            # Includes resampling, channel conversion and the chosen voice variation,
            # measured before PCM quantization/clamping can hide an overshoot.
            samples,rate,duration=core.prepare_wav_samples(path,row['rate'],row['channels'],variations.get(key,1))
            peak=audio_levels.db(float(np.abs(samples).max()))
            raw_peak=audio_levels.analyze(path)['peak_dbfs']
            # The export also checks the input peak, so satisfy both stages.
            peak=max((value for value in (peak,raw_peak) if value is not None),default=None)
            result['examined']+=1
            if peak is None:result['silent']+=1;continue
            ceiling=gain_limit(peak);current=audio_levels.valid_gain(gains.get(key,0))
            target=min(current,ceiling) if mode=='correct' else ceiling
            if mode=='maximize' and ceiling==audio_levels.MAX_GAIN and peak+ceiling<TARGET_DBFS-.1:result['limited']+=1
            if abs(target-current)<1e-8:continue
            replacements[key]=str(path)
            if target:gains[key]=target
            else:gains.pop(key,None)
            result['changed']+=1
        except Exception as error:result['errors'].append({'key':key,'error':str(error)})
    return result
