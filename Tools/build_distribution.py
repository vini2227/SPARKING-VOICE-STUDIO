import sys,shutil,json,datetime,subprocess,hashlib,zipfile
from pathlib import Path
app=Path(__file__).resolve().parent.parent
# Rebuild every size from the original artwork before compiling the launcher.
from PIL import Image
from io import BytesIO
import struct
logo=app/'Data/app_logo_round.png'
if not logo.is_file():raise RuntimeError('Missing original round LimitBreaker logo')
with Image.open(logo) as artwork:
 artwork=artwork.convert('RGBA')
 bounds=artwork.getchannel('A').getbbox()
 if bounds:artwork=artwork.crop(bounds)
 sizes=(16,20,24,32,40,48,64,96,128,256)
 payloads=[]
 for size in sizes:
  image=artwork.copy();image.thumbnail((size,size),Image.Resampling.LANCZOS)
  canvas=Image.new('RGBA',(size,size));canvas.alpha_composite(image,((size-image.width)//2,(size-image.height)//2))
  data=BytesIO();canvas.save(data,format='PNG');payloads.append(data.getvalue())
 offset=6+16*len(sizes);entries=[]
 for size,data in zip(sizes,payloads):
  entries.append(struct.pack('<BBBBHHII',size if size<256 else 0,size if size<256 else 0,0,0,1,32,len(data),offset));offset+=len(data)
 icon=struct.pack('<HHH',0,1,len(sizes))+b''.join(entries)+b''.join(payloads)
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
parent=app/'Distribution'/('TestRelease_'+stamp);parent.mkdir(parents=True)
root=parent/'Sparking Zero Voice Studio';root.mkdir()
ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pdb','voice_research_ui.py','voice_diagnostics.py')
shutil.copytree(app/'src',root/'src',ignore=ignore)
shutil.copytree(app/'Data',root/'Data',ignore=shutil.ignore_patterns('__pycache__','*.pyc','runtime_voice_contexts.json','extended_voice_contexts.json'))
(root/'Data/game_icon.ico').write_bytes(icon)
tools=root/'Tools';tools.mkdir()
for folder in ('vgmstream-cli','PythonDeps','UnrealReZen','FFmpeg','VoiceAI'):
 shutil.copytree(app/'Tools'/folder,tools/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pdb','oo2core*.dll'))
shutil.copy2(app/'Tools/VGAudioCli.exe',tools/'VGAudioCli.exe')
shutil.copy2(app/'Tools/oo2core_9_win64.dll',tools/'oo2core_9_win64.dll')
shutil.copy2(app/'Tools/oo2core_9_win64.dll',tools/'UnrealReZen/oo2core_9_win64.dll')
shutil.copytree(app/'Tools/UnrealPak',tools/'UnrealPak',ignore=shutil.ignore_patterns('*.pdb','*.lib','*.exp'))
runtime=app/'Runtime' if (app/'Runtime/python.exe').is_file() else Path(sys.executable).parent;target=root/'Runtime';target.mkdir()
for path in runtime.iterdir():
 if path.is_file() and (path.suffix.lower() in ('.exe','.dll') or path.name=='LICENSE.txt'):shutil.copy2(path,target/path.name)
for folder in ('DLLs','tcl'):
 shutil.copytree(runtime/folder,target/folder,ignore=ignore)
shutil.copytree(runtime/'Lib',target/'Lib',ignore=shutil.ignore_patterns('site-packages','__pycache__','*.pyc','test','tests','idlelib','ensurepip'))
site=target/'Lib/site-packages';site.mkdir()
prefixes=('numpy','cryptography','cffi','_cffi_backend','pycparser','PIL','pillow')
for path in (runtime/'Lib/site-packages').iterdir():
 if not any(path.name==p or path.name.startswith(p+'.') or path.name.startswith(p+'-') for p in prefixes):continue
 if path.is_dir():shutil.copytree(path,site/path.name,ignore=ignore)
 else:shutil.copy2(path,site/path.name)
cfg={'project':'','game':'','pak_key_file':'','unreal_editor':'','ui_language':'en','function_language':'en','unreplaced_policy':'original','voice_text_language':'en'}
# settings.json belongs to the user. core.config() supplies first-run defaults.
(root/'settings.example.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
(root/'runtime.path').write_text('Runtime\\pythonw.exe',encoding='utf-8')
launcher=root/'src/Launcher.cs';s=launcher.read_text(encoding='utf-8').replace('"-B \\"','"-E -B \\"')
launcher.write_text(s,encoding='utf-8')
csc=Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')
result=subprocess.run([str(csc),'/nologo','/target:winexe','/reference:System.Windows.Forms.dll','/win32icon:'+str(root/'Data/game_icon.ico'),'/out:'+str(root/'Sparking Zero Voice Studio.exe'),str(launcher)],capture_output=True,text=True)
if result.returncode:raise RuntimeError(result.stdout+result.stderr)
exe_data=(root/'Sparking Zero Voice Studio.exe').read_bytes()
if not all(data in exe_data for data in payloads):
 raise RuntimeError('Launcher icon verification failed: expected LimitBreaker artwork at all ten sizes')
(root/'icon_verification.json').write_text(json.dumps({'logo':'LimitBreaker round / Mirai 1','source_sha256':hashlib.sha256(logo.read_bytes()).hexdigest(),'icon_sha256':hashlib.sha256(icon).hexdigest(),'exe_sha256':hashlib.sha256(exe_data).hexdigest(),'sizes':list(sizes),'embedded_images_verified':True},indent=2),encoding='utf-8')

from readme_distribution import write_guides
write_guides(root)
license_file=app/'LICENSE'
if license_file.is_file():shutil.copy2(license_file,root/'LICENSE')
setup=r'''from pathlib import Path
import sys,json,tkinter as tk
from tkinter import messagebox
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'src'))
from i18n import Translator
try:language=json.loads((root/'settings.json').read_text(encoding='utf-8')).get('ui_language','en')
except (OSError,ValueError):language='en'
tr=Translator(language).text
ui=tk.Tk();ui.withdraw()
try:
    required=('Tools/UnrealPak/UnrealPak.exe','Tools/oo2core_9_win64.dll','Tools/UnrealReZen/oo2core_9_win64.dll','Tools/FFmpeg/bin/ffmpeg.exe','Tools/FFmpeg/bin/ffprobe.exe','Tools/VGAudioCli.exe','Tools/vgmstream-cli/vgmstream-cli.exe')
    missing=[name for name in required if not (root/name).is_file()]
    if missing:messagebox.showerror('Sparking Zero Voice Studio',tr('Ferramentas ausentes. Extraia novamente o ZIP completo:')+'\n'+'\n'.join(missing))
    else:messagebox.showinfo('Sparking Zero Voice Studio',tr('Ferramentas verificadas.'))
finally:ui.destroy()
'''
(root/'preparar_ferramentas.py').write_text(setup,encoding='utf-8')
(root/'Preparar ferramentas.bat').write_text('@echo off\r\n"%~dp0Runtime\\python.exe" -E -B "%~dp0preparar_ferramentas.py"\r\n',encoding='utf-8')
# Fail the build before publishing a ZIP if any app/helper source is invalid.
for source in list((root/'src').glob('*.py'))+[root/'preparar_ferramentas.py']:
 compile(source.read_text(encoding='utf-8'),str(source),'exec')
files=[p for p in root.rglob('*') if p.is_file()]
for path in files:
 if path.name in ('voice_research_ui.py','voice_diagnostics.py') or 'VoiceDiagnostics' in path.relative_to(root).parts:
  raise RuntimeError('Retired voice tool entered portable distribution: '+str(path))
from release_contract import validate_paths
validate_paths(p.relative_to(root).as_posix() for p in files)
manifest={'update_policy':'overlay-preserves-user-data','project_compatibility':'legacy-and-current','version':'test-'+stamp,'files':{p.relative_to(root).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},'excluded':['personal projects','audio files','cache','exports','keys.json','reference/game assets'],'bytes':sum(p.stat().st_size for p in files)}
(root/'distribution_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
zip_path=parent/('Sparking_Zero_Voice_Studio_'+stamp+'.zip')
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for path in root.rglob('*'):
  if path.is_file():z.write(path,path.relative_to(parent))
state={'root':str(root),'zip':str(zip_path),'unpacked_bytes':manifest['bytes'],'zip_bytes':zip_path.stat().st_size}
(app/'Reports/distribution_build.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state,indent=2),flush=True)
