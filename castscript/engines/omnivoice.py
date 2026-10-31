"""OmniVoice via the omnivoice package (https://github.com/k2-fsa/OmniVoice)."""

from __future__ import annotations

import sys

import numpy as np
import torch

from ..script import Voice
from . import torch_device

MODEL = "k2-fsa/OmniVoice"
SEED = 42


class OmniVoiceEngine:
    events = {"笑": "[laughter]", "叹气": "[sigh]"}

    def __init__(self, language: str):
        from omnivoice import OmniVoice

        device = torch_device()
        self.model = OmniVoice.from_pretrained(MODEL, device_map=device, dtype=torch.float32 if device == "cpu" else torch.float16)
        self.sample_rate = self.model.sampling_rate
        self.language = language
        self._prompts = {}

    def synthesize(self, text: str, voice: Voice, emotion: str | None) -> np.ndarray:
        if emotion:
            print(f"warning: OmniVoice cannot apply emotion '{emotion}' to voice '{voice.name}'; ignoring", file=sys.stderr)
        torch.manual_seed(SEED)
        if voice.kind == "ref":
            if voice.name not in self._prompts:
                self._prompts[voice.name] = self.model.create_voice_clone_prompt(ref_audio=voice.value, ref_text=voice.ref_text)
            audios = self.model.generate(text=text, language=self.language, voice_clone_prompt=self._prompts[voice.name])
        elif voice.kind == "design":
            # OmniVoice accepts only its attribute vocabulary here, e.g. "男，老年，低音调".
            audios = self.model.generate(text=text, language=self.language, instruct=voice.value)
        else:
            raise ValueError(f"OmniVoice has no preset voices; voice '{voice.name}' uses preset")
        return np.asarray(audios[0], dtype=np.float32)
