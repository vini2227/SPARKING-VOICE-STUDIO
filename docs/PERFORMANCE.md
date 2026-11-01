# Audio processing performance

Choose a mode under Settings > Audio processing. This is an installation preference and does not change project formats or audio quality.

- **Automatic** (default): up to 4 simultaneous voice tasks, limited by CPU count and available RAM.
- **Economy**: up to 2 tasks, with a lower CPU budget.
- **Fast**: up to 8 tasks when CPU count and RAM allow.
- **Sequential**: one task per batch, matching the previous processing order.

The CPU budget leaves one logical processor available when possible. Unknown storage performance is handled with conservative defaults and bounded in-flight work; the app does not benchmark disks automatically. Simultaneous batches share a global worker limit. Long-running tools already in progress finish before cancellation removes temporary export files.

Parallel work covers original WAV decoding when materializing project audio, matched-bank migration, migrated-original comparisons and export conversion/encoding. AWB/ACB assembly, package construction and final validation remain sequential. Identical PCM with the same HCA key is encoded once per export.

External tool failures caused by resource contention get one sequential retry after the batch workers have stopped. Invalid audio/metadata are not silently accepted. If a failure repeats, it is reported. Select Sequential to disable parallel batch processing.

Tk widgets stay on the UI thread. Progress-window updates are throttled. This change does not accelerate the Tk layout algorithm or enable GPU processing. Speedups vary with audio duration, cache state, storage and packaging/Unreal work.
