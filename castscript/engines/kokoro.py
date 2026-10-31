"""Kokoro-82M via the kokoro package (https://github.com/hexgrad/kokoro)."""

from __future__ import annotations

import sys

import numpy as np

from ..script import Voice

LANG_CODES = {"en": "a", "zh": "z", "ja": "j", "es": "e", "fr": "f", "hi": "h", "it": "i", "pt": "p"}


class KokoroEngine:
    events = {}
    sample_rate = 24000

    def __init__(self, language: str):
        from kokoro import KPipeline

        if language not in LANG_CODES:
            raise ValueError(f"Kokoro supports languages {sorted(LANG_CODES)}, not '{language}'")
        self.pipeline = KPipeline(lang_code=LANG_CODES[language], repo_id="hexgrad/Kokoro-82M")

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if voice.kind != "preset":
            raise ValueError(f"Kokoro only has preset voices; voice '{voice.name}' uses {voice.kind}")
        if emotion:
            print(f"warning: Kokoro cannot apply emotion '{emotion}' to voice '{voice.name}'; ignoring", file=sys.stderr)
        return np.concatenate([r.audio.numpy() for r in self.pipeline(text, voice=voice.value)]).astype(np.float32)
