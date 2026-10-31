"""dots.tts via the dots.tts package (https://github.com/studio-dots-ai/dots.tts)."""

from __future__ import annotations

import sys

import numpy as np
import torch

from ..script import Voice

MODEL = "dots-studio/dots.tts-soar"
SEED = 42


class DotsEngine:
    events = {}

    def __init__(self, language: str):
        from dots_tts.runtime import DotsTtsRuntime

        # Upstream runs on CUDA, or on CPU (single-threaded, float32 only) without it.
        precision = "bfloat16" if torch.cuda.is_available() else "float32"
        self.runtime = DotsTtsRuntime.from_pretrained(MODEL, precision=precision)
        self.sample_rate = self.runtime.sample_rate
        self.language = language.upper()

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if voice.kind != "ref":
            raise ValueError(f"dots.tts only clones ref voices; voice '{voice.name}' uses {voice.kind}")
        if emotion:
            print(f"warning: dots.tts cannot apply emotion '{emotion}' to voice '{voice.name}'; ignoring", file=sys.stderr)
        torch.manual_seed(SEED)
        result = self.runtime.generate(
            text=text, prompt_audio_path=voice.value, prompt_text=voice.ref_text, language=self.language
        )
        return result["audio"].float().cpu().squeeze().numpy()
