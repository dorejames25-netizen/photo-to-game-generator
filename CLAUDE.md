# Notes for AI assistants working in this repo

This is a standalone, game-agnostic tool: real photos in, original game art out. Read `docs/BLUEPRINT.md` before changing any image processing.

- **Never generate art from scratch.** All character and texture art must come from the user's own photographs; code only post-processes them (cutout, pixelate, texture-map, colour-grade, degrade). Don't add generative-image steps or bundle stock art.
- Keep it game-agnostic: game-specific colours and settings belong in a preset JSON in `ptg/presets/`, not hard-coded.
- Images are OpenCV BGR/BGRA uint8 arrays throughout; use `ptg/imageio.py` for reading/writing.
- New file names are snake_case. New CLI commands go in `ptg/cli.py` with `--help` text and a README row.
- Don't commit personal photos or third-party reference images; `Assets/` holds only `.gitkeep` placeholders and the shader in the repo.
- Run `python -m pytest -q` before committing.
- Terminal commands for the user: one command per code block.
