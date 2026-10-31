"""castscript CLI: python -m castscript SCRIPT --engine breeze ..."""

from __future__ import annotations

import argparse
from pathlib import Path

from .render import render
from .script import parse


def main() -> None:
    parser = argparse.ArgumentParser(prog="castscript")
    parser.add_argument("script", type=Path, help="*.cast.txt file")
    parser.add_argument("--engine", choices=("breeze", "qwen", "chatterbox", "omnivoice", "kitten", "kokoro", "pocket", "voxcpm", "indextts", "audio8", "dots"), default="breeze")
    parser.add_argument("--out", type=Path, help="output path without extension (default: next to the script)")
    parser.add_argument("--language", default="zh", help="language code for multilingual engines (default: zh)")
    parser.add_argument("--breeze-dir", type=Path, help="breeze-tts-mlx checkout")
    parser.add_argument("--breeze-checkpoint", type=Path, help="Breeze MLX checkpoint directory")
    parser.add_argument("--index-dir", type=Path, help="index-tts checkout with checkpoints/")
    args = parser.parse_args()

    script = parse(args.script)
    if args.engine == "breeze":
        from .engines.breeze import BreezeEngine

        if not args.breeze_dir or not args.breeze_checkpoint:
            parser.error("--engine breeze needs --breeze-dir and --breeze-checkpoint")
        engine = BreezeEngine(args.breeze_checkpoint, args.breeze_dir)
    elif args.engine == "qwen":
        from .engines.qwen import QwenEngine

        engine = QwenEngine(args.language)
    elif args.engine == "chatterbox":
        from .engines.chatterbox import ChatterboxEngine

        engine = ChatterboxEngine(args.language)
    elif args.engine == "omnivoice":
        from .engines.omnivoice import OmniVoiceEngine

        engine = OmniVoiceEngine(args.language)
    elif args.engine == "kitten":
        from .engines.kitten import KittenEngine

        engine = KittenEngine(args.language)
    elif args.engine == "kokoro":
        from .engines.kokoro import KokoroEngine

        engine = KokoroEngine(args.language)
    elif args.engine == "pocket":
        from .engines.pocket import PocketEngine

        engine = PocketEngine(args.language)
    elif args.engine == "voxcpm":
        from .engines.voxcpm import VoxCPMEngine

        engine = VoxCPMEngine()
    elif args.engine == "audio8":
        from .engines.audio8 import Audio8Engine

        engine = Audio8Engine()
    elif args.engine == "dots":
        from .engines.dots import DotsEngine

        engine = DotsEngine(args.language)
    else:
        from .engines.indextts import IndexTTSEngine

        if not args.index_dir:
            parser.error("--engine indextts needs --index-dir")
        engine = IndexTTSEngine(args.index_dir.resolve(), args.language)

    out = args.out or args.script.with_name(args.script.name.removesuffix(".cast.txt"))
    render(script, engine, out)


if __name__ == "__main__":
    main()
