# brother-ptouch-automation

**Template-driven label automation for the Brother P-touch Cube Plus (PT-P710BT).** One engine, three surfaces — a CLI, an HTTP service, and a Claude Code skill — sitting on top of a byte-exact raster encoder.

Print a pantry jar, a cable flag, or a filament spool label from a terminal, a web request, or a chat message. Same engine, same output.

![kitchen pantry jar](docs/previews/kitchen_pantry_jar_12mm.png)
![electronics cable flag](docs/previews/electronics_cable_flag_12mm.png)
![3d printing filament spool](docs/previews/three_d_printing_filament_spool_12mm.png)

## Why

The Brother P-touch Editor app is fine for one-off labels, but it's terrible at the workflows you actually want:

- Labelling ten jars in a row without clicking through a GUI
- Printing a label from a script, a scheduled job, or a chatbot
- Sharing a template library across projects
- Getting the *same* label twice in a row, reliably

This project is a small, fast automation layer that fixes those. Templates are real Python classes with validated field schemas. The raster encoder is byte-exact against Brother's official command reference. The three surfaces (CLI, HTTP service, Claude Code skill) all call the same engine, so a label triggered from Claude comes off the tape identical to one triggered from the shell.

## Features

- **10 templates out of the box** across kitchen, electronics, and 3D-printing use cases — add your own with one Python file
- **Byte-exact** raster output, cross-checked against [`treideme/brother_pt`](https://github.com/treideme/brother_pt) in CI
- **Tape-aware** — print-head geometry is handled for every supported TZe width (3.5 / 6 / 9 / 12 / 18 / 24 mm)
- **Dry-run first** — every surface renders a PNG preview before anything leaves for the printer
- **HTTP service** with optional bearer-token auth, so the printer can live on one machine and clients call it from anywhere on the LAN
- **Claude Code skill** — install the symlink and Claude sessions can discover templates, propose labels, and print them
- **50 tests**, ruff clean, CI on every push

## Template gallery

All rendered at 180 DPI for 12mm tape — drop straight onto a TZe cassette.

| Pack | Template | Preview |
|---|---|---|
| `kitchen/` | `pantry_jar` | ![](docs/previews/kitchen_pantry_jar_12mm.png) |
| `kitchen/` | `spice` | ![](docs/previews/kitchen_spice_12mm.png) |
| `kitchen/` | `leftover` | ![](docs/previews/kitchen_leftover_12mm.png) |
| `kitchen/` | `freezer` | ![](docs/previews/kitchen_freezer_12mm.png) |
| `electronics/` | `cable_flag` | ![](docs/previews/electronics_cable_flag_12mm.png) |
| `electronics/` | `component_bin` | ![](docs/previews/electronics_component_bin_12mm.png) |
| `electronics/` | `psu_polarity` | ![](docs/previews/electronics_psu_polarity_12mm.png) |
| `three_d_printing/` | `filament_spool` | ![](docs/previews/three_d_printing_filament_spool_12mm.png) |
| `three_d_printing/` | `print_bin` | ![](docs/previews/three_d_printing_print_bin_12mm.png) |
| `three_d_printing/` | `tool_tag` | ![](docs/previews/three_d_printing_tool_tag_12mm.png) |

## Quickstart

```bash
git clone https://github.com/aes87/brother-ptouch-automation.git
cd brother-ptouch-automation
python3.11 -m venv .venv
.venv/bin/pip install -e '.[barcode,service]'

# List the templates
.venv/bin/lp list

# Inspect a template's fields
.venv/bin/lp show kitchen/pantry_jar

# Render to PNG + raster command stream (no printing)
.venv/bin/lp render kitchen/pantry_jar \
  -f name=FLOUR -f purchased=2026-04-19 \
  --png-out flour.png --bin-out flour.bin

# "Print" (dry-run transport until hardware transport lands)
.venv/bin/lp print kitchen/pantry_jar \
  -f name=FLOUR -f purchased=2026-04-19 \
  --bin-out flour.bin
```

## Three surfaces

### CLI

```bash
lp list [--category kitchen]          # discover templates
lp show <category>/<name>             # field schema for a template
lp render <template> -f k=v ...       # PNG + raster preview
lp print  <template> -f k=v ...       # encode + send (dry-run for now)
lp render-image <file.png>            # raster-encode an arbitrary image
lp tape <mm>                          # persist current tape width
lp tape-info                          # print-head geometry per tape
lp serve --host 127.0.0.1 --port 8765 # run the HTTP service
```

### HTTP service

```bash
export LABEL_PRINTER_TOKEN=s3cret  # optional
lp serve --host 127.0.0.1 --port 8765
```

```bash
curl -s http://127.0.0.1:8765/templates | jq .
curl -X POST http://127.0.0.1:8765/render \
  -H 'Authorization: Bearer s3cret' \
  -H 'Content-Type: application/json' \
  -d '{"template":"kitchen/pantry_jar","tape_mm":12,"fields":{"name":"FLOUR","purchased":"2026-04-19"}}' \
  --output flour.png
```

Endpoints: `GET /health`, `GET /templates`, `POST /render`, `POST /print`. The `/print` endpoint returns the raster command bytes today (dry-run); Phase 5 flips it to actually drive the USB/BT transport.

### Claude Code skill

The `skill/` directory is a Claude Code skill. Symlink it into `~/.claude/skills/label-printer/` and Claude sessions can print labels:

```bash
ln -s "$(pwd)/skill" ~/.claude/skills/label-printer
```

From any Claude session:

> "label this jar — sriracha, opened 2026-04-10"

Claude picks the right template, proposes fields, dry-renders a PNG for you to review, and only prints once you approve.

## How it works

```
                  ┌─────────────────────────────────────────────┐
 CLI (lp) ────┐   │                 label_printer               │
              │   │                                             │
 Skill ───────┼─▶ │  templates ──▶ engine (Pillow)              │
              │   │                    │                        │
 Service ─────┘   │                    ▼                        │
                  │              raster encoder                 │
                  │                    │                        │
                  │                    ▼                        │
                  │     transport {usb, bluetooth, dryrun}      │
                  └─────────────────────────────────────────────┘
                                       │
                                       ▼
                                 PT-P710BT
```

- **Templates** render a Pillow `Image` sized for the loaded tape. They declare a field schema (`TemplateField`) so the CLI, the service, and the skill can all introspect what data they need.
- **The engine** converts the image to a 1-bit raster aligned to the 128-pin head, pads for the tape's physical margin, and emits the full Brother command stream (init + dynamic mode + print info + mode + compression + TIFF-PackBits raster + print-and-feed).
- **Transports** only care about `send(bytes)`. `DryRunTransport` writes to a file; USB and Bluetooth transports are staged for the hardware day (see roadmap).
- **Goldens** in `tests/golden/raster/` lock the encoder's byte output. A cross-check test reproduces the exact sequence `treideme/brother_pt` would produce for the same raster bytes and asserts byte-for-byte equality.

## Adding your own template

Drop a file in `src/label_printer/templates/<pack>/<name>.py`:

```python
from PIL import Image
from label_printer.engine.layout import LabelCanvas, fit_text_to_box, DEFAULT_BOLD
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class GardenSeedTemplate(Template):
    meta = TemplateMeta(
        category="garden",
        name="seed_packet",
        summary="Seed packet: variety + sow-by + year.",
        fields=[
            TemplateField("variety", "Cultivar.", example="Brandywine tomato"),
            TemplateField("sow_by", "Sow-by date.", example="2026-05-15"),
            TemplateField("year", "Harvest year.", required=False, example="2025"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        # compose your label here
        ...
```

The registry discovers it on next run. No manifest file, no re-install.

## Hardware & compatibility

- **Designed for** the **Brother PT-P710BT** ("P-touch Cube Plus") — 180 DPI, 128-pin head, TZe tapes 3.5–24 mm, USB + Bluetooth Classic (SPP)
- **Should also work** with the **PT-E550W** and **PT-P750W** — they share the exact same raster command reference and the same 128-pin head
- **Does not work** with the smaller **PT-P300BT** (original Cube) or the **PT-P910BT** (Cube Pro) — different command sets, different head geometry
- **Does not work** with Brother QL shipping-label printers or with Dymo / Zebra / Epson — completely different protocols

The encoder targets Brother's [Raster Command Reference for PT-E550W / PT-P750W / PT-P710BT](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf).

## Roadmap

- [x] **Phase 1** — raster encoder + `DryRunTransport` + byte goldens + cross-check against `brother_pt`
- [x] **Phase 2** — template engine + registry + 10 templates across 3 packs
- [x] **Phase 3** — CLI + HTTP service + Claude Code skill, all on `DryRunTransport`
- [ ] **Phase 4** — chat-bridge integration (Telegram / Slack) in dry-run
- [ ] **Phase 5** — USB + Bluetooth transports, first physical prints, tape-width autodetect
- [ ] **Phase 6** — `lp print --remote <host>` for running the service on a dedicated machine

See [`docs/implementation-plan.md`](docs/implementation-plan.md) for the full plan.

## Development

```bash
.venv/bin/pytest                  # unit + integration
.venv/bin/pytest -m hardware      # transport tests, require the physical printer
.venv/bin/ruff check src tests
```

Regenerate byte goldens after an intentional encoder change:

```bash
REGEN_GOLDENS=1 .venv/bin/pytest tests/test_raster_encoder.py
```

## Credits

Built from Brother's [official raster command manual](https://download.brother.com/welcome/docp100064/cv_pte550wp750wp710bt_eng_raster_102.pdf), informed by two excellent open-source implementations:

- [treideme/brother_pt](https://github.com/treideme/brother_pt) — Python USB driver, Apache 2.0
- [robby-cornelissen/pt-p710bt-label-maker](https://github.com/robby-cornelissen/pt-p710bt-label-maker) — Python Bluetooth driver

See [`CREDITS.md`](CREDITS.md) for the full dependency list and license attributions.

## License

MIT — see [`LICENSE`](LICENSE). Bundled DejaVu fonts are under the Bitstream Vera license; see [`assets/fonts/LICENSE-DejaVu.txt`](assets/fonts/LICENSE-DejaVu.txt).
