# Art direction & pipeline rules

Consolidated from the Character Development Blueprint and the Game Design Handover Document.

## The rule that matters most

Every character and texture starts as a **real photograph** — real people, real costumes, real props. The tool's job is only to post-process: cut out, pixelate, texture-map, colour-grade and degrade. Do not add art generated from scratch (generic vector art, anime illustrations, stock 3D models). That's what makes the output original work.

## Target looks

- **High-contrast graphic novel / cel-shaded** — hard ink outlines on faces, clothing and folds; heavy black backdrop; flat bold colour against deep saturated shadows. → `graphic_novel` preset.
- **Cyberpunk industrial realism** — characters lit by magenta, cyan and violet rim light in low-light, rain-slicked concrete settings. → `nightmare` preset.
- **Analog VHS corruption** — finished images degraded with red/blue edge bleeding, scanlines, tracking distortion and grain. → `ptg vhs` / `--vhs`, and the Godot shader in-game.

## Processing channels

| Channel | Input | Steps |
|---|---|---|
| 1 · Digitized 2D sprite (Doom / Mortal Kombat style) | Costume photos from the cardinal angles (front, back, sides) | Remove background → downscale to a crunchy grid (128 or 256) → indexed low-range palette |
| 2 · Photo-to-texture mesh (gritty low-poly horror) | Flat, neutral-lit photos of masks, faces, fabrics, surfaces | Convert to flat optimised texture maps → map onto simple blocky low-poly meshes → let the screen-space VHS shader blend the seams |

## Photo ingestion constraints

1. **Chroma isolation** — solid, non-reflective white or green backdrop for clean alpha masks.
2. **Neutral diffuse lighting** — no strong directional light in raw photos; the engine handles lighting.
3. **Descriptive snake_case names** — e.g. `villain_stalker_walk_front.png`.

## Asset folder tree

- `Textures/` — neon signage, metal, concrete overlays, processed character art
- `Models/` — low-poly meshes, vehicles, walls, interactables
- `Shaders/` — CRT lens post-processing, chromatic distortion, glitches
- `Audio/` — hums, static, synth bass loops, footsteps
- `HDRI/` — 360° HDR panoramas for horizon/reflection lighting
- `Sprites/`, `Photos/` — added by this tool for channel 1 output and source photos

## CRT / VHS shader parameters

Tracking jitter, horizontal micro waves, chromatic aberration, horizontal scanlines, round bubble-lens vignette, procedural grain. Implemented in `Assets/Shaders/vhs_crt.gdshader` (Godot 4) and mirrored offline in `ptg/vhs.py`.

## Example palette (`nightmare` preset)

| Group | Colours | Role |
|---|---|---|
| The Void | `#0B0C10` `#1F2833` | Base and shadows |
| Decay & Surveillance | `#2C3531` `#4E5D4C` | Midtones |
| Neon Glitch | `#FF0055` `#00F0FF` | High-voltage accents |
| Terminal Horizon | `#8B00FF` `#FF5500` | Glow highlights |
