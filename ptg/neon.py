"""Neon relight: ink-line tracing + gradient-map colour grading of a real photo.

Evolution of the original process_character.py: instead of three hard brightness
bands it maps luminance through the preset's colour ramp (smooth, or posterized for a
cel-shaded look), boosts local contrast first, and lays traced ink lines on top.
"""
import cv2
import numpy as np

from .imageio import merge_alpha, split_alpha
from .presets import load_preset, ramp_lut


def local_contrast(bgr, clip=2.5):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


def ink_lines(bgr, block=0, c=6, thickness=1):
    """Returns a 0..255 mask: 0 where an ink line is, 255 elsewhere.
    block=0 picks a neighbourhood size from the image size so results match at any resolution."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    for _ in range(2):  # flatten skin/fabric/rock noise, keep real edges
        gray = cv2.bilateralFilter(gray, 9, 60, 60)
    if not block:
        block = max(9, min(gray.shape) // 30)
    block = block if block % 2 else block + 1
    lines = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY, block, c)
    lines = cv2.medianBlur(lines, 3)  # drop speckle
    if thickness > 1:
        lines = cv2.erode(lines, np.ones((thickness, thickness), np.uint8))
    return lines


def posterize(gray, levels):
    step = 255.0 / (levels - 1)
    return (np.round(gray / step) * step).astype(np.uint8)


def relight(img, preset="nightmare", ink=None, posterize_levels="preset"):
    p = load_preset(preset) if isinstance(preset, str) else preset
    bgr, alpha = split_alpha(img)

    boosted = local_contrast(bgr)
    gray = cv2.cvtColor(boosted, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 40, 40)
    levels = p["posterize"] if posterize_levels == "preset" else posterize_levels
    if levels:
        gray = posterize(gray, int(levels))

    out = ramp_lut(p["ramp"])[gray]

    ink_cfg = p["ink"]
    use_ink = ink_cfg["enabled"] if ink is None else ink
    if use_ink:
        lines = ink_lines(bgr, ink_cfg["block"], ink_cfg["c"], ink_cfg["thickness"])
        out = (out.astype(np.float32) * (lines[..., None] / 255.0)).astype(np.uint8)

    return merge_alpha(out, alpha)
