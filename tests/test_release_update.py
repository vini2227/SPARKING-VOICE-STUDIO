"""No game/GUI dependencies: release policy and extraction-over-existing regression tests."""
import sys,tempfile,unittest,zipfile,hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Tools'))
from release_contract import validate_paths

class ReleaseUpdateTests(unittest.TestCase):
 def test_contract_excludes_private_state(self):
  validate_paths(['src/app.py','Data/help_guides.json','Runtime/python.exe','settings.example.json','UPDATE.md'])
  for name in ['settings.json','Projects/project.json','Cache/recovery.json','settings.json/child','keys.json','export_preferences.json','voice_effect_presets.json','project_sequence.json','Reports/log.txt','../settings.json','/settings.json','src/private.wav']:
   with self.assertRaises(ValueError,msg=name):validate_paths([name])
  with self.assertRaises(ValueError):validate_paths(['src/App.py','src/app.py'])
 def test_overlay_keeps_every_user_file_byte_for_byte(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);app=root/'Sparking Zero Voice Studio';app.mkdir()
   private={'settings.json':b'{"ui_language":"pt","game":"existing game"}',
    'export_preferences.json':b'{"mode":"package"}','voice_effect_presets.json':b'{"custom":true}',
    'project_sequence.json':b'{"last_number":23}','recent_projects_preferences.json':b'{"keep":true}',
    'Projects/old/project.json':b'{"bank":"BTLCV_0070_00_US","replacements":{}}',
    'Projects/old/voice.wav':b'unchanged recording','Cache/Recovery/recovery.json':b'unchanged recovery',
    'Exports/old/export.bin':b'unchanged export','Imports/voice.bin':b'unchanged import','keys.json':b'private fixture'}
   for name,data in private.items():p=app/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   (app/'src').mkdir();(app/'src/app.py').write_text('# old app')
   names={'src/app.py':b'# new app','settings.example.json':b'{"ui_language":"en"}','UPDATE.md':b'update guide'}
   validate_paths(names)
   archive=root/'update.zip'
   with zipfile.ZipFile(archive,'w') as z:
    for name,data in names.items():z.writestr(app.name+'/'+name,data)
   with zipfile.ZipFile(archive) as z:z.extractall(root)
   self.assertEqual((app/'src/app.py').read_bytes(),b'# new app')
   for name,data in private.items():self.assertEqual((app/name).read_bytes(),data,name)
 def test_optional_real_release(self):
  archive=os.environ.get('SZVS_RELEASE_ZIP')
  if not archive:self.skipTest('Set SZVS_RELEASE_ZIP to verify an actual build')
  with zipfile.ZipFile(archive) as z:
   self.assertIsNone(z.testzip());prefix='Sparking Zero Voice Studio/'
   names=[name[len(prefix):] for name in z.namelist() if not name.endswith('/')]
   self.assertTrue(all(name.startswith(prefix) for name in z.namelist()))
   validate_paths(names);self.assertNotIn('settings.json',names)
   manifest=json.loads(z.read(prefix+'distribution_manifest.json'))
   for name,info in manifest['files'].items():self.assertEqual(hashlib.sha256(z.read(prefix+name)).hexdigest(),info['sha256'],name)

if __name__=='__main__':unittest.main(verbosity=2)
