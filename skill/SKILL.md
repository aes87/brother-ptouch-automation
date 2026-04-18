---
name: label-printer
description: >
  Design and print labels on the Brother P-touch Cube Plus (PT-P710BT) from
  templates — kitchen (pantry jars, spice, leftovers, freezer), electronics
  (cable flags, component bins, PSU polarity), 3D printing (filament spools,
  print bins, tool tags). Invoke when the user asks for a label, mentions
  "label maker", "p-touch", "tape", or wants to label a physical object.
  Always dry-renders a PNG preview first and requires confirmation before
  sending to the printer.
allowed-tools: Bash, Read, Write
model: sonnet
---

# Label Printer

You generate labels for the Brother PT-P710BT ("P-touch Cube Plus") via the `lp` CLI.

**Expected install**: `lp` on `$PATH`, OR set `LP` to the absolute path of the executable (e.g. `LP=/path/to/label-printer/.venv/bin/lp`) at the top of your session. If neither works, ask the user where their `label-printer` checkout lives.

**Default tape: 12mm.** Many users also stock 24mm; confirm tape width if it matters.

## Core workflow

1. **Understand the request.** What's being labeled, and which template fits?
2. **Pick a template.** Run `lp list` if you're unsure; run `lp show <qualified>` to see its field schema. Never invent a template.
3. **Dry-render a PNG preview.** Always. Save to `/tmp/label_preview.png` and show the user. Do NOT print without explicit confirmation.
4. **Confirm, then print.** Once the user approves, run `lp print ...`. Once real transports land, this sends to the physical printer; until then it dry-runs to a `.bin` file and you tell the user that.
5. **Prefer 12mm** unless the user says otherwise or the label obviously needs width (e.g. large multi-field spool label).

## Template catalog

Kitchen:
- `kitchen/pantry_jar` — name + purchased + optional expiry
- `kitchen/spice` — name + optional origin + best-by
- `kitchen/leftover` — contents + cooked date + auto eat-by
- `kitchen/freezer` — contents + frozen date + portion

Electronics:
- `electronics/cable_flag` — source + dest, fold-over label
- `electronics/component_bin` — value + footprint + optional tolerance
- `electronics/psu_polarity` — voltage + current + polarity icon

3D printing:
- `three_d_printing/filament_spool` — material + color + brand + opened + optional temps
- `three_d_printing/print_bin` — part + optional project + quantity
- `three_d_printing/tool_tag` — tool + optional owner

## Commands you will use

```bash
# Discover
lp list
lp list --category kitchen
lp show kitchen/pantry_jar

# Dry-render preview to PNG (no bytes go anywhere near the printer)
lp render kitchen/pantry_jar \
  -f name=FLOUR -f purchased=2026-04-19 \
  --png-out /tmp/label_preview.png

# Encode-only (dry-run). Writes the raster command stream to a file.
# This is the DEFAULT. No flag needed.
lp print kitchen/pantry_jar \
  -f name=FLOUR -f purchased=2026-04-19 \
  --bin-out /tmp/label.bin

# Actually print. Add --send ONLY after the user has approved the preview.
lp print kitchen/pantry_jar \
  -f name=FLOUR -f purchased=2026-04-19 \
  --send
```

**`--send` is the only way tape moves.** Without it, `lp print` is always a dry-run — it encodes + writes bytes but never drives the transport. Never pass `--send` without the user's explicit approval of the preview.

## Rules

- **Always dry-render first.** Show the user the PNG, get an OK, then print. Even after hardware is wired up, never skip the preview.
- **Field values go via repeated `-f key=value`.** Quote values with spaces.
- **Dates in ISO 8601** (`YYYY-MM-DD`). Convert relative dates ("today", "last Tuesday") before calling.
- **Use `lp show <template>` to check required fields** before constructing the command. Don't guess.
- **Free-form requests**: infer the best template, confirm your pick with the user before rendering. If multiple could fit (e.g. "label this jar of paprika"), ask.
- **If the user sends a photo**: read the text yourself from the image (vision) and extract the fields. Don't rely on OCR tooling — the model reads labels better than a CLI pipeline.

## Failure modes

- `lp` not found → tell the user to activate their `label-printer` venv, or set `LP=/abs/path/to/lp`.
- Template not found → run `lp list` and pick the closest match, or ask.
- Missing required field → `lp show` the template, prompt the user for the missing piece, then retry.
- USB/BT transport error → transports may still be stubs. Use `--transport dryrun` (the default) and report the `.bin` path.
