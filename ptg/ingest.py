"""Drop-zone ingestion: unzip packs, snake_case every name, route files into the asset tree.

Assets/DropZone/            ← dump anything here (zips, loose files)
Assets/DropZone/photos/     ← character / prop reference photos for the generator
        ↓  ptg sort
Assets/Photos  Textures  Models  Shaders  Audio  HDRI
"""
import re
import shutil
import zipfile
from pathlib import Path

ROUTES = {
    "Textures": {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp", ".tif", ".tiff", ".dds", ".ktx"},
    "Models": {".fbx", ".obj", ".glb", ".gltf", ".blend", ".dae", ".mtl", ".bin"},
    "Shaders": {".gdshader", ".gdshaderinc", ".shader", ".glsl", ".hlsl"},
    "Audio": {".wav", ".ogg", ".mp3", ".flac"},
    "HDRI": {".hdr", ".exr"},
}
SKIP = {".gitkeep", ".ds_store", "thumbs.db", "desktop.ini"}


def snake_case(name):
    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    stem = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower()
    return (stem or "unnamed") + suffix


def route_for(path, in_photos):
    if in_photos:
        return "Photos"
    ext = Path(path).suffix.lower()
    for folder, exts in ROUTES.items():
        if ext in exts:
            return folder
    return None


def _unique(dest):
    if not dest.exists():
        return dest
    i = 2
    while (d := dest.with_name(f"{dest.stem}_{i}{dest.suffix}")).exists():
        i += 1
    return d


def sort_dropzone(dropzone="Assets/DropZone", assets="Assets", dry_run=False):
    dz, root = Path(dropzone), Path(assets)
    report = {"moved": [], "unknown": [], "unzipped": []}

    for z in list(dz.rglob("*.zip")):
        target = z.with_suffix("")
        if not dry_run:
            with zipfile.ZipFile(z) as zf:
                for member in zf.namelist():  # zip-slip guard
                    if Path(member).is_absolute() or ".." in Path(member).parts:
                        raise ValueError(f"Unsafe path in {z.name}: {member}")
                zf.extractall(target)
            z.unlink()
        report["unzipped"].append(str(z))

    for f in sorted(p for p in dz.rglob("*") if p.is_file()):
        if f.name.lower() in SKIP or "__macosx" in (s.lower() for s in f.parts):
            continue
        in_photos = "photos" in (s.lower() for s in f.relative_to(dz).parts[:-1])
        folder = route_for(f, in_photos)
        if not folder:
            report["unknown"].append(str(f))
            continue
        dest = _unique(root / folder / snake_case(f.name))
        report["moved"].append((str(f), str(dest)))
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), dest)

    if not dry_run:  # tidy now-empty folders (keep photos/ and DropZone itself)
        for d in sorted((p for p in dz.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
            if d.name.lower() != "photos" and not any(d.iterdir()):
                d.rmdir()
    return report
