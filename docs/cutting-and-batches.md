# Brother PT-P750W cutting behavior — what actually works

> Source notes for anyone touching `encode_job` / `encode_batch`, adding a new
> transport, or trying to understand why the obvious-from-the-spec interpretation
> of the cut commands doesn't match real hardware.

The Brother Raster Command Reference is correct but **its example sequences
are for single-page jobs**. Multi-label jobs with half-cuts between need a
specific pattern that the spec doesn't spell out. We learned this empirically
across six hardware test rounds. This note pins what we found so the next
person doesn't have to.

## The headline finding

**`ESC i M` bit 6 (auto-cut, `0x40`) on a chained job tells the printer to
full-cut after every page**, regardless of the half-cut bit. The half-cut bit
in `ESC i K` only fires when auto-cut is *off* — half-cut is its own
mechanism, separate from auto-cut, not a modifier on it.

The spec's example for chain printing sets `ESC i K = 0x0C` on every page
(half-cut + no-chain). That works for **a chain of single-page jobs** but
not for one batched multi-label job. The single example easily reads as the
canonical pattern; it's not.

## The canonical sequence

Three independent reverse-engineered implementations converge on the same
shape. We followed all three to get a working PT-P750W batch:

* [philpem/printer-driver-ptouch](https://github.com/philpem/printer-driver-ptouch) — CUPS driver, C
* [boxine/rasterprynt](https://github.com/boxine/rasterprynt) — Python, PT-P950NW (same command grammar)
* [masatomizuta/py-brotherlabel](https://github.com/masatomizuta/py-brotherlabel) — Python, PT-P9xx family

```
# Once per batch:
\x00 * 100                        # invalidate
\x1B \x40                         # ESC @ — initialize
\x1B \x69 \x61 \x01               # ESC i a 01 — raster mode
\x1B \x69 \x21 \x00               # ESC i ! 00 — status notify
\x1B \x69 \x4D \x00               # ESC i M 00 — Mode: AUTO-CUT OFF
\x1B \x69 \x4B \x04               # ESC i K 04 — half-cut on, chain on
\x1B \x69 \x64 \x0E \x00          # ESC i d — margin (default 14 dots)

# Per page i in 0..N-1:
if i > 0:
    \x0C                          # FF — page separator (no eject)
if i == N-1:
    \x1B \x69 \x4B \x0C            # ESC i K 0C — kick: half-cut + no-chain
\x1B \x69 \x7A ... n9 \x00        # ESC i z — print info; n9 = 0 first / 1 mid / 2 last
\x4D \x02                         # compression: TIFF-PackBits
... raster lines ...

# Once at end:
\x1A                              # SUB — print + feed + cut
```

Three things make this different from a single-page job:

1. **`ESC i M / K / d` are job-level, not per-page.** Re-emitting them between
   pages would reset the printer's state. Send once.
2. **`ESC i z`'s `n9` byte (offset +11 from the prefix) is per-page.** `0` for
   the first/only page, `1` for any middle pages, `2` for the last. The printer
   uses this to chain correctly.
3. **The "kick" before the last page.** With auto-cut off, the terminating
   `\x1A` only feeds — it doesn't cut. Re-emitting `ESC i K = 0x0C` (half-cut +
   no-chain) before the last page's `ESC i z` flips the no-chain bit on, and
   *that* bit drives the end-of-job feed-and-cut. Per spec p.33: "1: No chain
   printing (Feeding and cutting are performed after the last one is printed)."

## Why we don't use `ESC i A`

`ESC i A` ("cut every N labels") only takes effect when auto-cut is **on**.
With auto-cut off — which is what makes the canonical batch pattern work —
`ESC i A` is meaningless. `encode_batch` deliberately does not emit it.

For single-label `encode_job` / `build_prologue` we *do* emit `ESC i A 01`
explicitly. Auto-cut is on for single labels (so the printer cuts at the end
of the job), and stating `01` makes the job self-contained against any
printer-side persistent overrides — without it, the printer might be in a
state where its persistent "cut every N" is something other than 1.

## Persistent printer settings — what to ignore

The Brother **ES Device Settings** tool (Windows-only, USB-only) and the
print driver's "Preferences" panel both expose cut-related controls:

* "Auto cut" with a labels-count.
* "Half cut" checkbox.
* "Chain printing" checkbox.

These persist into the printer's firmware state and *can* affect what the
printer does. We tested every plausible combination (auto-cut on/off,
labels-count 1/99, half-cut on/off, chain printing on/off) — **none of them
produce half-cuts-between-batched-labels for our raw raster path**. The
canonical pattern above works regardless of the persistent settings.

This is good news: the codebase doesn't depend on the user opening Brother's
Windows tool to configure their printer. New users get half-cut batches out
of the box once the printer is on Wi-Fi.

The persistent-settings rabbit hole was a productive dead end. Future
contributors hitting unexpected cut behavior should look at the per-job byte
stream first, not the persistent driver config.

## Single-label vs batch — what differs

| | Single label (`encode_job`) | Batch (`encode_batch`) |
|---|---|---|
| Auto-cut (`ESC i M` bit 6) | **on** (0x40) | **off** (0x00) |
| `ESC i A` | sent once, n=1 | not sent |
| `ESC i K` | sent once, half-cut + no-chain (0x0C) | sent twice: 0x04 at start, 0x0C right before last page |
| `ESC i z` n9 byte | 0 (only page) | 0 / 1 / 2 per position |
| Inter-page byte | n/a | 0x0C between pages |
| Terminator | 0x1A | 0x1A |

A 1-image batch degrades to `encode_job()` byte-for-byte to keep single-label
test invariants stable.

## Spec PDF locations

The Brother Raster Command Reference for PT-E550W / PT-P750W / PT-P710BT
(version 1.02): [PDF on download.brother.com](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf).
The relevant sections:

* p. 5–6 — print data structure overview ("control codes are sent at the
  beginning of each page")
* p. 33 — `ESC i M` (Mode) and `ESC i K` (Advanced) bit assignments
* p. 34 — `ESC i A` (Auto cut count)
* p. 37–38 — page terminators (`\x0C` between pages, `\x1A` at end)
* QL-800 manual mirror documents the `ESC i z` n9 byte explicitly:
  [manualowl mirror p.35](https://www.manualowl.com/m/Brother%20International/QL-800/Manual/605535?page=35)
  (the PT-P750W reference doesn't enumerate n9 values but the printer honors
  them the same way).

## If you're adding a new transport

The transport's job is to deliver the bytes encoded by `encode_job` /
`encode_batch` — full stop. The cut behavior described here is encoded into
those bytes, not into anything the transport does. USB and Bluetooth will
work with the same bytes that the network transport ships today. No new
flags, no new options.
