"""castscript app: build castscript.app, a macOS menu bar app that runs `castscript web` and opens it."""

from __future__ import annotations

import argparse
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

from .web import PORT

MACOS = Path(__file__).with_name("macos")


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="castscript app", description="Build and open the castscript menu bar app (macOS).")
    parser.add_argument("--dest", type=Path, default=Path.home() / "Applications", help="where to put castscript.app (default: ~/Applications)")
    parser.add_argument("--workdir", type=Path, help="passed to castscript web")
    parser.add_argument("--port", type=int, default=PORT, help=f"passed to castscript web (default: {PORT})")
    args = parser.parse_args(argv)
    if sys.platform != "darwin":
        parser.error("the menu bar app is macOS only; use `castscript web` elsewhere")
    if not shutil.which("swiftc"):
        parser.error("swiftc not found; install the Xcode command line tools with `xcode-select --install`")

    # The app runs the server with this exact interpreter, so it keeps working outside a shell.
    command = [sys.executable, "-m", "castscript", "web", "--no-browser", "--port", str(args.port)]
    if args.workdir:
        command += ["--workdir", str(args.workdir.expanduser().resolve())]

    app = args.dest.expanduser() / "castscript.app"
    if app.exists():
        subprocess.run(["osascript", "-e", 'quit app "castscript"'], check=False)
        shutil.rmtree(app)
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    resources = contents / "Resources"
    resources.mkdir()
    subprocess.run(["swiftc", "-O", str(MACOS / "menu.swift"), "-o", str(contents / "MacOS" / "castscript")], check=True)
    shutil.copy(MACOS / "menubar.svg", resources)
    shutil.copy(MACOS / "appicon.icns", resources)
    (resources / "command").write_text("\n".join(command) + "\n", encoding="utf-8")
    (resources / "url").write_text(f"http://127.0.0.1:{args.port}/\n", encoding="utf-8")
    with (contents / "Info.plist").open("wb") as f:
        plistlib.dump({
            "CFBundleName": "castscript", "CFBundleDisplayName": "castscript", "CFBundleIdentifier": "io.github.jazelly.castscript",
            "CFBundleExecutable": "castscript", "CFBundleIconFile": "appicon", "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": "0.1.0", "LSMinimumSystemVersion": "14.0", "LSUIElement": True,
        }, f)
    subprocess.run(["open", str(app)], check=True)
    print(f"built and opened {app}; look for the castscript icon in the menu bar")
