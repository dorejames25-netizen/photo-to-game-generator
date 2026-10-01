"""Command line: python -m ptg <command> ...   (or `ptg` after pip install -e .)"""
import argparse
import sys
from pathlib import Path

from . import cutout, imageio, ingest, neon, sprite, texture, vhs
from .presets import list_presets, load_preset


def _inputs(path):
    p = Path(path)
    if p.is_dir():
        return sorted(f for f in p.iterdir() if imageio.is_image(f))
    return [p]


def _out_for(src, out, suffix, ext=".png"):
    out = Path(out)
    if out.suffix:  # explicit file
        return out
    return out / f"{Path(src).stem}{suffix}{ext}"


def cmd_sort(a):
    r = ingest.sort_dropzone(a.dropzone, a.assets, a.dry_run)
    for z in r["unzipped"]:
        print(f"unzipped  {z}")
    for src, dst in r["moved"]:
        print(f"{'would move' if a.dry_run else 'moved'}  {src}  →  {dst}")
    for u in r["unknown"]:
        print(f"skipped (unknown type)  {u}")
    print(f"\n{len(r['moved'])} file(s) routed, {len(r['unknown'])} left in the drop zone.")


def cmd_character(a):
    p = load_preset(a.preset)
    for src in _inputs(a.input):
        img = imageio.read(src)
        if a.cutout != "none":
            img = cutout.remove_background(img, a.cutout)
        art = neon.relight(img, p, ink=False if a.no_ink else None)
        if a.vhs:
            art = vhs.vhs(art, p, seed=a.seed, label=a.label)
        dst = imageio.write(_out_for(src, a.output, f"_{p['name']}"), art)
        print(f"{src}  →  {dst}")


def cmd_sprite(a):
    p = load_preset(a.preset)
    files = _inputs(a.input)
    made = {}
    for src in files:
        img = imageio.read(src)
        if a.cutout != "none":
            img = cutout.remove_background(img, a.cutout)
        if a.relight:
            img = neon.relight(img, p)
        spr, pal = sprite.make_sprite(img, a.size, p, a.colors)
        dst = sprite.to_indexed_png(spr, pal, _out_for(src, a.output, f"_{a.size}"))
        made[src] = (spr, pal)
        print(f"{src}  →  {dst}  ({len(pal)} colours)")
    if a.sheet:
        for base, angles in sprite.group_by_angle(made).items():
            frames = {ang: made[path][0] for ang, path in angles.items()}
            sheet, order = sprite.pack_sheet(frames)
            pal = next(iter(made.values()))[1] if not a.colors else sprite.kmeans_palette(
                sheet[..., :3], sheet[..., 3], a.colors)
            out_dir = Path(a.output) if not Path(a.output).suffix else Path(a.output).parent
            dst = sprite.to_indexed_png(sheet, pal, out_dir / f"{base}_sheet_{a.size}.png")
            print(f"sheet  {base}: {' | '.join(order)}  →  {dst}")


def cmd_texture(a):
    for src in _inputs(a.input):
        tex = texture.make_texture(imageio.read(src), a.size, not a.keep_lighting, a.seamless)
        if a.preset:
            tex = neon.relight(tex, a.preset, ink=False)
        dst = imageio.write(_out_for(src, a.output, "_albedo"), tex)
        print(f"{src}  →  {dst}  ({tex.shape[1]}×{tex.shape[0]})")


def cmd_vhs(a):
    for src in _inputs(a.input):
        out = vhs.vhs(imageio.read(src), a.preset, seed=a.seed, label=a.label)
        dst = imageio.write(_out_for(src, a.output, "_vhs"), out)
        print(f"{src}  →  {dst}")


def cmd_run(a):
    """Full batch: sort the drop zone, then every photo → character art + sprite."""
    cmd_sort(argparse.Namespace(dropzone=a.dropzone, assets=a.assets, dry_run=False))
    photos = Path(a.assets) / "Photos"
    if not any(imageio.is_image(f) for f in photos.iterdir()):
        print("No photos in", photos)
        return
    print("\n— character art —")
    cmd_character(argparse.Namespace(input=str(photos), output=str(Path(a.assets) / "Textures" / "Characters"),
                                     preset=a.preset, cutout=a.cutout, no_ink=False, vhs=False, seed=None, label=None))
    print("\n— sprites —")
    cmd_sprite(argparse.Namespace(input=str(photos), output=str(Path(a.assets) / "Sprites"), preset=a.preset,
                                  cutout=a.cutout, relight=True, size=a.size, colors=None, sheet=True))


def cmd_presets(a):
    for name in list_presets():
        p = load_preset(name)
        print(f"{name:15} {p['description']}")


def build_parser():
    ap = argparse.ArgumentParser(prog="ptg", description="Photo-to-Game Generator")
    sub = ap.add_subparsers(dest="cmd", required=True)
    cut = dict(default="auto", choices=["auto", "green", "white", "rembg", "none"],
               help="background removal (default: auto)")

    s = sub.add_parser("sort", help="unzip + snake_case + route the drop zone into the asset tree")
    s.add_argument("--dropzone", default="Assets/DropZone"); s.add_argument("--assets", default="Assets")
    s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_sort)

    s = sub.add_parser("character", help="photo → neon ink-traced character art")
    s.add_argument("input"); s.add_argument("output")
    s.add_argument("--preset", default="nightmare"); s.add_argument("--cutout", **cut)
    s.add_argument("--no-ink", action="store_true"); s.add_argument("--vhs", action="store_true")
    s.add_argument("--label"); s.add_argument("--seed", type=int); s.set_defaults(fn=cmd_character)

    s = sub.add_parser("sprite", help="photo → pixelated indexed-palette sprite (channel 1)")
    s.add_argument("input"); s.add_argument("output")
    s.add_argument("--size", type=int, default=128); s.add_argument("--preset", default="nightmare")
    s.add_argument("--colors", type=int, help="adaptive N-colour palette instead of the preset's")
    s.add_argument("--relight", action="store_true", help="neon-grade before pixelating")
    s.add_argument("--sheet", action="store_true", help="pack <name>_front/back/left/right into a strip")
    s.add_argument("--cutout", **cut); s.set_defaults(fn=cmd_sprite)

    s = sub.add_parser("texture", help="flat photo → POT texture map for low-poly meshes (channel 2)")
    s.add_argument("input"); s.add_argument("output")
    s.add_argument("--size", type=int); s.add_argument("--seamless", action="store_true")
    s.add_argument("--keep-lighting", action="store_true"); s.add_argument("--preset", help="also colour-grade")
    s.set_defaults(fn=cmd_texture)

    s = sub.add_parser("vhs", help="apply VHS/CRT degradation to a finished image")
    s.add_argument("input"); s.add_argument("output")
    s.add_argument("--preset", default="nightmare"); s.add_argument("--label"); s.add_argument("--seed", type=int)
    s.set_defaults(fn=cmd_vhs)

    s = sub.add_parser("run", help="sort the drop zone, then batch every photo into art + sprites")
    s.add_argument("--dropzone", default="Assets/DropZone"); s.add_argument("--assets", default="Assets")
    s.add_argument("--preset", default="nightmare"); s.add_argument("--size", type=int, default=128)
    s.add_argument("--cutout", **cut); s.set_defaults(fn=cmd_run)

    s = sub.add_parser("presets", help="list the built-in looks"); s.set_defaults(fn=cmd_presets)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        a.fn(a)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
