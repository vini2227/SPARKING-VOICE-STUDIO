# Sparking Zero Voice Studio — Portable edition

## Installation
1. Extract the entire ZIP into a writable folder, such as Documents. Do not run the app inside the ZIP or install it in Program Files.
2. Open `Sparking Zero Voice Studio.exe`. Python, audio tools, UnrealPak and Oodle are bundled; no separate Python, Codex or Excel installation is required. `Preparar ferramentas.bat` is an optional tool check.
3. In Settings, select the game installation folder. For Replacer, leave CustomProject and Custom Engine empty to read references directly from the game. The game package key is configured automatically; no `keys.json` is required.
4. Save settings and open a voice bank. New installations start in English. You can change the app language without selecting folders first. Updating with your existing `settings.json` keeps your language choice.

## Requirements
- Windows 10 or 11, 64-bit; .NET Framework 4.8 and the 64-bit Visual C++ runtime required by the bundled Unreal tools.
- An installed copy of DRAGON BALL Sparking! ZERO, including the `.pak`, `.utoc` and `.ucas` files for your game version.
- **Custom Engine and CustomProject are not included.** Custom export requires a compatible Unreal 5.1 Custom Engine with the CriWare plugin and its DLLs, plus CustomProject containing compatible voice references. A generic Unreal installation is not sufficient.
- CustomProject is optional for Replacer. If configured, it supplies references; otherwise the app reads them from the installed game and refreshes its cache when game containers change.

## Main features
- Browse US/JP banks, official localized character names, Cue IDs, functions, interaction tags, filters and repeated voices; compare original and edited audio.
- Import audio, video or external voice packages; record from a microphone; trim audio; adjust gain, fix clipping and maximize volume.
- Local voice enhancement, background isolation and effects: reverb, echo, pitch, bass/treble, double voice, distortion and radio. Preview before applying; quality depends on the recording.
- Change voice speed from 0.25x to 3.00x, with pitch preservation enabled by default (can be disabled), preview and undo/redo. Preserve pitch to change tempo only.
- Save and recover projects, browse recent projects, share/merge, migrate banks and copy voices by tags/functions. Ctrl+Z undoes; Ctrl+Y or Ctrl+Shift+Z redoes. Help and interface support 16 languages.
- External voices confirmed identical to the game are treated as originals, not replacements. Previewing external audio is limited to confirmed differences. Choose whether unreplaced voices keep original audio or become silence.

## Replacer and Custom exports
**Replacer:** exports `.pak`, `.utoc` and `.ucas` together in the mod folder. The original bank determines which character is replaced; changing the project or folder name does not change that target. An empty Replacer folder name uses the official base-character name in the app language. Keep a custom character's own mod installed: a voice package does not include the character. Keep related PAK/UTOC/UCAS files together when importing. Replacer does not launch Unreal Editor.

**Custom:** exports the `.uasset` in “Custom - Unreal mod folder” and the `.pak` in “Custom - Game mod folder”; intermediate files and reports go into a support folder. Folder labels follow the app language. The project name must exactly match the mod/plugin folder under `Plugins` in Unreal. The bank name must match the custom character ID and US/JP language. Select both CustomProject and Custom Engine in Settings.

Exports are grouped by project number and name. Each export version starts with an increasing number, so the latest sorts last by name. Open folder offers exports first, then edited audio and projects; without a project, exports opens the general export folder. Always test the result in the game.

## Projects and backups
Close the app and back up the existing folder before updating. Extract the new application ZIP into the same installation, merging folders and replacing application files. Keep Projects, Cache, settings.json, preferences, counters and saved presets. These personal files are not included in the new ZIP. Do not create a second nested app folder. Keep the same location: old projects may contain absolute audio paths. Legacy projects retain their existing format; missing optional fields remain supported. See UPDATE.md.

## Troubleshooting and included files
For access-denied errors, extract the app to a writable folder such as Documents. Folder opening retries with Windows Explorer; it does not request administrator rights or change Windows permissions. For Custom import errors, check the `import.log` path shown by the app and verify the compatible Engine/CriWare installation. Imported assets must match the intended bank and game version.

The package contains no personal projects, recordings, exports, cache, game/reference assets or author settings. The default game package key and bundled tools are included. Component licenses accompany the runtime and libraries; voice-engine credits are in `Tools/VoiceAI/NOTICE.txt`. For support, provide the app/game version, bank, export mode and relevant log. Local technical checks do not replace an in-game test.
