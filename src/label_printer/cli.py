"""Command-line entry point: `lp`."""

from __future__ import annotations

from pathlib import Path

import click
from PIL import Image

from label_printer import RasterOptions, TapeWidth, encode_job
from label_printer import state as state_mod
from label_printer.tape import geometry_for
from label_printer.templates import default_registry
from label_printer.transport.dryrun import DryRunTransport


def _tape_from_mm(mm: int) -> TapeWidth:
    try:
        return TapeWidth(4 if mm in (3, 4) else mm)
    except ValueError as e:
        valid = ", ".join(str(int(t)) for t in TapeWidth)
        raise click.BadParameter(f"tape must be one of: {valid}") from e


def _default_tape() -> int:
    try:
        return state_mod.load().tape_mm
    except Exception:
        return 12


def _parse_fields(pairs: tuple[str, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise click.BadParameter(f"expected key=value, got {pair!r}")
        k, v = pair.split("=", 1)
        out[k.strip()] = v
    return out


@click.group()
@click.version_option()
def main() -> None:
    """Brother PT-P710BT label printer automation."""


# --- Registry-driven commands -----------------------------------------------

@main.command("list")
@click.option("--category", type=str, default=None, help="Filter by category.")
def list_templates(category: str | None) -> None:
    """List available label templates."""
    reg = default_registry()
    items = reg.by_category(category) if category else list(reg)
    if not items:
        click.echo("No templates found.")
        return
    width = max(len(t.meta.qualified) for t in items)
    for t in sorted(items, key=lambda x: x.meta.qualified):
        click.echo(f"  {t.meta.qualified:<{width}}  {t.meta.summary}")


@main.command()
@click.argument("qualified")
def show(qualified: str) -> None:
    """Show a template's field schema."""
    reg = default_registry()
    try:
        template = reg.get(qualified)
    except KeyError as e:
        raise click.ClickException(str(e)) from e
    click.echo(f"{template.meta.qualified}")
    click.echo(f"  {template.meta.summary}")
    click.echo(f"  default tape: {int(template.meta.default_tape)}mm")
    click.echo("  fields:")
    for f in template.meta.fields:
        req = "required" if f.required and f.default is None else "optional"
        default = f" (default: {f.default!r})" if f.default is not None else ""
        example = f"  e.g. {f.example!r}" if f.example else ""
        click.echo(f"    - {f.name}  [{req}]{default}{example}")
        click.echo(f"      {f.description}")


@main.command(name="render")
@click.argument("qualified")
@click.option("--tape", "tape_mm", type=int, default=None, help="Tape width in mm.")
@click.option("-f", "--field", "fields", multiple=True, help="key=value template field.")
@click.option("--png-out", type=click.Path(path_type=Path), default=None,
              help="Where to save the rendered PNG preview.")
@click.option("--bin-out", type=click.Path(path_type=Path), default=None,
              help="Where to save the raw command stream.")
def render_template(qualified: str, tape_mm: int | None, fields: tuple[str, ...],
                    png_out: Path | None, bin_out: Path | None) -> None:
    """Render a template to a PNG and/or raster command stream (no printing)."""
    reg = default_registry()
    try:
        template = reg.get(qualified)
    except KeyError as e:
        raise click.ClickException(str(e)) from e

    tape = _tape_from_mm(tape_mm) if tape_mm else template.meta.default_tape
    data = template.validate(_parse_fields(fields))
    image = template.render(data, tape)

    if png_out is None and bin_out is None:
        png_out = Path(f"out_{qualified.replace('/', '_')}_{int(tape)}mm.png")

    if png_out:
        png_out.parent.mkdir(parents=True, exist_ok=True)
        image.save(png_out)
        click.echo(f"png: {png_out}  ({image.width}×{image.height})")

    if bin_out:
        cmd_bytes = encode_job(image, tape)
        transport = DryRunTransport(bin_out)
        transport.send(cmd_bytes)
        click.echo(f"bin: {bin_out}  ({len(cmd_bytes)} bytes)")


@main.command(name="print")
@click.argument("qualified")
@click.option("--tape", "tape_mm", type=int, default=None)
@click.option("-f", "--field", "fields", multiple=True, help="key=value template field.")
@click.option("--transport", "transport_name",
              type=click.Choice(["dryrun", "usb", "bluetooth"]),
              default="dryrun", show_default=True)
@click.option("--bin-out", type=click.Path(path_type=Path), default=Path("out.bin"),
              help="For dryrun transport: where to write bytes.")
def print_template(qualified: str, tape_mm: int | None, fields: tuple[str, ...],
                   transport_name: str, bin_out: Path) -> None:
    """Encode + send a template-based label to the printer."""
    reg = default_registry()
    try:
        template = reg.get(qualified)
    except KeyError as e:
        raise click.ClickException(str(e)) from e

    tape = _tape_from_mm(tape_mm) if tape_mm else template.meta.default_tape
    data = template.validate(_parse_fields(fields))
    image = template.render(data, tape)
    cmd_bytes = encode_job(image, tape)

    if transport_name == "dryrun":
        transport = DryRunTransport(bin_out)
        transport.send(cmd_bytes)
        click.echo(transport.hex_preview(cmd_bytes))
        click.secho("dry-run: nothing was printed", fg="yellow")
        return

    raise click.ClickException(
        f"transport '{transport_name}' not available yet — arrives in Phase 5."
    )


# --- Image-to-raster passthrough (Phase 1 surface, still useful) ------------

@main.command("render-image")
@click.argument("image_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--tape", "tape_mm", type=int, default=None, show_default=True,
              help=f"Tape width in mm (default from state, currently {_default_tape()}).")
@click.option("--out", "out_path", type=click.Path(path_type=Path), default=Path("out.bin"),
              show_default=True, help="Where to write the raster command stream.")
@click.option("--no-auto-cut", is_flag=True)
@click.option("--mirror", is_flag=True)
@click.option("--feed-dots", type=int, default=14, show_default=True)
def render_image(image_path: Path, tape_mm: int | None, out_path: Path, no_auto_cut: bool,
                 mirror: bool, feed_dots: int) -> None:
    """Render an arbitrary image (skipping templates) to a command stream."""
    tape = _tape_from_mm(tape_mm) if tape_mm else _tape_from_mm(_default_tape())
    img = Image.open(image_path)
    options = RasterOptions(auto_cut=not no_auto_cut, mirror=mirror, feed_dots=feed_dots)
    data = encode_job(img, tape, options)
    transport = DryRunTransport(out_path)
    transport.send(data)
    click.echo(transport.hex_preview(data))


# --- State + geometry --------------------------------------------------------

@main.command()
@click.argument("width", type=int)
def tape(width: int) -> None:
    """Persist the currently-loaded tape width (mm)."""
    _tape_from_mm(width)  # validates
    state = state_mod.load()
    state.tape_mm = width
    path = state_mod.save(state)
    click.echo(f"tape = {width}mm  (saved to {path})")


@main.command("tape-info")
def tape_info() -> None:
    """Show geometry for each supported tape width."""
    click.echo(f"{'width':>7}  {'margin':>6}  {'print':>5}")
    for t in TapeWidth:
        geom = geometry_for(t)
        click.echo(f"{geom.display_mm:>5.1f}mm  {geom.margin_pins:>6}  {geom.print_pins:>5} pins")


@main.command()
def scan() -> None:
    """List connected printers (Phase 5 stub)."""
    click.echo("Hardware transports not wired up yet. Printer arrives 2026-04-19.")


# --- Service mode ------------------------------------------------------------

@main.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8765, show_default=True, type=int)
def serve(host: str, port: int) -> None:
    """Run the label-printer HTTP service (Phase 6 stub, dry-run only)."""
    try:
        import uvicorn
    except ImportError as e:
        raise click.ClickException(
            "Install the service extras: pip install -e '.[service]'"
        ) from e
    from label_printer.service import app

    click.echo(f"label-printer service on http://{host}:{port} (dry-run mode)")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
