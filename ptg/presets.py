"""Look presets: palettes, gradient ramps, ink and VHS settings.

A preset is a JSON file. Built-ins live in ptg/presets/; pass a path to use your own.
"""
import json
from pathlib import Path

import numpy as np

PRESET_DIR = Path(__file__).parent / "presets"

DEFAULT_VHS = {"aberration": 2, "scanlines": 0.2, "jitter": 1, "wave": 1.0,
               "grain": 0.05, "vignette": 0.35, "tracking_band": False}
DEFAULT_INK = {"enabled": True, "block": 0, "c": 6, "thickness": 1}


def hex_to_bgr(h):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def list_presets():
    return sorted(p.stem for p in PRESET_DIR.glob("*.json"))


def load_preset(name_or_path="nightmare"):
    p = Path(name_or_path)
    if not p.suffix:
        p = PRESET_DIR / f"{name_or_path}.json"
    if not p.exists():
        raise FileNotFoundError(
            f"Preset '{name_or_path}' not found. Built-ins: {', '.join(list_presets())}")
    data = json.loads(p.read_text())
    data.setdefault("posterize", None)
    data["ink"] = {**DEFAULT_INK, **data.get("ink", {})}
    data["vhs"] = {**DEFAULT_VHS, **data.get("vhs", {})}
    return data


def ramp_lut(stops):
    """256-entry BGR lookup table interpolated through the hex stops (dark → light)."""
    cols = np.array([hex_to_bgr(s) for s in stops], dtype=np.float32)
    xs = np.linspace(0, 255, len(cols))
    idx = np.arange(256)
    lut = np.stack([np.interp(idx, xs, cols[:, c]) for c in range(3)], axis=1)
    return lut.astype(np.uint8)


def palette_bgr(preset):
    return np.array([hex_to_bgr(h) for h in preset["palette"]], dtype=np.uint8)
