"""Pocket TTS via the pocket-tts package (https://github.com/kyutai-labs/pocket-tts)."""

from __future__ import annotations

import sys

import numpy as np
import torch

from ..script import Voice

LANGUAGES = {"en": "english", "fr": "french", "de": "german", "pt": "portuguese", "it": "italian", "es": "spanish", "nl": "dutch"}
SEED = 42


class PocketEngine:
    events = {}

    def __init__(self, language: str):
        from pocket_tts import TTSModel

        if language not in LANGUAGES:
            raise ValueError(f"Pocket TTS supports languages {sorted(LANGUAGES)}, not '{language}'")
        self.model = TTSModel.load_model(language=LANGUAGES[language])
        self.sample_rate = self.model.sample_rate
        self._states = {}

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if voice.kind == "design":
            raise ValueError(f"Pocket TTS has no voice design; voice '{voice.name}' uses design")
        if emotion:
            print(f"warning: Pocket TTS cannot apply emotion '{emotion}' to voice '{voice.name}'; ignoring", file=sys.stderr)
        # A preset is a built-in voice name such as "alba"; a ref is a WAV path. Both load the same way.
        if voice.name not in self._states:
            self._states[voice.name] = self.model.get_state_for_audio_prompt(voice.value)
        torch.manual_seed(SEED)
        return self.model.generate_audio(self._states[voice.name], text).numpy().astype(np.float32)
