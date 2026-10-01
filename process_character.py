"""Original one-shot script, kept so old invocations still work.

It now runs through the full pipeline (ptg.neon.relight) instead of the three hard
brightness bands. For everything else use the CLI:  python -m ptg --help
"""
from ptg import imageio, neon


def generate_retro_asset(image_path, output_path, preset="outrun"):
    art = neon.relight(imageio.read(image_path), preset)
    path = imageio.write(output_path, art)
    print(f"Asset pipeline complete! Saved to: {path}")
    return path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python process_character.py <photo> <output.png> [preset]")
        sys.exit(1)
    generate_retro_asset(*sys.argv[1:4])
