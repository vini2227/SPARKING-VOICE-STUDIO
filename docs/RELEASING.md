# Preparing a release

1. Start from a controlled Windows development installation with the configured external tools and tested Runtime. Read docs/LICENSING.md before distributing dependencies.
2. Run the update and legacy-project tests. Run UI/audio/export checks appropriate to the changes.
3. Run Runtime/python.exe -E -B Tools/build_distribution.py. The builder compiles the C# launcher and stages application files only. It requires Pillow and the Windows .NET C# compiler. It is not a dependency downloader.
4. Verify ZIP CRC, every distribution_manifest.json hash, the release path allowlist and that no user state entered the archive.
5. Extract it over a disposable copy of an older installation; compare hashes of user projects, audio, settings, presets, counters and recovery files before/after. Open representative old projects and test the extracted application with its own bundled Runtime.
6. Add an accurate changelog and publish the application ZIP plus SHA256 through GitHub Releases when explicitly authorized. Source and portable ZIPs are different artifacts.

The manifest describes a release; it must not trigger deletion of unknown files in an existing installation. Close the app before extraction. New optional settings/project fields require defaults and regression fixtures. Never bump a project schema merely to reject older manifests.
