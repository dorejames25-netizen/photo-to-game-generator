"""Analog VHS / CRT degradation for finished stills (offline twin of the Godot shader)."""
import cv2
import numpy as np

from .imageio import merge_alpha, split_alpha
from .presets import load_preset


def vhs(img, preset="nightmare", seed=None, label=None, **overrides):
    p = load_preset(preset) if isinstance(preset, str) else preset
    cfg = {**p["vhs"], **{k: v for k, v in overrides.items() if v is not None}}
    rng = np.random.default_rng(seed)
    bgr, alpha = split_alpha(img)
    h, w = bgr.shape[:2]
    out = bgr.astype(np.float32)
    px = max(0.5, w / 1000)  # pixel-based settings are tuned for ~1000px wide images
    cfg["aberration"] *= px; cfg["jitter"] *= px; cfg["wave"] *= px

    # 1. horizontal colour bleed (tape luma/chroma smear)
    out = cv2.blur(out, (3, 1))

    # 2. chromatic aberration: red right, blue left
    a = int(cfg["aberration"])
    if a:
        out[..., 2] = np.roll(out[..., 2], a, axis=1)
        out[..., 0] = np.roll(out[..., 0], -a, axis=1)

    # 3. tracking jitter + horizontal micro waves (per-row shift)
    rows = np.arange(h)
    shift = cfg["wave"] * np.sin(rows / h * np.pi * 18 + rng.uniform(0, 6.28))
    if cfg["jitter"]:
        shift += rng.normal(0, cfg["jitter"] * 0.35, h)
        for _ in range(rng.integers(1, 4)):  # a few torn bands
            y0 = rng.integers(0, h); bh = rng.integers(2, max(3, h // 40))
            shift[y0:y0 + bh] += rng.uniform(-1, 1) * cfg["jitter"] * 4
    shift = np.round(shift).astype(int)
    if np.any(shift):
        cols = (np.arange(w)[None, :] - shift[:, None]) % w
        out = out[rows[:, None], cols]

    # 4. tracking-error band near the bottom
    if cfg["tracking_band"]:
        y0 = int(h * rng.uniform(0.78, 0.9)); bh = max(4, h // 30)
        band = out[y0:y0 + bh]
        band += rng.normal(40, 35, band.shape[:2])[..., None]
        out[y0:y0 + bh] = np.roll(band, rng.integers(-w // 30, w // 30), axis=1)

    # 5. scanlines
    if cfg["scanlines"]:
        period = max(2, h // 270)
        mask = np.where((rows // (period // 2 or 1)) % 2 == 0, 1.0, 1.0 - cfg["scanlines"])
        out *= mask[:, None, None]

    # 6. film / tape grain
    if cfg["grain"]:
        out += rng.normal(0, 255 * cfg["grain"], (h, w))[..., None]

    # 7. bubble-lens vignette
    if cfg["vignette"]:
        yy, xx = np.mgrid[0:h, 0:w]
        d = ((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 2
        out *= np.clip(1 - d * cfg["vignette"] * 1.6, 0, 1)[..., None]

    out = np.clip(out, 0, 255).astype(np.uint8)

    if label:
        scale = max(0.4, w / 1400)
        th = max(1, int(scale * 2))
        (tw, tht), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, th)
        org = (int(w * 0.04), int(h * 0.94))
        cv2.putText(out, label, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (40, 255, 120), th, cv2.LINE_AA)

    return merge_alpha(out, alpha)
