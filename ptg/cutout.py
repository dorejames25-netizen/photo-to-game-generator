"""Background removal → BGRA.

Methods:
  green / white  chroma-key against the solid backdrop the shoot guidelines ask for
  rembg          AI matting for photos without a clean backdrop (optional: pip install rembg)
  auto           sample the border: green or white backdrop → chroma key, otherwise rembg if installed
  none           keep the full photo, no alpha
"""
import cv2
import numpy as np

from .imageio import split_alpha


def _border_pixels(bgr, width=8):
    h, w = bgr.shape[:2]
    return np.concatenate([bgr[:width].reshape(-1, 3), bgr[-width:].reshape(-1, 3),
                           bgr[:, :width].reshape(-1, 3), bgr[:, -width:].reshape(-1, 3)])


def _green_mask(hsv, tol):
    lo = np.array([35 - tol // 2, 60, 40]); hi = np.array([85 + tol // 2, 255, 255])
    return cv2.inRange(hsv, lo, hi)


def _white_mask(hsv, tol):
    lo = np.array([0, 0, 220 - tol]); hi = np.array([180, 30 + tol, 255])
    return cv2.inRange(hsv, lo, hi)


def detect_backdrop(bgr):
    hsv = cv2.cvtColor(_border_pixels(bgr)[None], cv2.COLOR_BGR2HSV)
    if (_green_mask(hsv, 10) > 0).mean() > 0.6:
        return "green"
    if (_white_mask(hsv, 10) > 0).mean() > 0.6:
        return "white"
    return None


def _clean(fg_mask, feather):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    m = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, k)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k, iterations=2)
    # keep the largest subject blob, fill its holes
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m)
    if n > 1:
        biggest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        m = np.where(labels == biggest, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(m, contours, -1, 255, thickness=cv2.FILLED)
    if feather:
        m = cv2.GaussianBlur(m, (0, 0), feather)
    return m


def chroma_key(bgr, backdrop="green", tolerance=10, feather=1.0):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    bg = _green_mask(hsv, tolerance) if backdrop == "green" else _white_mask(hsv, tolerance)
    alpha = _clean(cv2.bitwise_not(bg), feather)
    if backdrop == "green":  # kill green spill on edges
        b, g, r = cv2.split(bgr)
        g = np.minimum(g, np.maximum(r, b))
        bgr = cv2.merge([b, g, r])
    return np.dstack([bgr, alpha])


def rembg_cutout(bgr):
    try:
        from rembg import remove
    except ImportError as e:
        raise RuntimeError("rembg not installed. Run: pip install rembg") from e
    rgba = remove(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    rgba = np.asarray(rgba)
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)


def remove_background(img, method="auto", tolerance=10):
    bgr, alpha = split_alpha(img)
    if alpha is not None and method == "auto":
        return img  # already cut out
    if method == "none":
        return bgr
    if method == "auto":
        found = detect_backdrop(bgr)
        if found:
            return chroma_key(bgr, found, tolerance)
        try:
            return rembg_cutout(bgr)
        except RuntimeError:
            print("  ! no green/white backdrop and rembg not installed — keeping full photo")
            return bgr
    if method in ("green", "white"):
        return chroma_key(bgr, method, tolerance)
    if method == "rembg":
        return rembg_cutout(bgr)
    raise ValueError(f"Unknown cutout method: {method}")
