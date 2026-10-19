"""Load legacy manifests through the real project-open entry point without GUI/game writes."""
import sys,tempfile,json,wave,unittest,hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
if sys.platform=='win32':
 import app,core

@unittest.skipUnless(sys.platform=='win32','The application is Windows-only')
class LegacyProjectTests(unittest.TestCase):
 def test_missing_settings_uses_english_without_creating_file(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(core,'APP',Path(tmp)):
   self.assertEqual(core.config()['ui_language'],'en');self.assertEqual(core.config()['game'],'')
   self.assertFalse((Path(tmp)/'settings.json').exists())
 def test_legacy_and_current_optional_fields(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(core,'APP',Path(tmp)):
   root=Path(tmp)
   for schema in (None,1,2,3,4,5,6):
    folder=root/'Projects'/('old project '+str(schema));folder.mkdir(parents=True)
    audio=folder/'voice.wav'
    with wave.open(str(audio),'wb') as out:out.setparams((1,2,24000,100,'NONE','not compressed'));out.writeframes(b'\0\0'*100)
    data={'bank':'BTLCV_0070_00_US','replacements':{'S1':str(audio)},'export_name':'BTLCV_4177_44_US','project_name':'Legacy project','unknown_preserved_field':{'value':3}}
    if schema is not None:data['schema']=schema
    if schema is not None and schema>=2:data.update(gains={'S1':-2},variations={'S1':2})
    if schema is not None and schema>=5:
     for field in ('trim_originals','processing_originals','effects_originals','speed_originals','duplicate_originals'):data[field]={'S1':{'original':str(audio),'trimmed':str(audio)}}
    path=folder/'project.json';path.write_text(json.dumps(data),encoding='utf-8');before=path.read_bytes();pcm=audio.read_bytes()
    owner=SimpleNamespace(busy=False,banks=[data['bank']],load_bank=Mock(),fail=Mock())
    app.Studio.open_project_path(owner,path)
    owner.fail.assert_not_called();owner.load_bank.assert_called_once()
    loaded=owner.load_bank.call_args.args[1]
    for key,value in data.items():self.assertEqual(loaded[key],value)
    self.assertEqual(path.read_bytes(),before);self.assertEqual(audio.read_bytes(),pcm)
 def test_missing_audio_reports_error_without_rewriting_manifest(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(core,'APP',Path(tmp)):
   path=Path(tmp)/'project.json';path.write_text(json.dumps({'bank':'BTLCV_0070_00_US','replacements':{'S1':str(Path(tmp)/'missing.wav')}}));before=path.read_bytes()
   owner=SimpleNamespace(busy=False,banks=['BTLCV_0070_00_US'],load_bank=Mock(),fail=Mock())
   app.Studio.open_project_path(owner,path);owner.fail.assert_called_once();owner.load_bank.assert_not_called();self.assertEqual(before,path.read_bytes())

if __name__=='__main__':unittest.main(verbosity=2)
