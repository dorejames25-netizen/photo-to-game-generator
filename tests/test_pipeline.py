import json
import zipfile

import cv2
import numpy as np
import pytest
from PIL import Image

from ptg import cli, cutout, ingest, neon, sprite, texture, vhs
from ptg.presets import list_presets, load_preset, ramp_lut


def figure_on(backdrop, size=(320, 240)):
    """A rough 'person' (head + body) on a green or white backdrop."""
    h, w = size
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (40, 200, 40) if backdrop == "green" else (250, 250, 250)
    cv2.circle(img, (w // 2, h // 4), h // 9, (120, 150, 200), -1)
    cv2.rectangle(img, (w // 2 - 35, h // 4 + 30), (w // 2 + 35, h - 20), (60, 30, 30), -1)
    cv2.line(img, (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), (230, 230, 230), 3)
    return img


def test_presets_load_and_ramps_build():
    assert {"nightmare", "outrun", "graphic_novel"} <= set(list_presets())
    for name in list_presets():
        p = load_preset(name)
        assert ramp_lut(p["ramp"]).shape == (256, 3)
    with pytest.raises(FileNotFoundError):
        load_preset("does_not_exist")


@pytest.mark.parametrize("backdrop", ["green", "white"])
def test_auto_cutout_detects_backdrop(backdrop):
    img = figure_on(backdrop)
    assert cutout.detect_backdrop(img) == backdrop
    out = cutout.remove_background(img, "auto")
    assert out.shape[-1] == 4
    alpha = out[..., 3]
    assert alpha[2, 2] < 10                              # corner is transparent
    assert alpha[img.shape[0] // 2, img.shape[1] // 2] > 245  # body is solid


def test_relight_keeps_alpha_and_uses_ramp():
    cut = cutout.remove_background(figure_on("green"), "green")
    art = neon.relight(cut, "outrun", ink=False, posterize_levels=None)
    assert art.shape == cut.shape
    assert np.array_equal(art[..., 3], cut[..., 3])


def test_sprite_is_indexed_and_transparent(tmp_path):
    cut = cutout.remove_background(figure_on("green"), "green")
    spr, pal = sprite.make_sprite(cut, 64, "nightmare")
    assert spr.shape == (64, 64, 4)
    assert set(np.unique(spr[..., 3])) <= {0, 255}
    path = sprite.to_indexed_png(spr, pal, tmp_path / "s.png")
    im = Image.open(path)
    assert im.mode == "P" and im.info.get("transparency") == 0
    assert len(np.unique(np.asarray(im))) <= len(pal) + 1


def test_sheet_grouping_orders_angles():
    groups = sprite.group_by_angle(["stalker_walk_back.png", "stalker_walk_front.png",
                                    "stalker_walk_left.png", "random.png"])
    assert set(groups) == {"stalker_walk"}
    frames = {a: np.zeros((8, 8, 4), np.uint8) for a in groups["stalker_walk"]}
    sheet, order = sprite.pack_sheet(frames)
    assert order == ["front", "back", "left"] and sheet.shape == (8, 24, 4)


def test_texture_is_power_of_two_and_seamless():
    ramp = np.tile(np.linspace(0, 255, 500, dtype=np.uint8), (300, 1))  # hard seam when tiled
    img = np.dstack([ramp] * 3)
    raw = texture.make_texture(img, flatten=False)
    tex = texture.make_texture(img, flatten=False, seamless=True)
    assert tex.shape[0] == tex.shape[1] == 256
    seam = lambda t: np.abs(t[:, 0].astype(int) - t[:, -1].astype(int)).mean()
    assert seam(raw) > 100 and seam(tex) < 10


def test_vhs_same_size_and_deterministic():
    img = figure_on("white")
    a = vhs.vhs(img, "nightmare", seed=3)
    b = vhs.vhs(img, "nightmare", seed=3)
    assert a.shape == img.shape and np.array_equal(a, b)


def test_snake_case():
    assert ingest.snake_case("Villain Stalker-Walk FRONT.PNG") == "villain_stalker_walk_front.png"
    assert ingest.snake_case("rustyMetal01.jpg") == "rusty_metal01.jpg"


def test_sort_dropzone_routes_and_unzips(tmp_path):
    dz, assets = tmp_path / "DropZone", tmp_path / "Assets"
    (dz / "photos").mkdir(parents=True)
    cv2.imwrite(str(dz / "photos" / "Hero Front.jpg"), figure_on("green"))
    (dz / "Hum Loop.WAV").write_bytes(b"RIFF")
    (dz / "notes.xyz").write_text("?")
    with zipfile.ZipFile(dz / "pack.zip", "w") as z:
        z.writestr("Concrete Tile.png", b"x")
        z.writestr("models/Crate.FBX", b"x")
    r = ingest.sort_dropzone(dz, assets)
    assert (assets / "Photos" / "hero_front.jpg").exists()
    assert (assets / "Audio" / "hum_loop.wav").exists()
    assert (assets / "Textures" / "concrete_tile.png").exists()
    assert (assets / "Models" / "crate.fbx").exists()
    assert r["unknown"] == [str(dz / "notes.xyz")]
    assert not (dz / "pack.zip").exists()


def test_cli_end_to_end(tmp_path):
    dz, assets = tmp_path / "DropZone", tmp_path / "Assets"
    (dz / "photos").mkdir(parents=True)
    for ang in ("front", "back", "left", "right"):
        cv2.imwrite(str(dz / "photos" / f"stalker_idle_{ang}.png"), figure_on("green"))
    assert cli.main(["run", "--dropzone", str(dz), "--assets", str(assets), "--size", "64"]) == 0
    assert len(list((assets / "Textures" / "Characters").glob("*.png"))) == 4
    sheet = assets / "Sprites" / "stalker_idle_sheet_64.png"
    assert sheet.exists() and Image.open(sheet).size == (256, 64)
