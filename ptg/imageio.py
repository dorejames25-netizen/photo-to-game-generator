"""Shared image I/O helpers. Images are BGR or BGRA uint8 numpy arrays (OpenCV order)."""
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".tga"}


def read(path):
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {path}")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    if img.dtype != np.uint8:  # 16-bit PNG/TIFF
        img = cv2.convertScaleAbs(img, alpha=255.0 / img.max())
    return img


def write(path, img):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if img.shape[-1] == 4 and path.suffix.lower() in {".jpg", ".jpeg"}:
        path = path.with_suffix(".png")  # JPEG can't hold transparency
    if not cv2.imwrite(str(path), img):
        raise IOError(f"Could not write image: {path}")
    return path


def split_alpha(img):
    if img.shape[-1] == 4:
        return img[..., :3].copy(), img[..., 3].copy()
    return img, None


def merge_alpha(bgr, alpha):
    if alpha is None:
        return bgr
    return np.dstack([bgr, alpha])


def is_image(path):
    return Path(path).suffix.lower() in IMAGE_EXTS
