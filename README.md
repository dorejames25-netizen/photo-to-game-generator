# Photo-to-Game Generator

Turn your own photographs — real people, real costumes, real props, real places — into original, game-ready art. No generated-from-nothing characters: every asset starts as a photo you took, and the tool post-processes it into the look your game needs.

It's engine- and game-agnostic. Looks are swappable presets, and the outputs are plain PNGs plus a drop-in Godot shader.

```
photo ─► cutout ─► neon relight + ink tracing ─► ┬─► character art (+ VHS degrade)
                                                 ├─► pixel sprite / sprite sheet   (channel 1)
flat photo ─► de-light ─► tile ─────────────────── └─► texture map for low-poly meshes (channel 2)
```

## Install

Python 3.10+.

```
pip install -r requirements.txt
```

Optional, for cutting people out of photos without a green/white backdrop:

```
pip install rembg
```

## Quick start

1. Drop raw files into `Assets/DropZone/` — reference photos go in `Assets/DropZone/photos/`, anything else (zips, models, audio, HDRIs) loose.
2. Run the whole batch:

```
python -m ptg run --preset nightmare
```

That sorts the drop zone, then turns every photo into neon character art in `Assets/Textures/Characters/` and an indexed pixel sprite in `Assets/Sprites/` (plus sprite sheets for directional sets).

## Commands

| Command | What it does |
|---|---|
| `ptg sort` | Unzips packs, renames everything to snake_case, routes files into `Photos/ Textures/ Models/ Shaders/ Audio/ HDRI/`. `--dry-run` to preview. |
| `ptg character IN OUT` | Photo → ink-traced, colour-graded character art. `--vhs` adds tape degradation, `--label` adds an on-screen caption. |
| `ptg sprite IN OUT` | Photo → crunchy pixel sprite as a true palette-indexed PNG. `--size 128/256`, `--relight`, `--colors N` for an adaptive palette, `--sheet` to pack directional shots. |
| `ptg texture IN OUT` | Flat-lit photo → square power-of-two texture with baked lighting removed. `--seamless` to tile, `--preset` to colour-grade. |
| `ptg vhs IN OUT` | VHS/CRT degradation on any finished image (offline twin of the shader). |
| `ptg presets` | List the built-in looks. |

Run them as `python -m ptg <command>`, or `pip install -e .` once and use `ptg <command>`. `IN` can be a file or a folder; `OUT` a file or a folder. Every command has `--help`.

## Looks (presets)

| Preset | Look |
|---|---|
| `nightmare` | Neon cyberpunk horror — void blacks, magenta/cyan neon, violet glow, heavy tape damage. |
| `outrun` | Classic synthwave dual-tone — navy, hot magenta, electric cyan. |
| `graphic_novel` | High-contrast cel shading — black shadows, flat reds, neon blue highlights, thick ink. |

A preset is a small JSON file in `ptg/presets/`. Copy one to make your own look for a new game, then pass `--preset path/to/mine.json`. Fields: `ramp` (shadow→highlight colours for the relight), `palette` (sprite colours), `posterize` (cel-shade bands, or `null`), `ink`, `vhs`.

## Shooting photos that process well

- **Backdrop:** solid, non-reflective green or white. The cutout detects it automatically.
- **Light:** soft and even. No strong directional light — the engine lights the scene.
- **Names:** snake_case, `<subject>_<action>_<angle>.png`, e.g. `stalker_walk_front.png`. Angles `front`, `back`, `left`, `right` (and `front_left` etc.) are packed into sprite sheets automatically.
- **Sprites:** shoot each pose from the front, back and both sides.
- **Textures:** shoot fabrics, masks and surfaces straight-on and flat.

## Godot

`Assets/Shaders/vhs_crt.gdshader` is a full-screen VHS/CRT post-process for Godot 4: tracking jitter, rolling tracking-error band, horizontal micro waves, chromatic aberration, scanlines, bubble-lens curvature and vignette, and grain — each with its own slider. Setup is in the comment at the top of the file.

Sprites import best with the texture filter set to **Nearest**.

## Repo layout

```
ptg/                 the generator (Python package)
  presets/           look presets (JSON)
Assets/
  DropZone/          raw incoming files  (photos/ for reference photos)
  Photos/ Textures/ Sprites/ Models/ Shaders/ Audio/ HDRI/
docs/BLUEPRINT.md    art direction and pipeline rules
process_character.py original one-shot script, now runs through the pipeline
```

Binary assets under `Assets/` are tracked with Git LFS (see `.gitattributes`); install it once with `git lfs install`. When a game's asset library grows, `Assets/` can move to its own repo as the drop-zone repo.
