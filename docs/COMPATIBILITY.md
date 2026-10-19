# Project and update compatibility

Portable application files and user state have distinct ownership. Releases replace only src, immutable Data catalogs, Tools, Runtime, guides and an explicit root-file allowlist. The same ZIP can be extracted for a first installation or merged over the existing installation. Missing settings.json uses core.DEFAULTS. A release must never supply settings.json or a Projects directory.

Project files from earlier versions use optional fields. Current loading supports legacy manifests without schema and schemas 1 through the current schema 6 in the regression fixtures. Gains, variations, recovery originals and newer bookkeeping fields are absent by default in older manifests. Existing validation is retained: referenced files must exist inside the installation and gain/variation references must belong to replacement voices.

Tests read legacy JSON through the actual project-open entry point and verify no manifest/audio is changed by loading. All fixture variants are also verified after extracting a release over an installation containing user files. New releases must retain these fixtures. These checks are evidence for the formats covered, not a promise to repair corrupted files, deleted recordings, another application's project format, or changed game cue identities.

Keep the installation at the same absolute path. Existing projects may contain absolute audio/source references. Copying only project.json, changing drive letters or extracting into a different folder is not the same operation as updating in place. Use the application's shared-project workflow for supported transport.

A game update is separate from an app update. Cue identity conflicts must use the existing review/migration flow. User data is never rewritten by the release builder.
