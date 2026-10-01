"""Channel 2 — Photo-to-texture maps for low-poly meshes (gritty Chilla's Art style).

Flat-lit photo of a mask, face, fabric or surface → square, power-of-two texture with
baked lighting gradients removed, optionally made seamless for tiling.
"""
import cv2
import numpy as np

from .imageio import merge_alpha, split_alpha


def center_square(img):
    h, w = img.shape[:2]
    s = min(h, w)
    y, x = (h - s) // 2, (w - s) // 2
    return img[y:y + s, x:x + s]


def delight(bgr, strength=1.0):
    """Divide out large-scale lighting so the engine's lights do the work."""
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    l = lab[..., 0]
    sigma = max(l.shape) / 8
    low = cv2.GaussianBlur(l, (0, 0), sigma) + 1.0
    flat = l / low * l.mean()
    lab[..., 0] = np.clip(l * (1 - strength) + flat * strength, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2BGR)


def make_seamless(img):
    """Offset-and-blend: edges come from the half-shifted copy, centre from the original."""
    h, w = img.shape[:2]
    shifted = np.roll(img, (h // 2, w // 2), axis=(0, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.maximum(np.abs(xx / (w - 1) - 0.5), np.abs(yy / (h - 1) - 0.5)) * 2  # 0 centre → 1 edge
    wgt = np.clip((edge - 0.5) / 0.5, 0, 1) ** 1.5
    wgt = wgt[..., None] if img.ndim == 3 else wgt
    return (img * (1 - wgt) + shifted * wgt).astype(np.uint8)


def nearest_pow2(n, cap=4096):
    p = 1
    while p * 2 <= min(n, cap):
        p *= 2
    return p


def make_texture(img, size=None, flatten=True, seamless=False):
    bgr, alpha = split_alpha(center_square(img))
    if flatten:
        bgr = delight(bgr)
    out = merge_alpha(bgr, alpha)
    if seamless:
        out = make_seamless(out)
    size = size or nearest_pow2(out.shape[0])
    return cv2.resize(out, (size, size), interpolation=cv2.INTER_AREA)
