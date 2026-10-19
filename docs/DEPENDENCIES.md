# Dependencies and distribution boundaries

Python 3.12 (with Tkinter), NumPy, Pillow, cryptography, arabic-reshaper and python-bidi are required. Optional audio editing uses pedalboard and sounddevice; optional isolation uses ONNX Runtime. The tested version snapshot is in requirements files and Data/dependency_versions.json. It is not an automatic dependency update policy.

External tools are not included in the source archive:

| Tool | Expected location |
| --- | --- |
| FFmpeg / FFprobe | Tools/FFmpeg/bin/ffmpeg.exe and ffprobe.exe |
| vgmstream | Tools/vgmstream-cli/vgmstream-cli.exe |
| VGAudio | Tools/VGAudioCli.exe |
| UnrealPak | Tools/UnrealPak/UnrealPak.exe |
| UnrealReZen | Tools/UnrealReZen/UnrealReZen.exe |
| Compatible Oodle | Tools/oo2core_9_win64.dll |
| DeepFilterNet | Tools/VoiceAI/deep-filter.exe |
| Isolation model | Tools/VoiceAI/Kim_Vocal_2.onnx |

Audio UI dependencies can be installed in the Python environment. Existing portable installations keep their tool-local PythonDeps folders. Preserve upstream licenses and validate redistribution rights for each binary/model. No Custom Engine, CustomProject or game content is supplied.
