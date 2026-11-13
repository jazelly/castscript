"""castscript web: a local browser GUI for writing scripts and rendering them with any installed engine.

The server itself imports no engine. Each render runs `python -m castscript` inside that engine's own
virtual environment, exactly as the CLI is used, so engines with conflicting dependencies stay apart.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .script import ScriptError, parse

PORT = 47810
PACKAGE_PARENT = Path(__file__).resolve().parent.parent
PAGE = Path(__file__).with_name("web.html")
ENGINES = ("breeze", "qwen", "chatterbox", "omnivoice", "kitten", "kokoro", "pocket", "voxcpm", "indextts", "audio8", "dots")
# Voice kinds each engine accepts, from the SPEC.md support table.
VOICE_KINDS = {
    "breeze": "ref, design", "qwen": "ref, design, preset", "chatterbox": "ref", "omnivoice": "ref, design",
    "kitten": "ref, preset", "kokoro": "preset", "pocket": "ref, preset", "voxcpm": "ref, design",
    "indextts": "ref", "audio8": "ref", "dots": "ref",
}
PROGRESS_RE = re.compile(r"^\[(\d+)/(\d+)\]")


def find_engines(envs: Path | None, breeze_dir: Path | None, breeze_checkpoint: Path | None) -> dict[str, list[str]]:
    """Map each installed engine to the command prefix that renders with it."""
    found: dict[str, list[str]] = {}
    if breeze_dir and breeze_checkpoint:
        python = breeze_dir / ".venv" / "bin" / "python"
        if python.is_file():
            found["breeze"] = [str(python), "-m", "castscript", "--engine", "breeze",
                               "--breeze-dir", str(breeze_dir), "--breeze-checkpoint", str(breeze_checkpoint)]
    if not envs:
        return found
    for engine in ENGINES[1:]:
        for name in (engine, "index-tts") if engine == "indextts" else (engine,):
            for python in (envs / name / "bin" / "python", envs / name / ".venv" / "bin" / "python"):
                if python.is_file():
                    command = [str(python), "-m", "castscript", "--engine", engine]
                    if engine == "indextts":
                        command += ["--index-dir", str(envs / name)]
                    found.setdefault(engine, command)
    return found


class Job:
    """The one render that may run at a time."""

    def __init__(self):
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None
        self.state = "idle"  # idle | running | done | failed | stopped
        self.script = self.engine = ""
        self.log: list[str] = []
        self.done = self.total = 0

    def start(self, command: list[str], script: str, engine: str) -> None:
        env = {**os.environ, "PYTHONPATH": str(PACKAGE_PARENT), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
        with self.lock:
            if self.state == "running":
                raise RuntimeError("a render is already running")
            self.state, self.script, self.engine = "running", script, engine
            self.log, self.done, self.total = [" ".join(command)], 0, 0
            self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
        threading.Thread(target=self._follow, args=(self.proc,), daemon=True).start()

    def _follow(self, proc: subprocess.Popen) -> None:
        for raw in proc.stdout:
            # Progress bars redraw with \r; keep only their latest state.
            line = raw.rstrip("\n").split("\r")[-1].rstrip()
            if not line:
                continue
            with self.lock:
                self.log.append(line)
                del self.log[:-500]
                if m := PROGRESS_RE.match(line):
                    self.done, self.total = int(m[1]), int(m[2])
        code = proc.wait()
        with self.lock:
            if self.state == "running":
                self.state = "done" if code == 0 else "failed"

    def stop(self) -> None:
        with self.lock:
            if self.state == "running" and self.proc:
                self.state = "stopped"
                self.proc.terminate()

    def snapshot(self) -> dict:
        with self.lock:
            return {"state": self.state, "script": self.script, "engine": self.engine,
                    "log": self.log[-200:], "done": self.done, "total": self.total}


def make_handler(workdir: Path, engines: dict[str, list[str]], job: Job):
    def inside(rel: str) -> Path:
        path = (workdir / rel).resolve()
        if not path.is_relative_to(workdir):
            raise ValueError(f"path outside the workspace: {rel}")
        return path

    def outputs(rel: str) -> list[dict]:
        script = inside(rel)
        stem = script.name.removesuffix(".cast.txt")
        found = []
        for mp3 in sorted(script.parent.glob(f"{stem}-*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True):
            srt = mp3.with_suffix(".srt")
            found.append({
                "engine": mp3.stem.removeprefix(f"{stem}-"),
                "mp3": mp3.relative_to(workdir).as_posix(),
                "srt": srt.relative_to(workdir).as_posix() if srt.is_file() else None,
            })
        return found

    def state() -> dict:
        voices = []
        for wav in sorted(workdir.rglob("*.wav")):
            transcript = wav.with_suffix(".txt")
            if transcript.is_file():
                voices.append({"path": wav.relative_to(workdir).as_posix(),
                               "transcript": transcript.read_text(encoding="utf-8").strip()})
        return {
            "workdir": str(workdir),
            "scripts": [p.relative_to(workdir).as_posix() for p in sorted(workdir.rglob("*.cast.txt"))],
            "voices": voices,
            "engines": [{"name": e, "installed": e in engines, "voices": VOICE_KINDS[e]} for e in ENGINES],
            "job": job.snapshot(),
        }

    def check(path: Path) -> dict:
        try:
            script = parse(path)
        except ScriptError as e:
            return {"ok": False, "error": str(e).replace(str(path), path.name)}
        return {"ok": True, "voices": len(script.voices), "lines": len(script.lines)}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data, status: int = 200) -> None:
            self._send(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", status)

        def do_GET(self):
            url = urlparse(self.path)
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/":
                    self._send(PAGE.read_bytes(), "text/html; charset=utf-8")
                elif url.path == "/api/state":
                    self._json(state())
                elif url.path == "/api/job":
                    self._json(job.snapshot())
                elif url.path == "/api/script":
                    path = inside(query["path"])
                    self._json({"text": path.read_text(encoding="utf-8"), "outputs": outputs(query["path"])})
                elif url.path.startswith("/files/"):
                    path = inside(unquote(url.path.removeprefix("/files/")))
                    types = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".srt": "text/plain; charset=utf-8"}
                    self._send(path.read_bytes(), types.get(path.suffix, "application/octet-stream"))
                else:
                    self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (ValueError, KeyError, OSError) as e:
                self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            try:
                if self.path == "/api/script":
                    if not body["path"].endswith(".cast.txt"):
                        raise ValueError("script names must end in .cast.txt")
                    path = inside(body["path"])
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(body["text"], encoding="utf-8")
                    self._json(check(path))
                elif self.path == "/api/render":
                    path = inside(body["path"])
                    if body["engine"] not in engines:
                        raise ValueError(f"engine '{body['engine']}' is not installed")
                    out = path.with_name(f"{path.name.removesuffix('.cast.txt')}-{body['engine']}")
                    command = engines[body["engine"]] + [str(path), "--out", str(out), "--language", body.get("language", "zh")]
                    job.start(command, body["path"], body["engine"])
                    self._json(job.snapshot())
                elif self.path == "/api/stop":
                    job.stop()
                    self._json(job.snapshot())
                elif self.path == "/api/voice":
                    name = re.sub(r"[^\w\-]+", "_", body["name"]).strip("_")
                    if not name or not body["transcript"].strip():
                        raise ValueError("a voice needs a name and its transcript")
                    wav = inside(f"voices/{name}.wav")
                    wav.parent.mkdir(parents=True, exist_ok=True)
                    wav.write_bytes(base64.b64decode(body["audio"]))
                    wav.with_suffix(".txt").write_text(body["transcript"].strip() + "\n", encoding="utf-8")
                    self._json(state())
                else:
                    self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
            except (ValueError, KeyError, OSError, RuntimeError) as e:
                self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)

    return Handler


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="castscript web", description="Open the castscript GUI in a browser.")
    parser.add_argument("--workdir", type=Path, default=Path.home() / "castscript",
                        help="folder holding scripts, voices, and renders (default: ~/castscript)")
    parser.add_argument("--envs", type=Path, help="folder with one virtual environment per engine, named after it")
    parser.add_argument("--breeze-dir", type=Path, help="breeze-tts-mlx checkout with its .venv")
    parser.add_argument("--breeze-checkpoint", type=Path, help="Breeze MLX checkpoint directory")
    parser.add_argument("--port", type=int, default=PORT, help=f"port on 127.0.0.1 (default: {PORT})")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = parser.parse_args(argv)

    workdir = args.workdir.expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    resolve = lambda p: p.expanduser().resolve() if p else None
    engines = find_engines(resolve(args.envs), resolve(args.breeze_dir), resolve(args.breeze_checkpoint))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(workdir, engines, Job()))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"castscript web: {url}  workspace {workdir}  engines: {', '.join(engines) or 'none found'}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
