# Updating an existing installation

1. Close Sparking Zero Voice Studio, including its background operations.
2. Keep a backup of your existing folder, especially Projects and settings.json.
3. Extract the entire new application ZIP into the existing installation's parent folder. Merge the folder named Sparking Zero Voice Studio and replace its application files. If your installation was renamed, copy the contents of the ZIP's application folder into your existing folder instead. Do not create another nested application folder.
4. Open the executable from that same folder.

The same ZIP supports first installation and updates. It contains no settings.json, projects, recordings, recovery cache, export preferences, saved effect presets, counters, keys or user logs. A fresh installation obtains empty paths and English from the program defaults. An update keeps the files already present on disk. settings.example.json is documentation only; do not copy it over settings.json.

Keep the same installation location and the entire project directories. Older project files can contain absolute paths. Moving only project.json or only the audio files can break those references. Updates do not erase, recreate or automatically migrate project.json files. Older optional fields remain optional.

Opening projects still requires their referenced audio and game banks. A damaged/deleted audio file cannot be recovered by an update. Game updates that change cue identities require the existing review/migration workflow; the application must not guess matches by row position.

## Release checks

Tools/release_contract.py prevents personal files entering generated releases. Tests cover overlay preservation, first-run defaults, legacy/current project loading and source privacy checks. Project compatibility fixtures are synthetic; existing projects are inspected read-only, without writing to their project.json files.

The source repository ZIP is for developers. End users should use the portable application ZIP from Releases.
