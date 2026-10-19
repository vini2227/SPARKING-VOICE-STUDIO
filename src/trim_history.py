"""Keep the complete replacement audio separately from derived trimmed WAVs."""
from pathlib import Path
import core

def active(history,replacements):
    result={}
    for key,item in history.items():
        if not isinstance(item,dict):continue
        if item.get('trimmed')!=replacements.get(key):continue
        if not isinstance(item.get('original'),str):continue
        try:path=core.owned(item['original'])
        except ValueError:continue
        if not path.is_file():continue
        result[key]={'original':item['original'],'trimmed':item['trimmed']}
    return result
