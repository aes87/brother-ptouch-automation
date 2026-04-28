# Proposal 0001 — QR-code context linking

**Status**: open (feature request)
**Opened**: 2026-04-18
**Updated**: 2026-04-18 (pivoted to "Claude resolves from a photo" after phone-compat discussion)
**Requested by**: @harteWired

## One-line summary

Let any label optionally carry a small QR code pointing at the canonical source of truth — an Obsidian vault note or a GitHub file — and let Claude resolve the link from a photo. The phone never has to understand the QR's contents.

## Motivation

Labels tell you *what* something is. They don't tell you the stuff you only find out you wanted 6 months later:

- the spice is "Smoked Paprika", sure — but what did I pay? what's it good for? which recipe uses it?
- the filament is "PLA · Obsidian Black · Bambu" — but what were my slicer settings? did I calibrate? what was my last dry-box cycle?
- the cable is "NAS → SWITCH p3" — but which VLAN? which patch panel port?
- the print bin is "Fan tub clip v2" — but where's the STL, the README, the revision history?

All of that context exists in the Obsidian vault and the GitHub repos. The label needs a stable way to point at it. Photograph the QR → Claude reads it → fetches the vault note or repo file → answers in chat. Done.

## The key insight: Claude is the resolver

An earlier draft of this proposal tried to design a QR payload that *any* phone's native scanner could open — `https://` for web, `obsidian://` for Obsidian URIs, hosted redirect services to bridge the gap. All of those are painful: they require publishing the vault, hosting infrastructure, or desktop-only caveats.

But we don't need any of that. The Telegram bridge + Claude Code on this machine already gives us a much better resolver:

1. User sees a label, photographs the QR with their phone
2. Sends the photo to Claude via Telegram
3. Claude reads the QR out of the image (vision)
4. Claude parses the short-form, reads the vault note / repo file directly, summarises in chat

The phone never has to understand the QR's contents. The QR can literally contain `vault:kitchen/spice/paprika` as a plain string — iOS and Android will shrug at that, but Claude won't.

### Why this is better than "encode a universal URL"

- **No URL scheme problem.** Native scanners don't need to handle anything.
- **No hosting.** No redirect service, no GitHub Pages site, no publishing the vault anywhere.
- **No "Obsidian not installed" dead-end.** The vault lives on the same machine as Claude; access is direct via `cli-anything-obsidian`.
- **Richer response.** "Open the note" is a poor interaction compared to "summarise the relevant part, answer my specific question, cross-reference the git history." Claude can do all of that in one exchange.
- **Works from anywhere you have your phone.** No device-local app requirement.

The plumbing already exists:

| Piece | Status |
|---|---|
| Telegram → Claude bridge | shipped (telegram-channel project) |
| Vault access from Claude | shipped (cli-anything-obsidian) |
| Repo access from Claude | trivially — the workspace is on the same disk |
| This project's skill | shipped; needs a small extension for "photo → resolve → summarise" |

## Design

### QR payload (short-form, opaque to the phone)

The QR contains a single short-form string. Whitespace-trimmed, ≤ 200 chars for QR density sanity.

| Short form | Meaning |
|---|---|
| `vault:<path>` | Obsidian vault note at `<path>` in the default vault |
| `vault:<name>:<path>` | Same, explicit vault |
| `gh:<owner>/<repo>/<path>` | GitHub file at HEAD on the default branch |
| `gh:<owner>/<repo>#<n>` | GitHub issue |
| `gh:<path>` | Uses default owner/repo from config |
| `gist:<id>` | Gist URL |
| `https://…` | Raw URL (Claude can still follow it) |
| `{"type":"filament_spool","spool_id":"..."}` | Arbitrary JSON — Claude figures out what to do |

For `gh:` short-forms, a human-scanned real URL is a free bonus: iOS/Android recognise `github.com/...` and open it even if the QR content started as `gh:...` after Claude expands it at print time. But this is sugar, not required — the primary reader is Claude.

### Config

`~/.config/label-printer/links.toml`:

```toml
[vault]
default = "aes-vault"

[github]
default_owner = "harteWired"
default_branch = "main"
```

### Claude-side resolver (new skill action)

Extend the `/label-printer` skill (or create a sibling `/label-lookup` skill) with a "photo → resolve" workflow:

1. Photo arrives in a Claude session (Telegram attachment, paste, etc.)
2. Skill runs QR detection (`pyzbar`, `qreader`, or similar) to extract the payload string
3. Parses the short-form:
   - `vault:<path>` → `cli-anything-obsidian` reads the note, skill summarises
   - `gh:<path>` → skill reads the file from the local repo clone, summarises
   - URL → skill opens with WebFetch
   - JSON → skill interprets the structure (e.g., filament spool → pull spool record + last-dry date)
4. Skill replies in-channel with the summary. If the user's original Telegram message included a question ("what temp do I print this at?"), answer it using the resolved context.

### Label printing side

Two levels of integration on the print surface:

1. **`utility/qr` is sufficient today**. Print `data=vault:kitchen/spice/paprika` and a caption and you're done. No new template needed.
2. **Optional: extend existing templates with a `link` field**. If set, reserve a small QR region at the right edge of the label and encode the resolved link. Existing fields unchanged, QR is opt-in per-label.

The at-print-time resolver (expanding `vault:...` → `obsidian://...`) becomes **optional** — only used if you want the QR to also work as a native URL on the phone, which is a nice-to-have for `gh:` targets and irrelevant for `vault:` ones.

## Acceptance criteria

**Core (printing side, done inside this repo)**

- [ ] `label_printer.engine.links` module: parses and validates short-forms, loads config
- [ ] `~/.config/label-printer/links.toml` with sensible defaults if absent
- [ ] `utility/qr` accepts short-form strings in its `data` field (no expansion needed — the short form is what Claude scans)
- [ ] At least two existing templates (`kitchen/spice`, `three_d_printing/filament_spool`) gain an optional `link` field that renders a small QR at the right edge
- [ ] CLI: `lp links resolve <short>` prints the expanded URL (debugging aid for the `gh:`/web side)
- [ ] Tests: short-form parsing, QR embedding in existing templates

**Resolver side (Claude-side, done in the skill)**

- [ ] Skill action: accept a photo, detect + decode the QR, parse the short-form
- [ ] `vault:` → read via cli-anything-obsidian, summarise relevant sections
- [ ] `gh:` → read the local clone of the repo, summarise
- [ ] URL / `https:` → WebFetch, summarise
- [ ] Unknown / unparseable → return the raw payload and say so
- [ ] When the user's message contains a question, answer it using the resolved context
- [ ] Reply via Telegram with the summary (+ optional follow-up)

**Docs**

- [ ] README: a "Linking labels back to context" section explaining the photo-to-Claude flow
- [ ] SKILL.md: updated with the new action

## Non-goals

- Hosting any public redirect or resolver service. The whole point of the pivot is we don't need one.
- Publishing the vault publicly. Still a private resource, read only by Claude on your machine.
- Writing an Obsidian plugin to backlink from note → printed label (can be a separate tool that reads a local index file, if you ever want it).
- Encoding full note content in the QR (impractical — QRs max out around 3 KB).
- Making QRs readable by arbitrary phone scanners when they contain `vault:` URIs. Claude is the intended reader; natives won't understand it and that's fine.

## Open questions

- **QR error correction**: on 12mm tape the QR is ~70×70 px ≈ 10×10 mm. Use error-correction level M (~15% redundancy) as today — fine for photo capture. Higher level = denser QR = harder to scan.
- **Short-form lifespan**: these strings become printed bytes on a jar. If we rename the syntax later (say we drop `gh:` in favour of `github:`), old labels break. Lock in the syntax before printing a lot. Version-tag the short-form (`v1:vault:...`) if we want forward flexibility.
- **Per-label metadata beyond the short-form**: do we also want a `label_id` in the QR for the local label→link index? Probably overkill — the short-form itself is the identity.
- **QR density budget**: an 18-char short-form (`vault:kitchen/spice/paprika`) encodes fine at 70 px. A 60-char GitHub URL (`gh:harteWired/brother-ptouch-automation/docs/proposals/0001-qr-context-linking.md`) is tighter. If this becomes a problem, introduce a short-hash alias mapping in a local TOML.

## Rough sizing

- Printing side: ~half a day. Short-form validator + config loader + `link` field on two templates + tests.
- Skill side: ~half a day. Add the photo-decode → resolve → summarise action to the existing skill, reuse `cli-anything-obsidian` for vault access.
- Polish + docs: a few hours.

Total: ≤ 1½ days of work across both sides.
