"""Verified identity of migrated WAV copies; export inputs stay preserved."""
from pathlib import Path
import wave
import core

def stamp(source):
    path = Path(source).resolve()
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)

def classify(project, bank):
    # Run on the bank-loading worker, never decode audio on the Tk thread.
    originals = {}
    if not project or not project.get('migration') or bank.external:
        return originals
    for key, source in project.get('replacements', {}).items():
        row = bank.wave_rows.get(key)
        if row is None:
            continue
        try:
            before = stamp(source)
            if core.same_pcm(source, bank.original(row)) and stamp(source) == before:
                originals[key] = before
        except (OSError, ValueError, RuntimeError, EOFError, wave.Error):
            # An unavailable comparison never hides a possible replacement.
            continue
    return originals

def is_original(owner, key):
    verified = getattr(owner, 'migrated_original_audio', {}).get(key)
    source = owner.replacements.get(key)
    if not verified or not source:
        return False
    if owner.gains.get(key, 0) != 0 or owner.variations.get(key, 1) != 1:
        return False
    try:
        return stamp(source) == verified
    except OSError:
        return False

def is_replaced(owner, key):
    return key in owner.replacements and not is_original(owner, key)
