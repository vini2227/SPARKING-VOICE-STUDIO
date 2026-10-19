# Sparking Zero Voice Studio

Windows desktop editor for DRAGON BALL: Sparking! ZERO voice banks, with Custom and Replacer export workflows.

## Features

- English/Japanese bank browsing, localized character names and cue/function/interaction filtering.
- Original/edited playback, media import, microphone recording, trimming and volume controls.
- Pitch-preserving speed changes, effects, clipping protection and optional local voice enhancement/isolation.
- Duplicate recording identification that survives derived edits when the input has been preserved.
- Project saves, session undo/redo, automatic recovery and portable project sharing.
- Custom and Replacer exports, original per-voice sample rates/channels and PCM16 encoder inputs.
- Interface, help and user guides in 16 languages.

## Install and update

End users should use a portable application ZIP, not the source ZIP. Close the app, merge a new portable ZIP into the **same installation folder**, and replace application files. Do not delete the old folder. Generated releases exclude personal settings and project folders. See [UPDATE.md](UPDATE.md) and [compatibility](docs/COMPATIBILITY.md).

[User guides in 16 languages](docs/USER_GUIDES.md).

## Run from source

Windows x64, Python 3.12 with Tkinter:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -E -B src/app.py
```

Keep the checkout writable. The app uses built-in English/empty-path defaults if settings.json does not exist; settings.example.json is documentation, not an installer. Configure the game path in Settings.

External audio and Unreal tools must be installed separately for the features that require them. See [dependencies](docs/DEPENDENCIES.md). **Custom Engine and CustomProject are not included.** No game assets, personal audio, game key files, compiled tools, model weights or Python runtime are included in this source package.

## Development

- `src/`: application modules and C# Windows launcher.
- `Data/`: localization, public identification/reference catalogs and artwork; rights status is documented below.
- `Tools/`: source/release builders, release safety policy and localized guide generator.
- `tests/`: update preservation and project compatibility regression tests.
- `docs/`: architecture, release process and compatibility policy.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_release_update.py" -v
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_legacy_projects.py" -v
```

The second test requires Windows and the Python dependencies; it does not launch Unreal or the game. Full UI and real export validation require a configured local development installation.

## License

The original application source code is licensed under [GNU GPL version 3](LICENSE), SPDX identifier `GPL-3.0-only`. You may use, modify and redistribute it, including commercially, subject to the license. Distribution of covered binaries requires providing the corresponding source through a GPL-compliant method. Third-party components retain their own licenses. See [scope and third-party notices](docs/LICENSING.md).

Game assets and proprietary tools are not relicensed or included in this repository. Downloadable application packages are distributed separately through GitHub Releases.

See [contributing](CONTRIBUTING.md) and [changelog](CHANGELOG.md).
