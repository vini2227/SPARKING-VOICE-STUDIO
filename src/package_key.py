"""Default Sparking ZERO archive key, with an optional user override."""
import json
from pathlib import Path
DEFAULT_PACKAGE_KEY=bytes.fromhex('b2407c45ea7c528738a94c0a25ea8f419de4377628eb30c0ae6a80dd9a9f3ef0')

def encryption_key(cfg):
    path=str(cfg.get('pak_key_file') or '').strip()
    if not path:return DEFAULT_PACKAGE_KEY
    try:
        data=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        value=str(data['00000000-0000-0000-0000-000000000000']).strip()
        result=bytes.fromhex(value.removeprefix('0x').removeprefix('0X'))
        if len(result)!=32:raise ValueError('Invalid key length')
        return result
    except (OSError,ValueError,KeyError,TypeError):
        raise ValueError('Arquivo de chave inválido. Corrija o keys.json ou deixe o campo vazio para usar a chave padrão.') from None
