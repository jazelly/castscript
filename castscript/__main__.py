"""castscript CLI: python -m castscript SCRIPT --engine breeze ..."""

from __future__ import annotations

import argparse
from pathlib import Path

from .render import render
from .script import parse


def main() -> None:
    parser = argparse.ArgumentParser(prog="castscript")
    parser.add_argument("script", type=Path, help="*.cast.txt file")
    parser.add_argument("--engine", choices=("breeze", "qwen"), default="breeze")
    parser.add_argument("--out", type=Path, help="output path without extension (default: next to the script)")
    parser.add_argument("--breeze-dir", type=Path, help="breeze-tts-mlx checkout")
    parser.add_argument("--breeze-checkpoint", type=Path, help="Breeze MLX checkpoint directory")
    args = parser.parse_args()

    script = parse(args.script)
    if args.engine == "breeze":
        from .engines.breeze import BreezeEngine

        if not args.breeze_dir or not args.breeze_checkpoint:
            parser.error("--engine breeze needs --breeze-dir and --breeze-checkpoint")
        engine = BreezeEngine(args.breeze_checkpoint, args.breeze_dir)
    else:
        from .engines.qwen import QwenEngine

        engine = QwenEngine()

    out = args.out or args.script.with_name(args.script.name.removesuffix(".cast.txt"))
    render(script, engine, out)


if __name__ == "__main__":
    main()
