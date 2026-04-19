"""Cable flag with optional QR code and small-print details.

Like ``electronics/cable_flag``, this prints two identical faces separated by
a wrap gap sized to the cable's outer diameter, so the flag reads the same
whichever side is facing you. Unlike the basic flag, each face carries:

    ┌─────────────────────────────┬──────┐
    │   TITLE (large, bold)       │      │
    │   ─────────────────────     │  QR  │
    │   date   detail line(s)     │      │
    └─────────────────────────────┴──────┘

QR and details are both optional. When ``link`` is omitted there is no QR,
and the text block expands to the full face width. The QR is a square
sized to the full print height; scan the flag with a phone (or have Claude
resolve a short-form like ``vault:...``).
"""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    DEFAULT_FONT,
    LabelCanvas,
    TwoLineLayout,
    draw_dashed_vline,
    draw_text,
    fit_text_to_box,
    load_font,
    mm_to_dots,
    split_lines_to_fit,
    text_width,
)
from label_printer.engine.qr import render_qr
from label_printer.engine.wire import diameter_mm, wrap_length_mm
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


def _detail_lines(data: dict) -> list[str]:
    """Gather the small-print lines: date first (if present), then details."""
    lines: list[str] = []
    date = data.get("date")
    if date:
        lines.append(str(date))
    details = data.get("details")
    if details:
        # Accept both real newlines and literal "\n" escapes (common from CLI / JSON callers).
        normalized = str(details).replace("\\n", "\n")
        for line in normalized.splitlines():
            line = line.strip()
            if line:
                lines.append(line)
    return lines


# Fraction of available face height reserved for small-print lines when the QR
# variant has any. Larger than TwoLineLayout's default 0.28 because the QR
# variant typically has 1-4 small lines (date + details) versus one subtitle.
_SMALL_RATIO = 0.32


class CableFlagQrTemplate(Template):
    meta = TemplateMeta(
        category="electronics",
        name="cable_flag_qr",
        summary=(
            "Cable flag with large title, small date/details, and optional QR on each face."
        ),
        fields=[
            TemplateField("title", "Large text on each face.", example="NAS → SW p3"),
            TemplateField(
                "date",
                "Small-print date line (ISO 8601 preferred).",
                required=False,
                example="2026-04-19",
            ),
            TemplateField(
                "details",
                "Small-print detail line(s). Use newlines to separate.",
                required=False,
                example="VLAN 20\\npatch A-14",
            ),
            TemplateField(
                "link",
                "QR payload — short-form (vault:, gh:), URL, or any opaque string. "
                "Omit to skip the QR.",
                required=False,
                example="vault:networking/nas-eth0",
            ),
            TemplateField(
                "wire",
                "Cable type or gauge — e.g. 'ethernet', 'hdmi', 'usb-c', '18 AWG', '5mm'. "
                "Default: ethernet (5.5mm OD).",
                required=False,
                default="ethernet",
                example="ethernet",
            ),
            TemplateField(
                "overlap_mm",
                "Extra length beyond a full wrap for adhesive-on-adhesive closure.",
                required=False,
                default=3.0,
                example="3.0",
            ),
        ],
        default_tape=TapeWidth.MM_12,
    )

    def render(self, data: dict, tape: TapeWidth) -> Image.Image:
        title = str(data["title"])
        link = data.get("link")
        lines = _detail_lines(data)
        wire_spec = data.get("wire") or "ethernet"
        overlap = float(data.get("overlap_mm") or 3.0)

        geom = geometry_for(tape)
        face_h = geom.print_pins

        # QR sits flush on the right edge of each face, square = full face height.
        qr_size = face_h if link else 0
        qr_gap = mm_to_dots(1.5) if link else 0

        # Vertical budget: title on top, small-lines block underneath. Start
        # from TwoLineLayout for padding/gap constants, then size the small
        # block as a total (not per-line) — TwoLineLayout.secondary_h reserves
        # one line of subtitle, but we may have several.
        layout = TwoLineLayout(tape=tape, secondary_ratio=_SMALL_RATIO)
        avail = layout.available
        title_y = layout.primary_y
        min_per_line = 8
        min_title_h = 12  # readable bold floor

        if lines:
            # Target total small-block height: cover min_per_line × N but at
            # least the configured secondary_ratio fraction.
            target_block = max(min_per_line * len(lines), layout.secondary_h)
            # Cap so the title still gets at least min_title_h.
            block_ceiling = max(min_per_line * len(lines), avail - min_title_h - layout.gap)
            small_block_h = min(target_block, block_ceiling)
            small_line_h = max(min_per_line, small_block_h // len(lines))
            # If min_per_line × N still exceeds block_ceiling, shrink per-line below floor.
            if small_line_h * len(lines) > avail - min_title_h - layout.gap:
                small_line_h = max(6, (avail - min_title_h - layout.gap) // len(lines))
            title_h = max(min_title_h, avail - small_line_h * len(lines) - layout.gap)
            small_block_y = title_y + title_h + layout.gap
        else:
            small_line_h = 0
            title_h = avail
            small_block_y = title_y + title_h

        # Size the title within a provisional horizontal budget. Width gets
        # finalised after we know how wide the small lines are.
        text_area_target = mm_to_dots(55)
        title_font = fit_text_to_box(title, text_area_target, title_h, DEFAULT_BOLD)
        title_w = text_width(title, title_font)

        # Small-line font: pinned by reserved height.
        small_font = load_font(DEFAULT_FONT, max(7, small_line_h - 2)) if lines else None

        # Wrap small lines to whichever is wider: the title or a 20mm floor.
        wrapped_small: list[str] = []
        if small_font:
            width_budget = max(title_w, mm_to_dots(20))
            for line in lines:
                wrapped_small.extend(split_lines_to_fit(line, width_budget, small_font))
            # If wrapping added lines, recompute the budget — the small block
            # grew vertically, so title_h needs to shrink to compensate.
            if len(wrapped_small) > len(lines):
                n = len(wrapped_small)
                block_ceiling = max(min_per_line * n, avail - min_title_h - layout.gap)
                small_block_h = min(max(min_per_line * n, layout.secondary_h), block_ceiling)
                small_line_h = max(min_per_line, small_block_h // n)
                if small_line_h * n > avail - min_title_h - layout.gap:
                    small_line_h = max(6, (avail - min_title_h - layout.gap) // n)
                small_font = load_font(DEFAULT_FONT, max(6, small_line_h - 2))
                title_h = max(min_title_h, avail - small_line_h * n - layout.gap)
                title_font = fit_text_to_box(title, text_area_target, title_h, DEFAULT_BOLD)
                title_w = text_width(title, title_font)
                small_block_y = title_y + title_h + layout.gap

        small_w = (
            max((text_width(line, small_font) for line in wrapped_small), default=0)
            if small_font
            else 0
        )
        text_w = max(title_w, small_w)

        # Face length: text area + side padding + QR (if any).
        face_text_pad = mm_to_dots(2)
        face_dots = face_text_pad + text_w + mm_to_dots(2) + qr_gap + qr_size
        face_min_dots = mm_to_dots(20)
        face_dots = max(face_dots, face_min_dots)

        od = diameter_mm(wire_spec)
        wrap_mm = wrap_length_mm(od, overlap_mm=overlap)
        wrap_dots = mm_to_dots(wrap_mm)

        total = face_dots * 2 + wrap_dots
        canvas = LabelCanvas.create(tape, length_mm=total * 25.4 / 180)

        # Render the QR once — both faces carry an identical copy.
        qr_img = render_qr(str(link), qr_size) if link else None

        for face_x in (0, face_dots + wrap_dots):
            if qr_img is not None:
                canvas.image.paste(qr_img, (face_x + face_dots - qr_size, 0))

            text_x = face_x + face_text_pad

            draw_text(canvas, title, title_font, text_x, title_y, anchor="lt")

            if small_font and wrapped_small:
                cursor_y = small_block_y
                for line in wrapped_small:
                    draw_text(canvas, line, small_font, text_x, cursor_y, anchor="lt")
                    cursor_y += small_line_h

        # Dashed fold lines at both edges of the wrap section.
        draw_dashed_vline(canvas, face_dots)
        draw_dashed_vline(canvas, face_dots + wrap_dots)
        return canvas.image
