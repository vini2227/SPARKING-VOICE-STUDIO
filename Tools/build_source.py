"""Build a source-only, privacy-checked GitHub preparation snapshot."""
from pathlib import Path
import ast,datetime,hashlib,json,re,shutil,zipfile

APP=Path(__file__).resolve().parents[1]
def build():
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 parent=APP/'Distribution'/('Source_'+stamp);root=parent/'SparkingZeroVoiceStudio';root.mkdir(parents=True)
 ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pdb','voice_research_ui.py','voice_diagnostics.py')
 shutil.copytree(APP/'src',root/'src',ignore=ignore)
 (root/'Data').mkdir()
 def clean(value):
  if isinstance(value,dict):return {key:clean(item) for key,item in value.items()}
  if isinstance(value,list):return [clean(item) for item in value]
  if isinstance(value,str):
   if re.match(r'^[A-Za-z]:[\\/]',value):return re.split(r'[\\/]',value)[-1]
   if re.search(r'[A-Za-z]:[\\/]Users[\\/]',value,re.I):return '[local provenance removed]'
  return value
 for path in (APP/'Data').iterdir():
  if not path.is_file() or path.name in {'runtime_voice_contexts.json','extended_voice_contexts.json'}:continue
  if path.suffix not in {'.json','.png','.ico'}:continue
  dest=root/'Data'/path.name
  if path.suffix=='.json':dest.write_text(json.dumps(clean(json.loads(path.read_text(encoding='utf-8-sig'))),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  else:shutil.copy2(path,dest)
 (root/'Tools').mkdir()
 for name in ('build_source.py','build_distribution.py','release_contract.py','readme_distribution.py','readme_languages.json','UPDATE.md','usmap_schema.py','audit_voice_identification.py'):
  shutil.copy2(APP/'Tools'/name,root/'Tools'/name)
 ai=root/'Tools/VoiceAI';ai.mkdir()
 for path in (APP/'Tools/VoiceAI').glob('*'):
  if path.is_file() and path.name in {'models.json','mdx_model_data.json','provenance.json','NOTICE.txt','LICENSE-DeepFilterNet-APACHE.txt','LICENSE-DeepFilterNet.txt','LICENSE-MDX-Net.txt'}:shutil.copy2(path,ai/path.name)
 templates=APP/'Publication' if (APP/'Publication').is_dir() else APP
 for name in ('.gitignore','.gitattributes','README.md','LICENSE','CONTRIBUTING.md','CHANGELOG.md','requirements.txt','requirements-ai.txt','settings.example.json'):
  shutil.copy2(templates/name,root/name)
 for name in ('docs','.github'):shutil.copytree(templates/name,root/name)
 shutil.copy2(APP/'Tools/UPDATE.md',root/'UPDATE.md')
 guides=json.loads((APP/'Tools/readme_languages.json').read_text(encoding='utf-8'));folder=root/'Readme';folder.mkdir()
 links=[]
 for lang,item in guides.items():
  name='README_'+lang+'.md';(folder/name).write_text(item['text'],encoding='utf-8');links.append('- ['+item['name']+'](../Readme/'+name+')')
 (root/'docs/USER_GUIDES.md').write_text('# User guides\n\n'+'\n'.join(links)+'\n',encoding='utf-8')
 (root/'tests').mkdir()
 for name in ('test_release_update.py','test_legacy_projects.py','test_cpu_jobs.py','test_package_browser.py'):shutil.copy2(APP/'tests'/name,root/'tests'/name)
 manifest={}
 for path in sorted(root.rglob('*')):
  if not path.is_file():continue
  name=path.relative_to(root).as_posix()
  if path.suffix.lower() in {'.exe','.dll','.onnx','.pyd','.wav','.hca','.awb','.pak','.ucas','.utoc','.uasset','.uexp'}:raise ValueError('Unexpected binary/game data: '+name)
  if path.name in {'settings.json','keys.json','error.log'}:raise ValueError('Private state: '+name)
  if path.suffix in {'.py','.cs','.md','.json','.txt','.yml'}:
   text=path.read_text(encoding='utf-8-sig')
   if re.search(r'[A-Za-z]:[\\/](?:[\\/]?)Users[\\/]',text,re.I):raise ValueError('Personal path: '+name)
   if path.suffix=='.py':ast.parse(text,filename=name)
   if path.suffix=='.json':json.loads(text)
  manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
 (root/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
 archive=parent/('Sparking_Zero_Voice_Studio_Source_'+stamp+'.zip')
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for path in sorted(root.rglob('*')):
   if path.is_file():z.write(path,path.relative_to(parent))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for name,digest in manifest.items():assert hashlib.sha256(z.read(root.name+'/'+name)).hexdigest()==digest
 digest=hashlib.sha256(archive.read_bytes()).hexdigest();archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
 result={'root':str(root),'zip':str(archive),'files':len(manifest)+1,'bytes':archive.stat().st_size,'sha256':digest,'source_privacy_verified':True}
 (APP/'Reports/source_publication.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result),flush=True)
if __name__=='__main__':build()
