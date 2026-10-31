"""Parse castscript files. See SPEC.md."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

LINE_PAUSE = 0.4
PARAGRAPH_PAUSE = 0.8
SCENE_PAUSE = 2.0
EVENTS = ("笑", "叹气", "咳嗽", "清嗓子")

VOICE_RE = re.compile(r"^@voice\s+(?P<name>[^=]+?)\s*=\s*(?P<kind>ref|design|preset)\s*[:：]\s*(?P<value>.+)$")
PAUSE_RE = re.compile(r"^<(?:pause|停顿)\s+(?P<seconds>\d+(?:\.\d+)?)\s*(?:s|秒)?>$")
LINE_RE = re.compile(
    r"^(?P<speaker>[^：:（()）]+?)\s*(?:[（(](?P<emotion>[^）)]*)[）)])?\s*[：:]\s*(?P<text>.+)$"
)
EVENT_RE = re.compile(r"\[(?:" + "|".join(EVENTS) + r")\]")


class ScriptError(ValueError):
    pass


@dataclass
class Voice:
    name: str
    kind: str  # ref | design | preset
    value: str  # resolved WAV path, description, or preset name
    ref_text: str | None = None


@dataclass
class Line:
    lineno: int
    speaker: str
    emotion: str | None
    text: str
    pause_after: float = 0.0


@dataclass
class Script:
    voices: dict[str, Voice]
    lines: list[Line]


def convert_events(text: str, tags: dict[str, str]) -> str:
    """Replace each vocal event with the engine's tag for it, dropping events the engine lacks."""
    return EVENT_RE.sub(lambda m: tags.get(m[0][1:-1], ""), text).strip()


def strip_events(text: str) -> str:
    return convert_events(text, {})


def parse(path: Path) -> Script:
    voices: dict[str, Voice] = {}
    lines: list[Line] = []
    explicit_pause = False

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = raw.strip()
        if s.startswith("#"):
            continue
        if not s:
            if lines and not explicit_pause:
                lines[-1].pause_after = max(lines[-1].pause_after, PARAGRAPH_PAUSE)
            continue
        if s == "---":
            if lines and not explicit_pause:
                lines[-1].pause_after = max(lines[-1].pause_after, SCENE_PAUSE)
            continue
        if m := PAUSE_RE.match(s):
            if not lines:
                raise ScriptError(f"{path}:{lineno}: pause before the first line")
            lines[-1].pause_after = float(m["seconds"])
            explicit_pause = True
            continue
        if m := VOICE_RE.match(s):
            voices[m["name"]] = _voice(path, lineno, m["name"], m["kind"], m["value"].strip(), voices)
            continue
        if s.startswith("@voice"):
            raise ScriptError(f"{path}:{lineno}: invalid voice definition (KIND must be ref, design, or preset): {s}")
        if m := LINE_RE.match(s):
            speaker = m["speaker"].strip()
            if speaker not in voices:
                raise ScriptError(f"{path}:{lineno}: voice '{speaker}' is not defined")
            emotion = (m["emotion"] or "").strip() or None
            lines.append(Line(lineno, speaker, emotion, m["text"].strip(), LINE_PAUSE))
            explicit_pause = False
            continue
        raise ScriptError(f"{path}:{lineno}: cannot parse line: {s}")

    if lines:
        lines[-1].pause_after = 0.0
    return Script(voices, lines)


def _voice(path: Path, lineno: int, name: str, kind: str, value: str, voices: dict) -> Voice:
    if name in voices:
        raise ScriptError(f"{path}:{lineno}: voice '{name}' is defined twice")
    if kind != "ref":
        return Voice(name, kind, value)
    wav = (path.parent / value).resolve()
    transcript = wav.with_suffix(".txt")
    if not wav.is_file():
        raise ScriptError(f"{path}:{lineno}: reference audio not found: {wav}")
    if not transcript.is_file():
        raise ScriptError(f"{path}:{lineno}: reference transcript not found: {transcript}")
    return Voice(name, kind, str(wav), transcript.read_text(encoding="utf-8").strip())
