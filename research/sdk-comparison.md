# PT-P710BT SDK / Library Comparison

Scouted 2026-04-18 while scoping the project. Goal: pick a reference implementation to build on rather than reimplement the raster protocol.

## Candidates

| Project | Lang | Transport | PT-P710BT | Notes |
|---|---|---|---|---|
| [treideme/brother_pt](https://github.com/treideme/brother_pt) | Python | USB | ✓ explicit | Implements raster protocol; also supports PT-E550W, PT-P750W. Best starting point. |
| [robby-cornelissen/pt-p710bt-label-maker](https://github.com/robby-cornelissen/pt-p710bt-label-maker) | Python | Bluetooth | ✓ primary target | Written specifically for this model over BT. Use as BT transport reference. |
| [philpem/printer-driver-ptouch](https://github.com/philpem/printer-driver-ptouch) | C | CUPS | ✓ | Full CUPS filter. Heavier; pulls in CUPS. Useful as spec sanity check. |
| [ryankurte/rust-ptouch](https://github.com/ryankurte/rust-ptouch) | Rust | USB | ✓ | Clean Rust implementation. Not our language but readable spec. |
| [philpem/libptouch](https://github.com/philpem/libptouch) | C | USB | ✓ | Low-level library behind the CUPS driver. |
| Brother official | PDF | — | ✓ | [Raster Command Reference](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf). Source of truth. |

## Decision

1. **Protocol source of truth**: Brother's official Raster Command Reference PDF (E550W/P750W/P710BT).
2. **USB transport**: start from `treideme/brother_pt`, vendor into `src/label_printer/transport/usb.py` and adapt as needed.
3. **BT transport**: study `robby-cornelissen/pt-p710bt-label-maker` — extract the BT SPP handshake + chunking logic into `src/label_printer/transport/bluetooth.py`.
4. **Imaging**: Pillow (`PIL.Image`) → 1-bit monochrome raster → raster command stream per Brother's spec.

## Non-goals

- CUPS integration — too heavy for our use case; we want direct control and the ability to move the printer between machines without driver setup.
- Windows support — not planned. This printer will live on a Linux devcontainer / server.
- P-touch Editor file import (.lbx / .lbl) — out of scope.
