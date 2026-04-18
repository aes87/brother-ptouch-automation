# Creating a template pack

A *pack* is the unit of distribution for label templates. Built-in packs ship with this project (`kitchen`, `electronics`, `three_d_printing`, `utility`). External packs install as separate pip packages and register themselves via the `label_printer.packs` entry-point group.

This guide shows how to build an external pack.

## 1. Layout

```
my-ham-radio-pack/
├── pyproject.toml
└── label_printer_ham/
    ├── __init__.py          # exposes PACK
    ├── callsign.py
    └── qsl_sticker.py
```

## 2. Write templates

Templates are plain subclasses of `label_printer.templates.base.Template`. Same shape as any built-in.

```python
# label_printer_ham/callsign.py
from PIL import Image
from label_printer.engine.layout import (
    LabelCanvas, DEFAULT_BOLD, draw_row, fit_text_to_height,
    mm_to_dots, text_width,
)
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class CallsignTemplate(Template):
    meta = TemplateMeta(
        category="ham_radio",
        name="callsign",
        summary="Operator callsign badge.",
        fields=[
            TemplateField("call", "Callsign.", example="W1AW"),
            TemplateField("name", "Operator name.", required=False, example="Hiram"),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data, tape):
        call = str(data["call"]).upper()
        geom = geometry_for(tape)
        font = fit_text_to_height(call, geom.print_pins - 4, DEFAULT_BOLD)
        length = text_width(call, font) + mm_to_dots(6)
        canvas = LabelCanvas.create(tape, length_mm=length * 25.4 / 180)
        draw_row(canvas, call, font, 2)
        return canvas.image
```

**Important**: `meta.category` MUST match the pack's `name`. The pack primitive enforces this to catch copy-paste bugs.

## 3. Expose a `PACK`

```python
# label_printer_ham/__init__.py
from label_printer.templates.pack import TemplatePack
from .callsign import CallsignTemplate
from .qsl_sticker import QslStickerTemplate

PACK = TemplatePack(
    name="ham_radio",
    version="0.1.0",
    summary="Amateur radio labels — callsigns, QSL cards, antenna identification.",
    templates=(
        CallsignTemplate(),
        QslStickerTemplate(),
    ),
    homepage="https://github.com/yourname/label-printer-ham",
)
```

## 4. Declare the entry point

In your `pyproject.toml`:

```toml
[project]
name = "label-printer-ham"
version = "0.1.0"
dependencies = ["label-printer>=0.2"]

[project.entry-points."label_printer.packs"]
ham_radio = "label_printer_ham:PACK"
```

## 5. Install + verify

```bash
pip install -e .
lp packs        # your pack should show up alongside the built-ins
lp list --category ham_radio
lp show ham_radio/callsign
```

## Rules

- Pack-name collisions are resolved by **first-registered wins**. Built-ins register first, so they always beat externals with the same name. Between two externals with the same name, whichever pip resolves first is loaded; the others are logged and surfaced in `lp packs` under "failed packs" so the conflict is visible. A collision never crashes the CLI.
- Templates must carry `meta.category == pack.name`. Enforced at `TemplatePack` construction.
- Bump the pack's `version` when the template schema changes in an incompatible way (e.g. renaming a field). Old labels printed under v1 won't regenerate identically under v2, and that's expected.
- External packs MAY depend on this project's helpers (`label_printer.engine.layout`, `label_printer.tape`, etc.). Those are considered public API.
- External packs MUST NOT import from a built-in pack's module tree — if you need to reuse a built-in template, subclass or copy it rather than reach across pack boundaries.

## Trust model

Installing a pack means trusting its maintainer with arbitrary code execution on your machine.

Discovery uses Python's standard `importlib.metadata` entry-point mechanism. When `lp` starts up, it imports every package that declares an entry point in the `label_printer.packs` group and runs the module's top-level code to obtain the `PACK` object. That's the same contract as every other Python entry-point consumer (pip, pytest plugins, Click plugins, etc.), but it's worth being explicit:

- Treat `pip install label-printer-<something>` with the same caution you'd treat installing any other PyPI package.
- Prefer packs you can read the source of, pinned to a specific version.
- A compromised pack can read files, env vars (including `secrets-manager` keys if they're in the environment), and hijack the print pipeline.

If you suspect a pack is broken or untrustworthy and want to run `lp` without loading it, set `LABEL_PRINTER_DISABLE_ENTRY_POINT_PACKS=1`. Only built-in packs will load in that mode:

```bash
LABEL_PRINTER_DISABLE_ENTRY_POINT_PACKS=1 lp list
```

Broken packs are isolated — one pack that fails to import won't take down the CLI. `lp packs` shows the failures at the bottom of its output so you can identify which installed pack to uninstall or pin.
