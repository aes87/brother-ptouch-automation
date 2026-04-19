# Creating a preset

Most new labels don't need a Python class — they just need a preset entry in a pack's `presets.toml`. The preset loader reads it at registry init and builds a full `Template` instance on the fly, complete with field schema, validation, and layout.

## When to use a preset vs a Python class

| Use a preset | Write a Python class |
|---|---|
| Two-line "big headline · small subtitle" with optional icon | Wrap-around geometry (cable flags) |
| Multiple optional fields composed into the subtitle | Polarity icons, GHS pictograms, colour swatches |
| A conditional suffix when some field is set | Anything that doesn't fit the two-line mold |
| A derived date (today + N days → eat-by) | Multi-face labels |

Around 30 of the 36 shipped labels are presets. The remaining 6 are Python because they have layouts no other template needs.

## Minimum viable preset

```toml
# src/label_printer/templates/kitchen/presets.toml

[[presets]]
qualified = "kitchen/teabag"
summary   = "Tea label: name + best-by."
layout    = "two_line"
primary   = "{name}"
secondary = [ "bb {best_by}" ]

[[presets.fields]]
name = "name"
required = true
example = "Lapsang Souchong"

[[presets.fields]]
name = "best_by"
required = true
example = "2027-06"
```

That's enough for `lp list` to show it, `lp show kitchen/teabag` to report its schema, and `lp render kitchen/teabag -f name=... -f best_by=...` to produce a label.

## Top-level keys

| Key | Required | Notes |
|---|---|---|
| `qualified` | yes | `<pack>/<name>`, e.g. `kitchen/teabag` |
| `summary` | no | One-line description shown in `lp list` |
| `layout` | no | Currently only `two_line` (default) |
| `default_tape` | no | mm, default 12 |
| `primary` | maybe | Plain string template for the headline (use either this or `primary_parts`) |
| `primary_parts` | maybe | List form — see below |
| `primary_join` | no | Separator when using `primary_parts` |
| `secondary` | no | List of plain strings and/or conditional fragments |
| `secondary_join` | no | Separator between non-empty `secondary` entries |
| `secondary_ratio` | no | Fraction of tape height for the subtitle (default 0.28) |
| `max_width_mm` | no | Longest line width budget (default 120) |
| `padding_mm` | no | Side padding (default 6) |
| `icon_field` | no | Name of a field whose value is a Lucide icon |
| `handles_extras` | no | List of compose-extras keys this preset handles internally (e.g. `["link"]`) |

## String templates

Use `{field_name}` placeholders anywhere in `primary`, `primary_parts[].text`, or `secondary[].text`. Missing optional fields resolve to an empty string (not the literal "None").

## Conditional fragments

A `secondary` or `primary_parts` entry can be a table with one of `if`, `if_all`, `if_any`:

```toml
secondary = [
  "{purchased}",
  { if = "expires", text = " · exp {expires}" },           # only when `expires` is set
  { if_all = ["origin", "year"], text = " · {origin} {year}" },
  { if_any = ["nozzle_temp", "bed_temp"], text = " · temps" },
]
```

"Set" means a truthy value. Strings like `"no"`, `"false"`, `"0"` are treated as falsy so boolean-ish fields (`fragile=yes`) work naturally.

## Joining non-empty parts

Use `secondary_join` (or `primary_join`) when you want a separator between non-empty parts, without leading / trailing / doubled separators:

```toml
secondary_join = " · "
secondary = [
  { if = "origin",  text = "{origin}" },
  { if = "best_by", text = "bb {best_by}" },
]
# origin + best_by:  "Spain · bb 2027-01"
# origin only:       "Spain"
# best_by only:      "bb 2027-01"
# neither:           ""
```

## Derived fields

For computed values (currently: date arithmetic), add one or more `[[presets.derived]]` entries. They run before string substitution so `{eat_by}` in `secondary` resolves correctly.

```toml
[[presets.derived]]
name       = "eat_by"
kind       = "date_offset"
from_field = "cooked"
days_field = "eat_within_days"
```

Only `date_offset` is supported today.

## Fields

Each `[[presets.fields]]` entry declares one field Claude / the CLI / the service can accept. Schema:

| Key | Notes |
|---|---|
| `name` | required |
| `required` | default `true` |
| `default` | used when the caller omits the field |
| `example` | shown in `lp show` and the docs site |
| `description` | longer explanation |

## Gotchas

- TOML **inline tables must fit on one line**. Use the `[[presets.fields]]` array-of-tables syntax for readable multi-line entries.
- Omit `primary_parts` if you set `primary`, and vice versa. The loader prefers `primary_parts` when both are present.
- Icons require the `[icons]` extra (pulls in `cairosvg`). The preset just passes the icon *name* through; rendering happens in the layout helper.
