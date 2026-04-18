# Encoder validation — cross-check with brother_pt

Our raster encoder is cross-checked against `treideme/brother_pt` in `tests/test_raster_encoder.py::test_matches_brother_pt_byte_for_byte`. Same tape, same raster bytes, same options → identical output byte-for-byte.

## Where we intentionally diverge

**Mode '1' ink convention**. `brother_pt` treats mode '1' white pixels as ink (leaves the bytes unmodified, and `compress_buffer` treats any non-zero byte as "bit-1"). We treat mode '1' black pixels as ink — matching the intuition that text-on-tape labels are composed with black text on a white background.

This only diverges at the image-interpretation layer. Once we have flat raster bytes, the command framing is identical. The cross-check test therefore runs at the raster-bytes layer, not the image layer.

**Mode 'L' threshold**. We threshold at 128 (dithering off). `brother_pt` treats any non-pure-white pixel as ink. For flat PNGs (pure black / pure white) both produce the same raster. For anti-aliased text the thresholds disagree — a subpixel gray becomes ink in `brother_pt` but not in ours. 128 is the more common expectation and avoids gray edges becoming thick.

## Known cross-check scope

- ✓ Invalidate + ESC@ init
- ✓ Dynamic command mode (raster)
- ✓ Status notification enable
- ✓ `ESC i z` print-information (with tape width + line count)
- ✓ Mode byte (auto-cut + mirror)
- ✓ Advanced mode byte (chaining)
- ✓ Margin (feed dots)
- ✓ TIFF compression mode
- ✓ Raster lines (both Z-shortcut and packbits)
- ✓ Print-and-feed terminator (`0x1A`)

## Not yet validated (needs hardware day)

- Status-response parsing (media width autodiscovery)
- Error-code interpretation on real faults
- Chaining behaviour across multi-page jobs
- Half-cut vs auto-cut command bits on the P710BT specifically
- BT SPP handshake timing

Those become tests with a `hardware` marker once the printer is on the bench.
