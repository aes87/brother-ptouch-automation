# Brother Raster Command Protocol — PT-P710BT

**Source of truth**: [Brother Software Developer's Manual — Raster Command Reference, PT-E550W / PT-P750W / PT-P710BT](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf)

## Print data shape (from the manual)

Per Brother, a print job consists of:

1. **Initialization commands** — reset printer state, declare job parameters.
2. **Control codes** — set print mode, tape info, resolution, margins, chaining, etc. Repeated for each page in a multi-page job.
3. **Raster data** — one row of pixels at a time, encoded per the manual's raster line format.
4. **Print command** — commit and feed.

## Key printer facts to encode into the transport layer

- **Print head**: 128 pins at 180 DPI. Usable print area depends on tape width — the tape covers only a portion of the head's span, and the Brother reference gives the offset per tape width. We must pad raster lines so that the tape-relevant pins line up correctly.
- **Tape width declaration**: the job must declare tape width (mm) so the printer can verify the loaded cassette matches. Mismatch → error.
- **Chaining / auto-cut / half-cut**: configurable per job via control codes.
- **Compression**: TIFF (PackBits) compression is supported and recommended for larger prints.

## What we still need to verify experimentally

- Exact BT SPP init sequence on fresh pairing.
- Whether PT-P710BT accepts the same status-request command as E550W (for tape-width autodiscovery).
- Max practical raster line count before the printer buffers out. (Manual says 500 mm @ 180 DPI ≈ 3543 lines.)
- Timing on `send → print → ready` — affects our "print next label" loop throughput.

These become Phase 1 experiments once the printer is on the bench.
