# Changelog

## 2026.11.01 — Multi-character packages and CPU processing

- Added a searchable package browser organized by character/folder and US/JP banks, including voice counts and returning to the package list through Project tools.
- Support custom bank names such as BTLCV_Toas_14_US when validated against the original mod container. Retain the original asset mount and chunk identity on voice-only Replacer export.
- Validate ACB/AWB IDs and HCA headers before reconciling legacy metadata in app-owned copies. Original mod files remain unchanged.
- Added Automatic, Economy, Fast and Sequential audio-processing modes, bounded parallel jobs, shared CPU limits and sequential retry for tool failures.
- Verified the GTPack2 fixture's 21 voice banks in 14 groups, a real voice-only package export, and the extracted portable application. In-game verification was not performed by these tests.
- Malwarebytes staff whitelisted the reported launcher SHA-256 `828788f5f3331327cadd073a726aa969215b4970b1ce061ace9dd671d0a7d9f8`. The reviewed ZIP preserves that executable exactly; the correction is in Malwarebytes' detection database, not an antivirus bypass or a guarantee about other vendors/future builds.
- Official response: https://forums.malwarebytes.com/topic/341415-false-positive-sparking-zero-voice-studioexe-machinelearninganomalous/#findComment-1766947

## 2026.10.18 — First public release

- Licensed original application source under GPL-3.0-only; retained third-party notices and distribution boundaries.

- Portable release archives omit settings.json, preserving existing paths and language when extracted over an installation.
- Added a fail-closed release path contract, update documentation in 16 languages and legacy project/update tests.
- Prepared a separate source tree with dependencies, contribution notes, CI and license/third-party review status.

## Included application work

- Reduced redundant voice-table measurements/rebuilds and neutralized regrouping flashes.
- Pitch-preserving slower/faster presets (0.90x / 1.10x).
- Restore-before-speed audio preserved in saves, recovery and shared projects.
- Duplicate identification based on preserved imported audio through derived edits.
- Workflow progress/cancellation, support reports, export review and before/after previews.
- Updated bundled dependency setup and retained localized UI/help.

Updates are distributed as portable ZIP archives; an automatic updater is not included.
