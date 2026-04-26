"""Pin the small-text sharpening fixes from issue #3.

Each test fences off one of the regressions a future refactor could re-introduce:

* fontmode is set per-draw based on the font: bitmap (Spleen) and small
  outline glyphs render aliased ('1'); large outline glyphs keep AA on
  ('L'). A blanket fontmode='1' staircases big text — that was the
  overcorrection in the first sharpening pass. A blanket 'L' grey-fringes
  small text. The policy must remain conditional.
* Text positions must be integer pixels: passing ``y = (h - line_h) // 2``
  is fine, but adding floats anywhere upstream smears glyphs across
  thresholded columns.
* The font registry picks Spleen for small targets and DejaVu for large.
  The boundary is ``BITMAP_THRESHOLD_PX`` — locking it in here means a
  later "clean up the registry" pass can't silently swap which font small
  text gets.
* ``image.to_monochrome`` must keep the no-dither threshold path. Pillow's
  ``convert('1')`` defaults to Floyd-Steinberg dithering, which scatters
  grey pixels through black text — we must keep using ``point()``.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from label_printer.engine.fonts import (
    BITMAP_THRESHOLD_PX,
    SPLEEN_DIR,
    is_bitmap_font,
    pick_font,
)
from label_printer.engine.image import to_monochrome
from label_printer.engine.layout import (
    DEFAULT_BOLD,
    LabelCanvas,
    TwoLineLayout,
    draw_text,
    load_font,
    render_two_line_label,
)
from label_printer.tape import TapeWidth


def test_draw_text_uses_aliased_mode_for_bitmap_fonts():
    """Spleen glyphs render with fontmode='1' — they have no AA to disable."""
    canvas = LabelCanvas.create(TapeWidth.MM_12, length_mm=20)
    spleen = pick_font(16)
    assert is_bitmap_font(spleen)
    draw_text(canvas, "Hi", spleen, 2, 2, anchor="lt")
    assert canvas.draw.fontmode == "1"


def test_draw_text_uses_aliased_mode_for_small_outline_fonts():
    """Small (≤14px cap) DejaVu rendering must drop AA — at this size
    AA-then-threshold gives inconsistent stems, the original bug."""
    canvas = LabelCanvas.create(TapeWidth.MM_12, length_mm=20)
    small = load_font(DEFAULT_BOLD, 12)  # cap height ~9px
    cap_h = small.getbbox("A")[3] - small.getbbox("A")[1]
    assert cap_h <= 14
    draw_text(canvas, "x", small, 2, 2, anchor="lt")
    assert canvas.draw.fontmode == "1"


def test_draw_text_keeps_antialiasing_for_large_outline_fonts():
    """Large (>14px cap) DejaVu rendering must keep AA on — at 18px+ the
    stems are wide enough that AA looks smooth, and forcing aliased mode
    here is what made big headlines stairstep."""
    canvas = LabelCanvas.create(TapeWidth.MM_12, length_mm=20)
    big = load_font(DEFAULT_BOLD, 40)  # cap height ~28px
    cap_h = big.getbbox("A")[3] - big.getbbox("A")[1]
    assert cap_h > 14
    draw_text(canvas, "X", big, 2, 2, anchor="lt")
    assert canvas.draw.fontmode == "L"


def test_label_canvas_does_not_pin_fontmode_globally():
    """The canvas constructor must NOT pre-set fontmode='1' globally —
    that's what stairsteps every big-text label. Pillow's default for
    an RGB canvas is 'L' (AA on), and ``draw_text`` flips it per-call.
    """
    canvas = LabelCanvas.create(TapeWidth.MM_12, length_mm=20)
    # Whatever Pillow defaults to is fine, but it must not be '1' — that
    # would mean we re-introduced the global override.
    assert canvas.draw.fontmode != "1"


def test_two_line_label_small_line_renders_without_grey_pixels():
    """Spleen-rendered small line must threshold to pure black and white.

    The big line above it is allowed to have grey pixels (AA on), but the
    Spleen subtitle has no AA to begin with so its rows must be 0/255.
    We check the bottom strip of the label only.
    """
    img = render_two_line_label(TapeWidth.MM_12, "AP Flour", "2026-04-19", padding_mm=2.0)
    # Bottom 18 rows are the secondary band on a 70-pin canvas.
    bottom = img.crop((0, img.height - 18, img.width, img.height))
    pixels = set(bottom.convert("L").getdata())
    assert pixels <= {0, 255}, f"grey pixels in Spleen-rendered subtitle band: {pixels - {0, 255}}"


def test_draw_text_rounds_float_coordinates():
    """Float coords (e.g. (canvas.length - text_w) / 2) must snap to integer pixels.

    Pillow itself silently floors floats; the fix lifts that to an explicit
    ``int(round(...))`` so e.g. ``y=12.5`` lands on row 13, not 12. This
    matters most when callers compute centred positions and end up with
    ``.5`` offsets — the rounding change shifts text by up to one pixel
    versus old behaviour, which is the entire point.
    """
    canvas = LabelCanvas.create(TapeWidth.MM_12, length_mm=30)
    font = load_font(None, 12)
    # Drawing at (12.6, 12.6) with rounding goes to (13, 13). With Pillow's
    # default float-floor it would go to (12, 12). We don't assert position
    # directly — instead we assert the rendered image is identical to drawing
    # at the rounded integer coordinates.
    canvas2 = LabelCanvas.create(TapeWidth.MM_12, length_mm=30)
    draw_text(canvas, "Test", font, 12.6, 12.6, anchor="lt")
    draw_text(canvas2, "Test", font, 13, 13, anchor="lt")
    assert list(canvas.image.getdata()) == list(canvas2.image.getdata())


def test_pick_font_returns_bitmap_for_small_sizes():
    """Cap-height in [smallest-Spleen, BITMAP_THRESHOLD_PX] → a Spleen cut."""
    for size in (12, 13, 14, BITMAP_THRESHOLD_PX):
        font = pick_font(size)
        assert is_bitmap_font(font), f"size {size}px should pick Spleen (got {font.path})"


def test_pick_font_returns_outline_for_large_sizes():
    """Cap-height > threshold → a DejaVu outline glyph (proportional letters)."""
    font = pick_font(BITMAP_THRESHOLD_PX + 4)
    assert not is_bitmap_font(font)
    # Sanity: the path is one of the bundled DejaVu cuts.
    assert "DejaVu" in str(font.path)


def test_pick_font_picks_largest_fitting_spleen():
    """At a 16-pixel target, Spleen 8x16 fits exactly and should win."""
    font = pick_font(16)
    assert is_bitmap_font(font)
    # The 8x16 cut has a cap height of 16 (full em).
    assert font.getbbox("A")[3] == 16


def test_pick_font_falls_through_below_smallest_bitmap():
    """If the target is smaller than the smallest Spleen variant, fall back."""
    font = pick_font(10)  # smaller than Spleen 6x12's 12-pixel native cap
    # Either falls back to outline OR uses a smaller bitmap if one existed —
    # in our bundle the smallest is 6x12, so this must be DejaVu Bold.
    assert not is_bitmap_font(font), (
        f"no bitmap variant fits 10px, expected outline fallback (got {font.path})"
    )


def test_to_monochrome_uses_no_dither_threshold():
    """A grey 'L' image must threshold cleanly: every pixel is exactly 0 or 1.

    If anyone swaps ``point(...)`` for ``convert('1')`` Pillow's
    Floyd-Steinberg dithering will scatter grey-ish 1-bit pixels through
    flat-grey regions. This test catches that regression: a uniform grey
    field becomes either fully white or fully black, never speckled.
    """
    # Just-above-threshold grey: must threshold to all white.
    img = Image.new("L", (32, 32), 130)
    mono = to_monochrome(img)
    assert mono.mode == "1"
    assert set(mono.getdata()) == {255}, "speckled — dithering may have leaked in"

    # Just-below-threshold grey: must threshold to all black.
    img2 = Image.new("L", (32, 32), 120)
    mono2 = to_monochrome(img2)
    assert set(mono2.getdata()) == {0}, "speckled — dithering may have leaked in"


def test_two_line_layout_default_snaps_subtitle_to_spleen_12x24_on_12mm():
    """v3 sharpening: 12mm secondary band must reserve 24 dots so ``pick_font``
    lands on Spleen 12x24 — bumped from the v2 8x16 cut after a printed
    sample showed the subtitle was the line begging for more pixels.
    """
    layout = TwoLineLayout(tape=TapeWidth.MM_12)
    assert layout.secondary_h == 24, (
        f"12mm subtitle must reserve 24 dots (Spleen 12x24), got {layout.secondary_h}"
    )
    font = pick_font(layout.secondary_h)
    assert is_bitmap_font(font)
    assert font.size == 24, f"expected Spleen 12x24, got size={font.size}"


def test_two_line_layout_default_snaps_subtitle_to_spleen_16x32_on_24mm():
    """24mm has plenty of vertical room; the same default ratio must promote
    the subtitle one Spleen tier higher to 16x32 — keeping the wider tape
    visually proportional to the 12mm rendering.
    """
    layout = TwoLineLayout(tape=TapeWidth.MM_24)
    assert layout.secondary_h == 32, (
        f"24mm subtitle must reserve 32 dots (Spleen 16x32), got {layout.secondary_h}"
    )
    font = pick_font(layout.secondary_h)
    assert is_bitmap_font(font)
    assert font.size == 32, f"expected Spleen 16x32, got size={font.size}"


def test_spleen_assets_present():
    """The Spleen bundle must be on disk, otherwise pick_font silently degrades."""
    for name in ("spleen-6x12.otb", "spleen-8x16.otb", "spleen-12x24.otb"):
        assert (SPLEEN_DIR / name).exists(), f"missing bundled Spleen asset: {name}"


def test_draw_text_helper_is_the_aliasing_chokepoint():
    """All template code goes through ``draw_text`` (or its helpers
    ``draw_row`` / ``draw_centered_text``). That's the chokepoint where
    fontmode is decided. If a template ever bypasses it and calls
    ``canvas.draw.text`` directly with a small outline font, AA leaks
    back in — this test pins that ``draw_text`` is what flips the mode,
    not the canvas constructor.
    """
    canvas = LabelCanvas.create(TapeWidth.MM_12, length_mm=15)
    spleen = pick_font(16)
    # Bypass the helper: nothing forces the mode, so any leftover
    # state from a previous draw on this canvas would be in effect.
    # Confirm draw_text *itself* sets the mode each call.
    canvas.draw.fontmode = "L"
    draw_text(canvas, "Hi", spleen, 2, 2, anchor="lt")
    assert canvas.draw.fontmode == "1"


def test_two_line_label_descender_does_not_clip_secondary_row():
    """v3.1: title with descenders ('y', 'j') must keep its glyphs inside the
    primary row — descenders extend down into the descent space we reserved,
    but the secondary row's cap top still lives strictly below the lowest
    primary ink + the layout gap.

    Without this guarantee, baseline-anchoring the headline would push 'p',
    'g', 'y', 'j' tails into the subtitle's pixel band. We sized the
    primary's baseline-anchor offset by ``descender_max(font)`` precisely
    to dodge that — this test pins it.
    """
    layout = TwoLineLayout(tape=TapeWidth.MM_12)
    img = render_two_line_label(TapeWidth.MM_12, "Pottery jar", "2026-04-26", padding_mm=2.0)
    arr = img.convert("L").load()
    w, h = img.size

    # Bottom of the primary band of ink (anywhere in [0, secondary_y)).
    primary_bottom = -1
    for y in range(layout.secondary_y - 1, -1, -1):
        if any(arr[x, y] < 128 for x in range(w)):
            primary_bottom = y
            break
    # Top of the secondary band of ink (anywhere in [secondary_y, h)).
    secondary_top = h
    for y in range(layout.secondary_y, h):
        if any(arr[x, y] < 128 for x in range(w)):
            secondary_top = y
            break

    assert primary_bottom >= 0, "primary text didn't render"
    assert secondary_top < h, "secondary text didn't render"
    # Primary descender (the 'y' or 'j' tail) must end strictly above the
    # secondary row, not bleed into it.
    assert primary_bottom < layout.secondary_y, (
        f"primary descender at y={primary_bottom} reaches into secondary row "
        f"(starts at y={layout.secondary_y})"
    )
    # And secondary cap top must land at or below row top — i.e. it doesn't
    # collide upward into the gap.
    assert secondary_top >= layout.secondary_y, (
        f"secondary ink at y={secondary_top} bleeds above secondary row top "
        f"(y={layout.secondary_y})"
    )


def test_two_line_label_no_descender_title_eats_descent_slack():
    """v3.1: a no-descender title ('Japanese Sencha') must visibly fill the
    primary row down to its bottom, not float halfway up. Before baseline
    anchoring, the glyph cell reserved ~7-9 pins for descenders the text
    didn't have, leaving a fat gap above the subtitle. After: visible
    bottom of caps lands at row_bottom - descender_max, so the gap to the
    secondary cap is roughly ``descender_max + layout.gap`` (small) instead
    of ``descent_unused + layout.gap + cap_top_offset`` (large).

    We pin the visible gap to ≤ 5 pins on a 12mm tape — generous enough to
    survive small font-fit changes, tight enough to fail the regression we
    just fixed (the v3 gap was ~12 pins).
    """
    img = render_two_line_label(TapeWidth.MM_12, "Smoked Paprika", "Spain · bb 2027-01", padding_mm=2.0)
    arr = img.convert("L").load()
    w, h = img.size
    ink_rows = [any(arr[x, y] < 128 for x in range(w)) for y in range(h)]
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for y, ink in enumerate(ink_rows):
        if ink and start is None:
            start = y
        elif not ink and start is not None:
            runs.append((start, y - 1))
            start = None
    if start is not None:
        runs.append((start, h - 1))
    assert len(runs) >= 2, f"expected primary+secondary ink runs, got {runs}"
    visible_gap = runs[1][0] - runs[0][1] - 1
    assert visible_gap <= 5, (
        f"visible gap between primary and secondary is {visible_gap} pins — "
        f"v3.1 baseline-anchoring should keep it ≤ 5 (was ~12 in v3)"
    )


def test_imagedraw_default_fontmode_is_not_one():
    """Sanity — confirm the default *would* introduce greys, so the assertion
    in ``test_label_canvas_sets_fontmode_one`` is meaningful and not trivially
    satisfied by Pillow's defaults.
    """
    img = Image.new("RGB", (60, 24), "white")
    d = ImageDraw.Draw(img)
    # Default fontmode is 'L' on RGB canvases — antialiased.
    assert d.fontmode != "1"
