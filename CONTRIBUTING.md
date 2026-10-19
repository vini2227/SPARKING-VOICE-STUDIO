# Contributing

Keep changes focused and retain project compatibility. New project fields must be optional on load; never silently discard an old project or guess cue remapping by row number. Keep audio input files immutable and preserve originals for undo/restore. Keep UI work on the Tk thread and group layout changes without global redraw suppression.

Run the update/compatibility tests before changing serialization or packaging. Add a regression fixture when fixing a project-loading issue. Translate user-facing additions across the 16 supported languages. Never commit Projects, Cache, configuration, logs, audio, keys, generated packages or binary tools. Pull requests should explain behavior changes and validation.
