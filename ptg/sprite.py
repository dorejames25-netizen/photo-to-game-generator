"""Channel 1 — Digitized 2D sprites (Doom / Mortal Kombat style).

Cut-out photo → crop to subject → crunchy low-res grid → indexed colour palette PNG.
Directional shots named <name>_<front|back|left|right|...>.png can be packed into sheets.
"""
import re
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .imageio import split_alpha
from .presets import load_preset, palette_bgr

ANGLE_ORDER = ["front", "front_right", "right", "back_right", "back",
               "back_left", "left", "front_left"]
ANGLE_RE = re.compile(r"^(?P<base>.+?)_(?P<angle>" + "|".join(sorted(ANGLE_ORDER, key=len, reverse=True)) + r")$")


def crop_to_subject(img, pad=0.04):
    bgr, alpha = split_alpha(img)
    if alpha is None:
        return img
    ys, xs = np.where(alpha > 16)
    if not len(ys):
        return img
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    p = int(max(y1 - y0, x1 - x0) * pad)
    h, w = alpha.shape
    return img[max(0, y0 - p):min(h, y1 + p), max(0, x0 - p):min(w, x1 + p)]


def fit_square(img, size):
    """Scale the longest side to `size` and centre on a transparent square canvas."""
    if img.shape[-1] == 3:
        img = np.dstack([img, np.full(img.shape[:2], 255, np.uint8)])
    h, w = img.shape[:2]
    s = size / max(h, w)
    nh, nw = max(1, round(h * s)), max(1, round(w * s))
    small = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((size, size, 4), np.uint8)
    y, x = (size - nh), (size - nw) // 2  # feet on the floor
    canvas[y:y + nh, x:x + nw] = small
    return canvas


def kmeans_palette(bgr, alpha, n):
    px = bgr[alpha > 127] if alpha is not None else bgr.reshape(-1, 3)
    px = np.float32(px)
    n = max(2, min(n, len(px)))
    _, _, centers = cv2.kmeans(px, n, None,
                               (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0),
                               3, cv2.KMEANS_PP_CENTERS)
    return centers.astype(np.uint8)


def quantize(bgr, pal):
    d = ((bgr[:, :, None, :].astype(np.int32) - pal[None, None].astype(np.int32)) ** 2).sum(-1)
    return d.argmin(-1).astype(np.uint8)


def to_indexed_png(bgra, pal, path):
    """Write a true palette-indexed PNG (index 0 = transparent) — tiny and engine friendly."""
    bgr, alpha = bgra[..., :3], bgra[..., 3]
    idx = quantize(bgr, pal) + 1
    idx[alpha < 128] = 0
    rgb_pal = [0, 0, 0]
    for b, g, r in pal:
        rgb_pal += [int(r), int(g), int(b)]
    im = Image.fromarray(idx, mode="P")
    im.putpalette(rgb_pal + [0] * (768 - len(rgb_pal)))
    path = Path(path).with_suffix(".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, transparency=0, optimize=True)
    return path


def make_sprite(img, size=128, preset="nightmare", colors=None):
    """Returns (bgra_sprite, palette). colors=N uses an adaptive N-colour palette instead of the preset's."""
    p = load_preset(preset) if isinstance(preset, str) else preset
    sprite = fit_square(crop_to_subject(img), size)
    bgr, alpha = sprite[..., :3], sprite[..., 3]
    alpha = np.where(alpha > 127, 255, 0).astype(np.uint8)  # crisp pixel edges
    pal = kmeans_palette(bgr, alpha, colors) if colors else palette_bgr(p)
    snapped = pal[quantize(bgr, pal)]
    return np.dstack([snapped, alpha]), pal


def group_by_angle(paths):
    groups = defaultdict(dict)
    for path in paths:
        m = ANGLE_RE.match(Path(path).stem)
        if m:
            groups[m["base"]][m["angle"]] = path
    return groups


def pack_sheet(frames):
    """Horizontal strip in ANGLE_ORDER. frames: {angle: bgra}"""
    ordered = [frames[a] for a in ANGLE_ORDER if a in frames]
    return np.hstack(ordered), [a for a in ANGLE_ORDER if a in frames]
