"""Cable flag with wire-size-aware wrap section.

Layout (left to right, as the tape exits the printer):

    ┌─────────────────┬─────────────┬─────────────────┐
    │   source → dest │   wrap      │   source → dest │
    │   (front face)  │   (blank)   │   (back face)   │
    └─────────────────┴─────────────┴─────────────────┘

When wrapped around a cable, the wrap section circles the cable and the
two face sections stick together back-to-back. Both faces read the same
direction so the flag is legible whichever side is facing you.

The wrap width is computed from the cable's outer diameter (π·OD plus a
3 mm overlap for adhesive). Default is "ethernet" (5.5 mm OD).
"""

from __future__ import annotations

from PIL import Image

from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    draw_dashed_vline,
    draw_text,
    fit_text_to_box,
    font_line_height,
    mm_to_dots,
    text_width,
)
from label_printer.engine.wire import diameter_mm, wrap_length_mm
from label_printer.tape import TapeWidth, geometry_for
from label_printer.templates.base import Template, TemplateField, TemplateMeta


class CableFlagTemplate(Template):
    meta = TemplateMeta(
        category="electronics",
        name="cable_flag",
        summary="Cable flag: 'source → dest' printed on both faces with a wrap gap sized to the cable.",
        fields=[
            TemplateField("source", "Source end.", example="NAS"),
            TemplateField("dest", "Destination end.", example="SWITCH p3"),
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
        src = str(data["source"])
        dst = str(data["dest"])
        wire_spec = data.get("wire") or "ethernet"
        overlap = float(data.get("overlap_mm") or 3.0)

        od = diameter_mm(wire_spec)
        wrap_mm = wrap_length_mm(od, overlap_mm=overlap)
        wrap_dots = mm_to_dots(wrap_mm)

        text = f"{src} → {dst}"
        geom = geometry_for(tape)
        face_avail_h = geom.print_pins - 4
        face_min_mm = 18.0
        face_min_dots = mm_to_dots(face_min_mm)

        font = fit_text_to_box(text, mm_to_dots(60), face_avail_h, DEFAULT_BOLD)
        text_w = text_width(text, font)
        face_dots = max(face_min_dots, text_w + mm_to_dots(4))

        total = face_dots * 2 + wrap_dots
        canvas = LabelCanvas.create(tape, length_mm=total * 25.4 / 180)
        y = (geom.print_pins - font_line_height(font)) // 2

        # Front face (leftmost section)
        draw_text(canvas, text, font, face_dots // 2, y, anchor="mt")
        # Back face (rightmost section)
        draw_text(canvas, text, font, face_dots + wrap_dots + face_dots // 2, y, anchor="mt")

        # Dashed fold lines at both edges of the wrap section
        draw_dashed_vline(canvas, face_dots)
        draw_dashed_vline(canvas, face_dots + wrap_dots)
        return canvas.image
