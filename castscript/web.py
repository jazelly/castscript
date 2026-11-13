"""castscript web: the local web app for writing scripts, managing voices, and rendering with any installed engine.

Workspace (default ~/castscript):
  scripts/NAME.cast.txt   scripts; imported ones are symlinks to where they live
  voices/NAME.wav + .txt  reference voices; imported ones are symlinks too
  renders/ID/             one folder per render
  castscript.db           settings and render history

The server imports no engine. Each render runs `python -m castscript` inside that engine's own virtual
environment, exactly as the CLI is used, so engines with conflicting dependencies stay apart.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .db import Store
from .script import ScriptError, parse

PORT = 47810
PACKAGE_PARENT = Path(__file__).resolve().parent.parent
WEBUI = Path(__file__).with_name("webui")
ENGINES = ("breeze", "qwen", "chatterbox", "omnivoice", "kitten", "kokoro", "pocket", "voxcpm", "indextts", "audio8", "dots")
# Voice kinds each engine accepts, from the SPEC.md support table.
VOICE_KINDS = {
    "breeze": ["ref", "design"], "qwen": ["ref", "design", "preset"], "chatterbox": ["ref"], "omnivoice": ["ref", "design"],
    "kitten": ["ref", "preset"], "kokoro": ["preset"], "pocket": ["ref", "preset"], "voxcpm": ["ref", "design"],
    "indextts": ["ref"], "audio8": ["ref"], "dots": ["ref"],
}
NAME_RE = re.compile(r"^[\w\-. ]+$")
PROGRESS_RE = re.compile(r"^\[(\d+)/(\d+)\]")
DONE_RE = re.compile(r"^done: ([\d.]+)s audio")
ERROR_LINE_RE = re.compile(r":(\d+): ")


def engine_commands(settings: dict[str, str]) -> dict[str, list[str]]:
    """Map each installed engine to the command prefix that renders with it."""
    found: dict[str, list[str]] = {}
    if settings["breeze_dir"] and settings["breeze_checkpoint"]:
        breeze = Path(settings["breeze_dir"]).expanduser()
        python = breeze / ".venv" / "bin" / "python"
        if python.is_file():
            found["breeze"] = [str(python), "-m", "castscript", "--engine", "breeze", "--breeze-dir", str(breeze),
                               "--breeze-checkpoint", str(Path(settings["breeze_checkpoint"]).expanduser())]
    if not settings["envs"]:
        return found
    envs = Path(settings["envs"]).expanduser()
    for engine in ENGINES[1:]:
        for name in (engine, "index-tts") if engine == "indextts" else (engine,):
            for python in (envs / name / "bin" / "python", envs / name / ".venv" / "bin" / "python"):
                if python.is_file() and engine not in found:
                    found[engine] = [str(python), "-m", "castscript", "--engine", engine]
                    if engine == "indextts":
                        found[engine] += ["--index-dir", str(envs / name)]
    return found


def check_script(path: Path) -> dict:
    try:
        script = parse(path.resolve())
    except ScriptError as e:
        message = str(e)
        m = ERROR_LINE_RE.search(message)
        return {"ok": False, "error": message[m.end():] if m else message, "line": int(m[1]) if m else None}
    except OSError as e:
        return {"ok": False, "error": str(e), "line": None}
    kinds = sorted({v.kind for v in script.voices.values()})
    return {"ok": True, "voices": len(script.voices), "lines": len(script.lines), "kinds": kinds}


class Workspace:
    def __init__(self, root: Path):
        self.root = root
        self.scripts, self.voices, self.renders = root / "scripts", root / "voices", root / "renders"
        for d in (self.scripts, self.voices, self.renders):
            d.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _name(name: str) -> str:
        if not NAME_RE.match(name) or name.startswith("."):
            raise ValueError(f"invalid name: {name!r}")
        return name

    def script_path(self, name: str) -> Path:
        return self.scripts / f"{self._name(name)}.cast.txt"

    def voice_path(self, name: str) -> Path:
        return self.voices / f"{self._name(name)}.wav"

    @staticmethod
    def _entry(path: Path, name: str) -> dict:
        linked = path.is_symlink()
        return {"name": name, "linked": linked, "target": str(path.resolve()) if linked else None,
                "missing": not path.exists()}

    def list_scripts(self) -> list[dict]:
        return [self._entry(p, p.name.removesuffix(".cast.txt")) for p in sorted(self.scripts.glob("*.cast.txt"))]

    def list_voices(self) -> list[dict]:
        voices = []
        for wav in sorted(self.voices.glob("*.wav")):
            transcript = wav.with_suffix(".txt")
            entry = self._entry(wav, wav.stem)
            entry["transcript"] = transcript.read_text(encoding="utf-8").strip() if transcript.exists() else ""
            voices.append(entry)
        return voices

    def import_path(self, source: Path) -> dict:
        """Symlink scripts and voices found at source into the workspace; names already taken are skipped."""
        source = source.expanduser().resolve()
        if not source.exists():
            raise ValueError(f"not found: {source}")
        files = [source] if source.is_file() else sorted(source.rglob("*"))
        base = source.parent if source.is_file() else source

        def name_for(path: Path, suffix: str) -> str:
            parts = path.relative_to(base).parts
            return re.sub(r"[^\w\-. ]+", "_", "-".join(parts)[: -len(suffix)])

        added = {"scripts": [], "voices": [], "skipped": 0}
        for path in files:
            if path.name.endswith(".cast.txt"):
                link = self.scripts / f"{name_for(path, '.cast.txt')}.cast.txt"
                targets = [(link, path)]
                kind = "scripts"
            elif path.suffix == ".wav" and path.with_suffix(".txt").is_file():
                link = self.voices / f"{name_for(path, '.wav')}.wav"
                targets = [(link, path), (link.with_suffix(".txt"), path.with_suffix(".txt"))]
                kind = "voices"
            else:
                continue
            if any(t.exists() or t.is_symlink() for t, _ in targets):
                added["skipped"] += 1
                continue
            for target, real in targets:
                target.symlink_to(real)
            added[kind].append(link.name.removesuffix(".cast.txt").removesuffix(".wav"))
        return added


class Runner:
    """Runs one render at a time and records it in the store."""

    def __init__(self, store: Store, workspace: Workspace):
        self.store, self.workspace = store, workspace
        self.lock = threading.Lock()
        self.current: dict | None = None  # {id, proc, log, done, total, stopped}

    def start(self, command: list[str], script: str, engine: str, language: str) -> int:
        with self.lock:
            if self.current:
                raise RuntimeError("a render is already running")
            render_id = self.store.add_render(script, engine, language)
            out_dir = self.workspace.renders / str(render_id)
            out_dir.mkdir(parents=True, exist_ok=True)
            source = self.workspace.script_path(script).resolve()
            command = command + [str(source), "--out", str(out_dir / script), "--language", language]
            env = {**os.environ, "PYTHONPATH": str(PACKAGE_PARENT), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"}
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                    text=True, encoding="utf-8", errors="replace", bufsize=1)
            self.current = {"id": render_id, "proc": proc, "log": [" ".join(command)], "done": 0, "total": 0, "stopped": False}
        threading.Thread(target=self._follow, args=(self.current,), daemon=True).start()
        return render_id

    def _follow(self, job: dict) -> None:
        audio_seconds = None
        for raw in job["proc"].stdout:
            # Progress bars redraw with \r; keep only their latest state.
            line = raw.rstrip("\n").split("\r")[-1].rstrip()
            if not line:
                continue
            with self.lock:
                job["log"].append(line)
                del job["log"][1:-1000]
                if m := PROGRESS_RE.match(line):
                    job["done"], job["total"] = int(m[1]), int(m[2])
                if m := DONE_RE.match(line):
                    audio_seconds = float(m[1])
        code = job["proc"].wait()
        status = "stopped" if job["stopped"] else "done" if code == 0 else "failed"
        self.store.finish_render(job["id"], status, "\n".join(job["log"]), audio_seconds)
        with self.lock:
            self.current = None

    def stop(self, render_id: int) -> None:
        with self.lock:
            if self.current and self.current["id"] == render_id:
                self.current["stopped"] = True
                self.current["proc"].terminate()

    def live(self, render_id: int) -> dict | None:
        with self.lock:
            if self.current and self.current["id"] == render_id:
                return {"done": self.current["done"], "total": self.current["total"], "log": "\n".join(self.current["log"])}
        return None


def make_handler(workspace: Workspace, store: Store, runner: Runner):
    def render_view(row: dict) -> dict:
        folder = workspace.renders / str(row["id"])
        live = runner.live(row["id"])
        # ffmpeg writes the MP3 before the render finishes; offer files only once it has.
        files = {} if live else {ext: f"/api/renders/{row['id']}/{row['script']}.{ext}" for ext in ("mp3", "srt")
                                 if (folder / f"{row['script']}.{ext}").is_file()}
        view = {**row, "files": files, "progress": {"done": live["done"], "total": live["total"]} if live else None}
        if "log" in row and live:
            view["log"] = live["log"]
        return view

    def engines() -> list[dict]:
        installed = engine_commands(store.settings())
        return [{"name": e, "installed": e in installed, "kinds": VOICE_KINDS[e]} for e in ENGINES]

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def _json(self, data, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path: Path, cache: bool = False) -> None:
            data = path.read_bytes()
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or path.suffix in (".srt", ".txt"):
                ctype = ("text/plain" if path.suffix in (".srt", ".txt") else ctype) + "; charset=utf-8"
            start, end, status = 0, len(data) - 1, 200
            # Audio elements seek with Range requests.
            if m := re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", "")):
                start = int(m[1]) if m[1] else max(0, len(data) - int(m[2]))
                end = int(m[2]) if m[1] and m[2] else len(data) - 1
                status = 206
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            self.send_header("Cache-Control", "public, max-age=31536000, immutable" if cache else "no-cache")
            self.end_headers()
            self.wfile.write(data[start:end + 1])

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(length)) if length else {}

        def _dispatch(self, method: str) -> None:
            url = urlparse(self.path)
            parts = [unquote(p) for p in url.path.strip("/").split("/")]
            query = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if parts[0] != "api":
                    return self._static(url.path)
                route = (method, *parts[1:])
                self._api(route, query)
            except KeyError as e:
                self._json({"error": f"not found: {e.args[0]}"}, HTTPStatus.NOT_FOUND)
            except (ValueError, OSError, RuntimeError) as e:
                self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)

        def _static(self, path: str) -> None:
            file = (WEBUI / path.lstrip("/")).resolve()
            if file.is_relative_to(WEBUI) and file.is_file():
                return self._file(file, cache=path.startswith("/assets/"))
            index = WEBUI / "index.html"
            if not index.is_file():
                return self._json({"error": "web UI not built; run `pnpm build` in web/"}, HTTPStatus.NOT_FOUND)
            self._file(index)

        def _api(self, route: tuple, query: dict) -> None:
            match route:
                case ("GET", "scripts"):
                    self._json(workspace.list_scripts())
                case ("POST", "scripts"):
                    body = self._body()
                    path = workspace.script_path(body["name"])
                    if path.exists() or path.is_symlink():
                        raise ValueError(f"a script named {body['name']!r} already exists")
                    path.write_text(body.get("text", ""), encoding="utf-8")
                    self._json({"name": body["name"], "check": check_script(path)})
                case ("GET", "scripts", name):
                    path = workspace.script_path(name)
                    if not path.exists():
                        raise KeyError(name)
                    entry = Workspace._entry(path, name)
                    self._json({**entry, "text": path.read_text(encoding="utf-8"), "check": check_script(path)})
                case ("PUT", "scripts", name):
                    path = workspace.script_path(name)
                    if not path.exists():
                        raise KeyError(name)
                    path.write_text(self._body()["text"], encoding="utf-8")
                    self._json({"check": check_script(path)})
                case ("DELETE", "scripts", name):
                    workspace.script_path(name).unlink()
                    self._json({"ok": True})
                case ("GET", "voices"):
                    self._json(workspace.list_voices())
                case ("POST", "voices"):
                    body = self._body()
                    wav = workspace.voice_path(body["name"])
                    if wav.exists() or wav.is_symlink():
                        raise ValueError(f"a voice named {body['name']!r} already exists")
                    if not body.get("transcript", "").strip():
                        raise ValueError("a voice needs the transcript of its audio")
                    wav.write_bytes(base64.b64decode(body["audio"]))
                    wav.with_suffix(".txt").write_text(body["transcript"].strip() + "\n", encoding="utf-8")
                    self._json(workspace.list_voices())
                case ("GET", "voices", name, "audio"):
                    self._file(workspace.voice_path(name))
                case ("DELETE", "voices", name):
                    wav = workspace.voice_path(name)
                    wav.unlink()
                    wav.with_suffix(".txt").unlink(missing_ok=True)
                    self._json({"ok": True})
                case ("POST", "import"):
                    self._json(workspace.import_path(Path(self._body()["path"])))
                case ("GET", "engines"):
                    self._json(engines())
                case ("GET", "settings"):
                    self._json({**store.settings(), "workspace": str(workspace.root)})
                case ("PUT", "settings"):
                    self._json({**store.save_settings(self._body()), "workspace": str(workspace.root)})
                case ("GET", "renders"):
                    self._json([render_view(r) for r in store.renders(query.get("script"))])
                case ("POST", "renders"):
                    body = self._body()
                    commands = engine_commands(store.settings())
                    if body["engine"] not in commands:
                        raise ValueError(f"engine {body['engine']!r} is not installed; set the engines folder in Settings")
                    check = check_script(workspace.script_path(body["script"]))
                    if not check["ok"]:
                        raise ValueError(check["error"])
                    render_id = runner.start(commands[body["engine"]], body["script"], body["engine"],
                                             body.get("language") or store.settings()["language"])
                    self._json(render_view(store.render(render_id)))
                case ("GET", "renders", render_id):
                    self._json(render_view(store.render(int(render_id))))
                case ("POST", "renders", render_id, "stop"):
                    runner.stop(int(render_id))
                    self._json({"ok": True})
                case ("DELETE", "renders", render_id):
                    if runner.live(int(render_id)):
                        raise ValueError("stop the render before deleting it")
                    shutil.rmtree(workspace.renders / str(int(render_id)), ignore_errors=True)
                    store.delete_render(int(render_id))
                    self._json({"ok": True})
                case ("GET", "renders", render_id, filename):
                    path = (workspace.renders / str(int(render_id)) / filename).resolve()
                    if not path.is_relative_to(workspace.renders) or not path.is_file():
                        raise KeyError(filename)
                    self._file(path)
                case _:
                    raise KeyError("/".join(route[1:]))

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_DELETE(self):
            self._dispatch("DELETE")

    return Handler


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="castscript web", description="Open the castscript web app.")
    parser.add_argument("--workdir", type=Path, default=Path.home() / "castscript",
                        help="workspace with scripts, voices, renders, and the database (default: ~/castscript)")
    parser.add_argument("--port", type=int, default=PORT, help=f"port on 127.0.0.1 (default: {PORT})")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = parser.parse_args(argv)

    workspace = Workspace(args.workdir.expanduser().resolve())
    store = Store(workspace.root / "castscript.db")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(workspace, store, Runner(store, workspace)))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"castscript web: {url}  workspace {workspace.root}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
