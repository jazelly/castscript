"""KittenTTS 2 via the kittenml package (https://github.com/KittenML/KittenTTS)."""

from __future__ import annotations

import sys

import numpy as np

from ..script import Voice

MODEL = "KittenML/kitten-tts-2"
SEED = 42


class KittenEngine:
    events = {"笑": "<laugh>", "叹气": "<sigh>"}

    def __init__(self, language: str):
        from kittenml import KittenTTS
        from kittenml.kittentts2.text import EXPRESSION_TAGS

        # "auto" picks MLX on Apple Silicon and Torch elsewhere.
        self.model = KittenTTS(MODEL, backend="auto")
        self.sample_rate = self.model.sample_rate
        self._emotions = EXPRESSION_TAGS
        # Kitten's text normalizer is English-only and mangles other languages.
        self._normalize = language == "en"

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        # Kitten recognizes only a fixed list of English emotion tags, e.g. "angry" or "sad".
        if emotion in self._emotions:
            text = f"[{emotion}] {text}"
        elif emotion:
            print(f"warning: Kitten emotion must be one of {sorted(self._emotions)}; ignoring '{emotion}'", file=sys.stderr)
        kwargs = {"normalize": self._normalize, "advanced": {"seed": SEED}}
        if voice.kind == "ref":
            audio = self.model.generate(text, reference=voice.value, reference_text=voice.ref_text, **kwargs)
        elif voice.kind == "preset":
            audio = self.model.generate(text, voice=voice.value, **kwargs)
        else:
            raise ValueError(f"Kitten has no voice design; voice '{voice.name}' uses design")
        return np.asarray(audio, dtype=np.float32)
