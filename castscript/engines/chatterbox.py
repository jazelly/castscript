"""Chatterbox Multilingual V3 via the chatterbox-tts package (https://github.com/resemble-ai/chatterbox)."""

from __future__ import annotations

import sys

import numpy as np
import torch

from ..script import Voice
from . import torch_device

SEED = 42


class ChatterboxEngine:
    events = {}

    def __init__(self, language: str):
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        self.model = ChatterboxMultilingualTTS.from_pretrained(device=torch_device(), t3_model="v3")
        self.sample_rate = self.model.sr
        self.language = language
        self._ref = None

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if voice.kind != "ref":
            raise ValueError(f"Chatterbox only clones ref voices; voice '{voice.name}' uses {voice.kind}")
        if emotion:
            print(f"warning: Chatterbox cannot apply emotion '{emotion}' to voice '{voice.name}'; ignoring", file=sys.stderr)
        # Conditioning on a reference clip is slow, so redo it only when the speaker changes.
        if self._ref != voice.value:
            self.model.prepare_conditionals(voice.value)
            self._ref = voice.value
        torch.manual_seed(SEED)
        return self.model.generate(text, language_id=self.language).squeeze(0).numpy().astype(np.float32)
