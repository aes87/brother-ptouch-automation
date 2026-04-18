# Proposal 0001 — QR-code context linking

**Status**: open (feature request)
**Opened**: 2026-04-18
**Requested by**: @aes87

## One-line summary

Let any label optionally carry a small QR code that links back to the canonical "source of truth" for whatever's being labelled — an Obsidian vault note, a GitHub file, or any URL.

## Motivation

Labels tell you *what* something is. They don't tell you the stuff you only find out you wanted 6 months later:

- the spice is "Smoked Paprika", sure — but what did I pay? what's it good for? which recipe uses it?
- the filament is "PLA · Obsidian Black · Bambu" — but what were my slicer settings? did I calibrate? what was my last dry-box cycle?
- the cable is "NAS → SWITCH p3" — but which VLAN? which patch panel port?
- the print bin is "Fan tub clip v2" — but where's the STL, the README, the revision history?

All of that context exists in your Obsidian vault and your GitHub repos. The label just needs a stable way to point at it. Scan the QR with a phone → the right note / file / dashboard opens. Done.

## Core ideas

1. **Templates opt in to a `link` field**. If present, reserve a small QR region at the right edge of the label and encode the link. Text shrinks to accommodate — or the label grows — depending on tape width and caller preference.
2. **A link resolver turns short forms into full URLs**. Callers shouldn't have to write `obsidian://open?vault=MyVault&file=kitchen%2Fspice%2Fpaprika` every time. They write `vault:kitchen/spice/paprika` or `gh:aes87/3d-printing/designs/fan-tub-adapter/README.md` and the resolver expands it.
3. **Stable URLs are the caller's responsibility**. The resolver does not try to guarantee a note or file still exists — labels are printed, not regenerated. If you rename the vault note, the QR is stale. That's a feature (your label is a revision-stamped receipt) not a bug.
4. **Optional label→link index**. On print, write a row to `~/.config/label-printer/link_index.jsonl` (tape size, template, fields, resolved URL, timestamp). Lets you look up "what did that QR point to" even if the original intent is lost.

## Shortlink syntax

Keep it tiny and opinionated.

| Short form | Expands to |
|---|---|
| `https://…` / `http://…` | Passes through verbatim. |
| `vault:<note-path>` | `obsidian://open?vault=<vault>&file=<note-path>` — vault name from config. |
| `vault:<vault-name>:<note-path>` | Same, explicit vault override. |
| `gh:<owner>/<repo>/<path>` | `https://github.com/<owner>/<repo>/blob/main/<path>` — branch configurable. |
| `gh:<owner>/<repo>#<issue>` | `https://github.com/<owner>/<repo>/issues/<issue>`. |
| `gh:<path>` | Same as above but `owner/repo` defaulted from config. |
| `gist:<id>` | `https://gist.github.com/<owner>/<id>`. |

Examples:

```
vault:kitchen/spice/smoked-paprika
vault:Martha:inoculating/strains/lions-mane
gh:3d-printing/designs/fan-tub-adapter/README.md
gh:aes87/label-printer#12
```

Config lives in `~/.config/label-printer/links.toml`:

```toml
[vault]
default = "aes-vault"

[github]
default_owner = "aes87"
default_repo  = "brother-ptouch-automation"
default_branch = "main"
```

## Template integration

Two integration levels, in order of ambition.

### Level 1: a `link` field on existing templates

Every two-line template grows an optional `link` field. When set, the renderer leaves room for a small QR (tape-height square) at the right edge and encodes the resolved URL.

```bash
lp print kitchen/spice \
  -f name="Smoked Paprika" -f origin=Spain -f best_by=2027-01 \
  -f link=vault:kitchen/spice/smoked-paprika
```

Preview:

```
┌──────────────────────────────┬────┐
│  Smoked Paprika              │ QR │
│  Spain · bb 2027-01          │    │
└──────────────────────────────┴────┘
```

Trade-off: the QR gets small on 12mm tape (70 px = ~10 mm square) — that's about the limit of what a phone camera can reliably scan in the real world with error correction M. Narrow tapes (6mm, 9mm) are not viable for this.

### Level 2: a standalone "with_link" meta-template

Wrap any template in a decorator that appends a QR tail:

```bash
lp print kitchen/spice+link \
  -f name="Smoked Paprika" -f link=vault:kitchen/spice/smoked-paprika
```

Implementation is a meta-template that renders the inner template, appends a gap, and pastes a QR. Less invasive — no existing template signature changes.

### Level 3: dedicated `utility/labeled_qr`

Already half-covered by `utility/qr` with a caption. Could be renamed or given sugar for the short-link syntax: `lp print utility/qr -f data=vault:kitchen/spice/paprika -f caption=Paprika`.

## Open questions

- **Obsidian URI scanning UX**: if the phone doesn't have Obsidian installed, `obsidian://` URIs fail silently. Options:
  (a) always encode `vault://` as a raw `obsidian://` URI and accept that desktop-only;
  (b) encode a tiny web redirect (`https://my.site/l/<hash>`) that 302s to `obsidian://` on devices that support it, or shows a note summary otherwise. Requires hosting a resolver.
- **Default redirect service**: ship an optional `lp serve --links` mode that does the redirect, pulled from the same index file as option (b).
- **Hashing / short URLs**: for long GitHub URLs the QR gets dense. A local short-URL feature (`gh:…` → `go/l/abc`) is attractive but requires a resolver host.
- **Link rot detection**: a `lp links verify` command that walks the index and checks each URL (for vault notes: file exists; for GitHub: 200 on the raw endpoint). Reports broken ones. Optional Phase 6 nice-to-have.
- **Privacy**: the index file is local and plaintext. Fine. But a hosted redirect service would know every scan — explicitly opt-in if we ever build one.

## Acceptance criteria

- [ ] `label_printer.engine.links` module: resolves short forms → full URLs using config
- [ ] `~/.config/label-printer/links.toml` is read on startup; sensible defaults if absent
- [ ] `utility/qr` accepts short-form links in its `data` field
- [ ] At least two existing templates (`kitchen/spice` and `three_d_printing/filament_spool`) gain an optional `link` field
- [ ] CLI: `lp links resolve <short>` prints the expanded URL (debugging aid)
- [ ] CLI: on print, optionally append to `~/.config/label-printer/link_index.jsonl`
- [ ] Tests: resolver round-trip, at least one template with a rendered QR, no regressions on existing templates without `link`
- [ ] Docs: README section "Linking labels back to context"
- [ ] Proposal updated with the final chosen design and closed

## Non-goals

- Hosting a public redirect service (too much scope; maybe Phase 6).
- Writing an Obsidian plugin to backlink from note → printed label (can be a separate tool that reads the index file).
- Encoding the full note content in the QR (impractical, QRs cap out around 3 KB of text at low density).

## Rough sizing

Small feature. Resolver module + config loader + one or two template edits + tests: maybe a day. The fiddliness is in the QR fitting on 12 mm tape, not the linking logic.
