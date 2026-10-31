"""Render a parsed script with an engine into WAV, MP3, and SRT."""

from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from .script import Script, convert_events, strip_events

MAX_CHARS = 150
SENTENCE_RE = re.compile(r"(?<=[。！？!?…])")


def split_text(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    chunks, current = [], ""
    for sentence in filter(None, SENTENCE_RE.split(text)):
        if current and len(current) + len(sentence) > MAX_CHARS:
            chunks.append(current)
            current = ""
        current += sentence
    return chunks + [current] if current else chunks


def _srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def render(script: Script, engine, out_base: Path) -> None:
    sr = engine.sample_rate
    pieces: list[np.ndarray] = []
    cues: list[tuple[float, float, str]] = []
    cursor = 0.0
    started = time.perf_counter()

    for i, line in enumerate(script.lines, 1):
        voice = script.voices[line.speaker]
        text = convert_events(line.text, engine.events)
        line_started = time.perf_counter()
        # A line of only unsupported vocal events is empty; it keeps just its pause.
        for chunk in split_text(text) if text else []:
            audio = engine.synthesize(chunk, voice, line.emotion)
            duration = audio.size / sr
            if subtitle := strip_events(chunk):
                cues.append((cursor, cursor + duration, subtitle))
            pieces.append(audio)
            cursor += duration
        pieces.append(np.zeros(round(line.pause_after * sr), dtype=np.float32))
        cursor += line.pause_after
        took = time.perf_counter() - line_started
        print(f"[{i}/{len(script.lines)}] line {line.lineno} {line.speaker}: at {cursor:.1f}s, took {took:.1f}s", flush=True)

    out_base.parent.mkdir(parents=True, exist_ok=True)
    wav, mp3, srt = (out_base.with_suffix(s) for s in (".wav", ".mp3", ".srt"))
    sf.write(wav, np.concatenate(pieces), sr, subtype="PCM_16")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", "loudnorm=I=-16:TP=-1.5", "-b:a", "128k", str(mp3)],
        check=True,
    )
    srt.write_text(
        "\n".join(f"{n}\n{_srt_time(a)} --> {_srt_time(b)}\n{t}\n" for n, (a, b, t) in enumerate(cues, 1)),
        encoding="utf-8",
    )
    print(f"done: {cursor:.1f}s audio in {time.perf_counter() - started:.1f}s -> {mp3}, {srt}")
