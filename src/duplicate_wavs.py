"""Find identical custom WAV audio, independent of paths and RIFF metadata."""
import hashlib
import struct
import wave
from pathlib import Path


class DuplicateWavs:
    def __init__(self):
        self.cache = {}

    def fingerprint(self, source):
        path = Path(source).resolve()
        stat = path.stat()
        stamp = (stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
        cached = self.cache.get(path)
        if cached and cached[0] == stamp:
            return cached[1]
        digest = hashlib.sha256()
        with wave.open(str(path), 'rb') as audio:
            digest.update(struct.pack('<IIII', audio.getframerate(), audio.getnchannels(),
                                      audio.getsampwidth(), audio.getnframes()))
            remaining = audio.getnframes()
            while remaining:
                count = min(remaining, 65536)
                pcm = audio.readframes(count)
                if len(pcm) != count * audio.getnchannels() * audio.getsampwidth():
                    raise ValueError('Incomplete WAV audio')
                digest.update(pcm)
                remaining -= count
        after = path.stat()
        if stamp != (after.st_mtime_ns, after.st_ctime_ns, after.st_size):
            raise OSError('WAV changed during comparison')
        value = digest.hexdigest()
        self.cache[path] = (stamp, value)
        return value

    def find(self, replacements, valid_keys):
        buckets = {}
        active_paths = set()
        for key in sorted(valid_keys):
            source = replacements.get(key)
            if not source:
                continue
            try:
                active_paths.add(Path(source).resolve())
                signature = self.fingerprint(source)
            except (OSError, ValueError, EOFError, wave.Error):
                continue
            buckets.setdefault(signature, []).append(key)
        self.cache = {path: value for path, value in self.cache.items() if path in active_paths}
        groups = sorted((tuple(keys) for keys in buckets.values() if len(keys) > 1), key=lambda keys: keys[0])
        return {key: (number, members) for number, members in enumerate(groups, 1) for key in members}


ORIGIN_FIELDS=('duplicate_originals','speed_originals','effects_originals','processing_originals','trim_originals')

def origin(key,replacements,histories):
    """Follow preserved processing inputs, never match by filename or duration."""
    current=replacements.get(key);seen=set()
    while current and current not in seen:
        seen.add(current);previous=None
        for field in ORIGIN_FIELDS:
            item=histories.get(field,{}).get(key,{})
            if isinstance(item,dict) and item.get('trimmed')==current:
                candidate=item.get('original')
                if isinstance(candidate,str):
                    import core
                    try:path=core.owned(candidate)
                    except ValueError:continue
                    if path.is_file() and candidate not in seen:
                        previous=candidate;break
        if previous is None:return current
        current=previous
    return replacements.get(key)

def sources(owner):
    import migrated_audio
    histories={name:getattr(owner,name,{}) for name in ORIGIN_FIELDS}
    return {key:origin(key,owner.replacements,histories) for key in owner.replacements
            if migrated_audio.is_replaced(owner,key)}

DERIVED_EDITS={'Alterar velocidade da voz','Aplicar efeitos','Aplicar efeitos em todas as vozes editadas',
               'Cortar áudio','Aprimorar voz','Isolar voz','Maximizar volume','Corrigir clipping',
               'Corrigir clipping automaticamente','Restaurar antes da velocidade','Restaurar antes dos efeitos',
               'Restaurar antes da IA','Restaurar sem corte'}

def preserve_origins(owner,before,label):
    """Pin input identity across derived edits; a fresh import starts a new identity."""
    records=dict(getattr(owner,'duplicate_originals',{}));changed=False
    for key in set(before['replacements'])|set(owner.replacements):
        old=before['replacements'].get(key);new=owner.replacements.get(key)
        if old==new:continue
        if old and new and label in DERIVED_EDITS:
            original=origin(key,before['replacements'],before)
            pinned=before.get('_files',{}).get(original)
            # The immutable undo copy is part of the saved/shared project too.
            if pinned and Path(pinned['backup']).is_file():original=pinned['backup']
            records[key]={'original':original,'trimmed':new}
        else:records.pop(key,None)
        changed=True
    owner.duplicate_originals=records
    return changed
